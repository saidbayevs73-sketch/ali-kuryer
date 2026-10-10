"""Exercise real HTTP handlers against an isolated legacy SQLite database."""
import importlib
import json
import sqlite3
import threading
import time
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'orders.db'))
    monkeypatch.setenv('ADMIN_PASSWORD', 'isolated-test-password')
    monkeypatch.delenv('BOT_TOKEN', raising=False)
    import ali_kuryer
    legacy = importlib.reload(ali_kuryer)
    legacy.init_db()
    # Explicit fixture hours: do not depend on time of day.
    legacy.is_open = lambda row: bool(row['accepting_orders'])
    with legacy.conn() as db:
        db.execute('UPDATE restaurants SET accepting_orders=1')
    server = ThreadingHTTPServer(('127.0.0.1', 0), legacy.H)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def post(path, body, origin='https://ali-kuryer.onrender.com'):
        req = Request('http://127.0.0.1:%s%s' % (server.server_port, path),
                      json.dumps(body).encode(),
                      {'Content-Type': 'application/json', 'Origin': origin})
        try:
            with urlopen(req) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.load(exc)
    yield legacy, post
    server.shutdown()
    server.server_close()


def payload():
    return dict(name='Test customer', phone='+998900000001', street='Test street',
                house='1', payment='Naqd', lat=41.31, lng=69.28,
                items=[{'id': 1, 'qty': 2}], request_key='test-order-request-123456789')


def test_quote_order_retry_and_private_receipt(app):
    legacy, post = app
    status, quote = post('/api/order-quote', {'items': payload()['items']})
    assert status == 200 and quote['total'] == 60000 and quote['delivery_fee'] == 0
    p = payload() | {'expected_total': quote['total']}
    status, order = post('/api/orders', p)
    assert status == 201
    status, retry = post('/api/orders', p)
    assert status == 200 and retry == order
    with legacy.conn() as db:
        assert db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
    status, changed = post('/api/orders', p | {'house': '2'})
    assert status == 409
    assert post('/api/customer-orders/lookup', {'tokens': ['wrong', 1]}) == (200, [])
    status, receipts = post('/api/customer-orders/lookup', {'tokens': [order['tracking_token']]})
    assert status == 200 and receipts[0]['items'][0]['qty'] == 2
    assert receipts[0]['courier'] is None
    assert 'phone' not in receipts[0]
    assert post('/api/orders', p, 'https://evil.example')[0] == 403


def test_validation_and_server_price(app):
    legacy, post = app
    assert post('/api/orders', payload() | {'expected_total': 1})[0] == 409
    assert post('/api/orders', payload() | {'payment': 'Click'})[0] == 400
    assert post('/api/orders', payload() | {'lat': True})[0] == 400
    assert post('/api/order-quote', {'items': [{'id': 1, 'qty': 31}]})[0] == 400
    assert post('/api/order-quote', {'items': [{'id': 1, 'qty': 1}, {'id': 4, 'qty': 1}]})[0] == 400
    with legacy.conn() as db:
        db.execute('UPDATE restaurants SET accepting_orders=0')
    assert post('/api/orders', payload())[0] == 400


def test_courier_location_privacy(app):
    legacy, post = app
    _, order = post('/api/orders', payload())
    with legacy.conn() as db:
        c = db.execute('SELECT id FROM couriers LIMIT 1').fetchone()
        if c:
            cid = c[0]
        else:
            cid = db.execute("INSERT INTO couriers(name,phone,status,login,password_hash) VALUES('Test courier','+998900000002','active','test-courier','test-hash')").lastrowid
        db.execute("UPDATE couriers SET on_duty=1,latitude=41.32,longitude=69.29,location_epoch=? WHERE id=?", (time.time(), cid))
        db.execute("UPDATE orders SET status='Kuryer qabul qildi',courier_id=? WHERE id=?", (cid, order['order_id']))
    lookup = lambda: post('/api/customer-orders/lookup', {'tokens': [order['tracking_token']]})[1][0]
    assert lookup()['courier']['fresh'] is True
    with legacy.conn() as db:
        db.execute('UPDATE couriers SET location_epoch=? WHERE id=?', (time.time()-100, cid))
    assert lookup()['courier']['latitude'] is None
    with legacy.conn() as db:
        db.execute("UPDATE orders SET status='Yetkazildi' WHERE id=?", (order['order_id'],))
    assert lookup()['courier'] is None
