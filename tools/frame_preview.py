from pathlib import Path
import sys,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from recognition import native_limits,scaled
if __name__=='__main__':
 native_limits()
 import cv2
 source,seconds,destination=sys.argv[1:4];cap=cv2.VideoCapture(source)
 try:
  if not cap.isOpened():raise ValueError('Не удалось открыть видео')
  cap.set(cv2.CAP_PROP_POS_MSEC,max(0,float(seconds))*1000);ok,frame=cap.read()
  if not ok:raise ValueError('Кадр не прочитан')
  frame=scaled(frame,1600);ok,encoded=cv2.imencode('.jpg',frame)
  if not ok:raise ValueError('Ошибка кодирования')
  Path(destination).write_bytes(encoded.tobytes())
 finally:cap.release()
