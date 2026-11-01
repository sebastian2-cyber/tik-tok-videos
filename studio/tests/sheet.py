import sys,glob,os
from PIL import Image
slug=sys.argv[1]; which=sys.argv[2] if len(sys.argv)>2 else "mid"
ims=[]
for d in sorted(glob.glob(f"/home/user/tiktok-studio/cache/{slug}/shot_*_still")):
    fs=sorted(glob.glob(d+"/still_*.jpg")); ims.append(Image.open(fs[len(fs)//2] if which=="mid" else fs[-1]))
w,h=270,480; cols=5; rows=(len(ims)+cols-1)//cols
sheet=Image.new("RGB",(w*cols,h*rows),"black")
for i,im in enumerate(ims): sheet.paste(im.resize((w,h)),((i%cols)*w,(i//cols)*h))
sheet.save(f"/home/user/tiktok-studio/tests/sheet_{slug}_{which}.jpg"); print(len(ims))
