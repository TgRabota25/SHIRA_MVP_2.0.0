from pathlib import Path
import sys,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from recognition import native_limits,scaled,read_frame,orient
if __name__=='__main__':
 native_limits()
 import cv2
 source,seconds,destination=sys.argv[1:4];cap=cv2.VideoCapture(source)
 try:
  if not cap.isOpened():raise ValueError('Не удалось открыть видео')
  orient(cap)
  ok,frame=read_frame(cap,max(0,float(seconds)))
  if not ok:raise ValueError('Кадр не прочитан')
  frame=scaled(frame,2560);ok,encoded=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,95])
  if not ok:raise ValueError('Ошибка кодирования')
  Path(destination).write_bytes(encoded.tobytes())
 finally:cap.release()
