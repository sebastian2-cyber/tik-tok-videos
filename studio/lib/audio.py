"""Voice (Edge neural TTS), synthesized music bed and sound effects."""
import asyncio, os, ssl, subprocess, wave, json, hashlib
import numpy as np

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", "tts")
os.makedirs(CACHE, exist_ok=True)
VOICE = "de-DE-ConradNeural"
RATE = "+6%"


def tts(text, voice=VOICE, rate=RATE, pitch="-2Hz"):
    """Return path to a 44.1k mono wav of `text` (cached), trimmed of leading/trailing silence."""
    import edge_tts, edge_tts.communicate as c
    c._SSL_CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt")
    spoken = text.replace("„", "").replace("“", "").replace('"', "")
    key = hashlib.md5(f"{spoken}|{voice}|{rate}|{pitch}".encode()).hexdigest()[:14]
    wav = os.path.join(CACHE, key + ".wav")
    if os.path.exists(wav):
        return wav
    mp3 = wav[:-4] + ".mp3"
    for attempt in range(4):
        try:
            asyncio.run(edge_tts.Communicate(spoken, voice, rate=rate, pitch=pitch,
                                             proxy=os.environ.get("HTTPS_PROXY")).save(mp3))
            break
        except Exception:
            if attempt == 3:
                raise
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                    "highpass=f=70,acompressor=threshold=-18dB:ratio=2.5:attack=5:release=80,"
                    "equalizer=f=180:t=q:w=1:g=2",
                    "-ar", str(SR), "-ac", "1", wav], check=True)
    return wav


def read_wav(p):
    with wave.open(p) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
    return a


def write_wav(p, a):
    a = np.clip(a, -1, 1)
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((a * 32767).astype(np.int16).tobytes())


def duration(p):
    return len(read_wav(p)) / SR


# ------------------------------------------------------------------ synthesis helpers
def _env(n, a=0.005, r=0.3):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / r)
    return e


def _note(freq, dur, kind="pluck", vol=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "pluck":  # soft pizzicato
        s = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t) + 0.1 * np.sin(6 * np.pi * freq * t)
        s *= _env(n, 0.004, 0.18)
    elif kind == "bass":
        s = np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(4 * np.pi * freq * t)
        s *= _env(n, 0.01, 0.35)
    elif kind == "pad":
        s = sum(np.sin(2 * np.pi * freq * (1 + d) * t) for d in (-0.003, 0, 0.004)) / 3
        s *= np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.4).clip(0)
    elif kind == "bell":
        s = np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2.76 * t)
        s *= _env(n, 0.002, 0.5)
    return s * vol


def _add(out, pos, a):
    if pos >= len(out) or pos < 0:
        return
    k = min(len(a), len(out) - pos)
    out[pos:pos + k] += a[:k]


def music(seconds, bpm=96, seed=0):
    """Quirky, quiet 'deadpan crime' bed: walking pizzicato bass + sparse bells in D minor."""
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    out = np.zeros(int((seconds + 2) * SR))
    # D minor walking pattern
    bass_prog = [[146.8, 174.6, 220.0, 174.6], [130.8, 155.6, 196.0, 155.6],
                 [116.5, 146.8, 174.6, 146.8], [110.0, 138.6, 164.8, 220.0]]
    mel = [587.3, 698.5, 880.0, 783.99, 659.3, 587.3, 523.3, 440.0]
    t = 0.0
    bar = 0
    while t < seconds:
        prog = bass_prog[bar % 4]
        for i, f in enumerate(prog):
            pos = int((t + i * beat) * SR)
            nb = _note(f / 2, beat * 0.95, "pluck", 0.55)
            _add(out, pos, nb)
            if i % 2 == 1:
                ch = _note(f, beat * 0.4, "pluck", 0.18)
                pos2 = int((t + i * beat + beat * 0.5) * SR)
                _add(out, pos2, ch)
        if bar % 2 == 1:
            for k in range(2):
                f = mel[rng.integers(len(mel))]
                pos = int((t + (k * 2 + 1) * beat) * SR)
                nb = _note(f, 1.2, "bell", 0.08)
                _add(out, pos, nb)
        pad = _note(prog[0], beat * 4, "pad", 0.06)
        pos = int(t * SR)
        _add(out, pos, pad)
        t += beat * 4
        bar += 1
    out = out[:int(seconds * SR)]
    fade = int(1.0 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.abs(out).max() + 1e-9)


def sfx(kind):
    n = lambda d: int(d * SR)
    t = lambda d: np.arange(n(d)) / SR
    rng = np.random.default_rng(1)
    if kind == "whoosh":
        d = 0.45
        noise = rng.standard_normal(n(d))
        # crude band-pass sweep via moving average of differenced noise
        k = np.convolve(noise, np.ones(12) / 12, "same")
        s = (noise - k) * np.sin(np.pi * t(d) / d) ** 2
        return s * 0.25
    if kind == "boom":  # impact for the big signs
        d = 0.9
        f = 70 * np.exp(-t(d) * 3) + 35
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t(d) * 4)
        s += rng.standard_normal(n(d)) * np.exp(-t(d) * 30) * 0.3
        return s * 0.9
    if kind == "siren":
        d = 2.4
        f = 750 + 250 * np.sign(np.sin(2 * np.pi * 1.2 * t(d)))
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
        return s * np.minimum(1, t(d) / 0.3) * np.minimum(1, (d - t(d)) / 0.4)
    if kind == "gavel":
        out = np.zeros(n(0.8))
        for i, at in enumerate((0, 0.22)):
            d = 0.25
            s = rng.standard_normal(n(d)) * np.exp(-t(d) * 40) + np.sin(2 * np.pi * 180 * t(d)) * np.exp(-t(d) * 25)
            out[n(at):n(at) + len(s)] += s * 0.6
        return out
    if kind == "door":
        d = 0.6
        s = np.sin(2 * np.pi * 90 * t(d)) * np.exp(-t(d) * 9) + rng.standard_normal(n(d)) * np.exp(-t(d) * 25) * 0.4
        return s * 0.7
    if kind == "pop":
        d = 0.15
        return np.sin(2 * np.pi * (900 - 3000 * t(d)) * t(d)) * np.exp(-t(d) * 30) * 0.4
    if kind == "beep":
        d = 0.5
        out = np.zeros(n(d))
        for at in (0, 0.18):
            s = np.sin(2 * np.pi * 2200 * t(0.09)) * 0.25
            out[n(at):n(at) + len(s)] += s
        return out
    if kind == "jail":  # cell door clang
        d = 1.2
        s = sum(np.sin(2 * np.pi * f * t(d)) * np.exp(-t(d) * dk) for f, dk in ((220, 3), (563, 5), (1210, 8), (97, 4)))
        s += rng.standard_normal(n(d)) * np.exp(-t(d) * 40) * 0.5
        return s * 0.35
    if kind == "phone":
        d = 1.4
        s = (np.sin(2 * np.pi * 440 * t(d)) + np.sin(2 * np.pi * 480 * t(d))) * 0.12
        s *= (np.sin(2 * np.pi * 20 * t(d)) > 0) * (t(d) < 1.0)
        return s
    raise ValueError(kind)


def db(x):
    return 10 ** (x / 20)
