import json
from pathlib import Path
from config import data_dir,atomic_json

def _lanczos():
 from PIL import Image
 return getattr(Image,'Resampling',Image).LANCZOS

def strip_white(im):
 # Убирает белый фон вокруг иконки (заливка от углов), внутренние белые области не трогает.
 from PIL import Image,ImageChops,ImageDraw
 im=im.convert('RGBA')
 if im.getpixel((0,0))[3]<10:return im
 rgb=im.convert('RGB');w,h=rgb.size;sentinel=(255,0,255)
 for point in ((0,0),(w-1,0),(0,h-1),(w-1,h-1)):
  if min(rgb.getpixel(point))>225:ImageDraw.floodfill(rgb,point,sentinel,thresh=36)
 diff=ImageChops.difference(rgb,Image.new('RGB',rgb.size,sentinel)).convert('L')
 im.putalpha(diff.point(lambda v:0 if v<3 else 255));return im

def brand_icon(path,size):
 from PIL import Image
 with Image.open(path) as src:im=strip_white(src.copy())
 return im.resize((size,size),_lanczos())

def render_image(path,angle=0,size=None):
 from PIL import Image
 with Image.open(path) as src:im=src.convert('RGB')
 if angle%360:im=im.rotate(-(angle%360),expand=True,resample=Image.BICUBIC)
 if size:im.thumbnail(size,_lanczos())
 return im

class Rotations:
 # Поворот кадра хранится отдельно для каждого видео и переживает перезапуск.
 def __init__(self):
  self.path=Path(data_dir())/'rotations-v2.json';self.data={}
  try:
   loaded=json.loads(self.path.read_text('utf-8'))
   if isinstance(loaded,dict):self.data={str(k):int(v)%360 for k,v in loaded.items()}
  except Exception:pass
 def get(self,key):return int(self.data.get(str(key),0))%360
 def add(self,key,delta):
  value=(self.get(key)+int(delta))%360
  if value:self.data[str(key)]=value
  else:self.data.pop(str(key),None)
  try:atomic_json(self.path,self.data)
  except Exception:pass
  return value
