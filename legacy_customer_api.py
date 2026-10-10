"""Customer JSON API for the existing SQLite server; no FastAPI schema swap."""
import json
import hashlib
import customer_order_service as customer_orders
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
        # Operational readiness only: log aggregate counts and backup integrity,
        # never phone numbers, names, passwords or order contents.
        try:
            source = Path(legacy['DB']).resolve()
            record = {
                "storage_persistent": source == Path("/var/data").resolve() or
                    Path("/var/data").resolve() in source.parents,
                "legacy_db_exists": source.is_file(),
                "source_bytes": source.stat().st_size if source.exists() else 0,
                "backup_verified": False,
                "counts": {}
            }
            marker_file = source.parent / (source.name + '.customer-api-backup-complete')
            if marker_file.is_file():
                backup_name = marker_file.read_text(encoding='utf-8').strip()
                backup_file = source.parent / backup_name
                if backup_file.parent == source.parent and backup_file.is_file():
                    with sqlite3.connect('file:' + str(backup_file) + '?mode=ro', uri=True) as check:
                        record['backup_verified'] = (
                            check.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                        )
            if source.is_file():
                with sqlite3.connect('file:' + str(source) + '?mode=ro', uri=True) as read_only:
                    for table in ('customers', 'restaurants', 'menu_items', 'orders', 'order_items'):
                        if table in {r[0] for r in read_only.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        )}:
                            record['counts'][table] = read_only.execute(
                                'SELECT COUNT(*) FROM ' + table
                            ).fetchone()[0]
            # Inspect the attached persistent disk without writing or copying.
            # Useful when the active legacy DB accidentally lives on ephemeral storage.
            record["persistent_disk_candidates"] = []
            disk_root = Path("/var/data")
            if disk_root.is_dir():
                for candidate in sorted(disk_root.iterdir()):
                    if len(record["persistent_disk_candidates"]) >= 12:
                        break
                    if (not candidate.is_file() or candidate.is_symlink()
                            or candidate.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}):
                        continue
                    found = {"file": candidate.name, "bytes": candidate.stat().st_size,
                             "counts": {}, "integrity_ok": False}
                    try:
                        with sqlite3.connect('file:' + str(candidate) + '?mode=ro', uri=True,
                                             timeout=3) as diskdb:
                            names = {row[0] for row in diskdb.execute(
                                "SELECT name FROM sqlite_master WHERE type='table'")}
                            for table in ("customers", "restaurants", "menu_items",
                                          "orders", "order_items", "couriers",
                                          "tickets", "ticket_messages", "settings"):
                                if table in names:
                                    found["counts"][table] = diskdb.execute(
                                        "SELECT COUNT(*) FROM " + table).fetchone()[0]
                            found["integrity_ok"] = (
                                diskdb.execute("PRAGMA quick_check").fetchone()[0] == "ok"
                            )
                    except (sqlite3.Error, OSError):
                        found["error"] = "unreadable"
                    record["persistent_disk_candidates"].append(found)
            print('ALI_LEGACY_MIGRATION_READINESS ' +
                  json.dumps(record, sort_keys=True), flush=True)
        except Exception as audit_error:
            print('ALI_LEGACY_MIGRATION_READINESS check_failed ' +
                  type(audit_error).__name__, flush=True)
        with legacy['conn']() as db:
            customer_orders.initialize(db)
            db.execute('''CREATE TABLE IF NOT EXISTS web_order_details (
                order_id INTEGER PRIMARY KEY REFERENCES orders(id),
                recipient_name TEXT NOT NULL, latitude REAL NOT NULL,
                longitude REAL NOT NULL, street TEXT NOT NULL,
                house TEXT NOT NULL, note TEXT NOT NULL DEFAULT '')''')
        if os.getenv("ALI_LEGACY_WRITES_FROZEN") == "1":
            # Server-side, opt-in guard: old staff and customer requests cannot
            # modify SQLite while a validated migration is being reconciled.
            original_conn = legacy["conn"]
            blocked_ops = {
                sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE,
                sqlite3.SQLITE_DELETE, sqlite3.SQLITE_CREATE_TABLE,
                sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_ALTER_TABLE,
                sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX,
            }

            def frozen_connection():
                connection = original_conn()
                def deny_writes(action, arg1, arg2, database, trigger):
                    return sqlite3.SQLITE_DENY if action in blocked_ops else sqlite3.SQLITE_OK
                connection.set_authorizer(deny_writes)
                return connection

            legacy["conn"] = frozen_connection
            print("ALI_LEGACY_WRITE_FREEZE ACTIVE", flush=True)


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
            '/site-assets/storefront.js', '/site-assets/storefront.css',
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
        if os.getenv("ALI_LEGACY_WRITES_FROZEN") == "1":
            if path.startswith("/api/"):
                respond(self, {"error": "Eski server vaqtincha faqat o‘qish rejimida"}, 503)
            else:
                self.out("Baza ko‘chirilmoqda. O‘zgartirishlar vaqtincha to‘xtatilgan.", 503)
            return
        if staff_blocked(self):
            self.out('Topilmadi', 404)
            return
        if path in {'/api/order-quote', '/api/customer-orders/lookup'}:
            origin = self.headers.get('Origin', '')
            if origin and origin not in ALLOWED_ORIGINS:
                respond(self, {'error': 'Origin ruxsat etilmagan'}, 403)
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 1 <= size <= 16000:
                    raise ValueError('So‘rov hajmi noto‘g‘ri')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('So‘rov noto‘g‘ri')
                with legacy['conn']() as db:
                    if path == '/api/order-quote':
                        _, _, result = customer_orders.quote(db, data.get('items'), legacy['is_open'])
                    else:
                        tokens = data.get('tokens')
                        if not isinstance(tokens, list) or len(tokens) > 50:
                            raise ValueError('Ko‘pi bilan 50 ta buyurtma')
                        result = []
                        for token in tokens:
                            order = customer_orders.public_order(db, token)
                            if order:
                                order['tracking_token'] = token
                                result.append(order)
                respond(self, result)
            except (ValueError, TypeError, UnicodeError) as exc:
                respond(self, {'error': str(exc)}, 400)
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
                request_key = data.get('request_key', '')
                if request_key and (not isinstance(request_key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{20,80}', request_key)):
                    raise ValueError('Buyurtma kaliti noto‘g‘ri')
                payload_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
                previous = db.execute('SELECT * FROM web_order_receipts WHERE request_key=?', (request_key,)).fetchone() if request_key else None
                if previous:
                    if previous['payload_hash'] != payload_hash:
                        respond(self, {'error': 'Buyurtma kaliti boshqa savat uchun ishlatilgan'}, 409)
                        return
                    order = db.execute('SELECT * FROM orders WHERE id=?', (previous['order_id'],)).fetchone()
                    respond(self, {'order_id': order['id'], 'total': order['total'],
                                   'status': order['status'], 'tracking_token': order['tracking_token']})
                    return
                fresh, restaurant_id, amounts = customer_orders.quote(db, items, legacy['is_open'])
                total = amounts['total']
                if 'expected_total' in data and data['expected_total'] != total:
                    respond(self, {'error': 'Narx yangilandi. Savatdagi summani qayta tasdiqlang'}, 409)
                    return
                customer_id = db.execute('INSERT INTO customers(first_name,phone) VALUES(?,?)', (name, phone)).lastrowid
                oid = db.execute('''INSERT INTO orders(customer_id,restaurant_id,total,status,phone,address,payment,tracking_token)
                    VALUES(?,?,?,'Qabul qilindi',?,?,'Naqd',?)''',
                    (customer_id, restaurant_id, total, phone, full_address, token)).lastrowid
                for food, qty in fresh:
                    db.execute('INSERT INTO order_items(order_id,item_id,name,price,qty) VALUES(?,?,?,?,?)',
                               (oid, food['id'], food['name'], food['price'], qty))
                db.execute('INSERT INTO web_order_details(order_id,recipient_name,latitude,longitude,street,house,note) VALUES(?,?,?,?,?,?,?)',
                           (oid, name, lat, lng, street, house, note))
                db.execute('INSERT INTO web_order_receipts(request_key,payload_hash,order_id,subtotal,delivery_fee) VALUES(?,?,?,?,?)',
                           (request_key or secrets.token_urlsafe(32), payload_hash, oid, amounts['subtotal'], amounts['delivery_fee']))
                legacy['audit'](db, 'customer', customer_id, 'Web buyurtma', 'orders', oid, after={'total': total})
            respond(self, {'order_id': oid, 'total': total, 'status': 'Qabul qilindi', 'tracking_token': token}, 201)
        except (ValueError, TypeError, UnicodeError) as exc:
            respond(self, {'error': str(exc) or 'Buyurtma ma’lumotlarini tekshiring'}, 400)

    Handler.end_headers = headers
    Handler.do_GET, Handler.do_POST, Handler.do_OPTIONS = get, post, options
    legacy['init_db'] = initialize
