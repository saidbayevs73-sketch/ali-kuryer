# ALI KURYER — Render uchun to'liq tiklangan versiya
# Python 3.9+; tashqi kutubxona talab qilinmaydi.
# Render Start Command: python bot.py
# Environment: BOT_TOKEN, ADMIN_USER, ADMIN_PASSWORD, DB_PATH, PORT

import os, time, json, html, base64, hashlib, sqlite3
import urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

TOKEN = os.getenv('BOT_TOKEN', '')
API = 'https://api.telegram.org/bot' + TOKEN
DB = os.getenv('DB_PATH', 'ali_kuryer.db')
PORT = int(os.getenv('PORT', '10000'))
ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'ChangeMe_123!')
BOT_LINK = os.getenv('BOT_LINK', 'https://t.me/AliKuryerBot')

carts = {}
checkout = {}


def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c


def ph(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def init_db():
    with conn() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS customers(
          id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE,
          first_name TEXT DEFAULT '', username TEXT DEFAULT '', phone TEXT DEFAULT '',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS restaurants(
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT DEFAULT '', address TEXT DEFAULT '',
          login TEXT UNIQUE, password_hash TEXT DEFAULT '', status TEXT DEFAULT 'active',
          opens_at TEXT DEFAULT '09:00', closes_at TEXT DEFAULT '23:00', accepting_orders INTEGER DEFAULT 1,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS menu_items(
          id INTEGER PRIMARY KEY, restaurant_id INTEGER NOT NULL, name TEXT NOT NULL,
          price INTEGER NOT NULL, ingredients TEXT DEFAULT '', description TEXT DEFAULT '',
          image_url TEXT DEFAULT '', status TEXT DEFAULT 'approved',
          FOREIGN KEY(restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS couriers(
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT DEFAULT '', login TEXT UNIQUE,
          password_hash TEXT DEFAULT '', status TEXT DEFAULT 'active', online INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS orders(
          id INTEGER PRIMARY KEY, customer_id INTEGER, restaurant_id INTEGER, courier_id INTEGER,
          total INTEGER NOT NULL, status TEXT DEFAULT 'Qabul qilindi', phone TEXT DEFAULT '',
          address TEXT DEFAULT '', payment TEXT DEFAULT 'Naqd', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(customer_id) REFERENCES customers(id),
          FOREIGN KEY(restaurant_id) REFERENCES restaurants(id),
          FOREIGN KEY(courier_id) REFERENCES couriers(id)
        );
        CREATE TABLE IF NOT EXISTS order_items(
          id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, item_id INTEGER,
          name TEXT, price INTEGER, qty INTEGER,
          FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS logs(
          id INTEGER PRIMARY KEY, action TEXT, details TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        for k, v in {
            'operator_phone':'', 'complaints_phone':'', 'telegram_bot':BOT_LINK,
            'delivery_fee':'0', 'ai_enabled':'0'
        }.items():
            c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)', (k,v))
        if c.execute('SELECT COUNT(*) n FROM restaurants').fetchone()['n'] == 0:
            seeds = [
                ('Ali Burger','901111111','Toshkent','aliburger'),
                ('Osh Markazi','902222222','Toshkent','oshmarkazi'),
                ('Pizza House','903333333','Toshkent','pizzahouse')
            ]
            for name, phone, address, login in seeds:
                c.execute('INSERT INTO restaurants(name,phone,address,login,password_hash) VALUES(?,?,?,?,?)',
                          (name,phone,address,login,ph('123456')))
            ids = {r['name']:r['id'] for r in c.execute('SELECT id,name FROM restaurants')}
            menu = [
                (ids['Ali Burger'],'Classic Burger',30000,"Mol go'shti, pishloq, salat va sous",'Mazali klassik burger'),
                (ids['Ali Burger'],'Chicken Burger',28000,"Tovuq go'shti, salat va maxsus sous",'Tovuqli burger'),
                (ids['Ali Burger'],'Fri',12000,'Kartoshka','Qarsildoq kartoshka fri'),
                (ids['Osh Markazi'],"O'zbek Palovi",35000,"Guruch, go'sht, sabzi va no'xat",'Milliy palov'),
                (ids['Osh Markazi'],'Chuchvara',25000,"Xamir, go'sht",'Uy uslubidagi chuchvara'),
                (ids['Osh Markazi'],'Achichuk',10000,"Pomidor, piyoz, ko'kat",'Yangi salat'),
                (ids['Pizza House'],'Pepperoni Pizza',65000,'Pishloq, pepperoni, pomidor sousi','Pepperoni pizza'),
                (ids['Pizza House'],'Chicken Pizza',60000,"Tovuq go'shti, pishloq, sous",'Tovuqli pizza'),
                (ids['Pizza House'],'Margherita',50000,'Pishloq, pomidor, sous','Klassik pizza')
            ]
            c.executemany('INSERT INTO menu_items(restaurant_id,name,price,ingredients,description) VALUES(?,?,?,?,?)', menu)


def tg(method, data=None):
    if not TOKEN:
        return None
    try:
        req = urllib.request.Request(API+'/'+method, data=urllib.parse.urlencode(data or {}).encode())
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print('TG:', e)
        return None


def send(cid, text, kb=None):
    d = {'chat_id':cid, 'text':text}
    if kb:
        d['reply_markup'] = json.dumps(kb, ensure_ascii=False)
    return tg('sendMessage', d)


def main_kb():
    return {'keyboard':[
        [{'text':'🍔 Buyurtma berish'},{'text':'🍽 Restoranlar'}],
        [{'text':'📦 Buyurtmalarim'},{'text':'📍 Buyurtmani kuzatish'}],
        [{'text':'👤 Profilim'},{'text':'💬 Yordam'}],
        [{'text':"🛵 Kuryer bo'lish"},{'text':'🏪 Restoran hamkorligi'}]
    ], 'resize_keyboard':True}


def customer(msg):
    u = msg.get('from', {})
    tid = u.get('id')
    if not tid: return None
    with conn() as c:
        r = c.execute('SELECT id FROM customers WHERE telegram_id=?',(tid,)).fetchone()
        if r:
            c.execute('UPDATE customers SET first_name=?,username=? WHERE telegram_id=?',
                      (u.get('first_name','Mijoz'),u.get('username',''),tid))
            return r['id']
        return c.execute('INSERT INTO customers(telegram_id,first_name,username) VALUES(?,?,?)',
                         (tid,u.get('first_name','Mijoz'),u.get('username',''))).lastrowid


def restaurants_kb():
    with conn() as c:
        rs = c.execute("SELECT id,name FROM restaurants WHERE status='active' AND accepting_orders=1 ORDER BY name").fetchall()
    return {'inline_keyboard':[[{'text':r['name'],'callback_data':f"r:{r['id']}"}] for r in rs]}


def menu_kb(rid):
    with conn() as c:
        ms = c.execute("SELECT id,name,price FROM menu_items WHERE restaurant_id=? AND status='approved' ORDER BY id",(rid,)).fetchall()
    b = [[{'text':f"{m['name']} — {m['price']:,} so'm",'callback_data':f"i:{rid}:{m['id']}"}] for m in ms]
    b.append([{'text':'🛒 Savat','callback_data':'cart'}])
    return {'inline_keyboard':b}


def cart_text(uid):
    a = carts.get(uid, [])
    if not a: return "🛒 Savatingiz bo'sh."
    total = 0; lines = ['🛒 SAVAT','']
    for i,x in enumerate(a,1):
        sub = x['price']*x['qty']; total += sub
        lines.append(f"{i}. {x['name']} x{x['qty']} — {sub:,} so'm")
    lines += ['',f"💰 Jami: {total:,} so'm"]
    return '\n'.join(lines)


def cart_kb():
    return {'inline_keyboard':[
        [{'text':'✅ Buyurtmani tasdiqlash','callback_data':'checkout'}],
        [{'text':'🗑 Savatni tozalash','callback_data':'clear'}],
        [{'text':'🍽 Restoranlar','callback_data':'restaurants'}]
    ]}


def make_order(uid):
    a = carts.get(uid, [])
    st = checkout.get(uid, {})
    if not a or not st.get('address'): return None
    with conn() as c:
        cu = c.execute('SELECT * FROM customers WHERE telegram_id=?',(uid,)).fetchone()
        total = sum(x['price']*x['qty'] for x in a)
        oid = c.execute('INSERT INTO orders(customer_id,restaurant_id,total,phone,address,payment) VALUES(?,?,?,?,?,?)',
                        (cu['id'],a[0]['rid'],total,cu['phone'],st['address'],st.get('payment','Naqd'))).lastrowid
        for x in a:
            c.execute('INSERT INTO order_items(order_id,item_id,name,price,qty) VALUES(?,?,?,?,?)',
                      (oid,x['item_id'],x['name'],x['price'],x['qty']))
    carts[uid]=[]; checkout.pop(uid,None)
    return oid,total


def message(msg):
    cid = msg.get('chat',{}).get('id'); uid = msg.get('from',{}).get('id')
    if not cid or not uid: return
    customer(msg)
    t = msg.get('text','').strip()
    state = checkout.get(uid)
    if t == '/cancel':
        checkout.pop(uid,None); send(cid,'Bekor qilindi.',main_kb()); return
    if state:
        if state['step']=='phone':
            contact = msg.get('contact',{})
            phone = contact.get('phone_number') or t
            if len(phone) < 7:
                send(cid,"Telefon raqamini to'g'ri kiriting."); return
            with conn() as c: c.execute('UPDATE customers SET phone=? WHERE telegram_id=?',(phone,uid))
            state['step']='address'; send(cid,"📍 Yetkazish manzilini yozing. Bekor qilish: /cancel"); return
        if state['step']=='address':
            if len(t)<5: send(cid,"To'liq manzilni yozing."); return
            state['address']=t; state['step']='payment'
            send(cid,'💳 To‘lov usulini tanlang:',{'inline_keyboard':[
                [{'text':'💵 Naqd','callback_data':'pay:Naqd'}],
                [{'text':'💳 Bank karta','callback_data':'pay:Karta'}],
                [{'text':'📲 Online','callback_data':'pay:Online'}]
            ]}); return
    if t=='/start': send(cid,'👋 Assalomu alaykum!\n\n🛵 Ali Kuryer botiga xush kelibsiz.',main_kb()); return
    if t in ('/order','🍔 Buyurtma berish','/restaurants','🍽 Restoranlar'):
        send(cid,'🍽 Restoranni tanlang:',restaurants_kb()); return
    if t in ('/orders','📦 Buyurtmalarim'):
        with conn() as c:
            rows=c.execute('SELECT o.*,r.name rn FROM orders o LEFT JOIN restaurants r ON r.id=o.restaurant_id LEFT JOIN customers cu ON cu.id=o.customer_id WHERE cu.telegram_id=? ORDER BY o.id DESC LIMIT 10',(uid,)).fetchall()
        if not rows: send(cid,"📦 Buyurtmalar yo'q.",main_kb()); return
        s='📦 BUYURTMALARIM\n\n'+''.join(f"№{x['id']} — {x['rn']}\n💰 {x['total']:,} so'm\n📌 {x['status']}\n\n" for x in rows)
        send(cid,s,main_kb()); return
    if t in ('/track','📍 Buyurtmani kuzatish'):
        with conn() as c:
            x=c.execute('SELECT o.*,r.name rn FROM orders o LEFT JOIN restaurants r ON r.id=o.restaurant_id LEFT JOIN customers cu ON cu.id=o.customer_id WHERE cu.telegram_id=? ORDER BY o.id DESC LIMIT 1',(uid,)).fetchone()
        send(cid,'📍 Buyurtma topilmadi.',main_kb()) if not x else send(cid,f"📍 №{x['id']}\n🏪 {x['rn']}\n📌 {x['status']}",main_kb()); return
    if t in ('/profile','👤 Profilim'):
        with conn() as c: x=c.execute('SELECT * FROM customers WHERE telegram_id=?',(uid,)).fetchone()
        send(cid,f"👤 PROFIL\n\nIsm: {x['first_name']}\nTelefon: {x['phone'] or 'Kiritilmagan'}\nTelegram ID: {uid}",main_kb()); return
    if t in ('/support','💬 Yordam'):
        with conn() as c: p=c.execute("SELECT value FROM settings WHERE key='operator_phone'").fetchone()['value']
        send(cid,'💬 Yordam'+(('\n📞 '+p) if p else ': administrator bilan bog‘laning.'),main_kb()); return
    if t in ('/courier',"🛵 Kuryer bo'lish"):
        send(cid,"🛵 Kuryer bo'lish uchun administratorga murojaat qiling.",main_kb()); return
    if t in ('/partner','🏪 Restoran hamkorligi'):
        send(cid,'🏪 Restoran hamkorligi uchun administratorga murojaat qiling.',main_kb()); return
    send(cid,"👇 Kerakli bo'limni tanlang:",main_kb())


def callback(q):
    cid=q.get('message',{}).get('chat',{}).get('id'); uid=q.get('from',{}).get('id'); d=q.get('data','')
    if not cid or not uid: return
    tg('answerCallbackQuery',{'callback_query_id':q.get('id')})
    if d=='restaurants': send(cid,'🍽 Restoranni tanlang:',restaurants_kb()); return
    if d.startswith('r:'):
        rid=int(d.split(':')[1])
        with conn() as c: r=c.execute("SELECT name FROM restaurants WHERE id=? AND status='active'",(rid,)).fetchone()
        if r: send(cid,f"🍽 {r['name']}\n\nMenyudan taom tanlang:",menu_kb(rid))
        return
    if d.startswith('i:'):
        _,rid,iid=d.split(':')
        with conn() as c: m=c.execute("SELECT * FROM menu_items WHERE id=? AND restaurant_id=? AND status='approved'",(iid,rid)).fetchone()
        if not m: return
        if m['image_url']: tg('sendPhoto',{'chat_id':cid,'photo':m['image_url'],'caption':m['name']})
        send(cid,f"🍽 {m['name']}\n💰 {m['price']:,} so'm\n🥗 {m['ingredients']}\n📝 {m['description']}",
             {'inline_keyboard':[[{'text':"➕ Savatga qo'shish",'callback_data':f'a:{rid}:{iid}'}],[{'text':'🛒 Savat','callback_data':'cart'}]]}); return
    if d.startswith('a:'):
        _,rid,iid=d.split(':')
        with conn() as c: m=c.execute("SELECT * FROM menu_items WHERE id=? AND restaurant_id=? AND status='approved'",(iid,rid)).fetchone()
        if not m: return
        a=carts.setdefault(uid,[])
        if a and a[0]['rid']!=int(rid): send(cid,'⚠️ Savatda boshqa restoran bor. Avval savatni tozalang.',cart_kb()); return
        for x in a:
            if x['item_id']==int(iid): x['qty']+=1; break
        else: a.append({'rid':int(rid),'item_id':int(iid),'name':m['name'],'price':m['price'],'qty':1})
        send(cid,"✅ Savatga qo'shildi!\n\n"+cart_text(uid),cart_kb()); return
    if d=='cart': send(cid,cart_text(uid),cart_kb()); return
    if d=='clear': carts[uid]=[]; checkout.pop(uid,None); send(cid,'🗑 Savat tozalandi.',main_kb()); return
    if d=='checkout':
        if not carts.get(uid): send(cid,"🛒 Savat bo'sh.",main_kb()); return
        checkout[uid]={'step':'phone'}
        send(cid,'📞 Telefon raqamingizni yuboring yoki yozing. Bekor qilish: /cancel',{'keyboard':[[{'text':'Telefonni yuborish','request_contact':True}]],'resize_keyboard':True}); return
    if d.startswith('pay:'):
        if uid not in checkout: return
        checkout[uid]['payment']=d.split(':',1)[1]
        result=make_order(uid)
        if not result: send(cid,'Buyurtmani yaratib bo‘lmadi.',main_kb()); return
        oid,total=result
        send(cid,f"✅ BUYURTMA QABUL QILINDI!\n\n📦 №{oid}\n💰 {total:,} so'm\n📌 Qabul qilindi",main_kb())


def bot_loop():
    if not TOKEN:
        print('BOT_TOKEN yo‘q — Telegram qismi ishga tushmadi.'); return
    off=0; print('Ali Kuryer Telegram bot ishga tushdi')
    while True:
        try:
            r=tg('getUpdates',{'offset':off,'timeout':30})
            if not r or not r.get('ok'): time.sleep(3); continue
            for u in r.get('result',[]):
                off=u['update_id']+1
                try:
                    if 'message' in u: message(u['message'])
                    elif 'callback_query' in u: callback(u['callback_query'])
                except Exception as e: print('update:',e)
        except Exception as e: print('loop:',e); time.sleep(5)


def esc(x): return html.escape(str(x or ''))


def basic_ok(h):
    a=h.headers.get('Authorization','')
    if not a.startswith('Basic '): return False
    try:
        u,p=base64.b64decode(a[6:]).decode().split(':',1)
        return u==ADMIN_USER and p==ADMIN_PASSWORD
    except Exception: return False


def admin_page():
    with conn() as c:
        counts={
            'orders':c.execute('SELECT COUNT(*) n FROM orders').fetchone()['n'],
            'restaurants':c.execute('SELECT COUNT(*) n FROM restaurants').fetchone()['n'],
            'couriers':c.execute('SELECT COUNT(*) n FROM couriers').fetchone()['n'],
            'customers':c.execute('SELECT COUNT(*) n FROM customers').fetchone()['n']
        }
        orders=c.execute('SELECT o.*,r.name rn FROM orders o LEFT JOIN restaurants r ON r.id=o.restaurant_id ORDER BY o.id DESC LIMIT 20').fetchall()
    rows=''.join(f"<tr><td>#{x['id']}</td><td>{esc(x['rn'])}</td><td>{x['total']:,}</td><td>{esc(x['status'])}</td><td>{esc(x['address'])}</td></tr>" for x in orders)
    return f'''<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ali Kuryer Admin</title><style>body{{font-family:Arial;margin:0;background:#f4f4f4;color:#171717}}header{{background:#111;color:#fff;padding:20px}}.wrap{{max-width:1100px;margin:auto;padding:18px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}}.card{{background:#fff;padding:18px;border-radius:12px;border-top:4px solid #e21d2f}}table{{width:100%;background:#fff;border-collapse:collapse;margin-top:18px}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}a{{color:#e21d2f}}</style></head><body><header><b>🛵 Ali Kuryer — Admin</b></header><div class="wrap"><div class="cards"><div class="card">Buyurtmalar<br><b>{counts['orders']}</b></div><div class="card">Restoranlar<br><b>{counts['restaurants']}</b></div><div class="card">Kuryerlar<br><b>{counts['couriers']}</b></div><div class="card">Mijozlar<br><b>{counts['customers']}</b></div></div><h2>So‘nggi buyurtmalar</h2><table><tr><th>ID</th><th>Restoran</th><th>Jami</th><th>Holat</th><th>Manzil</th></tr>{rows}</table><p>Telegram: <a href="{esc(BOT_LINK)}">{esc(BOT_LINK)}</a></p></div></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, code, body, ctype='text/plain; charset=utf-8'):
        if isinstance(body,str): body=body.encode('utf-8')
        self.send_response(code); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path in ('/','/health'):
            self.send_bytes(200,'Ali Kuryer ishlayapti')
        elif path=='/admin':
            if not basic_ok(self):
                self.send_response(401); self.send_header('WWW-Authenticate','Basic realm="Ali Kuryer Admin"'); self.end_headers(); return
            self.send_bytes(200,admin_page(),'text/html; charset=utf-8')
        elif path in ('/restaurant','/courier'):
            self.send_bytes(200,'Ali Kuryer paneli tayyorlanmoqda.','text/plain; charset=utf-8')
        else:
            self.send_bytes(404,'Topilmadi')
    def log_message(self, fmt, *args): pass


def run():
    init_db()
    if TOKEN: Thread(target=bot_loop,daemon=True).start()
    server=ThreadingHTTPServer(('0.0.0.0',PORT),Handler)
    print(f'Web server 0.0.0.0:{PORT} da ishga tushdi')
    server.serve_forever()


if __name__=='__main__':
    run()
