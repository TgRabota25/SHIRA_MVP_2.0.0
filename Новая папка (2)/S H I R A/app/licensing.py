"""Gumroad license activation and periodic validation for SHIRA."""
import hashlib,json,os,platform,sys,urllib.parse,urllib.request,uuid
from datetime import datetime,timezone
from pathlib import Path
API='https://api.gumroad.com/v2/licenses/verify'
GRACE_SECONDS=7*24*60*60

def product_permalink():
    value=os.environ.get('SHIRA_GUMROAD_PRODUCT','').strip()
    if value:return value
    bases=[Path(__file__).resolve().parent]
    if hasattr(sys,'_MEIPASS'):bases.append(Path(sys._MEIPASS)/'app')
    for base in bases:
        candidate=base/'gumroad_product.txt'
        if candidate.is_file():
            value=candidate.read_text('utf-8-sig').strip()
            if value:return value
    return ''

def machine_id():
    raw=f"{platform.node()}|{platform.machine()}|{uuid.getnode()}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]

def license_path():
    from config import data_dir
    return data_dir()/'license.json'

def load():
    try:return json.loads(license_path().read_text('utf-8'))
    except Exception:return {}

def save(record):
    path=license_path();path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)

def verify(license_key):
    permalink=product_permalink()
    if not permalink:raise RuntimeError('Не настроен продукт Gumroad. Добавьте permalink или product ID в app/gumroad_product.txt.')
    key=' '.join(str(license_key).split()).strip()
    if not key:raise ValueError('Введите лицензионный ключ.')
    data=urllib.parse.urlencode({'product_permalink':permalink,'license_key':key,'increment_uses_count':'true'}).encode('utf-8')
    request=urllib.request.Request(API,data=data,headers={'User-Agent':'SHIRA/2.0','Content-Type':'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(request,timeout=20) as response:payload=json.loads(response.read().decode('utf-8'))
    except Exception as exc:
        raise RuntimeError('Не удалось связаться с Gumroad. Проверьте интернет и попробуйте снова.') from exc
    if not payload.get('success'):raise ValueError('Лицензионный ключ не найден или не подходит к этому продукту.')
    purchase=payload.get('purchase') or {}
    if purchase.get('refunded') or purchase.get('chargebacked'):raise ValueError('Эта покупка была возвращена или оспорена.')
    subscription=purchase.get('subscription')
    if subscription and (subscription.get('cancelled_at') or subscription.get('failed_at')):raise ValueError('Подписка отменена или оплата не прошла. Продлите подписку в Gumroad.')
    record={'license_key':key,'email':purchase.get('email',''),'product_permalink':permalink,'machine_id':machine_id(),'last_checked':datetime.now(timezone.utc).timestamp(),'sale_timestamp':purchase.get('sale_timestamp'),'subscription':bool(subscription)}
    save(record);return record

def cached_valid():
    record=load()
    if not record or record.get('machine_id')!=machine_id():return False
    try:last=float(record.get('last_checked',0))
    except Exception:return False
    return datetime.now(timezone.utc).timestamp()-last<=GRACE_SECONDS

def ensure_licensed():
    if cached_valid():return True
    record=load()
    if record.get('license_key'):
        try:
            verify(record['license_key']);return True
        except Exception:
            if cached_valid():return True
    return activate_dialog()

def activate_dialog():
    import tkinter as tk
    from tkinter import ttk,messagebox
    result={'activated':False}
    root=tk.Tk();root.title('Активация SHIRA');root.geometry('520x300');root.resizable(False,False);root.configure(background='#002B36')
    frame=ttk.Frame(root,padding=24);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='Активация SHIRA',font=('Segoe UI',16,'bold')).pack(anchor='w')
    ttk.Label(frame,text='Введите лицензионный ключ, полученный после оплаты на Gumroad.',wraplength=440,justify='left').pack(anchor='w',pady=(8,16))
    key_var=tk.StringVar();entry=ttk.Entry(frame,textvariable=key_var,width=48);entry.pack(fill='x');entry.focus_set()
    message=tk.StringVar(value='')
    ttk.Label(frame,textvariable=message,wraplength=440,justify='left',foreground='#F29696').pack(anchor='w',pady=(12,8))
    buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=(8,0))
    def activate():
        message.set('Проверяем ключ…');root.update_idletasks()
        try:
            record=verify(key_var.get());message.set('');result['activated']=True;root.destroy()
        except Exception as exc:message.set(str(exc))
    ttk.Button(buttons,text='Активировать',command=activate).pack(side='left')
    ttk.Button(buttons,text='Выход',command=root.destroy).pack(side='right')
    entry.bind('<Return>',lambda event:activate())
    root.protocol('WM_DELETE_WINDOW',root.destroy)
    root.mainloop()
    if not result['activated']:raise SystemExit('SHIRA не активирована.')
    return True
