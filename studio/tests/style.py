import sys, time; sys.path.insert(0,"/home/user/tiktok-studio/lib")
from studio import *
import bpy
sc=reset("final")
world("#d7cfc4",0.9)
room(5,5,3.0,wall="#e6c4b2",lower=tiled_mat(tile_tex("#a9d3c0","#8fbfa9",4,256,256)),lower_h=1.3)
sun((55,0,30),2.5)
area((1.5,-2,2.8),3,250,target=(0,0,1))
m=Char("man","suit",(-0.45,0.3,0),rot=-15,expr="neutral",seed=2)
m.pose(1,arm_l=(0,-6,0),arm_r=(-60,10,0),head=(0,0,10))
c=Char("cop","police",(0.6,0.6,0),rot=25,expr="angry",mustache=True,seed=5)
c.pose(1,arm_l=(0,-6,0),arm_r=(0,6,0),head=(0,0,-12))
camera((0.4,-3.2,1.75),(0.05,0.4,1.65),lens=30,shake_amt=0)
m.walk(1,40,(-0.45,0.3,0),(-0.2,0.0,0))
sc.frame_start=1;sc.frame_end=8;sc.render.filepath="/home/user/tiktok-studio/tests/anim/f_";t=time.time();bpy.ops.render.render(animation=True);print("ANIM per frame",round((time.time()-t)/8,2))
for eng in sys.argv[1:]:
    sc.render.engine=eng
    if eng=="BLENDER_WORKBENCH":
        sh=sc.display.shading; sh.light="STUDIO"; sh.color_type="TEXTURE"; sh.show_shadows=True; sh.show_cavity=True
    sc.render.filepath=f"/home/user/tiktok-studio/tests/style_{eng}.jpg"; t=time.time(); bpy.ops.render.render(write_still=True); print(eng,round(time.time()-t,1))
