"""Build a finished TikTok video from videos/<slug>/story.py

usage: python3 make_video.py <slug> [--preview] [--only 3,4] [--still]
  --preview   low samples (fast check)
  --still     render only the middle frame of each shot (contact sheet for checking)
"""
import sys, os, json, math, subprocess, importlib.util, time, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import audio as A

ROOT = os.path.dirname(os.path.abspath(__file__))
FPS = 24
OUT_W, OUT_H = 1080, 1920
VOICE_DELAY = 0.12
GAP = 0.38              # pause after each sentence
HL = (220, 130, 104)    # salmon highlight like the original
TXT = (255, 253, 242)


def load_story(slug):
    p = os.path.join(ROOT, "videos", slug, "story.py")
    spec = importlib.util.spec_from_file_location("story", p)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(p))
    spec.loader.exec_module(m)
    return m


def timeline(story):
    """Voice per shot -> durations in frames."""
    out = []
    for i, s in enumerate(story.SHOTS):
        wav = A.tts(s["text"], **story.VOICE) if s.get("text") else None
        speech = A.duration(wav) if wav else 0
        dur = s.get("dur") or (VOICE_DELAY + speech + GAP + s.get("pad", 0))
        out.append(dict(i=i, wav=wav, speech=speech, frames=max(int(round(dur * FPS)), 20)))
    return out


# ------------------------------------------------------------------ subtitles
def wrap(words, font, maxw, d):
    lines, cur = [], []
    for w in words:
        test = " ".join(x for x, _ in cur + [(w[0], 0)])
        if cur and d.textlength(test, font=font) > maxw:
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    # balance two lines like the original (shorter top line is fine)
    if len(lines) == 2 and len(lines[1]) == 1 and len(lines[0]) > 2:
        lines[1].insert(0, lines[0].pop())
    return lines


def subtitle_png(text, hl, path):
    font = ImageFont.truetype(os.path.join(ROOT, "fonts", "Montserrat-800.ttf"), 54)
    im = Image.new("RGBA", (OUT_W, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hl_words = set()
    for h in hl:
        hl_words.update(re.sub(r"[^\wäöüÄÖÜß\-]", "", w).lower() for w in h.split())
    words = []
    for w in text.split():
        core = re.sub(r"[^\wäöüÄÖÜß\-]", "", w).lower()
        words.append((w, core in hl_words))
    lines = wrap(words, font, OUT_W * 0.66, d)
    lh = 64
    y0 = 200 - lh * len(lines) / 2
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    space = d.textlength(" ", font=font)
    runs = []
    for li, ln in enumerate(lines):
        total = sum(d.textlength(w, font=font) for w, _ in ln) + space * (len(ln) - 1)
        x = (OUT_W - total) / 2
        y = y0 + li * lh
        for w, h in ln:
            runs.append((x, y, w, h))
            x += d.textlength(w, font=font) + space
    for x, y, w, h in runs:
        sd.text((x + 2, y + 4), w, font=font, fill=(0, 0, 0, 200), stroke_width=4, stroke_fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))
    im = Image.alpha_composite(im, shadow)
    d = ImageDraw.Draw(im)
    for x, y, w, h in runs:
        d.text((x, y), w, font=font, fill=HL if h else TXT, stroke_width=2, stroke_fill=(30, 26, 26))
    im.save(path)


# ------------------------------------------------------------------ audio mix
def mix(story, tl, path):
    total = sum(t["frames"] for t in tl) / FPS + 0.6
    n = int(total * A.SR)
    voice = np.zeros(n)
    fx = np.zeros(n)
    t0 = 0.0
    for t, s in zip(tl, story.SHOTS):
        if t["wav"]:
            a = A.read_wav(t["wav"])
            p = int((t0 + VOICE_DELAY) * A.SR)
            A._add(voice, p, a)
        for kind, at, vol in [(x + (1.0,))[:3] for x in s.get("sfx", [])]:
            a = A.sfx(kind) * vol
            p = int((t0 + at) * A.SR)
            A._add(fx, p, a)
        t0 += t["frames"] / FPS
    mus = A.music(total, bpm=getattr(story, "BPM", 96), seed=getattr(story, "SEED", 0))
    # duck music under the voice
    env = np.convolve(np.abs(voice), np.ones(2205) / 2205, "same")
    duck = 1 - 0.45 * np.clip(env / (env.max() + 1e-9) * 4, 0, 1)
    vpk = np.abs(voice).max() + 1e-9
    out = voice / vpk * A.db(-3) + mus * A.db(-21) * duck + fx * A.db(-10)
    out /= max(1.0, np.abs(out).max() / A.db(-1))
    A.write_wav(path, out)
    return total


# ------------------------------------------------------------------ main
def run(slug, preview=False, only=None, still=False):
    story = load_story(slug)
    work = os.path.join(ROOT, "cache", slug)
    os.makedirs(work, exist_ok=True)
    tl = timeline(story)
    json.dump(tl, open(os.path.join(work, "timeline.json"), "w"), indent=1)
    total = sum(t["frames"] for t in tl)
    print(f"{len(tl)} shots, {total} frames, {total / FPS:.1f}s", flush=True)
    for t in tl:
        if only and t["i"] not in only:
            continue
        d = os.path.join(work, f"shot_{t['i']:02d}" + ("_still" if still else ""))
        if not still and not preview and os.path.exists(os.path.join(d, "DONE")):
            continue
        st = time.time()
        args = [sys.executable, os.path.join(ROOT, "lib", "render_shot.py"), slug, str(t["i"]), str(t["frames"]), d]
        if preview:
            args.append("--preview")
        if still:
            args.append("--still")
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit(f"shot {t['i']} failed")
        print(f"shot {t['i']:02d} ok ({t['frames']} fr, {time.time() - st:.0f}s)", flush=True)
    if still or only:
        return
    # video track
    lst = os.path.join(work, "frames.txt")
    with open(lst, "w") as f:
        for t in tl:
            d = os.path.join(work, f"shot_{t['i']:02d}")
            for k in range(1, t["frames"] + 1):
                f.write(f"file '{d}/f_{k:04d}.jpg'\nduration {1 / FPS:.6f}\n")
    wav = os.path.join(work, "mix.wav")
    mix(story, tl, wav)
    subs, t0 = [], 0.0
    for t, s in zip(tl, story.SHOTS):
        dur = t["frames"] / FPS
        if s.get("text"):
            p = os.path.join(work, f"sub_{t['i']:02d}.png")
            subtitle_png(s.get("sub", s["text"]), s.get("hl", []), p)
            subs.append((p, t0, t0 + dur))
        t0 += dur
    inputs = ["-f", "concat", "-safe", "0", "-i", lst, "-i", wav]
    for p, _, _ in subs:
        inputs += ["-i", p]
    chain = f"[0:v]fps={FPS},scale={OUT_W}:{OUT_H}:flags=lanczos,unsharp=5:5:0.6[v0];"
    for k, (p, a, b) in enumerate(subs):
        chain += f"[v{k}][{k + 2}:v]overlay=0:{int(OUT_H * 0.815) - 200}:enable='between(t,{a:.3f},{b - 0.01:.3f})'[v{k + 1}];"
    chain = chain.rstrip(";")
    out_dir = os.path.join(ROOT, "videos", slug)
    out = os.path.join(out_dir, f"{slug}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", chain, "-map", f"[v{len(subs)}]",
                    "-map", "1:a", "-af", "loudnorm=I=-14:TP=-1.5:LRA=7", "-ar", "44100", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
                   check=True)
    print("DONE", out)


if __name__ == "__main__":
    a = sys.argv[1:]
    only = None
    if "--only" in a:
        only = {int(x) for x in a[a.index("--only") + 1].split(",")}
    run(a[0], preview="--preview" in a, only=only, still="--still" in a)
