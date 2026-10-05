# ALI KURYER — ishga tushirish:
# Python 3.9+; tashqi kutubxona talab qilinmaydi.
# BOT_TOKEN: Telegram bot tokeni (yo‘q bo‘lsa faqat web ishlaydi).
# ADMIN_USER: admin login; ADMIN_PASSWORD: yangi kuchli parol (majburiy).
# DB_PATH: mavjud ali_kuryer.db yo‘li; PORT: 10000 (standart).
# HTTPS serverda COOKIE_SECURE=1 o‘rnating.
# Panellar: /admin, /restaurant, /courier. Kuryerni admin yaratadi.
# Menyu rasmi: ochiq https rasm havolasi; tarkib majburiy.
# Yangi va tahrirlangan mahsulot admin tasdig‘idan keyin botda ko‘rinadi.
# Vaqt: Asia/Tashkent; boshlanish=tugash bo‘lsa 24 soat.
# Bazani yangilashdan avval zaxira nusxasini saqlang.
# Eski loginlar saqlanadi; demo oshxona parollarini haqiqiy ishda almashtiring.
# Kuryer kuzatuvi buyurtma va qabul qilish vaqtiga asoslangan; GPS yo‘q.

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
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL DEFAULT '');
        """)
        defaults={'operator_phone':'','complaints_phone':'','telegram_bot':'https://t.me/AliKuryerBot','ai_enabled':'0'}
        for k,v in defaults.items(): c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))

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
    token=ck.get('ak')
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
    links={
        'admin':[('/admin','Umumiy nazorat'),('/admin/restaurants','Oshxonalar'),('/admin/menu','Menyu'),('/admin/orders','Buyurtmalar'),('/admin/couriers','Kuryerlar'),('/adm
