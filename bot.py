import os, time, json, html, base64, hashlib, secrets, sqlite3
import urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise SystemExit('BOT_TOKEN topilmadi')
API = 'https://api.telegram.org/bot' + TOKEN
DB = os.getenv('DB_PATH','ali_kuryer.db')
ADMIN_USER = os.getenv('ADMIN_USER','admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD','ChangeMe_123!')
carts = {}
sessions = {}

def conn():
    c=sqlite3.connect(DB,timeout=30); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON'); return c

def ph(s): return hashlib.sha256(s.encode()).hexdigest()

def init_db():
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
    c=conn(); rs=c.execute("SELECT id,name FROM restaurants WHERE status='active' ORDER BY name").fetchall(); c.close()
    return {'inline_keyboard':[[{'text':r['name'],'callback_data':f"r:{r['id']}"}] for r in rs]}

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

def make_order(uid):
    a=carts.get(uid,[])
    if not a:return None
    c=conn(); cu=c.execute('SELECT id,phone FROM customers WHERE telegram_id=?',(uid,)).fetchone()
    if not cu:return None
    total=sum(x['price']*x['qty'] for x in a); rid=a[0]['rid']
    oid=c.execute('INSERT INTO orders(customer_id,restaurant_id,total,phone) VALUES(?,?,?,?)',(cu['id'],rid,total,cu['phone'])).lastrowid
    for x in a:c.execute('INSERT INTO order_items(order_id,item_id,name,price,qty) VALUES(?,?,?,?,?)',(oid,x['item_id'],x['name'],x['price'],x['qty']))
    c.commit();c.close();carts[uid]=[];return oid,total

def message(msg):
    cid=msg.get('chat',{}).get('id'); uid=msg.get('from',{}).get('id');
    if not cid or not uid:return
    customer(msg); t=msg.get('text','').strip()
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
    if d=='clear':carts[uid]=[];send(cid,'🗑 Savat tozalandi.',main_kb());return
    if d=='checkout':
        r=make_order(uid)
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

def rest_auth(h):
    ck=h.headers.get('Cookie','')
    for p in ck.split(';'):
        if p.strip().startswith('rk='):return sessions.get(p.strip()[3:])
    return None

def page(title,body):return '<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ali Kuryer</title><style>body{font-family:Arial;background:#f3f3f3;margin:0}header{background:#111;color:#fff;padding:18px;font-size:22px}nav{background:#fff;padding:12px}nav a{margin:5px;text-decoration:none;color:#111}.wrap{max-width:1100px;margin:20px auto;padding:10px}.card{background:#fff;padding:18px;margin:12px 0;border-radius:10px}input,textarea,select{width:100%;padding:10px;margin:5px 0 12px;box-sizing:border-box}button,.btn{background:#e60000;color:white;border:0;padding:10px 14px;border-radius:7px;text-decoration:none}table{width:100%;border-collapse:collapse;background:#fff}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left}</style></head><body><header>🛵 Ali Kuryer</header>'+body+'</body></html>'

def nav(admin=False):return '<nav>'+('<a href="/admin">📊 Dashboard</a><a href="/admin/restaurants">🏪 Restoranlar</a><a href="/admin/menu">🍽 Menyu</a><a href="/admin/orders">📦 Buyurtmalar</a>' if admin else '<a href="/restaurant">📊 Dashboard</a><a href="/restaurant/menu">🍽 Menyu</a><a href="/restaurant/orders">📦 Buyurtmalar</a>')+'</nav>'

def admin_page(path):
    c=conn()
    if path=='/admin':
        a=[c.execute('SELECT COUNT(*) n FROM customers').fetchone()['n'],c.execute('SELECT COUNT(*) n FROM restaurants').fetchone()['n'],c.execute('SELECT COUNT(*) n FROM menu_items').fetchone()['n'],c.execute('SELECT COUNT(*) n FROM orders').fetchone()['n']]
        body=nav(True)+f'<div class="wrap"><div class="card"><h1>Admin Dashboard</h1><h2>👤 Mijozlar: {a[0]}</h2><h2>🏪 Restoranlar: {a[1]}</h2><h2>🍽 Taomlar: {a[2]}</h2><h2>📦 Buyurtmalar: {a[3]}</h2></div></div>'
    elif path=='/admin/restaurants':
        rs=c.execute('SELECT * FROM restaurants ORDER BY id DESC').fetchall(); rows=''.join(f"<tr><td>{r['id']}</td><td>{esc(r['name'])}</td><td>{esc(r['phone'])}</td><td>{esc(r['address'])}</td><td>{esc(r['login'])}</td><td>{r['status']}</td></tr>" for r in rs)
        body=nav(True)+'''<div class="wrap"><div class="card"><h1>🏪 Restoran qo'shish</h1><form method="post" action="/admin/restaurants/new"><input name="name" placeholder="Restoran nomi" required><input name="phone" placeholder="Telefon"><input name="address" placeholder="Manzil"><input name="login" placeholder="Login" required><input name="password" placeholder="Parol" required><button>Yaratish</button></form></div><div class="card"><table><tr><th>ID</th><th>Nomi</th><th>Telefon</th><th>Manzil</th><th>Login</th><th>Holat</th></tr>ROWS</table></div></div>'''.replace('ROWS',rows)
    elif path=='/admin/menu':
        ms=c.execute('SELECT m.*,r.name rn FROM menu_items m JOIN restaurants r ON r.id=m.restaurant_id ORDER BY m.id DESC').fetchall(); rows=''
        for m in ms:
            act=(f'<a class="btn" href="/admin/menu/ok?id={m["id"]}">Tasdiqlash</a>' if m['status']=='pending' else esc(m['status']))
            rows+=f"<tr><td>{m['id']}</td><td>{esc(m['rn'])}</td><td>{esc(m['name'])}</td><td>{m['price']:,}</td><td>{esc(m['category'])}</td><td>{act}</td></tr>"
        body=nav(True)+f'<div class="wrap"><div class="card"><h1>🍽 Menyu nazorati</h1><p>Restoran qo\'shgan yangi taomlar avval pending bo\'ladi. Admin tasdiqlagach mijozlarga chiqadi.</p><table><tr><th>ID</th><th>Restoran</th><th>Taom</th><th>Narx</th><th>Kategoriya</th><th>Amal</th></tr>{rows}</table></div></div>'
    else:
        os_=c.execute('SELECT o.*,r.name rn,cu.first_name cn,cu.phone cp FROM orders o LEFT JOIN restaurants r ON r.id=o.restaurant_id LEFT JOIN customers cu ON cu.id=o.customer_id ORDER BY o.id DESC LIMIT 100').fetchall(); rows=''.join(f"<tr><td>#{o['id']}</td><td>{esc(o['cn'])}</td><td>{esc(o['rn'])}</td><td>{esc(o['cp'])}</td><td>{o['total']:,}</td><td>{esc(o['status'])}</td></tr>" for o in os_)
        body=nav(True)+f'<div class="wrap"><div class="card"><h1>📦 Buyurtmalar</h1><table><tr><th>ID</th><th>Mijoz</th><th>Restoran</th><th>Telefon</th><th>Summa</th><th>Holat</th></tr>{rows}</table></div></div>'
    c.close();return page('Admin',body)

def rest_page(r,path):
    c=conn()
    if path=='/restaurant':
        n=c.execute('SELECT COUNT(*) n FROM menu_items WHERE restaurant_id=?',(r['id'],)).fetchone()['n'];p=c.execute("SELECT COUNT(*) n FROM menu_items WHERE restaurant_id=? AND status='pending'",(r['id'],)).fetchone()['n'];o=c.execute('SELECT COUNT(*) n FROM orders WHERE restaurant_id=?',(r['id'],)).fetchone()['n']
        body=nav()+f'<div class="wrap"><div class="card"><h1>🏪 {esc(r["name"])}</h1><h2>🍽 Taomlar: {n}</h2><h2>⏳ Tasdiq kutmoqda: {p}</h2><h2>📦 Buyurtmalar: {o}</h2></div></div>'
    elif path=='/restaurant/menu':
        ms=c.execute('SELECT * FROM menu_items WHERE restaurant_id=? ORDER BY id DESC',(r['id'],)).fetchall(); rows=''.join(f"<tr><td>{m['id']}</td><td>{esc(m['name'])}</td><td>{m['price']:,}</td><td>{esc(m['category'])}</td><td>{m['status']}</td></tr>" for m in ms)
        body=nav()+'''<div class="wrap"><div class="card"><h1>🍽 Taom qo'shish</h1><form method="post" action="/restaurant/menu/new"><input name="name" placeholder="Taom nomi" required><input name="price" type="number" placeholder="Narxi" required><input name="category" placeholder="Kategoriya"><textarea name="ingredients" placeholder="Tarkibi"></textarea><textarea name="description" placeholder="Tavsifi"></textarea><input name="weight" placeholder="Og'irligi, masalan 450 g"><input name="image_url" placeholder="Rasm URL"><button>Admin tasdig'iga yuborish</button></form></div><div class="card"><table><tr><th>ID</th><th>Taom</th><th>Narx</th><th>Kategoriya</th><th>Holat</th></tr>ROWS</table></div></div>'''.replace('ROWS',rows)
    else:
        os_=c.execute('SELECT o.*,cu.first_name,cu.phone FROM orders o LEFT JOIN customers cu ON cu.id=o.customer_id WHERE o.restaurant_id=? ORDER BY o.id DESC',(r['id'],)).fetchall(); rows=''.join(f"<tr><td>#{o['id']}</td><td>{esc(o['first_name'])}</td><td>{esc(o['phone'])}</td><td>{o['total']:,}</td><td>{esc(o['status'])}</td></tr>" for o in os_);body=nav()+f'<div class="wrap"><div class="card"><h1>📦 Buyurtmalar</h1><table><tr><th>ID</th><th>Mijoz</th><th>Telefon</th><th>Summa</th><th>Holat</th></tr>{rows}</table></div></div>'
    c.close();return page('Restoran',body)

def login_page():return page('Restoran login','<div class="wrap"><div class="card"><h1>🏪 Restoran paneli</h1><form method="post" action="/restaurant/login"><input name="login" placeholder="Login" required><input name="password" type="password" placeholder="Parol" required><button>Kirish</button></form></div></div>')

class H(BaseHTTPRequestHandler):
    def get(self,path,q):
        if path.startswith('/admin'):
            if not auth(self): self.send_response(401);self.send_header('WWW-Authenticate','Basic realm="Ali Kuryer Admin"');self.end_headers();return
            if path=='/admin/menu/ok':
                iid=int(q.get('id',['0'])[0]);c=conn();c.execute("UPDATE menu_items SET status='approved' WHERE id=?",(iid,));c.commit();c.close();self.red('/admin/menu');return
            self.out(admin_page(path if path in ['/admin','/admin/restaurants','/admin/menu','/admin/orders'] else '/admin'));return
        if path.startswith('/restaurant'):
            r=rest_auth(self)
            if path=='/restaurant/login':self.out(login_page());return
            if not r:self.out(login_page());return
            self.out(rest_page(r,path if path in ['/restaurant','/restaurant/menu','/restaurant/orders'] else '/restaurant'));return
        self.out(page('Ali Kuryer','<div class="wrap"><div class="card"><h1>🛵 Ali Kuryer</h1><p>Server ishlayapti.</p><p><a class="btn" href="/restaurant">Restoran paneli</a></p></div></div>'))
    def do_GET(self):
        p,_,qs=self.path.partition('?');self.get(p,urllib.parse.parse_qs(qs))
    def do_POST(self):
        p,_,_=self.path.partition('?');f=form(self)
        if p=='/admin/restaurants/new' and auth(self):
            c=conn();c.execute('INSERT INTO restaurants(name,phone,address,login,password_hash) VALUES(?,?,?,?,?)',(f.get('name',[''])[0],f.get('phone',[''])[0],f.get('address',[''])[0],f.get('login',[''])[0],ph(f.get('password',[''])[0])));c.commit();c.close();self.red('/admin/restaurants');return
        if p=='/restaurant/login':
            c=conn();r=c.execute("SELECT * FROM restaurants WHERE login=? AND password_hash=? AND status='active'",(f.get('login',[''])[0],ph(f.get('password',[''])[0]))).fetchone();c.close()
            if not r:self.out(login_page());return
            s=secrets.token_urlsafe(24);sessions[s]=dict(r);self.send_response(303);self.send_header('Location','/restaurant');self.send_header('Set-Cookie','rk='+s+'; Path=/; HttpOnly');self.end_headers();return
        if p=='/restaurant/menu/new':
            r=rest_auth(self)
            if not r:self.out(login_page());return
            c=conn();c.execute("INSERT INTO menu_items(restaurant_id,name,price,ingredients,description,weight,category,image_url,status) VALUES(?,?,?,?,?,?,?,?,'pending')",(r['id'],f.get('name',[''])[0],int(f.get('price',['0'])[0]),f.get('ingredients',[''])[0],f.get('description',[''])[0],f.get('weight',[''])[0],f.get('category',[''])[0],f.get('image_url',[''])[0]));c.commit();c.close();self.red('/restaurant/menu');return
        self.send_response(404);self.end_headers()
    def out(self,s,status=200):
        b=s.encode();self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def red(self,u):self.send_response(303);self.send_header('Location',u);self.end_headers()
    def log_message(self,*a):pass

def web():
    port=int(os.getenv('PORT','10000'));ThreadingHTTPServer(('0.0.0.0',port),H).serve_forever()

if __name__=='__main__':
    init_db();print('ALI KURYER READY')
    Thread(target=web,daemon=True).start();bot_loop()
