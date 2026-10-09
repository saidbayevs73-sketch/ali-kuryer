"""Customer JSON API for the existing SQLite server; no FastAPI schema swap."""
import json
import math
import mimetypes
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ALLOWED_ORIGINS = {
    'https://ali-kuryer.uz', 'https://www.ali-kuryer.uz',
    'https://saidbayevs73-sketch.github.io',
    'https://ali-kuryer.onrender.com', 'https://ali-kuryer-1.onrender.com',
}


def install(legacy):
    """Patch the existing handler without replacing orders, users or passwords."""
    Handler = legacy['H']
    old_get, old_post = Handler.do_GET, Handler.do_POST
    old_init = legacy['init_db']
    old_end_headers = Handler.end_headers

    def initialize():
        # Take a consistent SQLite snapshot before the first customer API migration.
        database_path = Path(legacy['DB']).resolve()
        marker = database_path.parent / (database_path.name + '.customer-api-backup-complete')
        if database_path.is_file() and not marker.exists():
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            backup_path = database_path.parent / (database_path.name + '.before-customer-' + stamp + '.sqlite')
            with sqlite3.connect(str(database_path)) as source, sqlite3.connect(str(backup_path)) as target:
                source.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('Database backup integrity check failed')
            os.chmod(backup_path, 0o600)
            marker.write_text(backup_path.name, encoding='utf-8')
            print('Customer API: pre-migration SQLite backup verified', flush=True)
        old_init()
        with legacy['conn']() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS web_order_details (
                order_id INTEGER PRIMARY KEY REFERENCES orders(id),
                recipient_name TEXT NOT NULL, latitude REAL NOT NULL,
                longitude REAL NOT NULL, street TEXT NOT NULL,
                house TEXT NOT NULL, note TEXT NOT NULL DEFAULT '')''')

    def headers(self):
        origin = self.headers.get('Origin', '')
        if urlsplit(self.path).path.startswith('/api/') and origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        old_end_headers(self)

    def respond(self, payload, status=200):
        self.json_out(payload, status)

    def options(self):
        if self.headers.get('Origin', '') not in ALLOWED_ORIGINS:
            respond(self, {'error': 'Origin ruxsat etilmagan'}, 403)
            return
        self.send_response(204)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def staff_blocked(self):
        path = urlsplit(self.path).path
        if path.split('/')[1] not in {'admin', 'restaurant', 'courier'}:
            return False
        # A dedicated staff host may serve the existing role-protected panels.
        staff_host = os.getenv('STAFF_WEB_HOST', '').lower().strip()
        host = self.headers.get('Host', '').split(':')[0].lower()
        return not (os.getenv('ENABLE_STAFF_WEB_PANELS', '0') == '1' or
                    (staff_host and host == staff_host))

    def get(self):
        path = urlsplit(self.path).path
        if staff_blocked(self):
            self.out('Topilmadi', 404)
            return
        if path == '/':
            self.out((Path(__file__).parent / 'index.html').read_text(encoding='utf-8'))
            return
        public_files = {
            '/site-assets/customer.js', '/site-assets/customer.css',
            '/legal/offer.html', '/legal/privacy.html',
        }
        if path in public_files:
            asset = Path(__file__).parent / path.lstrip('/')
            if not asset.is_file():
                self.out('Topilmadi', 404)
                return
            body = asset.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mimetypes.guess_type(asset.name)[0] or 'application/octet-stream')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)
            return
        if not path.startswith('/api/'):
            old_get(self)
            return
        with legacy['conn']() as db:
            if path == '/api/restaurants':
                rows = db.execute("SELECT * FROM restaurants WHERE status='active' ORDER BY name").fetchall()
                # Explicit public fields: never expose login or password hashes.
                respond(self, [{'id': r['id'], 'name': r['name'], 'address': r['address'],
                                'accepting_orders': int(legacy['is_open'](r))} for r in rows])
            elif path == '/api/menu':
                rid = parse_qs(urlsplit(self.path).query).get('restaurant_id', [None])[0]
                query = "SELECT m.* FROM menu_items m JOIN restaurants r ON r.id=m.restaurant_id WHERE m.status='approved' AND r.status='active'"
                args = ()
                if rid is not None:
                    query += ' AND m.restaurant_id=?'
                    args = (rid,)
                rows = db.execute(query + ' ORDER BY m.id', args).fetchall()
                fields = ('id', 'restaurant_id', 'name', 'price', 'ingredients', 'description',
                          'weight', 'category', 'image_url', 'kind')
                respond(self, [{key: r[key] for key in fields if key in r.keys()} for r in rows])
            elif path == '/api/settings':
                respond(self, {})
            elif path == '/api/health':
                respond(self, {'ok': True, 'service': 'Ali Kuryer customer orders'})
            else:
                respond(self, {'error': 'Topilmadi'}, 404)

    def post(self):
        path = urlsplit(self.path).path
        if staff_blocked(self):
            self.out('Topilmadi', 404)
            return
        if path != '/api/orders':
            old_post(self)
            return
        origin = self.headers.get('Origin', '')
        if origin and origin not in ALLOWED_ORIGINS:
            respond(self, {'error': 'Origin ruxsat etilmagan'}, 403)
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 1 <= size <= 65536:
                raise ValueError('So‘rov hajmi noto‘g‘ri')
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('JSON so‘rov kerak')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('Buyurtma noto‘g‘ri')
            def text(key, limit, required=False):
                value = data.get(key, '')
                if not isinstance(value, str):
                    raise ValueError('Matn maydoni noto‘g‘ri')
                value = value.strip()
                if len(value) > limit or (required and not value):
                    raise ValueError('Ism, telefon, ko‘cha va uy ma’lumotlarini tekshiring')
                return value
            name, phone = text('name', 150, True), text('phone', 30, True)
            phone = re.sub(r'[\s-]', '', phone)
            if not re.fullmatch(r'\+998[0-9]{9}', phone):
                raise ValueError('Telefon +998XXXXXXXXX shaklida bo‘lsin')
            street, house = text('street', 160, True), text('house', 40, True)
            note = text('address', 300)
            if data.get('payment') != 'Naqd':
                raise ValueError('Hozir faqat naqd to‘lov mavjud')
            lat, lng = data.get('lat'), data.get('lng')
            if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (lat, lng)) or abs(lat) > 90 or abs(lng) > 180:
                raise ValueError('GPS koordinatalarni tekshiring')
            items = data.get('items')
            if not isinstance(items, list) or not 1 <= len(items) <= 100:
                raise ValueError('Savatni tekshiring')
            full_address = ', '.join(filter(None, [street, 'uy ' + house,
                text('entrance', 40), text('floor', 40), text('apartment', 40), note]))
            token = secrets.token_urlsafe(32)
            with legacy['conn']() as db:
                db.execute('BEGIN IMMEDIATE')
                fresh, restaurant_id, total = [], None, 0
                seen = set()
                for item in items:
                    if not isinstance(item, dict):
                        raise ValueError('Savatni tekshiring')
                    iid, qty = item.get('id'), item.get('qty')
                    if type(iid) is not int or type(qty) is not int or not 1 <= qty <= 30 or iid in seen:
                        raise ValueError('Taom yoki miqdor noto‘g‘ri')
                    seen.add(iid)
                    food = db.execute("SELECT * FROM menu_items WHERE id=? AND status='approved'", (iid,)).fetchone()
                    if not food or food['price'] <= 0:
                        raise ValueError('Savatdagi taom mavjud emas')
                    if restaurant_id is None:
                        restaurant_id = food['restaurant_id']
                    if restaurant_id != food['restaurant_id']:
                        raise ValueError('Bitta oshxonadan buyurtma bering')
                    fresh.append((food, qty))
                    total += food['price'] * qty
                restaurant = db.execute('SELECT * FROM restaurants WHERE id=?', (restaurant_id,)).fetchone()
                if not restaurant or restaurant['status'] != 'active' or not legacy['is_open'](restaurant):
                    raise ValueError('Oshxona hozir yopiq')
                customer_id = db.execute('INSERT INTO customers(first_name,phone) VALUES(?,?)', (name, phone)).lastrowid
                oid = db.execute('''INSERT INTO orders(customer_id,restaurant_id,total,status,phone,address,payment,tracking_token)
                    VALUES(?,?,?,'Qabul qilindi',?,?,'Naqd',?)''',
                    (customer_id, restaurant_id, total, phone, full_address, token)).lastrowid
                for food, qty in fresh:
                    db.execute('INSERT INTO order_items(order_id,item_id,name,price,qty) VALUES(?,?,?,?,?)',
                               (oid, food['id'], food['name'], food['price'], qty))
                db.execute('INSERT INTO web_order_details(order_id,recipient_name,latitude,longitude,street,house,note) VALUES(?,?,?,?,?,?,?)',
                           (oid, name, lat, lng, street, house, note))
                legacy['audit'](db, 'customer', customer_id, 'Web buyurtma', 'orders', oid, after={'total': total})
            respond(self, {'order_id': oid, 'total': total, 'status': 'Qabul qilindi', 'tracking_token': token}, 201)
        except (ValueError, TypeError, UnicodeError):
            respond(self, {'error': 'Buyurtma ma’lumotlarini tekshiring: telefon, GPS, savat va naqd to‘lov'}, 400)

    Handler.end_headers = headers
    Handler.do_GET, Handler.do_POST, Handler.do_OPTIONS = get, post, options
    legacy['init_db'] = initialize

    from loyalty_points import install as install_loyalty
    install_loyalty(legacy)
