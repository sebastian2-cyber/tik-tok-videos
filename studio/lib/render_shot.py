"""Render one shot of a story: render_shot.py <slug> <idx> <frames> <outdir> [--preview] [--still]"""
import sys, os, importlib.util
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio as S
import bpy

slug, idx, frames, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
preview, still = "--preview" in sys.argv, "--still" in sys.argv
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(root, "videos", slug, "story.py")
sys.path.insert(0, os.path.dirname(p))
spec = importlib.util.spec_from_file_location("story", p)
story = importlib.util.module_from_spec(spec)
spec.loader.exec_module(story)

shot = story.SHOTS[idx]
S.reset("preview" if preview else "final")
shot["scene"](frames)
sc = bpy.context.scene
os.makedirs(out, exist_ok=True)
if still:
    for f in sorted({1, frames // 2, frames}):
        sc.frame_set(f)
        sc.render.filepath = os.path.join(out, f"still_{f:04d}.jpg")
        bpy.ops.render.render(write_still=True)
else:
    sc.frame_start, sc.frame_end = 1, frames
    sc.render.filepath = os.path.join(out, "f_")
    bpy.ops.render.render(animation=True)
    open(os.path.join(out, "DONE"), "w").write("ok")
