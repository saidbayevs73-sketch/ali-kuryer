"""Public projections of existing orders. Access requires an unguessable receipt.

No second order database is introduced; staff panels remain the source of truth.
"""
import math
import os
import re
import time


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS web_order_receipts (
        request_key TEXT PRIMARY KEY, payload_hash TEXT NOT NULL,
        order_id INTEGER UNIQUE NOT NULL REFERENCES orders(id),
        subtotal INTEGER NOT NULL, delivery_fee INTEGER NOT NULL DEFAULT 0)''')


def delivery_fee():
    # Existing checkout charged only item prices. Preserve that tariff unless
    # the operator explicitly configures a fee; never invent a commercial price.
    raw = os.getenv('CUSTOMER_DELIVERY_FEE_UZS', '0')
    if not re.fullmatch(r'\d{1,7}', raw):
        raise ValueError('Yetkazish tarifi noto‘g‘ri sozlangan')
    return int(raw)


def quote(db, items, is_open):
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ValueError('Savatni tekshiring')
    fresh, rid, subtotal, seen = [], None, 0, set()
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
        if rid is None:
            rid = food['restaurant_id']
        if rid != food['restaurant_id']:
            raise ValueError('Bitta oshxonadan buyurtma bering')
        fresh.append((food, qty))
        subtotal += food['price'] * qty
    restaurant = db.execute('SELECT * FROM restaurants WHERE id=?', (rid,)).fetchone()
    if not restaurant or restaurant['status'] != 'active' or not is_open(restaurant):
        raise ValueError('Oshxona hozir yopiq')
    fee = delivery_fee()
    return fresh, rid, {'subtotal': subtotal, 'delivery_fee': fee,
                        'total': subtotal + fee, 'payment': 'Naqd'}


def public_order(db, token):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{40,60}', token):
        return None
    o = db.execute('''SELECT o.*, r.name restaurant_name FROM orders o
        LEFT JOIN restaurants r ON r.id=o.restaurant_id WHERE tracking_token=?''', (token,)).fetchone()
    if not o:
        return None
    receipt = db.execute('SELECT * FROM web_order_receipts WHERE order_id=?', (o['id'],)).fetchone()
    details = db.execute('SELECT * FROM web_order_details WHERE order_id=?', (o['id'],)).fetchone()
    lines = [dict(x) for x in db.execute(
        'SELECT item_id,name,price,qty FROM order_items WHERE order_id=?', (o['id'],))]
    result = {'id': o['id'], 'restaurant_name': o['restaurant_name'], 'status': o['status'],
              'total': o['total'], 'subtotal': receipt['subtotal'] if receipt else o['total'],
              'delivery_fee': receipt['delivery_fee'] if receipt else 0,
              'address': o['address'], 'payment': o['payment'], 'items': lines,
              'courier': None, 'destination': None, 'eta_minutes': None}
    if details:
        result['destination'] = {'latitude': details['latitude'], 'longitude': details['longitude']}
    # Never expose an off-duty courier or any location after completion.
    if o['status'] == 'Kuryer qabul qildi' and o['courier_id']:
        c = db.execute("SELECT * FROM couriers WHERE id=? AND status='active'", (o['courier_id'],)).fetchone()
        if c:
            fresh = bool(c['on_duty'] and c['location_epoch'] and 0 <= time.time() - c['location_epoch'] < 90
                         and c['latitude'] is not None and c['longitude'] is not None)
            result['courier'] = {'name': c['name'], 'phone': c['phone'], 'fresh': fresh,
                                 'location_at': c['location_at'],
                                 'latitude': c['latitude'] if fresh else None,
                                 'longitude': c['longitude'] if fresh else None}
            # Optional explicit operator-provided speed model; no invented ETA.
            speed = os.getenv('CUSTOMER_ETA_SPEED_KMH', '')
            if fresh and details and re.fullmatch(r'\d{1,2}', speed) and 5 <= int(speed) <= 60:
                a, b = math.radians(c['latitude']), math.radians(details['latitude'])
                dlat = b - a
                dlon = math.radians(details['longitude'] - c['longitude'])
                h = math.sin(dlat/2)**2 + math.cos(a)*math.cos(b)*math.sin(dlon/2)**2
                distance = 6371 * 2 * math.asin(min(1, math.sqrt(max(0, h))))
                minutes = max(3, math.ceil(distance * 1.4 / int(speed) * 60))
                result['eta_minutes'] = [minutes, minutes+10]
                result['eta_note'] = 'GPS bo‘yicha taxmin. Yo‘l va tirbandlik hisobga olinmagan.'
    return result
