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
    links={'admin':[('', 'Umumiy nazorat'),('/restaurants','Oshxonalar'),('/menu','Menyu'),('/orders','Buyurtmalar'),('/couriers','Kuryerlar'),('/history','O‘zgarishlar tarixi'),('/settings','Aloqa / AI')], 'restaurant':[('','Oshxona'),('/menu','Taom va ichimliklar'),('/orders','Buyurtmalar')], 'courier':[('','Buyurtmalar')]}[role]
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
    if role=='courier':where,args=(" WHERE (o.courier_id=? OR (o.courier_id IS NULL AND o.status='Tayyor'))",(se['id'],))
    rows=c.execute('SELECT o.*,r.name rn,r.address pickup,cu.first_name cn,cr.name courier FROM orders o LEFT JOIN restaurants r ON r.id=o.restaurant_id LEFT JOIN customers cu ON cu.id=o.customer_id LEFT JOIN couriers cr ON cr.id=o.courier_id'+where+' ORDER BY o.id DESC LIMIT 200',args).fetchall()
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
        text+='<tr><td>#'+str(o['id'])+'<br>'+esc(details)+'</td><td>'+esc(o['rn'])+'<br>'+esc(o['pickup'])+'</td><td>'+esc(o['cn'])+'<br>'+esc(o['phone'])+'<br>'+esc(o['address'])+'</td><td>'+str(o['total'])+'</td><td>'+esc(o['status'])+'<br>'+esc(o['courier'])+'</td><td>'+action+'</td></tr>'
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
                body+='<div class="card"><h1>Taom va ichimlik '+('tahrirlash' if m else 'qo‘shish')+'</h1>'+menu_editor(se,m)+'</div><div class="card">'
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
            elif path.endswith('/settings'):
                st={x['key']:x['value'] for x in c.execute('SELECT * FROM settings')}
                fields=field('operator_phone','Operator telefoni',st.get('operator_phone',''))+field('complaints_phone','Shikoyatlar telefoni',st.get('complaints_phone',''))+field('telegram_bot','Telegram bot manzili',st.get('telegram_bot',''),required=True)+'<label>AI yordamchi<select name="ai_enabled"><option value="0">O‘chiq</option><option value="1" '+('selected' if st.get('ai_enabled')=='1' else '')+'>Ulashga tayyor</option></select></label>'
                body+='<div class="card"><h1>Aloqa va AI sozlamalari</h1><p>Telefonlar va Telegram bot manzilini shu yerdan o‘zgartirasiz.</p>'+post_form('/admin/settings',se['csrf'],fields)+'</div>'
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
            self.red('/'+role,'ak='+token+'; Path=/; HttpOnly; SameSite=Lax; Max-Age='+str(SESSION_TTL)+('; Secure' if os.getenv('COOKIE_SECURE')=='1' else ''));return
        se=session(self,role)
        if not se:self.out(login_page(role),401);return
        if not secrets.compare_digest(v('csrf'),se['csrf']):self.out('So‘rov tasdiqlanmadi',403);return
        if path=='/'+role+'/logout':
            for token,val in list(sessions.items()):
                if val is se:sessions.pop(token,None)
            self.red('/','ak=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0');return
        with conn() as c:
            if path=='/admin/settings':
                for k in ('operator_phone','complaints_phone','telegram_bot','ai_enabled'):
                    c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,v(k)))
                audit(c,role,se['id'],'Sozlamalar yangilandi','settings',0,after={'telegram_bot':v('telegram_bot'),'operator_phone':v('operator_phone')});target='/admin/settings'
            elif path in ('/admin/restaurants/new','/admin/couriers/new'):
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
                if not data['name'] or data['price']<=0 or not data['ingredients'] or url.scheme!='https' or not url.netloc or data['kind'] not in ('Taom','Ichimlik'):raise ValueError('Nom, musbat narx, tarkib va https rasm havolasi talab qilinadi.')
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
                updated=c.execute("UPDATE orders SET courier_id=?,claimed_at=?,status='Kuryer qabul qildi' WHERE id=? AND courier_id IS NULL AND status='Tayyor'",(se['id'],ts,eid))
                if updated.rowcount!=1:raise ValueError('Buyurtma boshqa kuryer tomonidan olingan yoki hali tayyor emas.')
                audit(c,role,se['id'],'Kuryer qabul qildi','orders',eid,after={'courier_id':se['id'],'claimed_at':ts});target='/courier'
            else:self.out('Topilmadi',404);return
        self.red(target)
    def log_message(self,*a):pass

def web():
    port=int(os.getenv('PORT','10000'));ThreadingHTTPServer(('0.0.0.0',port),H).serve_forever()

if __name__=='__main__':
    if not ADMIN_PASSWORD or ADMIN_PASSWORD=='ChangeMe_123!':
        raise SystemExit('ADMIN_PASSWORD muhit o‘zgaruvchisiga yangi kuchli parol kiriting.')
    init_db();print('ALI KURYER READY')
    if TOKEN:
        Thread(target=web,daemon=True).start();bot_loop()
    else:
        print('BOT_TOKEN yo‘q: faqat web panellar ishga tushdi.');web()
