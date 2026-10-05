# YANGILASH TARTIBI:
# 1) Mavjud bazani zaxiralang. Faylni GitHub'dagi ali_kuryer.py o‘rniga qo‘ying.
# 2) Render Start Command: python ali_kuryer.py (o‘zgarmaydi).
# 3) BOT_TOKEN, ADMIN_USER, ADMIN_PASSWORD avvalgi qiymatlarda qoladi.
# 4) HTTPS uchun COOKIE_SECURE=1.
# 5) PUBLIC_BASE_URL=https://ali-kuryer-1.onrender.com (yoki o‘z domeningiz).
# 6) Doimiy disk /var/data bo‘lsa: DATA_DIR=/var/data, DB_PATH=/var/data/ali_kuryer.db.
#    Mavjud DB'ni yangi yo‘lga ko‘chirmasangiz bo‘sh baza ochiladi.
#    Doimiy disksiz lokal DB/rasmlar deploy/restartdan keyin yo‘qolishi mumkin.
# 7) Alohida admin domenini shu xizmatga ulang; ADMIN_HOST=admin.domen.uz.
#    ADMIN_HOST faqat domen nomi: https:// va /admin qo‘shilmaydi.
#    Domen tayyor bo‘lmaguncha ADMIN_HOST o‘rnatmang: /admin ishlaydi.
# 8) Aloqa raqami, bot/operator havolalari admin /settings'da kiritiladi.
# 9) GPS HTTPS va faol sahifada ishlaydi; fon rejimi uchun alohida mobil ilova kerak.
# 10) Xarita tashqi Leaflet CDN va OSM tarmog‘iga bog‘liq.
# Demo oshxonalar uchun standart 123456 parollarini admin orqali almashtiring.

# ALI KURYER — ishga tushirish:
# Python 3.9+; tashqi Python kutubxona talab qilinmaydi. Xarita Leaflet/OSM orqali.
# Render Start Command: python ali_kuryer.py
# Rasm va baza doimiy saqlanishi uchun serverga doimiy disk ulash zarur.
# BOT_TOKEN: Telegram bot tokeni (yo‘q bo‘lsa faqat web ishlaydi).
# ADMIN_USER: admin login; ADMIN_PASSWORD: yangi kuchli parol (majburiy).
# DB_PATH: mavjud ali_kuryer.db yo‘li; PORT: 10000 (standart).
# HTTPS serverda COOKIE_SECURE=1 o‘rnating.
# Panellar: /admin, /restaurant, /courier. Kuryerni admin yaratadi.
# Menyu rasmi: telefondan JPG/PNG/WEBP yuklash; tarkib majburiy.
# Yangi va tahrirlangan mahsulot admin tasdig‘idan keyin botda ko‘rinadi.
# Vaqt: Asia/Tashkent; boshlanish=tugash bo‘lsa 24 soat.
# Bazani yangilashdan avval zaxira nusxasini saqlang.
# Eski loginlar saqlanadi; demo oshxona parollarini haqiqiy ishda almashtiring.
# GPS: HTTPS, kuryer ruxsati va faol brauzer kerak. Fon kuzatuvi kafolatlanmaydi.
# Doimiy disk: DATA_DIR va DB_PATH; PUBLIC_BASE_URL bot kuzatish havolalari uchun.
# ADMIN_HOST va PUBLIC_HOST: admin uchun alohida domenni cheklash.

import os, time, json, html, base64, hashlib, secrets, sqlite3
import urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

TOKEN = os.getenv('BOT_TOKEN')
API = 'https://api.telegram.org/bot' + (TOKEN or '')
DB = os.getenv('DB_PATH','ali_kuryer.db')
ADMIN_USER = os.getenv('ADMIN_USER','admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD','ChangeMe_123!')
carts = {}
sessions = {}

def conn():
    c=sqlite3.connect(DB,timeout=30); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON'); return c

def ph(s): return hashlib.sha256(s.encode()).hexdigest()

def original_init_db():
    c=conn()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY,telegram_id INTEGER UNIQUE,first_name TEXT,username TEXT,phone TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS restaurants(id INTEGER PRIMARY KEY,name TEXT NOT NULL,phone TEXT DEFAULT '',address TEXT DEFAULT '',login TEXT UNIQUE,password_hash TEXT,status TEXT DEFAULT 'active',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS menu_items(id INTEGER PRIMARY KEY,restaurant_id INTEGER NOT NULL,name TEXT NOT NULL,price INTEGER NOT NULL,ingredients TEXT DEFAULT '',description TEXT DEFAULT '',weight TEXT DEFAULT '',category TEXT DEFAULT '',image_url TEXT DEFAULT '',status TEXT DEFAULT 'pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,customer_id INTEGER,restaurant_id INTEGER,total INTEGER,status TEXT DEFAULT 'Qabul qilindi',phone TEXT DEFAULT '',address TEXT DEFAULT '',payment TEXT DEFAULT 'Naqd',created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(customer_id) REFERENCES customers(id),FOREIGN KEY(restaurant_id) REFERENCES restaurants(id));
    CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY,order_id INTEGER,item_id INTEGER,name TEXT,price INTEGER,qty INTEGER,FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY,action TEXT,details TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    ''')
    if c.execute('SELECT COUNT(*) n FROM restaurants').fetchone()['n']==0:
        seeds=[('Ali Burger','901111111','Toshkent','aliburger'),('Osh Markazi','902222222','Toshkent','oshmarkazi'),('Pizza House','903333333','Toshkent','pizzahouse')]
        for x in seeds: c.execute('INSERT INTO restaurants(name,phone,address,login,password_hash) VALUES(?,?,?,?,?)',(x[0],x[1],x[2],x[3],ph('123456')))
        rs=c.execute('SELECT id,name FROM restaurants').fetchall()
        seedmenu={
        'Ali Burger':[('Classic Burger',30000,"Mol go'shti, pishloq, salat va sous"),('Chicken Burger',28000,'Tovuq go\'shti, salat va maxsus sous'),('Fri',12000,'Qarsildoq kartoshka fri')],
        'Osh Markazi':[('O\'zbek Palovi',35000,"Guruch, go'sht, sabzi va no'xat"),('Chuchvara',25000,'Uy uslubidagi chuchvara'),('Achichuk',10000,'Pomidor, piyoz va ko\'katlar')],
        'Pizza House':[('Pepperoni Pizza',65000,'Pishloq, pepperoni va pomidor sousi'),('Chicken Pizza',60000,'Tovuq go\'shti, pishloq va sous'),('Margherita',50000,'Pishloq, pomidor va maxsus sous')]}
        for r in rs:
            for n,p,d in seedmenu[r['name']]: c.execute("INSERT INTO menu_items(restaurant_id,name,price,description,status) VALUES(?,?,?,?, 'approved')",(r['id'],n,p,d))
    c.commit(); c.close()

def tg(method,data=None):
    try:
        u=API+'/'+method
        if data is not None:
            q=urllib.parse.urlencode(data).encode(); req=urllib.request.Request(u,data=q)
        else: req=urllib.request.Request(u)
        with urllib.request.urlopen(req,timeout=45) as r: return json.loads(r.read().decode())
    except Exception as e: print('TG:',e); return None

def send(cid,text,kb=None):
    d={'chat_id':cid,'text':text}
    if kb: d['reply_markup']=json.dumps(kb,ensure_ascii=False)
    return tg('sendMessage',d)

def customer(msg):
    u=msg.get('from',{}); tid=u.get('id');
    if not tid:return None
    c=conn(); r=c.execute('SELECT id FROM customers WHERE telegram_id=?',(tid,)).fetchone()
    if r: cid=r['id']; c.execute('UPDATE customers SET first_name=?,username=? WHERE telegram_id=?',(u.get('first_name','Mijoz'),u.get('username',''),tid))
    else: cid=c.execute('INSERT INTO customers(telegram_id,first_name,username) VALUES(?,?,?)',(tid,u.get('first_name','Mijoz'),u.get('username',''))).lastrowid
    c.commit(); c.close(); return cid

def main_kb(): return {'keyboard':[[{'text':'🍔 Buyurtma berish'},{'text':'🍽 Restoranlar'}],[{'text':'📦 Buyurtmalarim'},{'text':'📍 Buyurtmani kuzatish'}],[{'text':'👤 Profilim'},{'text':'💬 Yordam'}],[{'text':"🛵 Kuryer bo'lish"},{'text':'🏪 Restoran hamkorligi'}]],'resize_keyboard':True}

def restaurants_kb():
    c=conn(); rs=c.execute("SELECT * FROM restaurants WHERE status='active' ORDER BY name").fetchall(); c.close()
    return {'inline_keyboard':[[{'text':r['name']+' • '+r['opens_at']+'–'+r['closes_at']+(' • Ochiq' if is_open(r) else ' • Yopiq'),'callback_data':f"r:{r['id']}"}] for r in rs]}

def menu_kb(rid):
    c=conn(); ms=c.execute("SELECT id,name,price FROM menu_items WHERE restaurant_id=? AND status='approved' ORDER BY id",(rid,)).fetchall(); c.close()
    b=[[{'text':f"{m['name']} — {m['price']:,} so'm",'callback_data':f"i:{rid}:{m['id']}"}] for m in ms]
    b.append([{'text':'🛒 Savat','callback_data':'cart'}]); return {'inline_keyboard':b}

def cart_text(uid):
    a=carts.get(uid,[])
    if not a:return '🛒 Savatingiz bo\'sh.'
    s='🛒 SAVAT\n\n'; total=0
    for i,x in enumerate(a,1):
        sub=x['price']*x['qty']; total+=sub; s+=f"{i}. {x['name']} x{x['qty']} — {sub:,} so'm\n"
    return s+f"\n💰 Jami: {total:,} so'm"

def cart_kb(): return {'inline_keyboard':[[{'text':'✅ Buyurtmani tasdiqlash','callback_data':'checkout'}],[{'text':'🗑 Savatni tozalash','callback_data':'clear'}],[{'text':'🍽 Restoranlar','callback_data':'restaurants'}]]}

checkout_states={}

def make_order(uid):
    a=carts.get(uid,[])
    if not a:return None
    with conn() as c:
        c.execute('BEGIN IMMEDIATE')
        cu=c.execute('SELECT id,phone FROM customers WHERE telegram_id=?',(uid,)).fetchone()
        r=c.execute('SELECT * FROM restaurants WHERE id=?',(a[0]['rid'],)).fetchone()
        if not cu or not cu['phone'] or not r or not is_open(r):raise ValueError('Oshxona yopiq yoki telefon kiritilmagan.')
        fresh=[]
        for x in a:
            m=c.execute("SELECT * FROM menu_items WHERE id=? AND restaurant_id=? AND status='approved'",(x['item_id'],r['id'])).fetchone()
            if not m:raise ValueError('Savatdagi taom o‘zgargan. Savatni tozalab, qayta tanlang.')
            if m['price']!=x['price']:raise ValueError('Taom narxi o‘zgargan. Savatni tozalab, yangi narxda tanlang.')
            fresh.append((m,x['qty']))
        total=sum(m['price']*qty for m,qty in fresh)
        address=checkout_states.get(uid,{}).get('address','')
        if not address:raise ValueError('Yetkazish manzilini kiriting.')
        oid=c.execute('INSERT INTO orders(customer_id,restaurant_id,total,phone,address) VALUES(?,?,?,?,?)',(cu['id'],r['id'],total,cu['phone'],address)).lastrowid
        for m,qty in fresh:c.execute('INSERT INTO order_items(order_id,item_id,name,price,qty) VALUES(?,?,?,?,?)',(oid,m['id'],m['name'],m['price'],qty))
    carts[uid]=[];checkout_states.pop(uid,None);return oid,total

def message(msg):
    cid=msg.get('chat',{}).get('id'); uid=msg.get('from',{}).get('id');
    if not cid or not uid:return
    customer(msg); t=msg.get('text','').strip()
    state=checkout_states.get(uid)
    if t=='/cancel':
        checkout_states.pop(uid,None);send(cid,'Buyurtma rasmiylashtirish bekor qilindi.',main_kb());return
    if state:
        if state['step']=='phone':
            contact=msg.get('contact',{})
            if contact and contact.get('user_id')!=uid:send(cid,'O‘zingizning telefon raqamingizni yuboring.');return
            phone=contact.get('phone_number',t)
            if not re.fullmatch(r'\+?[0-9 ()-]{7,20}',phone):send(cid,'Telefon raqamingizni to‘g‘ri kiriting.');return
            with conn() as c:c.execute('UPDATE customers SET phone=? WHERE telegram_id=?',(phone,uid))
            state['step']='address';send(cid,'Yetkazish manzilini yozing (shahar, ko‘cha, uy). Bekor qilish: /cancel');return
        if state['step']=='address':
            if len(t)<5:send(cid,'To‘liq manzilni yozing.');return
            state['address']=t;state['step']='confirm'
            send(cid,cart_text(uid)+'\nManzil: '+t,cart_kb());return
    if t=='/start': send(cid,'👋 Assalomu alaykum!\n\n🛵 Ali Kuryer botiga xush kelibsiz.',main_kb());return
    if t in ('/order','🍔 Buyurtma berish','/restaurants','🍽 Restoranlar'):send(cid,'🍽 Restoranni tanlang:',restaurants_kb());return
    if t in ('/orders','📦 Buyurtmalarim'):
        c=conn();r=c.execute('SELECT o.*,r.name rn FROM orders o LEFT JOIN restaurants r ON r.id=o.restaurant_id LEFT JOIN customers cu ON cu.id=o.customer_id WHERE cu.telegram_id=? ORDER BY o.id DESC LIMIT 10',(uid,)).fetchall();c.close()
        if not r:send(cid,'📦 Buyurtmalar yo\'q.',main_kb());return
        s='📦 BUYURTMALARIM\n\n'+''.join(f"№{x['id']} — {x['rn']}\n💰 {x['total']:,} so'm\n📌 {x['status']}\n\n" for x in r);send(cid,s,main_kb());return
    if t in ('/track','📍 Buyurtmani kuzatish'):
        c=conn();r=c.execute('SELECT o.*,r.name rn FROM orders o LEFT JOIN restaurants r ON r.id=o.restaurant_id LEFT JOIN customers cu ON cu.id=o.customer_id WHERE cu.telegram_id=? ORDER BY o.id DESC LIMIT 1',(uid,)).fetchone();c.close();send(cid,'📍 Buyurtma topilmadi.',main_kb()) if not r else send(cid,f"📍 №{r['id']}\n🏪 {r['rn']}\n📌 {r['status']}",main_kb());return
    if t in ('/profile','👤 Profilim'):
        c=conn();r=c.execute('SELECT * FROM customers WHERE telegram_id=?',(uid,)).fetchone();c.close();send(cid,f"👤 PROFIL\n\nIsm: {r['first_name']}\nTelefon: {r['phone'] or 'Kiritilmagan'}\nTelegram ID: {uid}",main_kb());return
    if t in ('/support','💬 Yordam'):send(cid,'💬 Yordam: administrator bilan bog\'laning.',main_kb());return
    if t in ('/courier',"🛵 Kuryer bo'lish"):send(cid,'🛵 Kuryer bo\'lish uchun administratorga murojaat qiling.',main_kb());return
    if t in ('/partner','🏪 Restoran hamkorligi'):send(cid,'🏪 Restoran hamkorligi: admin restoran yaratadi va sizga login/parol beradi.',main_kb());return
    send(cid,'👇 Kerakli bo\'limni tanlang:',main_kb())

def callback(q):
    cid=q.get('message',{}).get('chat',{}).get('id');uid=q.get('from',{}).get('id');d=q.get('data','');
    if not cid:return
    tg('answerCallbackQuery',{'callback_query_id':q.get('id')})
    if d in ('restaurants',):send(cid,'🍽 Restoranni tanlang:',restaurants_kb());return
    if d.startswith('r:'):
        rid=int(d.split(':')[1]);c=conn();r=c.execute("SELECT name FROM restaurants WHERE id=? AND status='active'",(rid,)).fetchone();c.close()
        if r:send(cid,f"🍽 {r['name']}\n\nMenyudan taom tanlang:",menu_kb(rid))
        return
    if d.startswith('i:'):
        _,rid,iid=d.split(':');c=conn();m=c.execute("SELECT * FROM menu_items WHERE id=? AND restaurant_id=? AND status='approved'",(iid,rid)).fetchone();c.close()
        if not m:return
        extra=f"\n🥗 Tarkibi: {m['ingredients']}" if m['ingredients'] else ''
        if m['image_url']:
            tg('sendPhoto',{'chat_id':cid,'photo':m['image_url'],'caption':m['name']})
        send(cid,f"🍽 {m['name']}\n💰 {m['price']:,} so'm\n📝 {m['description']}{extra}",{'inline_keyboard':[[{'text':"➕ Savatga qo'shish",'callback_data':f'a:{rid}:{iid}'}],[{'text':'🛒 Savat','callback_data':'cart'}]]});return
    if d.startswith('a:'):
        _,rid,iid=d.split(':');c=conn();m=c.execute("SELECT * FROM menu_items WHERE id=? AND restaurant_id=? AND status='approved'",(iid,rid)).fetchone();c.close()
        if not m:return
        a=carts.setdefault(uid,[])
        if a and a[0]['rid']!=int(rid):send(cid,'⚠️ Savatda boshqa restoran bor. Avval savatni tozalang.',cart_kb());return
        for x in a:
            if x['item_id']==int(iid):x['qty']+=1;break
        else:a.append({'rid':int(rid),'item_id':int(iid),'name':m['name'],'price':m['price'],'qty':1})
        send(cid,'✅ Savatga qo\'shildi!\n\n'+cart_text(uid),cart_kb());return
    if d=='cart':send(cid,cart_text(uid),cart_kb());return
    if d=='clear':checkout_states.pop(uid,None);carts[uid]=[];send(cid,'🗑 Savat tozalandi.',main_kb());return
    if d=='checkout':
        if not carts.get(uid):send(cid,'Savat bo‘sh.',main_kb());return
        if checkout_states.get(uid,{}).get('step')!='confirm':
            checkout_states[uid]={'step':'phone'}
            send(cid,'Telefon raqamingizni yuboring yoki yozing. Bekor qilish: /cancel',{'keyboard':[[{'text':'Telefonni yuborish','request_contact':True}]],'resize_keyboard':True});return
        try:r=make_order(uid)
        except ValueError as e:send(cid,str(e),cart_kb());return
        if not r:send(cid,'🛒 Savat bo\'sh.',main_kb());return
        oid,total=r;send(cid,f"✅ BUYURTMA QABUL QILINDI!\n\n📦 №{oid}\n💰 {total:,} so'm\n📌 Qabul qilindi",main_kb())

def bot_loop():
    off=0;print('Bot ishga tushdi')
    while True:
        try:
            r=tg('getUpdates',{'offset':off,'timeout':30})
            if not r or not r.get('ok'):time.sleep(3);continue
            for u in r.get('result',[]):
                off=u['update_id']+1
                try:
                    if 'message' in u:message(u['message'])
                    elif 'callback_query' in u:callback(u['callback_query'])
                except Exception as e:print('update:',e)
        except Exception as e:print('loop:',e);time.sleep(5)

def esc(x):return html.escape(str(x or ''))
def form(h):
    n=int(h.headers.get('Content-Length','0'));return urllib.parse.parse_qs(h.rfile.read(n).decode())
def auth(h):
    a=h.headers.get('Authorization','')
    if not a.startswith('Basic '):return False
    try:u,p=base64.b64decode(a[6:]).decode().split(':',1);return u==ADMIN_USER and p==ADMIN_PASSWORD
    except:return False

# Alohida rollar, menyu tarixi va kuryer boshqaruvi.
from datetime import datetime
from zoneinfo import ZoneInfo
from http.cookies import SimpleCookie
import re

SESSION_TTL = 12 * 3600

def init_db():
    original_init_db()
    with conn() as c:
        for table, columns in {
            'restaurants': [('opens_at', "TEXT DEFAULT '09:00'"), ('closes_at', "TEXT DEFAULT '23:00'"), ('accepting_orders', 'INTEGER DEFAULT 1')],
            'menu_items': [('kind', "TEXT DEFAULT 'Taom'")],
            'orders': [('courier_id', 'INTEGER'), ('claimed_at', 'TEXT')],
        }.items():
            existing = {r['name'] for r in c.execute('PRAGMA table_info(' + table + ')')}
            for name, declaration in columns:
                if name not in existing:
                    c.execute('ALTER TABLE ' + table + ' ADD COLUMN ' + name + ' ' + declaration)
        c.executescript("""
        CREATE TABLE IF NOT EXISTS couriers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT DEFAULT '', login TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, status TEXT DEFAULT 'active');
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, actor_role TEXT, actor_id INTEGER, action TEXT, entity TEXT, entity_id INTEGER, before_json TEXT, after_json TEXT, created_at TEXT NOT NULL);
        """)

def now():
    return datetime.now(ZoneInfo('Asia/Tashkent')).isoformat(timespec='seconds')

def audit(c, role, actor, action, entity, eid, before=None, after=None):
    c.execute('INSERT INTO audit(actor_role,actor_id,action,entity,entity_id,before_json,after_json,created_at) VALUES(?,?,?,?,?,?,?,?)',
              (role,actor,action,entity,eid,json.dumps(before,ensure_ascii=False),json.dumps(after,ensure_ascii=False),now()))

def password_hash(p):
    salt=secrets.token_hex(16)
    return 'pbkdf2$'+salt+'$'+hashlib.pbkdf2_hmac('sha256',p.encode(),salt.encode(),260000).hex()

def password_ok(p, stored):
    if stored.startswith('pbkdf2$'):
        _,salt,digest=stored.split('$')
        return secrets.compare_digest(digest,hashlib.pbkdf2_hmac('sha256',p.encode(),salt.encode(),260000).hex())
    return secrets.compare_digest(ph(p),stored)

def is_open(r):
    t=datetime.now(ZoneInfo('Asia/Tashkent')).strftime('%H:%M')
    a,b=r['opens_at'],r['closes_at']
    return r['status']=='active' and r['accepting_orders'] and (a==b or (a<=t<b if a<b else t>=a or t<b))

def session(h,role):
    ck=SimpleCookie()
    try: ck.load(h.headers.get('Cookie',''))
    except Exception: return None
    token=ck.get('ak_'+role) or ck.get('ak')
    se=sessions.get(token.value) if token else None
    if not se or se['role']!=role or se['expires']<time.time():return None
    if role!='admin':
        with conn() as c:
            r=c.execute('SELECT * FROM '+('restaurants' if role=='restaurant' else 'couriers')+' WHERE id=? AND status=\'active\'',(se['id'],)).fetchone()
        if not r:return None
        se['record']=dict(r)
    return se

def page(title,body):
    return '<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' — Ali Kuryer</title><style>body{font-family:Arial;background:#f2f5f8;color:#172033;margin:0}header{background:#172033;color:white;padding:20px}nav{display:flex;gap:16px;flex-wrap:wrap;padding:16px;background:white}a{color:#b52320}.wrap{max-width:1200px;margin:auto;padding:16px}.card{background:white;border-radius:14px;padding:20px;margin:16px 0;overflow:auto}input,textarea,select{box-sizing:border-box;width:100%;padding:12px;margin:6px 0 14px;border:1px solid #cbd5e1;border-radius:8px}button,.btn{background:#c52b27;color:white;padding:10px 16px;border:0;border-radius:8px;cursor:pointer}table{width:100%;border-collapse:collapse}td,th{padding:12px;text-align:left;border-bottom:1px solid #ddd}img{width:100px;height:80px;object-fit:cover;border-radius:8px}label{display:block}pre{white-space:pre-wrap;word-break:break-word}small{color:#526174}</style></head><body><header>🛵 Ali Kuryer</header>'+body+'</body></html>'

def field(name,label,value='',typ='text',required=False):
    return '<label>'+esc(label)+'<input name="'+name+'" type="'+typ+'" value="'+esc(value)+'" '+('required' if required else '')+'></label>'

def post_form(path,csrf,body,button='Saqlash'):
    return '<form method="post" action="'+path+'"><input type="hidden" name="csrf" value="'+csrf+'">'+body+'<button>'+esc(button)+'</button></form>'

def navigation(role,se):
    links={'admin':[('', 'Umumiy nazorat'),('/restaurants','Oshxonalar'),('/menu','Menyu'),('/orders','Buyurtmalar'),('/couriers','Kuryerlar'),('/history','O‘zgarishlar tarixi')], 'restaurant':[('','Oshxona'),('/menu','Taom va ichimliklar'),('/orders','Buyurtmalar')], 'courier':[('','Buyurtmalar')]}[role]
    return '<nav>'+''.join('<a href="/'+role+x+'">'+label+'</a>' for x,label in links)+post_form('/'+role+'/logout',se['csrf'],'','Chiqish')+'</nav>'

def login_page(role,error=''):
    label={'admin':'Admin','restaurant':'Oshxona','courier':'Kuryer'}[role]
    return page(label+' — kirish','<div class="wrap"><div class="card"><h1>'+label+' paneliga kirish</h1><p>'+esc(error)+'</p><form method="post" action="/'+role+'/login">'+field('login','Login','',required=True)+field('password','Parol','','password',True)+'<button>Kirish</button></form></div><a href="/">Panellarni tanlash</a></div>')

def menu_editor(se,m=None):
    m=dict(m) if m else {}
    body=field('id','ID',m.get('id',''),'hidden')+field('name','Taom / ichimlik nomi',m.get('name',''),required=True)+field('price',"Narx (so‘m)",m.get('price',''),'number',True)
    body+='<label>Turi<select name="kind">'+''.join('<option '+('selected' if m.get('kind','Taom')==k else '')+'>'+k+'</option>' for k in ['Taom','Ichimlik'])+'</select></label>'
    for k,label in [('ingredients','Qisqacha tarkibi'),('description','Qisqacha tavsifi'),('weight','Og‘irligi / hajmi'),('category','Kategoriya'),('image_url','Rasm havolasi (https://...)')]:body+=field(k,label,m.get(k,''),required=k in ('ingredients','image_url'))
    return post_form('/restaurant/menu/save',se['csrf'],body,'Admin tasdig‘iga yuborish')

def order_table(c,role,se):
    where,args=('',())
    if role=='restaurant':where,args=(' WHERE o.restaurant_id=?',(se['id'],))
    if role=='courier':where,args=(" WHERE (o.courier_id=? OR (o.courier_id IS NULL AND o.status='Tayyor' AND r.status='active'))",(se['id'],))
    rows=c.execute('SELECT o.*,r.name rn,r.address pickup,r.latitude pickup_lat,r.longitude pickup_lon,cu.first_name cn,cr.name courier FROM orders o LEFT JOIN restaurants r ON r.id=o.restaurant_id LEFT JOIN customers cu ON cu.id=o.customer_id LEFT JOIN couriers cr ON cr.id=o.courier_id'+where+' ORDER BY o.id DESC LIMIT 200',args).fetchall()
    text='<table><tr><th>Buyurtma</th><th>Oshxona / manzil</th><th>Mijoz / yetkazish</th><th>Summa</th><th>Holat / kuryer</th><th>Amal</th></tr>'
    for o in rows:
        action=''
        if role=='restaurant':
            nxt={'Qabul qilindi':'Tayyorlanmoqda','Tayyorlanmoqda':'Tayyor'}.get(o['status'])
            if nxt:action=post_form('/restaurant/orders/status',se['csrf'],field('id','',o['id'],'hidden')+field('status','',nxt,'hidden'),nxt)
        if role=='admin' and o['status']=='Kuryer qabul qildi':
            action=post_form('/admin/orders/complete',se['csrf'],field('id','',o['id'],'hidden'),'Yetkazildi deb belgilash')
        if role=='courier' and o['courier_id'] is None:
            action=post_form('/courier/orders/claim',se['csrf'],field('id','',o['id'],'hidden'),'Qabul qilish')
        items=c.execute('SELECT name,qty FROM order_items WHERE order_id=?',(o['id'],)).fetchall()
        details=', '.join(x['name']+' × '+str(x['qty']) for x in items)
        pickup_map=''
        if o['pickup_lat'] is not None:
            pickup_map='<br><a target="_blank" rel="noopener" href="https://www.openstreetmap.org/?mlat='+str(o['pickup_lat'])+'&mlon='+str(o['pickup_lon'])+'#map=16/'+str(o['pickup_lat'])+'/'+str(o['pickup_lon'])+'">📍 Oshxona lokatsiyasi</a>'
        text+='<tr><td>#'+str(o['id'])+'<br>'+esc(details)+'</td><td>'+esc(o['rn'])+'<br>'+esc(o['pickup'])+pickup_map+'</td><td>'+esc(o['cn'])+'<br>'+esc(o['phone'])+'<br>'+esc(o['address'])+'</td><td>'+str(o['total'])+'</td><td>'+esc(o['status'])+'<br>'+esc(o['courier'])+'</td><td>'+action+'</td></tr>'
    return text+'</table>'

def history_table(c):
    rows=c.execute('SELECT a.*,r.name actor_name FROM audit a LEFT JOIN restaurants r ON a.actor_role=\'restaurant\' AND a.actor_id=r.id ORDER BY a.id DESC LIMIT 300').fetchall()
    text='<table><tr><th>Vaqt (Toshkent)</th><th>Kim</th><th>Amal / obyekt</th><th>Avval</th><th>Hozir</th></tr>'
    for a in rows:
        text+='<tr><td>'+esc(a['created_at'])+'</td><td>'+esc(a['actor_name'] or a['actor_role'])+' #'+str(a['actor_id'])+'</td><td>'+esc(a['action'])+' / '+esc(a['entity'])+' #'+str(a['entity_id'])+'</td><td><pre>'+esc(a['before_json'])+'</pre></td><td><pre>'+esc(a['after_json'])+'</pre></td></tr>'
    return text+'</table>'

def dashboard(role,se,path,q):
    body=navigation(role,se)+'<div class="wrap">'
    with conn() as c:
        if role=='restaurant':
            r=se['record']
            if path.endswith('/menu'):
                m=c.execute("SELECT * FROM menu_items WHERE id=? AND restaurant_id=? AND status!='deleted'",(q.get('edit',['0'])[0],se['id'])).fetchone()
                body+='<div class="card"><h1>Taom va ichimlik '+('tahrirlash' if m else 'qo‘shish')+'</h1>'+menu_editor(se,m)+'</div><div class="grid">'
                for item in c.execute("SELECT * FROM menu_items WHERE restaurant_id=? AND status!='deleted' ORDER BY id DESC",(se['id'],)):
                    body+='<div class="card"><img src="'+esc(item['image_url'])+'" alt="Taom rasmi"><h3>'+esc(item['name'])+' — '+str(item['price'])+' so‘m</h3><p>'+esc(item['kind'])+' • '+esc(item['ingredients'])+' • '+esc(item['status'])+'</p><a href="/restaurant/menu?edit='+str(item['id'])+'">Tahrirlash / narxni o‘zgartirish</a>'+post_form('/restaurant/menu/delete',se['csrf'],field('id','',item['id'],'hidden'),'O‘chirish')+'</div>'
                body+='</div>'
            elif path.endswith('/orders'):body+='<div class="card"><h1>Oshxona buyurtmalari</h1>'+order_table(c,role,se)+'</div>'
            else:
                body+='<div class="card"><h1>'+esc(r['name'])+'</h1><p>Hozir: '+('Ochiq' if is_open(r) else 'Yopiq')+'</p>'+post_form('/restaurant/hours',se['csrf'],field('opens_at','Ish boshlanishi',r['opens_at'],'time',True)+field('closes_at','Ish tugashi',r['closes_at'],'time',True)+'<label>Buyurtma qabul qilish<select name="accepting_orders"><option value="1" '+('selected' if r['accepting_orders'] else '')+'>Ochiq</option><option value="0" '+('selected' if not r['accepting_orders'] else '')+'>Yopiq</option></select></label>')+'</div>'
        elif role=='courier':body+='<div class="card"><h1>Kuryer: '+esc(se['record']['name'])+'</h1><p>Tayyor buyurtmalarni ko‘ring va qabul qiling. Ro‘yxatni yangilash uchun <a href="/courier">Yangilash</a>.</p>'+order_table(c,role,se)+'</div>'
        else:
            if path.endswith('/restaurants') or path.endswith('/couriers'):
                courier=path.endswith('/couriers');table='couriers' if courier else 'restaurants'
                fields=field('name','Ismi / nomi','',required=True)+field('phone','Telefon')
                if not courier:fields+=field('address','Manzil')
                fields+=field('login','Login','',required=True)+field('password','Parol (kamida 8 belgi)','','password',True)
                body+='<div class="card"><h1>'+('Kuryer' if courier else 'Oshxona')+' qo‘shish</h1>'+post_form(path+'/new',se['csrf'],fields)+'</div><div class="card">'
                for r in c.execute('SELECT * FROM '+table+' ORDER BY id DESC'):
                    body+='<p>#'+str(r['id'])+' '+esc(r['name'])+' • '+esc(r['login'])+' • '+esc(r['phone'])
                    if not courier:body+=' • '+esc(r['opens_at'])+'–'+esc(r['closes_at'])+' • '+('Ochiq' if is_open(r) else 'Yopiq')
                    body+='</p>'
                body+='</div>'
            elif path.endswith('/menu'):
                body+='<div class="card"><h1>Menyu nazorati</h1>'
                for m in c.execute('SELECT m.*,r.name rn FROM menu_items m JOIN restaurants r ON r.id=m.restaurant_id ORDER BY m.id DESC'):
                    body+='<div class="card"><img src="'+esc(m['image_url'])+'" alt="Rasm"><h3>'+esc(m['rn'])+' — '+esc(m['name'])+'</h3><p>'+str(m['price'])+' so‘m • '+esc(m['kind'])+' • '+esc(m['ingredients'])+' • '+esc(m['status'])+'</p>'
                    if m['status']=='pending':body+=post_form('/admin/menu/approve',se['csrf'],field('id','',m['id'],'hidden'),'Tasdiqlash')
                    body+='</div>'
                body+='</div>'
            elif path.endswith('/history'):body+='<div class="card"><h1>O‘zgarishlar: qo‘shish, o‘chirish, eski va yangi narxlar</h1>'+history_table(c)+'</div>'
            else:
                body+='<div class="card"><h1>Barcha buyurtmalar va kuryerlar</h1>'+order_table(c,role,se)+'</div>'
                if path=='/admin':
                    body+='<div class="card"><h2>Oshxonalar ish vaqti</h2>'
                    for r in c.execute('SELECT * FROM restaurants'):body+='<p>'+esc(r['name'])+' • '+esc(r['opens_at'])+'–'+esc(r['closes_at'])+' • '+('Ochiq' if is_open(r) else 'Yopiq')+'</p>'
                    body+='</div><div class="card"><h2>Kuryerlar</h2>'
                    for cr in c.execute('SELECT cr.*,COUNT(o.id) assigned FROM couriers cr LEFT JOIN orders o ON o.courier_id=cr.id GROUP BY cr.id'):body+='<p>'+esc(cr['name'])+' • '+esc(cr['phone'])+' • Qabul qilgan: '+str(cr['assigned'])+'</p>'
                    body+='</div><div class="card"><h2>So‘nggi o‘zgarishlar</h2>'+history_table(c)+'</div>'
    return page('Boshqaruv',body+'</div>')

class H(BaseHTTPRequestHandler):
    def out(self,s,status=200):
        b=s.encode();self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.end_headers();self.wfile.write(b)
    def red(self,u,cookie=None):
        self.send_response(303);self.send_header('Location',u)
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers()
    def do_GET(self):
        path,_,qs=self.path.partition('?');role=path.split('/')[1]
        if role not in ('admin','restaurant','courier'):
            self.out(page('Panellar','<div class="wrap"><div class="card"><h1>Panelni tanlang</h1><p><a href="/restaurant">Oshxona</a></p><p><a href="/courier">Kuryer</a></p><p><a href="/admin">Admin</a></p><p>Har bir panel uchun alohida login va parol talab qilinadi.</p></div></div>'));return
        se=session(self,role)
        if not se:self.out(login_page(role));return
        self.out(dashboard(role,se,path,urllib.parse.parse_qs(qs)))
    def do_POST(self):
        try:self.handle_post()
        except (ValueError,sqlite3.IntegrityError) as e:self.out(page('Xato','<div class="wrap"><div class="card"><h1>Ma’lumotni tekshiring</h1><p>'+esc(str(e))+'</p><a href="javascript:history.back()">Orqaga</a></div></div>'),400)
    def handle_post(self):
        path=self.path.partition('?')[0];role=path.split('/')[1]
        if role not in ('admin','restaurant','courier'):self.out('Topilmadi',404);return
        n=int(self.headers.get('Content-Length','0'))
        if n>65536:self.out('Ma’lumot hajmi katta',413);return
        f=urllib.parse.parse_qs(self.rfile.read(n).decode(),keep_blank_values=True)
        v=lambda key:f.get(key,[''])[0].strip()
        if path=='/'+role+'/login':
            rid=0;valid=False
            if role=='admin':valid=secrets.compare_digest(v('login'),ADMIN_USER) and secrets.compare_digest(v('password'),ADMIN_PASSWORD)
            else:
                with conn() as c:r=c.execute('SELECT * FROM '+('restaurants' if role=='restaurant' else 'couriers')+" WHERE login=? AND status='active'",(v('login'),)).fetchone()
                valid=r is not None and password_ok(v('password'),r['password_hash'])
                if valid:rid=r['id']
            if not valid:self.out(login_page(role,'Login yoki parol noto‘g‘ri.'),401);return
            token=secrets.token_urlsafe(32);sessions[token]={'role':role,'id':rid,'expires':time.time()+SESSION_TTL,'csrf':secrets.token_urlsafe(32)}
            self.red('/'+role,'ak_'+role+'='+token+'; Path=/; HttpOnly; SameSite=Lax; Max-Age='+str(SESSION_TTL)+('; Secure' if os.getenv('COOKIE_SECURE')=='1' else ''));return
        se=session(self,role)
        if not se:self.out(login_page(role),401);return
        if not secrets.compare_digest(v('csrf'),se['csrf']):self.out('So‘rov tasdiqlanmadi',403);return
        if path=='/'+role+'/logout':
            for token,val in list(sessions.items()):
                if val is se:sessions.pop(token,None)
            self.red('/','ak_'+role+'=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0');return
        with conn() as c:
            if path in ('/admin/restaurants/new','/admin/couriers/new'):
                if not v('name') or not v('login') or len(v('password'))<8:raise ValueError('Nom, login va kamida 8 belgili parol kerak.')
                table='restaurants' if 'restaurants' in path else 'couriers'
                if table=='restaurants':eid=c.execute('INSERT INTO restaurants(name,phone,address,login,password_hash) VALUES(?,?,?,?,?)',(v('name'),v('phone'),v('address'),v('login'),password_hash(v('password')))).lastrowid
                else:eid=c.execute('INSERT INTO couriers(name,phone,login,password_hash) VALUES(?,?,?,?)',(v('name'),v('phone'),v('login'),password_hash(v('password')))).lastrowid
                audit(c,role,se['id'],'Qo‘shildi',table,eid,after={'name':v('name'),'login':v('login')})
                target='/admin/'+table
            elif path=='/restaurant/hours':
                for key in ('opens_at','closes_at'):
                    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',v(key)):raise ValueError('Ish vaqti noto‘g‘ri.')
                before={k:se['record'][k] for k in ('opens_at','closes_at','accepting_orders')}
                after={'opens_at':v('opens_at'),'closes_at':v('closes_at'),'accepting_orders':int(v('accepting_orders'))}
                if after['accepting_orders'] not in (0,1):raise ValueError('Holat noto‘g‘ri.')
                c.execute('UPDATE restaurants SET opens_at=?,closes_at=?,accepting_orders=? WHERE id=?',(*after.values(),se['id']))
                audit(c,role,se['id'],'Ish vaqti o‘zgardi','restaurants',se['id'],before,after);target='/restaurant'
            elif path=='/restaurant/menu/save':
                keys=('name','price','ingredients','description','weight','category','image_url','kind')
                data={k:v(k) for k in keys};data['price']=int(data['price'])
                url=urllib.parse.urlsplit(data['image_url'])
                if not data['name'] or data['price']<=0 or not data['ingredients'] or not (re.fullmatch(r'/uploads/[a-f0-9]{32}\.(jpg|png|webp)',data['image_url']) or (url.scheme=='https' and url.netloc)) or data['kind'] not in ('Taom','Ichimlik'):raise ValueError('Nom, musbat narx, tarkib va rasm talab qilinadi.')
                eid=int(v('id') or 0)
                before=c.execute("SELECT * FROM menu_items WHERE id=? AND restaurant_id=? AND status!='deleted'",(eid,se['id'])).fetchone() if eid else None
                if eid and not before:self.out('Topilmadi',404);return
                if before:c.execute("UPDATE menu_items SET "+','.join(k+'=?' for k in keys)+",status='pending' WHERE id=? AND restaurant_id=?",(*data.values(),eid,se['id']))
                else:eid=c.execute('INSERT INTO menu_items(restaurant_id,'+','.join(keys)+') VALUES('+','.join('?' for _ in range(9))+')',(se['id'],*data.values())).lastrowid
                audit(c,role,se['id'],'Tahrirlandi' if before else 'Qo‘shildi','menu_items',eid,dict(before) if before else None,{**data,'status':'pending'});target='/restaurant/menu'
            elif path=='/restaurant/menu/delete':
                eid=int(v('id'));before=c.execute("SELECT * FROM menu_items WHERE id=? AND restaurant_id=? AND status!='deleted'",(eid,se['id'])).fetchone()
                if not before:self.out('Topilmadi',404);return
                c.execute("UPDATE menu_items SET status='deleted' WHERE id=? AND restaurant_id=?",(eid,se['id']));audit(c,role,se['id'],'O‘chirildi','menu_items',eid,dict(before),{'status':'deleted'});target='/restaurant/menu'
            elif path=='/admin/menu/approve':
                eid=int(v('id'));before=c.execute("SELECT * FROM menu_items WHERE id=? AND status='pending'",(eid,)).fetchone()
                if not before:raise ValueError('Tasdiq kutayotgan taom topilmadi.')
                c.execute("UPDATE menu_items SET status='approved' WHERE id=?",(eid,));audit(c,role,se['id'],'Tasdiqlandi','menu_items',eid,dict(before),{'status':'approved'});target='/admin/menu'
            elif path=='/restaurant/orders/status':
                eid=int(v('id'));before=c.execute('SELECT * FROM orders WHERE id=? AND restaurant_id=?',(eid,se['id'])).fetchone()
                if not before or {'Qabul qilindi':'Tayyorlanmoqda','Tayyorlanmoqda':'Tayyor'}.get(before['status'])!=v('status'):raise ValueError('Buyurtma holati mos emas.')
                c.execute('UPDATE orders SET status=? WHERE id=?',(v('status'),eid));audit(c,role,se['id'],'Buyurtma holati','orders',eid,dict(before),{'status':v('status')});target='/restaurant/orders'
            elif path=='/admin/orders/complete':
                eid=int(v('id'))
                before=c.execute("SELECT * FROM orders WHERE id=? AND status='Kuryer qabul qildi'",(eid,)).fetchone()
                if not before:raise ValueError('Kuryer qabul qilgan buyurtma topilmadi.')
                c.execute("UPDATE orders SET status='Yetkazildi' WHERE id=?",(eid,))
                audit(c,role,se['id'],'Yetkazildi','orders',eid,dict(before),{'status':'Yetkazildi'});target='/admin/orders'
            elif path=='/courier/orders/claim':
                eid=int(v('id'));ts=now()
                updated=c.execute("UPDATE orders SET courier_id=?,claimed_at=?,status='Kuryer qabul qildi' WHERE id=? AND courier_id IS NULL AND status='Tayyor' AND restaurant_id IN (SELECT id FROM restaurants WHERE status='active')",(se['id'],ts,eid))
                if updated.rowcount!=1:raise ValueError('Buyurtma boshqa kuryer tomonidan olingan yoki hali tayyor emas.')
                audit(c,role,se['id'],'Kuryer qabul qildi','orders',eid,after={'courier_id':se['id'],'claimed_at':ts});target='/courier'
            else:self.out('Topilmadi',404);return
        self.red(target)
    def log_message(self,*a):pass

def web():
    port=int(os.getenv('PORT','10000'));ThreadingHTTPServer(('0.0.0.0',port),H).serve_forever()


# V2: mobil panellar, fayl yuklash, GPS, reyting va operator xizmati.
import io, math
from pathlib import Path
from email.parser import BytesParser
from email.policy import default as email_policy
DATA_DIR=Path(os.getenv('DATA_DIR',str(Path(DB).resolve().parent)))
UPLOAD_DIR=DATA_DIR/'uploads'
PUBLIC_BASE_URL=os.getenv('PUBLIC_BASE_URL','').rstrip('/')
ADMIN_HOST=os.getenv('ADMIN_HOST','').lower().strip()
PUBLIC_HOST=os.getenv('PUBLIC_HOST','').lower().strip()
MAX_UPLOAD=8*1024*1024
login_attempts={}
_init_db_v1=init_db

def init_db():
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    Path(DB).resolve().parent.mkdir(parents=True,exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    _init_db_v1()
    with conn() as c:
        for table,cols in {
            'restaurants':[('latitude','REAL'),('longitude','REAL')],
            'couriers':[('on_duty','INTEGER DEFAULT 0'),('latitude','REAL'),('longitude','REAL'),('accuracy','REAL'),('location_at','TEXT'),('location_epoch','REAL')],
            'orders':[('tracking_token','TEXT'),('delivered_at','TEXT')]
        }.items():
            existing={r['name'] for r in c.execute('PRAGMA table_info('+table+')')}
            for name,decl in cols:
                if name not in existing:c.execute('ALTER TABLE '+table+' ADD COLUMN '+name+' '+decl)
        c.executescript('''
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ratings(order_id INTEGER PRIMARY KEY,customer_id INTEGER NOT NULL,courier_id INTEGER NOT NULL,stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),comment TEXT DEFAULT '',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY,role TEXT NOT NULL,actor_id INTEGER NOT NULL,subject TEXT NOT NULL,status TEXT DEFAULT 'Yangi',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ticket_messages(id INTEGER PRIMARY KEY,ticket_id INTEGER NOT NULL,role TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(ticket_id) REFERENCES tickets(id));
        ''')
        for o in c.execute('SELECT id FROM orders WHERE tracking_token IS NULL').fetchall():
            c.execute('UPDATE orders SET tracking_token=? WHERE id=?',(secrets.token_urlsafe(32),o['id']))

def settings():
    with conn() as c:return {r['key']:r['value'] for r in c.execute('SELECT * FROM settings')}

def safe_link(s):
    u=urllib.parse.urlsplit(s)
    return s if u.scheme=='https' and u.netloc and not u.username and not u.password else ''

def support_links():
    s=settings();a=''
    if s.get('support_phone'):a+='<a class="btn secondary" href="tel:'+esc(s['support_phone'])+'">☎ Qo‘ng‘iroq</a> '
    for key,label in [('operator_url','✉ Operator'),('bot_url','↗ Telegram bot')]:
        u=safe_link(s.get(key,''))
        if u:a+='<a class="btn secondary" href="'+esc(u)+'" target="_blank" rel="noopener">'+label+'</a> '
    return a

CSS='''
:root{--ink:#162c27;--muted:#667b72;--green:#12694e;--lime:#e7f4c3;--orange:#ff9d51;--line:#e0e9e2}*{box-sizing:border-box}body{margin:0;background:#f4f7f1;color:var(--ink);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}a{color:var(--green);text-decoration:none}a:hover{text-decoration:underline}header{background:#103d30;color:white;padding:19px max(22px,calc((100vw - 1240px)/2));display:flex;align-items:center;justify-content:space-between;gap:18px}.brand{font-weight:850;font-size:22px;letter-spacing:-.7px}.brand span{display:inline-flex;background:var(--lime);color:#123b2b;border-radius:12px;padding:3px 9px;margin-right:9px}header small{color:#c4dbcb}nav{position:sticky;top:0;z-index:10;background:#ffffffed;backdrop-filter:blur(12px);border-bottom:1px solid var(--line);padding:12px 20px;display:flex;align-items:center;gap:8px;overflow:auto}nav>a{white-space:nowrap;padding:9px 14px;border-radius:12px;font-weight:650}nav>a:hover{background:var(--lime);text-decoration:none}nav form{margin-left:auto}nav button{padding:8px 15px;background:#edf2eb;color:var(--green)}.wrap{max-width:1240px;margin:auto;padding:24px}.card{background:white;border:1px solid var(--line);border-radius:22px;padding:24px;margin:18px 0;box-shadow:0 6px 24px #143d2405;overflow:auto}.card .card{box-shadow:none;border-radius:17px}h1{font-size:clamp(25px,4vw,38px);letter-spacing:-1px;line-height:1.2;margin:5px 0 20px}h2{font-size:22px;letter-spacing:-.5px}h3{margin:12px 0 8px}.muted,small{color:var(--muted)}label{display:block;font-weight:650;font-size:13px;color:#456054}input,textarea,select{display:block;width:100%;background:#f9fbf7;border:1px solid #d8e2d8;border-radius:12px;padding:13px 14px;margin:7px 0 17px;color:var(--ink);font:inherit}input:focus,textarea:focus,select:focus{outline:3px solid #bce6d0;border-color:var(--green)}input[type=hidden]{display:none}input[type=checkbox]{display:inline;width:auto}button,.btn{display:inline-block;background:var(--green);color:white;border:0;border-radius:12px;padding:12px 18px;cursor:pointer;font:650 14px system-ui;min-height:44px;text-decoration:none}button:hover,.btn:hover{filter:brightness(1.08);text-decoration:none}.secondary{background:#edf4e8;color:var(--green)}.danger{background:#fff0ec;color:#b44431}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:16px}.grid>.card{margin:0}.hero{background:#123e30;color:white;border-radius:25px;padding:35px;margin-bottom:22px;position:relative;overflow:hidden}.hero p{color:#cee2d0;max-width:550px}.hero:after{content:'↗';font-size:180px;position:absolute;right:28px;top:-45px;color:#e7f4c317;pointer-events:none}.eyebrow{letter-spacing:2px;text-transform:uppercase;font-size:11px;font-weight:750}.stat strong{display:block;font-size:35px;letter-spacing:-1px}.pill{display:inline-block;border-radius:30px;padding:5px 12px;background:var(--lime);color:#466123;font-size:12px;font-weight:750;margin:4px 3px 4px 0}.pill.off{background:#fff0ec;color:#ac4d33}table{width:100%;border-collapse:collapse;font-size:14px}th{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:1px;background:#f7faf3}td,th{padding:15px 11px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}td form{margin:6px 0}img{width:100%;max-width:300px;height:185px;object-fit:cover;border-radius:14px;background:#edf2e6}pre{white-space:pre-wrap;word-break:break-word;font:12px/1.6 system-ui;background:#f7faf4;padding:10px;border-radius:10px}.login{max-width:480px;margin:45px auto}.login .card{padding:32px}.login button{width:100%}.actions{display:flex;gap:8px;flex-wrap:wrap}.actions form{display:inline-block}.map{height:420px;border-radius:18px;z-index:1}.message{padding:13px 17px;background:#f0f5ea;border-radius:15px;margin:8px 0}.message.admin{background:#e2f2e8}.empty{padding:30px;text-align:center;color:var(--muted)}.upload{border:2px dashed #b8d5b8;background:#f5faee;border-radius:17px;padding:20px;text-align:center}footer{text-align:center;color:var(--muted);padding:30px;font-size:12px}@media(max-width:600px){.wrap{padding:16px}.card{padding:18px;border-radius:18px}.hero{padding:25px}.map{height:330px}header small{display:none}nav{padding:8px;gap:0}nav>a{padding:9px;font-size:12px}.login{margin:22px auto}td,th{padding:11px 8px}h1{font-size:29px}}
'''
def page(title,body):
    return '<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#103d30"><title>'+esc(title)+' — Ali Kuryer</title><style>'+CSS+'</style></head><body><header><a class="brand" href="/" style="color:white"><span>↗</span>ALI KURYER</a><small>Yetkazish va hamkorlik platformasi</small></header>'+body+'<footer>Ali Kuryer • '+support_links()+'</footer></body></html>'

_nav_v1=navigation
def navigation(role,se):
    s=_nav_v1(role,se)
    extra='<a href="/'+role+'/support">Yordam</a>'
    if role=='admin':extra='<a href="/admin/map">Jonli xarita</a><a href="/admin/ratings">Baholar</a><a href="/admin/settings">Aloqa sozlamalari</a>'+extra
    if role=='courier':extra='<a href="/courier/ratings">Reytingim</a>'+extra
    return s.replace('</nav>',extra+'</nav>')

def location_fields(r=None):
    r=dict(r) if r else {}
    return field('latitude','Kenglik (latitude)',r.get('latitude') or '', 'number') .replace('type="number"','type="number" step="any"')+field('longitude','Uzunlik (longitude)',r.get('longitude') or '', 'number').replace('type="number"','type="number" step="any"')+'''<button type="button" class="secondary" onclick="navigator.geolocation.getCurrentPosition(p=>{document.querySelector('[name=latitude]').value=p.coords.latitude;document.querySelector('[name=longitude]').value=p.coords.longitude},()=>alert('Joylashuvga ruxsat bering yoki koordinatalarni kiriting'))">📍 Hozirgi joyni olish</button><p class="muted">Oshxonada turganingizda joyni oling yoki xaritadan olingan koordinatalarni kiriting.</p>'''

def login_page(role,error=''):
    label={'admin':'Admin','restaurant':'Oshxona','courier':'Kuryer'}[role]
    body='<div class="wrap login"><div class="card"><p class="eyebrow">'+('Boshqaruv markazi' if role=='admin' else 'Hamkorlar uchun')+'</p><h1>'+label+' paneliga kirish</h1><p style="color:#b44431">'+esc(error)+'</p><form method="post" action="/'+role+'/login">'+field('login','Login','',required=True)+field('password','Parol','','password',True)
    if role=='courier':
        body+='''<p class="muted">Ish vaqtida joylashuvingiz adminga, faol yetkazishda esa buyurtma egasiga ko‘rinadi. Ishni tugatganda kuzatuv to‘xtaydi.</p><input name="latitude" type="hidden"><input name="longitude" type="hidden"><input name="accuracy" type="hidden"><button type="button" class="secondary" id="permission">📍 Joylashuvga ruxsat berish</button><p id="geo-message" class="muted">Kirish uchun joylashuvga ruxsat bering.</p><script>document.getElementById('permission').onclick=()=>navigator.geolocation.getCurrentPosition(p=>{for(const k of ['latitude','longitude','accuracy'])document.querySelector('[name='+k+']').value=p.coords[k];document.getElementById('geo-message').textContent='Ruxsat olindi. Endi kirishingiz mumkin.';document.getElementById('enter').disabled=false},()=>document.getElementById('geo-message').textContent='Joylashuv olinmadi. Telefon GPS va brauzer ruxsatini tekshiring.',{enableHighAccuracy:true,timeout:20000});</script>'''
    body+='<button id="enter" '+('disabled' if role=='courier' else '')+'>Kirish</button></form></div>'+('' if role=='admin' else '<a href="/">← Panellarni tanlash</a>')+'</div>'
    return page(label,body)

def menu_editor(se,m=None):
    m=dict(m) if m else {}
    body=field('id','',m.get('id',''),'hidden')+field('name','Taom / ichimlik nomi',m.get('name',''),required=True)+field('price','Narx (so‘m)',m.get('price',''),'number',True)
    body+='<label>Turi<select name="kind">'+''.join('<option '+('selected' if m.get('kind','Taom')==k else '')+'>'+k+'</option>' for k in ['Taom','Ichimlik'])+'</select></label>'
    for k,label in [('ingredients','Qisqacha tarkibi'),('description','Tavsifi'),('weight','Og‘irligi / hajmi'),('category','Kategoriya')]:body+=field(k,label,m.get(k,''),required=k=='ingredients')
    if m.get('image_url'):body+='<img src="'+esc(m['image_url'])+'" alt="Hozirgi rasm">'
    body+='<div class="upload"><label>📷 Telefoningizdan rasm tanlang<input type="file" name="photo" accept="image/jpeg,image/png,image/webp" '+('required' if not m.get('image_url') else '')+' onchange="const f=this.files[0];if(f){document.getElementById(\'preview\').src=URL.createObjectURL(f);document.getElementById(\'preview\').hidden=false}"></label><small>JPG, PNG yoki WEBP • ko‘pi bilan 8 MB</small><img id="preview" hidden alt="Tanlangan rasm"></div>'
    return post_form('/restaurant/menu/save',se['csrf'],body,'Tasdiqqa yuborish').replace('<form method="post"','<form enctype="multipart/form-data" method="post"')

def coordinates(v,required=False):
    if not v('latitude') and not v('longitude') and not required:return None,None
    try:a,b=float(v('latitude')),float(v('longitude'))
    except (ValueError,TypeError):raise ValueError('Joylashuv koordinatalarini kiriting.')
    if not math.isfinite(a) or not math.isfinite(b) or not -90<=a<=90 or not -180<=b<=180:raise ValueError('Joylashuv noto‘g‘ri.')
    return a,b

def map_widget(endpoint):
    return '''<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><div id="live-map" class="map"></div><p id="map-status" class="muted">Joylashuvlar yuklanmoqda…</p><script>
if(window.L){const map=L.map('live-map').setView([41.31,69.28],11);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);const markers=L.layerGroup().addTo(map);let first=true;async function refresh(){try{const res=await fetch(ENDPOINT,{cache:'no-store'});if(!res.ok)throw Error();const d=await res.json();markers.clearLayers();let points=[];for(const x of d.locations){if(x.latitude==null)continue;points.push([x.latitude,x.longitude]);const text=document.createElement('div');text.textContent=x.name+' • '+(x.fresh?'Faol':'Eskirgan joylashuv')+' • '+x.location_at;L.circleMarker([x.latitude,x.longitude],{radius:9,color:x.fresh?'#12694e':'#a6a6a6',fillOpacity:.8}).addTo(markers).bindPopup(text)}if(first&&points.length){map.fitBounds(points,{maxZoom:15,padding:[30,30]});first=false}document.getElementById('map-status').textContent=d.locations.length?'Oxirgi ma’lumotlar: '+new Date().toLocaleTimeString():'Hozir faol joylashuv yo‘q.'}catch(e){document.getElementById('map-status').textContent='Xarita ma’lumotlari olinmadi. Qayta urinilmoqda.'}}refresh();setInterval(refresh,10000)}else document.getElementById('map-status').textContent='Xarita ochilmadi. Internetni tekshiring.';
</script>'''.replace('ENDPOINT',json.dumps(endpoint))

def tracking_script(se):
    return '''<script>
let watch=null,last=0;const status=document.getElementById('gps-status');const csrf=CSRF;
async function transmit(p){if(Date.now()-last<10000)return;last=Date.now();try{const r=await fetch('/courier/location',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({csrf,latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy})});status.textContent=r.ok?'● Joylashuvingiz adminga uzatilmoqda':'Joylashuv yuborilmadi. Qayta kiring.'}catch(e){status.textContent='Internet yo‘q. Joylashuv yuborilmadi.'}}
function startGPS(){if(!navigator.geolocation){status.textContent='Brauzer GPSni qo‘llamaydi';return}watch=navigator.geolocation.watchPosition(transmit,()=>{status.textContent='Joylashuv uzildi. GPS/ruxsatni tekshiring.';fetch('/courier/duty',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({csrf,on_duty:0})})},{enableHighAccuracy:true,maximumAge:5000,timeout:20000})}startGPS();document.addEventListener('visibilitychange',()=>{if(!document.hidden)last=0});
</script>'''.replace('CSRF',json.dumps(se['csrf']))

_order_table_v1=order_table
def order_table(c,role,se):
    result=_order_table_v1(c,role,se)
    if role=='courier':
        for o in c.execute("SELECT id FROM orders WHERE courier_id=? AND status='Kuryer qabul qildi'",(se['id'],)):
            result=result.replace('<td>#'+str(o['id'])+'<br>','<td>'+post_form('/courier/orders/complete',se['csrf'],field('id','',o['id'],'hidden'),'Yetkazildi')+'#'+str(o['id'])+'<br>')
    return result

def ratings_panel(c,role,se):
    where='' if role=='admin' else ' WHERE cr.id=?';args=() if role=='admin' else (se['id'],)
    body='<h1>'+('Mijozlar baholari' if role=='admin' else 'Mening reytingim')+'</h1>'
    rows=c.execute('SELECT cr.name,ra.* FROM ratings ra JOIN couriers cr ON cr.id=ra.courier_id'+where+' ORDER BY ra.created_at DESC',args).fetchall()
    if rows:
        body+='<p class="pill">★ '+str(round(sum(r['stars'] for r in rows)/len(rows),2))+' / 5 • '+str(len(rows))+' baho</p>'
        for r in rows:body+='<div class="message"><strong>'+esc(r['name'])+' • '+'★'*r['stars']+'</strong><p>'+esc(r['comment'] or 'Izohsiz')+'</p><small>Buyurtma #'+str(r['order_id'])+' • '+esc(r['created_at'])+'</small></div>'
    else:body+='<p class="empty">Hali baholar yo‘q.</p>'
    return body

_dashboard_v1=dashboard
def dashboard(role,se,path,q):
    with conn() as c:
        content=None
        if path.endswith('/support'):
            content='<h1>Qo‘llab-quvvatlash</h1><p>Operatorga savol yoki shikoyat yuboring.</p>'+support_links()
            if role!='admin':content+=post_form('/'+role+'/support/new',se['csrf'],field('subject','Murojaat mavzusi','',required=True)+'<label>Xabar<textarea name="body" required maxlength="4000"></textarea></label>','Yuborish')
            rows=c.execute('SELECT * FROM tickets '+('' if role=='admin' else 'WHERE role=? AND actor_id=? ')+'ORDER BY id DESC LIMIT 100',() if role=='admin' else (role,se['id'])).fetchall()
            for t in rows:
                content+='<div class="card"><h3>#'+str(t['id'])+' '+esc(t['subject'])+'</h3><span class="pill">'+esc(t['status'])+'</span><small>'+esc(t['role'])+' #'+str(t['actor_id'])+'</small>'
                for m in c.execute('SELECT * FROM ticket_messages WHERE ticket_id=? ORDER BY id',(t['id'],)):content+='<div class="message '+('admin' if m['role']=='admin' else '')+'"><strong>'+('Operator' if m['role']=='admin' else 'Murojaatchi')+'</strong><p>'+esc(m['body'])+'</p><small>'+esc(m['created_at'])+'</small></div>'
                fields=field('id','',t['id'],'hidden')+'<label>Javob<textarea name="body" maxlength="4000"></textarea></label>'
                if role=='admin':fields+='<label>Holat<select name="status">'+''.join('<option '+('selected' if t['status']==x else '')+'>'+x+'</option>' for x in ['Yangi','Ko‘rib chiqilmoqda','Hal qilindi'])+'</select></label>'
                content+=post_form('/'+role+'/support/reply',se['csrf'],fields,'Saqlash')+'</div>'
        elif path.endswith('/ratings'):content=ratings_panel(c,role,se)
        elif path=='/admin/map':content='<h1>Kuryerlar jonli xaritasi</h1><p>Yashil nuqta — oxirgi 90 soniyada yangilangan. Kulrang — oxirgi ma’lum joy.</p>'+map_widget('/admin/locations')
        elif path=='/admin/settings':
            s=settings();content='<h1>Aloqa sozlamalari</h1><p>Bu ma’lumotlar bot va hamkor panellarida ko‘rinadi.</p>'+post_form('/admin/settings/save',se['csrf'],field('support_phone','Operator telefon raqami',s.get('support_phone',''))+field('bot_url','Bot havolasi (https://t.me/...)',s.get('bot_url',''),'url')+field('operator_url','Operator havolasi (https://t.me/...)',s.get('operator_url',''),'url'))
        elif path in ('/admin/restaurants','/admin/couriers'):
            table=path.rsplit('/',1)[1];courier=table=='couriers'
            edit=c.execute('SELECT * FROM '+table+" WHERE id=? AND status!='deleted'",(q.get('edit',['0'])[0],)).fetchone();r=dict(edit) if edit else {}
            fields=field('id','',r.get('id',''),'hidden')+field('name','Kuryer ismi' if courier else 'Oshxona nomi',r.get('name',''),required=True)+field('phone','Telefon raqami',r.get('phone',''))
            if not courier:fields+=field('address','Manzil',r.get('address',''))+location_fields(r)
            fields+=field('login','Kirish logini',r.get('login',''),required=True)+field('password','Yangi parol (kamida 8 belgi)'+(' — o‘zgartirmaslik uchun bo‘sh qoldiring' if edit else ''),'','password',not edit)
            content='<h1>'+('Kuryerlar' if courier else 'Oshxonalar')+'</h1><div class="card"><h2>'+('Ma’lumotni tahrirlash' if edit else 'Yangi hamkor qo‘shish')+'</h2>'+post_form(path+'/save',se['csrf'],fields)+'</div><div class="grid">'
            for x in c.execute('SELECT * FROM '+table+" WHERE status!='deleted' ORDER BY id DESC"):
                avg=c.execute('SELECT AVG(stars) a,COUNT(*) n FROM ratings WHERE courier_id=?',(x['id'],)).fetchone() if courier else None
                content+='<div class="card"><span class="pill '+('off' if x['status']!='active' else '')+'">'+('Faol' if x['status']=='active' else 'Bloklangan')+'</span><h2>'+esc(x['name'])+'</h2><p>'+esc(x['phone'])+'<br>Login: '+esc(x['login'])+'</p>'
                if courier:content+='<p>★ '+(str(round(avg['a'],2)) if avg['a'] else '—')+' • '+str(avg['n'])+' baho</p>'
                else:
                    content+='<p>'+esc(x['address'])+'<br>'+esc(x['opens_at'])+'–'+esc(x['closes_at'])+'</p>'
                    if x['latitude'] is not None:content+='<a target="_blank" rel="noopener" href="https://www.openstreetmap.org/?mlat='+str(x['latitude'])+'&mlon='+str(x['longitude'])+'#map=16/'+str(x['latitude'])+'/'+str(x['longitude'])+'">📍 Lokatsiya</a>'
                content+='<div class="actions"><a class="btn secondary" href="'+path+'?edit='+str(x['id'])+'">Tahrirlash</a>'
                content+=post_form(path+'/status',se['csrf'],field('id','',x['id'],'hidden')+field('status','', 'blocked' if x['status']=='active' else 'active','hidden'),'Bloklash' if x['status']=='active' else 'Blokdan chiqarish')
                content+=post_form(path+'/status',se['csrf'],field('id','',x['id'],'hidden')+field('status','','deleted','hidden'),'O‘chirish').replace('<form ','<form onsubmit="return confirm(\'Hisob o‘chirilsinmi? Buyurtmalar tarixi saqlanadi.\')" ')
                content+='</div></div>'
            content+='</div>'
        elif role=='courier' and path=='/courier':
            r=se['record'];on=r['on_duty'];content='<h1>Salom, '+esc(r['name'])+'</h1><p class="pill '+('' if on else 'off')+'">'+('Ish faol' if on else 'Ish tugagan')+'</p><p id="gps-status" class="muted">'+('Joylashuv olinmoqda…' if on else 'Joylashuv uzatilmayapti.')+'</p>'
            content+=post_form('/courier/duty',se['csrf'],field('on_duty','',0 if on else 1,'hidden'),'Ishni tugatish' if on else 'Ishni boshlash')
            content+='<p class="muted">Ish vaqtida ushbu sahifani ochiq saqlang. Brauzer yopilganda kuzatuv uzilishi mumkin.</p><h2>Yetkazish buyurtmalari</h2>'+order_table(c,role,se)
            if on:content+=tracking_script(se)
        if content is not None:
            if role=='courier' and path!='/courier' and se['record']['on_duty']:
                content='<p id="gps-status" class="muted">Joylashuv olinmoqda…</p>'+content+tracking_script(se)
            return page('Boshqaruv',navigation(role,se)+'<div class="wrap"><div class="card">'+content+'</div></div>')
    result=_dashboard_v1(role,se,path,q)
    if path=='/admin':
        with conn() as c:
            counts=[('Faol buyurtmalar',c.execute("SELECT COUNT(*) FROM orders WHERE status!='Yetkazildi'").fetchone()[0]),('Oshxonalar',c.execute("SELECT COUNT(*) FROM restaurants WHERE status='active'").fetchone()[0]),('Ishdagi kuryerlar',c.execute("SELECT COUNT(*) FROM couriers WHERE status='active' AND on_duty=1").fetchone()[0]),('Yangi murojaatlar',c.execute("SELECT COUNT(*) FROM tickets WHERE status='Yangi'").fetchone()[0])]
        hero='<div class="hero"><p class="eyebrow">Boshqaruv markazi</p><h1>Hammasi nazoratingizda.</h1><p>Buyurtmalar, hamkorlar va yetkazish jarayonini bir joydan boshqaring.</p></div><div class="grid">'+''.join('<div class="card stat"><small>'+x+'</small><strong>'+str(n)+'</strong></div>' for x,n in counts)+'</div>'
        result=result.replace('<div class="wrap">','<div class="wrap">'+hero,1)
    return result

def tracking_link(o):
    if not PUBLIC_BASE_URL:return ''
    return PUBLIC_BASE_URL+'/track/'+o['tracking_token']

def notify_order(oid):
    with conn() as c:o=c.execute('SELECT o.*,cu.telegram_id FROM orders o JOIN customers cu ON cu.id=o.customer_id WHERE o.id=?',(oid,)).fetchone()
    if not o or not TOKEN:return
    buttons=[];url=tracking_link(o)
    if url:buttons.append([{'text':'📍 Buyurtmani kuzatish','url':url}])
    if o['status']=='Yetkazildi' and o['courier_id']:buttons.append([{'text':'★ Kuryerni baholash','callback_data':'rate:'+str(oid)}])
    send(o['telegram_id'],'📦 Buyurtma #'+str(oid)+'\nHolat: '+o['status'],{'inline_keyboard':buttons} if buttons else None)

_make_order_v1=make_order
def make_order(uid):
    result=_make_order_v1(uid)
    if result:
        with conn() as c:c.execute('UPDATE orders SET tracking_token=? WHERE id=?',(secrets.token_urlsafe(32),result[0]))
    return result

def location_record(r):
    return {k:r[k] for k in ('name','latitude','longitude','accuracy','location_at')}|{'fresh':bool(r['location_epoch'] and time.time()-r['location_epoch']<90)}

_H_v1=H
class H(_H_v1):
    def json_out(self,data,status=200):
        b=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b)
    def host_allowed(self,path):
        host=self.headers.get('Host','').lower().split(':')[0]
        if path.startswith('/admin') and ADMIN_HOST and host!=ADMIN_HOST:return False
        if host==ADMIN_HOST and ADMIN_HOST and path.startswith(('/restaurant','/courier')):return False
        return True
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        if not self.host_allowed(path):self.out('Topilmadi',404);return
        if path.startswith('/uploads/'):
            name=path.rsplit('/',1)[-1]
            if not re.fullmatch(r'[a-f0-9]{32}\.(jpg|png|webp)',name):self.out('Topilmadi',404);return
            f=UPLOAD_DIR/name
            if not f.is_file():self.out('Topilmadi',404);return
            b=f.read_bytes();self.send_response(200);self.send_header('Content-Type',{'jpg':'image/jpeg','png':'image/png','webp':'image/webp'}[f.suffix[1:]]);self.send_header('Content-Length',str(len(b)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','public, max-age=86400');self.end_headers();self.wfile.write(b);return
        if path=='/':
            if ADMIN_HOST and self.headers.get('Host','').lower().split(':')[0]==ADMIN_HOST:self.red('/admin');return
            body='<div class="wrap"><div class="hero"><p class="eyebrow">Ali Kuryer hamkorlari</p><h1>Birga yetkazamiz.</h1><p>Oshxonangizni boshqaring yoki tayyor buyurtmalarni mijozlarga yetkazing.</p></div><div class="grid"><a class="card" href="/restaurant"><p class="eyebrow">Oshxona uchun</p><h2>🍽 Menyu va buyurtmalar</h2><p class="muted">Taomlar, narxlar va ish vaqtingizni boshqaring.</p><span class="btn">Oshxona sifatida kirish →</span></a><a class="card" href="/courier"><p class="eyebrow">Kuryer uchun</p><h2>🛵 Yetkazishni boshlang</h2><p class="muted">Buyurtmani qabul qiling va manzilga yetkazing.</p><span class="btn">Kuryer sifatida kirish →</span></a></div></div>'
            self.out(page('Hamkorlar',body));return
        if path=='/admin/locations':
            if not session(self,'admin'):self.json_out({'error':'Kirish kerak'},401);return
            with conn() as c:rows=c.execute("SELECT * FROM couriers WHERE status='active' AND on_duty=1").fetchall()
            self.json_out({'locations':[location_record(r) for r in rows]});return
        if path.startswith('/track/'):
            token=path.split('/')[2] if len(path.split('/'))>2 else ''
            if not re.fullmatch(r'[A-Za-z0-9_-]{40,60}',token):self.out('Topilmadi',404);return
            with conn() as c:
                o=c.execute('SELECT o.*,r.name rn FROM orders o LEFT JOIN restaurants r ON r.id=o.restaurant_id WHERE tracking_token=?',(token,)).fetchone()
                if not o:self.out('Topilmadi',404);return
                cr=c.execute("SELECT * FROM couriers WHERE id=? AND status='active' AND on_duty=1",(o['courier_id'],)).fetchone() if o['status']=='Kuryer qabul qildi' else None
                rating=c.execute('SELECT * FROM ratings WHERE order_id=?',(o['id'],)).fetchone()
            if path.endswith('/location'):
                self.json_out({'locations':[location_record(cr)] if cr else [],'status':o['status']});return
            content='<div class="wrap"><div class="hero"><p class="eyebrow">Buyurtmangiz</p><h1>#'+str(o['id'])+' • '+esc(o['rn'])+'</h1><p>'+esc(o['status'])+'</p></div><div class="card">'
            if o['status']=='Kuryer qabul qildi':content+='<h2>Kuryer yo‘lda</h2>'+map_widget('/track/'+token+'/location')
            elif o['status']=='Yetkazildi':
                content+='<h2>Buyurtmangiz yetkazildi</h2>'
                if rating:content+='<p>Bahoyingiz: '+'★'*rating['stars']+'</p>'
                else:content+='<p>Kuryerga baho berish uchun Telegram botdagi “Buyurtmalarim” bo‘limiga kiring.</p>'
            else:content+='<p>Buyurtmangiz oshxonada. Kuryer qabul qilganda xarita shu sahifada ochiladi.</p><button onclick="location.reload()">Yangilash</button>'
            content+='<script>const oldStatus='+json.dumps(o['status'])+';setInterval(async()=>{try{const r=await fetch('+json.dumps('/track/'+token+'/location')+');if(r.ok&&(await r.json()).status!==oldStatus)location.reload()}catch(e){}},15000);</script>'
            self.out(page('Buyurtmani kuzatish',content+'</div></div>'));return
        super().do_GET()
    def do_POST(self):
        try:self.handle_post()
        except (ValueError,sqlite3.IntegrityError,UnicodeError) as e:self.out(page('Tekshiring','<div class="wrap"><div class="card"><h1>Ma’lumotni tekshiring</h1><p>'+esc(str(e))+'</p><a href="javascript:history.back()">← Orqaga</a></div></div>'),400)
    def read_fields(self):
        try:n=int(self.headers.get('Content-Length','0'))
        except ValueError:raise ValueError('So‘rov hajmi noto‘g‘ri.')
        if n<0 or n>MAX_UPLOAD+65536:raise ValueError('Rasm hajmi 8 MB dan oshmasin.')
        data=self.rfile.read(n)
        if len(data)!=n:raise ValueError('So‘rov to‘liq kelmadi.')
        photo=None
        if self.headers.get('Content-Type','').startswith('multipart/form-data'):
            mime=BytesParser(policy=email_policy).parsebytes(('Content-Type: '+self.headers.get('Content-Type')+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+data)
            if not mime.is_multipart():raise ValueError('Fayl yuklash shakli noto‘g‘ri.')
            f={}
            for part in mime.iter_parts():
                name=part.get_param('name',header='content-disposition');b=part.get_payload(decode=True) or b''
                if name=='photo' and part.get_filename() and b:photo=b
                elif name:
                    if len(b)>65536:raise ValueError('Matn hajmi katta.')
                    f[name]=[b.decode('utf-8')]
        else:
            if n>65536:raise ValueError('Matn hajmi katta.')
            f=urllib.parse.parse_qs(data.decode(),keep_blank_values=True)
        return f,photo
    def handle_post(self):
        path=urllib.parse.urlsplit(self.path).path
        if not self.host_allowed(path):self.out('Topilmadi',404);return
        role=path.split('/')[1]
        if role not in ('admin','restaurant','courier'):self.out('Topilmadi',404);return
        f,photo=self.read_fields();v=lambda k:f.get(k,[''])[0].strip()
        if path=='/'+role+'/login':
            key=(self.client_address[0],role,v('login'));attempt=login_attempts.get(key,(0,0))
            if attempt[0]>=10 and time.time()-attempt[1]<300:self.out(login_page(role,'Ko‘p urinish. 5 daqiqadan keyin qayta urinib ko‘ring.'),429);return
            rid=0;valid=False
            if role=='admin':valid=secrets.compare_digest(v('login'),ADMIN_USER) and secrets.compare_digest(v('password'),ADMIN_PASSWORD)
            else:
                with conn() as c:r=c.execute('SELECT * FROM '+('restaurants' if role=='restaurant' else 'couriers')+" WHERE login=? AND status='active'",(v('login'),)).fetchone()
                valid=r is not None and password_ok(v('password'),r['password_hash'])
                if valid:rid=r['id']
            if not valid:login_attempts[key]=(attempt[0]+1,time.time());self.out(login_page(role,'Login yoki parol noto‘g‘ri. Hisob bloklangan bo‘lishi ham mumkin.'),401);return
            if role=='courier':
                a,b=coordinates(v,True)
                with conn() as c:
                    c.execute('UPDATE couriers SET on_duty=1,latitude=?,longitude=?,accuracy=?,location_at=?,location_epoch=? WHERE id=?',(a,b,0,now(),time.time(),rid))
                    audit(c,role,rid,'Ish boshlandi','couriers',rid,after={'on_duty':1})
            login_attempts.pop(key,None)
            for k,s in list(sessions.items()):
                if s['expires']<time.time():sessions.pop(k,None)
            token=secrets.token_urlsafe(32);sessions[token]={'role':role,'id':rid,'expires':time.time()+SESSION_TTL,'csrf':secrets.token_urlsafe(32)}
            self.red('/'+role,'ak_'+role+'='+token+'; Path=/; HttpOnly; SameSite=Lax; Max-Age='+str(SESSION_TTL)+('; Secure' if os.getenv('COOKIE_SECURE')=='1' else ''));return
        se=session(self,role)
        if not se:self.out(login_page(role,'Qayta kiring.'),401);return
        if not secrets.compare_digest(v('csrf'),se['csrf']):self.out('So‘rov tasdiqlanmadi',403);return
        notice=None;target=None
        with conn() as c:
            if path in ('/admin/restaurants/save','/admin/couriers/save'):
                table=path.split('/')[2];eid=int(v('id') or 0)
                before=c.execute('SELECT * FROM '+table+" WHERE id=? AND status!='deleted'",(eid,)).fetchone() if eid else None
                if eid and not before:raise ValueError('Hisob topilmadi.')
                if not v('name') or not v('login') or (not before or v('password')) and len(v('password'))<8:raise ValueError('Nom, login va kamida 8 belgili parol kerak.')
                values={'name':v('name'),'phone':v('phone'),'login':v('login')}
                if not before or v('password'):values['password_hash']=password_hash(v('password'))
                if table=='restaurants':
                    a,b=coordinates(v);values.update(address=v('address'),latitude=a,longitude=b)
                if before:c.execute('UPDATE '+table+' SET '+','.join(k+'=?' for k in values)+' WHERE id=?',(*values.values(),eid))
                else:eid=c.execute('INSERT INTO '+table+'('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',tuple(values.values())).lastrowid
                snap=dict(before) if before else None
                if snap:snap.pop('password_hash',None)
                audit(c,role,0,'Tahrirlandi' if before else 'Qo‘shildi',table,eid,snap,{k:val for k,val in values.items() if k!='password_hash'});target='/admin/'+table
            elif path in ('/admin/restaurants/status','/admin/couriers/status'):
                table=path.split('/')[2];eid=int(v('id'));status=v('status')
                if status not in ('active','blocked','deleted'):raise ValueError('Holat noto‘g‘ri.')
                before=c.execute('SELECT * FROM '+table+" WHERE id=? AND status!='deleted'",(eid,)).fetchone()
                if not before:raise ValueError('Hisob topilmadi.')
                c.execute('UPDATE '+table+' SET status=? WHERE id=?',(status,eid))
                if table=='couriers' and status!='active':c.execute('UPDATE couriers SET on_duty=0 WHERE id=?',(eid,))
                affected_role='courier' if table=='couriers' else 'restaurant'
                if status!='active':
                    for token,s in list(sessions.items()):
                        if s['role']==affected_role and s['id']==eid:sessions.pop(token,None)
                audit(c,role,0,{'active':'Blokdan chiqarildi','blocked':'Bloklandi','deleted':'O‘chirildi'}[status],table,eid,{'status':before['status']},{'status':status});target='/admin/'+table
            elif path=='/admin/settings/save':
                phone=v('support_phone')
                if phone and not re.fullmatch(r'\+?[0-9 ()-]{7,24}',phone):raise ValueError('Telefon raqami noto‘g‘ri.')
                for key in ('bot_url','operator_url'):
                    if v(key) and not safe_link(v(key)):raise ValueError('Havola https:// bilan boshlansin.')
                old=settings();new={k:v(k) for k in ('support_phone','bot_url','operator_url')}
                for k,val in new.items():c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,val))
                audit(c,role,0,'Aloqa sozlamalari','settings',0,old,new);target='/admin/settings'
            elif path in ('/courier/location','/courier/duty'):
                if path.endswith('/location'):
                    a,b=coordinates(v,True)
                    accuracy=float(v('accuracy') or 0)
                    if not math.isfinite(accuracy) or accuracy<0:raise ValueError('GPS aniqligi noto‘g‘ri.')
                    if not se['record']['on_duty']:self.json_out({'error':'Ishni boshlang'},409);return
                    c.execute('UPDATE couriers SET latitude=?,longitude=?,accuracy=?,location_at=?,location_epoch=? WHERE id=?',(a,b,accuracy,now(),time.time(),se['id']))
                else:
                    duty=int(v('on_duty'))
                    if duty not in (0,1):raise ValueError('Holat noto‘g‘ri.')
                    c.execute('UPDATE couriers SET on_duty=? WHERE id=?',(duty,se['id']))
                    audit(c,role,se['id'],'Ish boshlandi' if duty else 'Ish tugadi','couriers',se['id'],after={'on_duty':duty})
                c.commit()
                if path.endswith('/location'):self.json_out({'ok':True});return
                target='/courier'
            elif path=='/courier/orders/complete':
                oid=int(v('id'));before=c.execute("SELECT * FROM orders WHERE id=? AND courier_id=? AND status='Kuryer qabul qildi'",(oid,se['id'])).fetchone()
                if not before:raise ValueError('Faol buyurtmangiz topilmadi.')
                c.execute("UPDATE orders SET status='Yetkazildi',delivered_at=? WHERE id=? AND courier_id=? AND status='Kuryer qabul qildi'",(now(),oid,se['id']))
                audit(c,role,se['id'],'Yetkazildi','orders',oid,{'status':before['status']},{'status':'Yetkazildi'});notice=oid;target='/courier'
            elif path=='/'+role+'/support/new' and role!='admin':
                if not v('subject') or not v('body') or len(v('body'))>4000:raise ValueError('Mavzu va xabar kiriting (4000 belgigacha).')
                tid=c.execute('INSERT INTO tickets(role,actor_id,subject,created_at) VALUES(?,?,?,?)',(role,se['id'],v('subject')[:200],now())).lastrowid
                c.execute('INSERT INTO ticket_messages(ticket_id,role,body,created_at) VALUES(?,?,?,?)',(tid,role,v('body'),now()));target='/'+role+'/support'
            elif path=='/'+role+'/support/reply':
                tid=int(v('id'));t=c.execute('SELECT * FROM tickets WHERE id=?',(tid,)).fetchone()
                if not t or role!='admin' and (t['role']!=role or t['actor_id']!=se['id']):self.out('Topilmadi',404);return
                if len(v('body'))>4000:raise ValueError('Xabar 4000 belgigacha bo‘lsin.')
                if role=='admin':
                    if v('status') not in ('Yangi','Ko‘rib chiqilmoqda','Hal qilindi'):raise ValueError('Holat noto‘g‘ri.')
                    c.execute('UPDATE tickets SET status=? WHERE id=?',(v('status'),tid));audit(c,role,0,'Murojaat holati','tickets',tid,{'status':t['status']},{'status':v('status')})
                if v('body'):
                    c.execute('INSERT INTO ticket_messages(ticket_id,role,body,created_at) VALUES(?,?,?,?)',(tid,role,v('body'),now()))
                    if role=='admin' and t['role']=='customer':
                        cu=c.execute('SELECT telegram_id FROM customers WHERE id=?',(t['actor_id'],)).fetchone()
                        if cu and TOKEN:Thread(target=send,args=(cu['telegram_id'],'💬 Operator javobi (#'+str(tid)+'):\n'+v('body')),daemon=True).start()
                target='/'+role+'/support'
        if target:
            if notice:Thread(target=notify_order,args=(notice,),daemon=True).start()
            self.red(target);return
        if path=='/restaurant/menu/save':
            eid=int(v('id') or 0)
            with conn() as c:old=c.execute("SELECT image_url FROM menu_items WHERE id=? AND restaurant_id=? AND status!='deleted'",(eid,se['id'])).fetchone() if eid else None
            if eid and not old:raise ValueError('Taom topilmadi.')
            if photo:
                if len(photo)>MAX_UPLOAD:raise ValueError('Rasm hajmi 8 MB dan oshmasin.')
                ext='png' if photo.startswith(b'\x89PNG\r\n\x1a\n') else 'jpg' if photo.startswith(b'\xff\xd8\xff') else 'webp' if photo[:4]==b'RIFF' and photo[8:12]==b'WEBP' else None
                if not ext or (ext=='png' and (len(photo)<45 or photo[12:16]!=b'IHDR' or b'IEND' not in photo[-16:])) or (ext=='jpg' and not photo.rstrip().endswith(b'\xff\xd9')) or (ext=='webp' and len(photo)<20):raise ValueError('To‘g‘ri JPG, PNG yoki WEBP rasm yuklang.')
                name=secrets.token_hex(16)+'.'+ext;(UPLOAD_DIR/name).write_bytes(photo);f['image_url']=['/uploads/'+name]
            elif old and old['image_url']:f['image_url']=[old['image_url']]
            else:raise ValueError('Taom rasmini tanlang.')
        if path=='/courier/orders/claim' and (not se['record']['on_duty'] or not se['record']['location_epoch'] or time.time()-se['record']['location_epoch']>90):raise ValueError('Avval ishni boshlang va GPS joylashuv yangilanishini kuting.')
        if path=='/courier/logout':
            with conn() as c:c.execute('UPDATE couriers SET on_duty=0 WHERE id=?',(se['id'],))
        data=urllib.parse.urlencode({k:val[0] for k,val in f.items()}).encode();self.rfile=io.BytesIO(data);self.headers.replace_header('Content-Length',str(len(data)))
        super().handle_post()
        if path in ('/restaurant/orders/status','/admin/orders/complete','/courier/orders/claim'):
            if path=='/admin/orders/complete':
                with conn() as c:c.execute("UPDATE orders SET delivered_at=? WHERE id=? AND status='Yetkazildi'",(now(),int(v('id'))))
            Thread(target=notify_order,args=(int(v('id')),),daemon=True).start()

support_states={}
rating_states={}
_message_v1=message
_callback_v1=callback

def message(msg):
    uid=msg.get('from',{}).get('id');cid=msg.get('chat',{}).get('id');t=msg.get('text','').strip()
    if not uid or not cid:return
    cuid=customer(msg)
    if t in ('/cancel','/start'):
        support_states.pop(uid,None);rating_states.pop(uid,None)
    if uid in rating_states and t not in ('/cancel','/start'):
        state=rating_states[uid];oid=state['order_id'];stars=state['stars']
        if len(t)>1000:send(cid,'Izoh 1000 belgigacha bo‘lsin.');return
        with conn() as c:
            o=c.execute("SELECT * FROM orders WHERE id=? AND customer_id=? AND status='Yetkazildi' AND courier_id IS NOT NULL",(oid,cuid)).fetchone()
            if not o:rating_states.pop(uid,None);send(cid,'Buyurtma topilmadi.');return
            try:c.execute('INSERT INTO ratings(order_id,customer_id,courier_id,stars,comment,created_at) VALUES(?,?,?,?,?,?)',(oid,cuid,o['courier_id'],stars,'' if t=='/skip' else t,now()))
            except sqlite3.IntegrityError:send(cid,'Bu buyurtmaga avval baho bergansiz.');rating_states.pop(uid,None);return
        rating_states.pop(uid,None);send(cid,'✅ Bahoyingiz saqlandi. Rahmat!',main_kb());return
    if uid in support_states and t not in ('/cancel','/start'):
        if not t or len(t)>4000:send(cid,'Murojaatingizni matn bilan yozing (4000 belgigacha).');return
        with conn() as c:
            tid=c.execute('INSERT INTO tickets(role,actor_id,subject,created_at) VALUES(?,?,?,?)',('customer',cuid,t[:100],now())).lastrowid
            c.execute('INSERT INTO ticket_messages(ticket_id,role,body,created_at) VALUES(?,?,?,?)',(tid,'customer',t,now()))
        support_states.pop(uid,None);send(cid,'✅ Murojaat #'+str(tid)+' operatorga yuborildi. Javob shu botga keladi.',main_kb());return
    if t in ('/support','💬 Yordam','/courier',"🛵 Kuryer bo'lish",'/partner','🏪 Restoran hamkorligi'):
        s=settings();txt='💬 Qo‘llab-quvvatlash\n'
        if s.get('support_phone'):txt+='☎ '+s['support_phone']+'\n'
        buttons=[[{'text':'Operatorga xabar yozish','callback_data':'support:new'}]]
        if safe_link(s.get('operator_url','')):buttons.append([{'text':'Telegram operator','url':s['operator_url']}])
        send(cid,txt,{'inline_keyboard':buttons});return
    if t in ('/orders','📦 Buyurtmalarim','/track','📍 Buyurtmani kuzatish'):
        with conn() as c:orders=c.execute('SELECT o.*,r.name rn FROM orders o LEFT JOIN restaurants r ON r.id=o.restaurant_id WHERE customer_id=? ORDER BY o.id DESC LIMIT 10',(cuid,)).fetchall()
        if not orders:send(cid,'Hali buyurtmangiz yo‘q.',main_kb());return
        for o in orders:
            buttons=[];u=tracking_link(o)
            if u:buttons.append([{'text':'📍 Kuzatish','url':u}])
            if o['status']=='Yetkazildi' and o['courier_id']:buttons.append([{'text':'★ Kuryerni baholash','callback_data':'rate:'+str(o['id'])}])
            send(cid,'📦 #'+str(o['id'])+' • '+str(o['rn'])+'\n'+o['status']+'\n'+str(o['total'])+' so‘m',{'inline_keyboard':buttons} if buttons else None)
        return
    _message_v1(msg)

def callback(q):
    uid=q.get('from',{}).get('id');cid=q.get('message',{}).get('chat',{}).get('id');d=q.get('data','')
    if not uid or not cid:return
    if d=='support:new':
        tg('answerCallbackQuery',{'callback_query_id':q.get('id')});support_states[uid]=True;checkout_states.pop(uid,None);rating_states.pop(uid,None);send(cid,'Operatorga xabaringizni yozing. Bekor qilish: /cancel');return
    if d.startswith(('rate:','stars:')):
        tg('answerCallbackQuery',{'callback_query_id':q.get('id')})
        try:oid=int(d.split(':')[1]);stars=int(d.split(':')[2]) if d.startswith('stars:') else None
        except (ValueError,IndexError):return
        with conn() as c:
            o=c.execute("SELECT o.* FROM orders o JOIN customers cu ON cu.id=o.customer_id WHERE o.id=? AND cu.telegram_id=? AND o.status='Yetkazildi' AND o.courier_id IS NOT NULL",(oid,uid)).fetchone()
            rated=c.execute('SELECT 1 FROM ratings WHERE order_id=?',(oid,)).fetchone()
        if not o:send(cid,'Faqat o‘zingizning yetkazilgan buyurtmangizni baholaysiz.');return
        if rated:send(cid,'Bu buyurtmaga baho berilgansiz.');return
        if stars is None:send(cid,'Kuryer xizmatini baholang:',{'inline_keyboard':[[{'text':str(i)+' ★','callback_data':'stars:'+str(oid)+':'+str(i)} for i in range(1,6)]]});return
        if not 1<=stars<=5:return
        rating_states[uid]={'order_id':oid,'stars':stars};checkout_states.pop(uid,None);support_states.pop(uid,None);send(cid,'Izoh yozing yoki izohsiz saqlash uchun /skip yuboring. Bekor qilish: /cancel');return
    if d.startswith('i:'):
        try:_,rid,iid=d.split(':')
        except ValueError:return
        with conn() as c:m=c.execute("SELECT m.* FROM menu_items m JOIN restaurants r ON r.id=m.restaurant_id WHERE m.id=? AND m.restaurant_id=? AND m.status='approved' AND r.status='active'",(iid,rid)).fetchone()
        if not m:return
        tg('answerCallbackQuery',{'callback_query_id':q.get('id')})
        text=m['name']+'\n💰 '+str(m['price'])+' so‘m\n🥗 '+m['ingredients']+'\n'+m['description']
        kb={'inline_keyboard':[[{'text':'➕ Savatga qo‘shish','callback_data':'a:'+str(rid)+':'+str(iid)}],[{'text':'🛒 Savat','callback_data':'cart'}]]}
        photo=m['image_url']
        if photo.startswith('/uploads/'):
            if PUBLIC_BASE_URL:photo=PUBLIC_BASE_URL+photo
            else:
                send_photo_file(cid,UPLOAD_DIR/photo.rsplit('/',1)[-1],text,kb);return
        if photo:
            result=tg('sendPhoto',{'chat_id':cid,'photo':photo,'caption':text[:1024],'reply_markup':json.dumps(kb,ensure_ascii=False)})
            if result and result.get('ok'):return
        send(cid,text,kb);return
    if d.startswith('a:'):
        try:rid=int(d.split(':')[1])
        except (ValueError,IndexError):return
        with conn() as c:r=c.execute('SELECT * FROM restaurants WHERE id=?',(rid,)).fetchone()
        if not r or r['status']!='active':send(cid,'Oshxona vaqtincha mavjud emas.');return
    _callback_v1(q)

def send_photo_file(cid,path,caption,kb):
    if not path.is_file():send(cid,caption,kb);return
    boundary='ak'+secrets.token_hex(16);data=b''
    for k,val in {'chat_id':str(cid),'caption':caption[:1024],'reply_markup':json.dumps(kb,ensure_ascii=False)}.items():data+=('--'+boundary+'\r\nContent-Disposition: form-data; name="'+k+'"\r\n\r\n'+val+'\r\n').encode()
    data+=('--'+boundary+'\r\nContent-Disposition: form-data; name="photo"; filename="'+path.name+'"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+path.read_bytes()+('\r\n--'+boundary+'--\r\n').encode()
    try:
        req=urllib.request.Request(API+'/sendPhoto',data=data,headers={'Content-Type':'multipart/form-data; boundary='+boundary})
        with urllib.request.urlopen(req,timeout=45) as res:result=json.loads(res.read())
        if not result.get('ok'):send(cid,caption,kb)
    except Exception:send(cid,caption,kb)

if __name__=='__main__':
    if not ADMIN_PASSWORD or ADMIN_PASSWORD=='ChangeMe_123!':raise SystemExit('ADMIN_PASSWORD muhit o‘zgaruvchisiga yangi kuchli parol kiriting.')
    init_db();print('ALI KURYER V2 READY')
    if TOKEN:Thread(target=web,daemon=True).start();bot_loop()
    else:print('BOT_TOKEN yo‘q: faqat web panellar ishga tushdi.');web()
