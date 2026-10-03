import os
import time
import json
import sqlite3
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread, Lock
from html import escape

TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
DB_PATH = os.getenv('DB_PATH', 'ali_kuryer.db')
PORT = int(os.getenv('PORT', '10000'))
API = f'https://api.telegram.org/bot{TOKEN}' if TOKEN else ''
DB_LOCK = Lock()

RESTAURANTS = {
    '1': {'name': 'Ali Burger', 'phone': '+998900000001', 'items': {
        '101': {'name': 'Classic Burger', 'price': 30000, 'description': "Mol go'shti, pishloq, salat va sous"},
        '102': {'name': 'Chicken Burger', 'price': 28000, 'description': "Tovuq go'shti, salat va maxsus sous"},
        '103': {'name': 'Fri', 'price': 12000, 'description': 'Qarsildoq kartoshka fri'}}},
    '2': {'name': 'Osh Markazi', 'phone': '+998900000002', 'items': {
        '201': {'name': "O'zbek Palovi", 'price': 35000, 'description': "Guruch, go'sht, sabzi va no'xat"},
        '202': {'name': 'Chuchvara', 'price': 25000, 'description': 'Uy uslubidagi chuchvara'},
        '203': {'name': 'Achichuk', 'price': 10000, 'description': 'Pomidor, piyoz va ko‘katlar'}}},
    '3': {'name': 'Pizza House', 'phone': '+998900000003', 'items': {
        '301': {'name': 'Pepperoni Pizza', 'price': 65000, 'description': 'Pishloq, pepperoni va pomidor sousi'},
        '302': {'name': 'Chicken Pizza', 'price': 60000, 'description': "Tovuq go'shti, pishloq va sous"},
        '303': {'name': 'Margherita', 'price': 50000, 'description': 'Pishloq, pomidor va maxsus sous'}}}
}

carts = {}


def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with DB_LOCK:
        conn = db()
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT DEFAULT '',
            username TEXT DEFAULT '', phone TEXT DEFAULT '', lat REAL, lon REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL,
            restaurant_id TEXT NOT NULL, items_json TEXT NOT NULL, total INTEGER NOT NULL,
            phone TEXT DEFAULT '', address TEXT DEFAULT '', lat REAL, lon REAL,
            payment_method TEXT DEFAULT 'cash', status TEXT DEFAULT 'Qabul qilindi',
            courier_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS couriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, status TEXT DEFAULT 'offline', blocked INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, blocked INTEGER DEFAULT 0
        );
        ''')
        for rid, r in RESTAURANTS.items():
            conn.execute('INSERT OR IGNORE INTO restaurants(id,name,phone) VALUES(?,?,?)', (int(rid), r['name'], r['phone']))
        conn.commit()
        conn.close()


def telegram(method, data=None):
    if not TOKEN:
        return None
    try:
        url = f'{API}/{method}'
        encoded = urllib.parse.urlencode(data or {}).encode('utf-8')
        req = urllib.request.Request(url, data=encoded)
        with urllib.request.urlopen(req, timeout=45) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print('Telegram API xatosi:', e)
        return None


def send_message(chat_id, text, keyboard=None):
    data = {'chat_id': chat_id, 'text': text}
    if keyboard:
        data['reply_markup'] = json.dumps(keyboard, ensure_ascii=False)
    return telegram('sendMessage', data)


def answer_callback(cid, text=''):
    return telegram('answerCallbackQuery', {'callback_query_id': cid, 'text': text})


def main_keyboard():
    return {'keyboard': [
        [{'text': '🍔 Buyurtma berish'}, {'text': '🍽 Restoranlar'}],
        [{'text': '📦 Buyurtmalarim'}, {'text': '📍 Buyurtmani kuzatish'}],
        [{'text': '👤 Profilim'}, {'text': '💬 Yordam'}],
        [{'text': '🛵 Kuryer bo‘lish'}, {'text': '🏪 Restoran hamkorligi'}]
    ], 'resize_keyboard': True}


def restaurants_keyboard():
    return {'inline_keyboard': [[{'text': r['name'], 'callback_data': f'restaurant:{rid}'}] for rid, r in RESTAURANTS.items()]}


def menu_keyboard(rid):
    r = RESTAURANTS[rid]
    rows = [[{'text': f"{i['name']} — {i['price']:,} so'm", 'callback_data': f'item:{rid}:{iid}'}] for iid, i in r['items'].items()]
    rows.append([{'text': '🛒 Savat', 'callback_data': 'cart'}])
    return {'inline_keyboard': rows}


def item_keyboard(rid, iid):
    return {'inline_keyboard': [
        [{'text': '➕ Savatga qo‘shish', 'callback_data': f'add:{rid}:{iid}'}],
        [{'text': '🛒 Savatni ko‘rish', 'callback_data': 'cart'}]
    ]}


def get_cart(uid):
    return carts.setdefault(uid, [])


def cart_text(uid):
    cart = get_cart(uid)
    if not cart:
        return '🛒 Savatingiz hozircha bo‘sh.'
    total = sum(x['price'] for x in cart)
    lines = ['🛒 SAVATINGIZ', '']
    for n, x in enumerate(cart, 1):
        lines += [f"{n}. {x['name']}", f"   {x['price']:,} so'm", '']
    lines.append(f"💰 Jami: {total:,} so'm")
    return '\n'.join(lines)


def cart_keyboard(uid):
    if not get_cart(uid):
        return {'inline_keyboard': [[{'text': '🍔 Buyurtma berish', 'callback_data': 'restaurants'}]]}
    return {'inline_keyboard': [
        [{'text': '✅ Buyurtmani tasdiqlash', 'callback_data': 'checkout'}],
        [{'text': '🗑 Savatni tozalash', 'callback_data': 'clear_cart'}]
    ]}


def save_user(message):
    u = message.get('from', {})
    uid = u.get('id')
    if not uid:
        return None
    with DB_LOCK:
        conn = db()
        conn.execute('''INSERT INTO users(id,first_name,username) VALUES(?,?,?)
                        ON CONFLICT(id) DO UPDATE SET first_name=excluded.first_name, username=excluded.username''',
                     (uid, u.get('first_name', 'Mijoz'), u.get('username', '')))
        conn.commit(); conn.close()
    return uid


def request_contact_keyboard():
    return {'keyboard': [[{'text': '📱 Telefon raqamimni yuborish', 'request_contact': True}], [{'text': '⬅️ Menyu'}]], 'resize_keyboard': True, 'one_time_keyboard': True}


def request_location_keyboard():
    return {'keyboard': [[{'text': '📍 Lokatsiyamni yuborish', 'request_location': True}], [{'text': '⬅️ Menyu'}]], 'resize_keyboard': True, 'one_time_keyboard': True}


def create_order(uid):
    cart = get_cart(uid)
    if not cart:
        return None
    with DB_LOCK:
        conn = db(); u = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
        if not u or not u['phone'] or u['lat'] is None or u['lon'] is None:
            conn.close(); return None
        rid = cart[0]['restaurant_id']
        total = sum(x['price'] for x in cart)
        cur = conn.execute('''INSERT INTO orders(customer_id,restaurant_id,items_json,total,phone,lat,lon,payment_method)
                              VALUES(?,?,?,?,?,?,?,?)''',
                           (uid, rid, json.dumps(cart, ensure_ascii=False), total, u['phone'], u['lat'], u['lon'], 'cash'))
        oid = cur.lastrowid; conn.commit(); conn.close()
    carts[uid] = []
    return oid, total, rid


def handle_message(m):
    chat_id = m.get('chat', {}).get('id'); uid = save_user(m)
    if not chat_id or not uid: return
    text = m.get('text', '').strip()
    contact = m.get('contact'); location = m.get('location')
    if contact and contact.get('phone_number'):
        with DB_LOCK:
            conn=db(); conn.execute('UPDATE users SET phone=? WHERE id=?',(contact['phone_number'],uid)); conn.commit(); conn.close()
        send_message(chat_id, '✅ Telefon raqamingiz saqlandi. Endi aniq lokatsiyangizni yuboring.', request_location_keyboard()); return
    if location:
        with DB_LOCK:
            conn=db(); conn.execute('UPDATE users SET lat=?,lon=? WHERE id=?',(location.get('latitude'),location.get('longitude'),uid)); conn.commit(); conn.close()
        send_message(chat_id, '✅ Lokatsiya saqlandi. Endi buyurtmani tasdiqlashingiz mumkin.', main_keyboard()); return
    if text == '/start':
        send_message(chat_id, '👋 Assalomu alaykum!\n\n🛵 Ali Kuryer botiga xush kelibsiz.', main_keyboard()); return
    if text in ['/order','🍔 Buyurtma berish','/restaurants','🍽 Restoranlar']:
        send_message(chat_id, '🍽 Restoranni tanlang:', restaurants_keyboard()); return
    if text in ['/orders','📦 Buyurtmalarim']:
        with DB_LOCK:
            conn=db(); rows=conn.execute('SELECT * FROM orders WHERE customer_id=? ORDER BY id DESC LIMIT 10',(uid,)).fetchall(); conn.close()
        if not rows: send_message(chat_id,'📦 Sizda hozircha buyurtmalar yo‘q.',main_keyboard()); return
        out=['📦 BUYURTMALARIM','']
        for o in rows: out.append(f"№{o['id']} — {o['total']:,} so'm — {o['status']}")
        send_message(chat_id,'\n'.join(out),main_keyboard()); return
    if text in ['/track','📍 Buyurtmani kuzatish']:
        with DB_LOCK:
            conn=db(); o=conn.execute('SELECT * FROM orders WHERE customer_id=? ORDER BY id DESC LIMIT 1',(uid,)).fetchone(); conn.close()
        send_message(chat_id, f"📍 Buyurtma №{o['id']}\nHolati: {o['status']}" if o else '📍 Avval buyurtma bering.', main_keyboard()); return
    if text in ['/profile','👤 Profilim']:
        with DB_LOCK:
            conn=db(); u=conn.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone(); conn.close()
        send_message(chat_id, f"👤 PROFILIM\n\nIsm: {u['first_name']}\nTelefon: {u['phone'] or 'Kiritilmagan'}\nLokatsiya: {'Saqlangan' if u['lat'] is not None else 'Kiritilmagan'}", main_keyboard()); return
    if text in ['/support','💬 Yordam']:
        send_message(chat_id,'💬 Yordam\n\nAdministrator bilan bog‘laning.',main_keyboard()); return
    if text in ['/courier','🛵 Kuryer bo‘lish']:
        send_message(chat_id,'🛵 KURYER BO‘LISH\n\nIsm-familiya, telefon va transport ma’lumotlari bilan administratorga murojaat qiling.',main_keyboard()); return
    if text in ['/partner','🏪 Restoran hamkorligi']:
        send_message(chat_id,'🏪 RESTORAN HAMKORLIGI\n\nRestoraningizni Ali Kuryer platformasiga ulang.',main_keyboard()); return
    send_message(chat_id,'👇 Kerakli bo‘limni tanlang:',main_keyboard())


def handle_callback(c):
    cid=c.get('id'); data=c.get('data',''); msg=c.get('message',{}); chat_id=msg.get('chat',{}).get('id'); uid=c.get('from',{}).get('id')
    if not chat_id: return
    answer_callback(cid)
    if data in ('restaurants','cart'):
        send_message(chat_id, '🍽 Restoranni tanlang:' if data=='restaurants' else cart_text(uid), restaurants_keyboard() if data=='restaurants' else cart_keyboard(uid)); return
    if data.startswith('restaurant:'):
        rid=data.split(':',1)[1]; r=RESTAURANTS.get(rid)
        if r: send_message(chat_id,f"🍽 {r['name']}\n📞 {r['phone']}\n\nMenyudan taom tanlang:",menu_keyboard(rid))
        return
    if data.startswith('item:'):
        _,rid,iid=data.split(':'); i=RESTAURANTS[rid]['items'].get(iid)
        if i: send_message(chat_id,f"🍽 {i['name']}\n\n💰 Narxi: {i['price']:,} so'm\n📝 {i['description']}",item_keyboard(rid,iid))
        return
    if data.startswith('add:'):
        _,rid,iid=data.split(':'); i=RESTAURANTS[rid]['items'].get(iid)
        if i:
            get_cart(uid).append({'restaurant_id':rid,'restaurant':RESTAURANTS[rid]['name'],'name':i['name'],'price':i['price']})
            send_message(chat_id,'✅ Savatga qo‘shildi.\n\n'+cart_text(uid),cart_keyboard(uid))
        return
    if data=='clear_cart':
        carts[uid]=[]; send_message(chat_id,'🗑 Savat tozalandi.',main_keyboard()); return
    if data=='checkout':
        with DB_LOCK:
            conn=db(); u=conn.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone(); conn.close()
        if not u['phone']:
            send_message(chat_id,'📱 Buyurtma uchun telefon raqamingizni yuboring.',request_contact_keyboard()); return
        if u['lat'] is None:
            send_message(chat_id,'📍 Buyurtma uchun aniq lokatsiyangizni yuboring.',request_location_keyboard()); return
        result=create_order(uid)
        if not result: send_message(chat_id,'❌ Buyurtma yaratilmadi. Qayta urinib ko‘ring.',main_keyboard()); return
        oid,total,rid=result
        send_message(chat_id,f"✅ BUYURTMA QABUL QILINDI!\n\n📦 №{oid}\n🍽 {RESTAURANTS[rid]['name']}\n📞 Restoran: {RESTAURANTS[rid]['phone']}\n💰 Jami: {total:,} so‘m\n📌 Holati: Qabul qilindi\n\n🛵 Kuryer tayinlangach xabar beramiz.",main_keyboard()); return


def bot_loop():
    offset=0; print('Ali Kuryer bot ishga tushdi...')
    while True:
        try:
            result=telegram('getUpdates',{'offset':offset,'timeout':30})
            if not result or not result.get('ok'):
                time.sleep(3); continue
            for update in result.get('result',[]):
                offset=update['update_id']+1
                try:
                    if 'message' in update: handle_message(update['message'])
                    elif 'callback_query' in update: handle_callback(update['callback_query'])
                except Exception as e: print('Update xatosi:',e)
        except Exception as e:
            print('Bot loop xatosi:',e); time.sleep(5)


def admin_page(auth):
    if not auth: return None
    with DB_LOCK:
        conn=db(); users=conn.execute('SELECT COUNT(*) n FROM users').fetchone()['n']; orders=conn.execute('SELECT COUNT(*) n FROM orders').fetchone()['n']; couriers=conn.execute('SELECT COUNT(*) n FROM couriers').fetchone()['n']; restaurants=conn.execute('SELECT COUNT(*) n FROM restaurants').fetchone()['n']; rows=conn.execute('''SELECT o.*,u.first_name FROM orders o LEFT JOIN users u ON u.id=o.customer_id ORDER BY o.id DESC LIMIT 50''').fetchall(); conn.close()
    html=['<!doctype html><html lang="uz"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ali Kuryer Admin</title><style>body{font-family:Arial;background:#111;color:#fff;margin:0;padding:20px}h1{color:#f00}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.card{background:#222;padding:18px;border-radius:12px}.num{font-size:28px;font-weight:bold}table{width:100%;margin-top:20px;border-collapse:collapse;background:#fff;color:#111}th,td{padding:10px;border:1px solid #ddd;text-align:left}@media(max-width:700px){.cards{grid-template-columns:repeat(2,1fr)}table{font-size:12px}}</style><h1>🔴 Ali Kuryer — Admin</h1><div class="cards">']
    for title,n in [('Mijozlar',users),('Buyurtmalar',orders),('Kuryerlar',couriers),('Restoranlar',restaurants)]: html.append(f'<div class="card"><div>{title}</div><div class="num">{n}</div></div>')
    html.append('</div><table><tr><th>ID</th><th>Mijoz</th><th>Telefon</th><th>Summa</th><th>Holat</th><th>Lokatsiya</th></tr>')
    for r in rows:
        loc=f"{r['lat']},{r['lon']}" if r['lat'] is not None else '-'
        html.append(f"<tr><td>#{r['id']}</td><td>{escape(r['first_name'] or '')}</td><td>{escape(r['phone'] or '')}</td><td>{r['total']:,}</td><td>{escape(r['status'])}</td><td>{escape(loc)}</td></tr>")
    html.append('</table></html>')
    return ''.join(html)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/','/health'):
            body=b'Ali Kuryer Bot OK'
            self.send_response(200); self.send_header('Content-Type','text/plain; charset=utf-8'); self.end_headers(); self.wfile.write(body); return
        if self.path.startswith('/admin'):
            auth=False
            header=self.headers.get('Authorization','')
            if header.startswith('Basic '):
                import base64
                try:
                    raw=base64.b64decode(header[6:]).decode('utf-8'); u,p=raw.split(':',1); auth=(u==ADMIN_USER and p==ADMIN_PASSWORD)
                except Exception: pass
            if not auth:
                self.send_response(401); self.send_header('WWW-Authenticate','Basic realm="Ali Kuryer Admin"'); self.end_headers(); return
            body=admin_page(True).encode('utf-8'); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write(body); return
        self.send_response(404); self.end_headers()
    def log_message(self,fmt,*args): pass


def run_server():
    server=HTTPServer(('0.0.0.0',PORT),Handler); print(f'Web server: {PORT}'); server.serve_forever()


if __name__=='__main__':
    if not TOKEN:
        raise SystemExit('XATO: BOT_TOKEN topilmadi.')
    init_db()
    Thread(target=run_server,daemon=True).start()
    bot_loop()
