import sys, time; sys.path.insert(0,"/home/user/tiktok-studio/lib")
from studio import *
import bpy
sc=reset("final")
world("#d7cfc4",0.9)
room(5,5,3.0,wall="#e6c4b2",lower=tiled_mat(tile_tex("#a9d3c0","#8fbfa9",4,256,256)),lower_h=1.3)
sun((55,0,30),2.5); area((1.5,-2,2.8),3,250,target=(0,0,1))
m=Char("man","suit",(-0.45,0.3,0),rot=-15,seed=2); c=Char("cop","police",(0.6,0.6,0),rot=25,expr="angry",mustache=True,seed=5)
camera((0.4,-3.2,1.75),(0.05,0.4,1.65),lens=30,shake_amt=0)
cy=sc.cycles
import os; print("threads",sc.render.threads, os.cpu_count())
def run(label, **kw):
    for k,v in kw.items():
        if k=="res": sc.render.resolution_percentage=v
        else: setattr(cy,k,v)
    sc.render.filepath=f"/home/user/tiktok-studio/tests/b_{label}.jpg"
    t=time.time(); bpy.ops.render.render(write_still=True); print(label, round(time.time()-t,2), flush=True)
run("warm")
run("base")
run("s8", samples=8)
run("s8_fastgi", use_fast_gi=True, ao_bounces_render=1)
run("s8_fastgi_b2", max_bounces=2, diffuse_bounces=1)
run("s8_fastgi_b2_75pct", res=75)
cy.use_denoising=False; run("nodenoise_75")
