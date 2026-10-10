"""Regression tests for Super Admin settings, auth enforcement and audit."""
import os
import pytest

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/ali_kuryer_ci_customer.db")
os.environ.setdefault("SECRET_KEY", "only-for-regression-tests")
os.environ.setdefault("ENVIRONMENT", "test")

from main import app
from app import control_center, models, security
from app.database import SessionLocal

client = TestClient(app)


@pytest.fixture
def roles():
    with SessionLocal() as db:
        # Fresh configuration so other integration tests keep their defaults.
        db.query(control_center.AdminConfigAudit).delete()
        db.query(control_center.AdminConfiguration).delete()
        db.commit()
        actors = []
        for suffix, role in ((71, "admin"), (72, "customer")):
            phone = "+9989011199" + str(suffix)
            user = db.query(models.User).filter_by(phone=phone).first()
            if user is None:
                user = models.User(
                    name="Config test " + role, phone=phone,
                    password_hash=security.hash_password("SecureRegression!123"),
                    role=role, is_active=True
                )
                db.add(user)
            db.commit()
            db.refresh(user)
            actors.append(user)
        admin, customer = actors
        tokens = {
            "admin": {"Authorization": "Bearer " + security.admin_access_token(admin)},
            "customer": {"Authorization": "Bearer " + security.create_access_token({
                "sub": str(customer.id), "role": "customer"
            })},
            "phone": customer.phone,
        }
    yield tokens
    with SessionLocal() as db:
        db.query(control_center.AdminConfigAudit).delete()
        db.query(control_center.AdminConfiguration).delete()
        db.commit()


def test_only_admin_can_change_settings(roles):
    payload = {"changes": {"site_notice": "Salom, Namangan!"}}
    assert client.get("/api/admin/control-center").status_code == 401
    assert client.post("/api/admin/control-center", json=payload).status_code == 401
    assert client.post("/api/admin/control-center", json=payload,
                       headers=roles["customer"]).status_code == 403
    r = client.get("/api/admin/control-center", headers=roles["admin"])
    assert r.status_code == 200, r.text
    assert r.json()["login"] == "admin"
    assert "ADMIN_PASSWORD" not in r.text
    assert "SECRET_KEY" not in r.text


def test_changes_are_persistent_public_and_audited(roles):
    req = {"changes": {"site_notice": "Bugun yangi menyu!", "site_accent": "#AB1234",
                       "customer_sms": False, "courier_notice": "Yo‘l qoidalariga rioya qiling"}}
    res = client.post("/api/admin/control-center", json=req, headers=roles["admin"])
    assert res.status_code == 200, res.text
    assert set(res.json()["changed"]) == set(req["changes"])
    public = client.get("/api/control-center/public")
    assert public.status_code == 200
    assert public.json()["settings"]["site"]["site_accent"] == "#ab1234"
    assert public.json()["settings"]["site"]["site_notice"] == "Bugun yangi menyu!"
    assert public.json()["settings"]["courier"]["courier_notice"] == "Yo‘l qoidalariga rioya qiling"
    assert public.json()["settings"]["customer"]["customer_sms"] is False
    assert client.get("/api/auth/options").json()["sms_registration"] is False
    assert client.post("/api/auth/otp/request", json={
        "phone": "+998901111991"
    }).status_code == 403
    audit = client.get("/api/admin/control-center/history", headers=roles["admin"])
    assert audit.status_code == 200
    assert len(audit.json()["events"]) == 4
    assert client.get("/api/admin/control-center/history",
                      headers=roles["customer"]).status_code == 403


def test_control_server_enforces_customer_password_login(roles, monkeypatch):
    before = client.post("/api/auth/login", json={
        "phone": roles["phone"], "password": "SecureRegression!123"
    })
    assert before.status_code == 200, before.text
    # Only Google can replace phone/password for these test settings.
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "fake-public-id-for-readiness.apps.googleusercontent.com")
    change = client.post("/api/admin/control-center", json={"changes": {
        "customer_password_login": False, "customer_google_login": True,
    }}, headers=roles["admin"])
    assert change.status_code == 200, change.text
    blocked = client.post("/api/auth/login", json={
        "phone": roles["phone"], "password": "SecureRegression!123"
    })
    assert blocked.status_code == 403
    # The admin session cannot be disabled by customer feature flags.
    still_access = client.get("/api/admin/control-center", headers=roles["admin"])
    assert still_access.status_code == 200


def test_invalid_config_and_customer_lockout_rejected(roles, monkeypatch):
    for bad in (
        {"site_accent": "red; background:url(javascript:alert(1))"},
        {"site_notice": "<script>bad</script>"},
        {"customer_sms": "off"},
        {"ADMIN_PASSWORD": "secret"},
    ):
        res = client.post("/api/admin/control-center", json={"changes": bad},
                          headers=roles["admin"])
        assert res.status_code == 422, (bad, res.text)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("ALI_USERNAME_LOGIN_ENABLED", raising=False)
    monkeypatch.delenv("TELEGRAM_LOGIN_ENABLED", raising=False)
    monkeypatch.delenv("FIREBASE_PHONE_ENABLED", raising=False)
    denied = client.post("/api/admin/control-center", json={"changes": {
        "customer_password_login": False
    }}, headers=roles["admin"])
    assert denied.status_code == 422


def test_admin_panel_is_mobile_html_with_no_embedded_password(roles):
    page = client.get("/super-admin")
    assert page.status_code == 200
    assert 'name="viewport"' in page.text
    assert 'autocomplete="current-password"' in page.text
    assert "ADMIN_PASSWORD=" not in page.text


def test_admin_chooses_new_login_only_after_password_confirmation(roles, monkeypatch):
    with SessionLocal() as db:
        admin = db.query(models.User).filter_by(role="admin").filter(
            models.User.name == "Config test admin").first()
        assert admin is not None
        monkeypatch.setenv("ADMIN_PHONE", admin.phone)
        # Always start the temporary regression account at the default alias.
        db.query(models.AdminLoginPreference).filter_by(user_id=admin.id).delete()
        db.commit()

    old = client.post("/api/auth/admin/login", json={
        "username": "admin", "password": "SecureRegression!123"
    })
    assert old.status_code == 200, old.text

    missing_password = client.post("/api/auth/admin/change-username", headers=roles["admin"],
                                   json={"new_username": "alikuryer_owner", "current_password": "wrong"})
    assert missing_password.status_code == 401

    nonadmin = client.post("/api/auth/admin/change-username", headers=roles["customer"],
                           json={"new_username": "alikuryer_owner", "current_password": "anything"})
    assert nonadmin.status_code == 403

    changed = client.post("/api/auth/admin/change-username", headers=roles["admin"],
                          json={"new_username": "alikuryer_owner", "current_password": "SecureRegression!123"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["username"] == "alikuryer_owner"
    assert client.get("/api/auth/admin/account", headers=roles["admin"]).json()["username"] == "alikuryer_owner"
    assert client.post("/api/auth/admin/login", json={
        "username": "admin", "password": "SecureRegression!123"
    }).status_code == 401
    assert client.post("/api/auth/admin/login", json={
        "username": "alikuryer_owner", "password": "SecureRegression!123"
    }).status_code == 200

    # Restore old test alias; never touch a real production administrator.
    reset = client.post("/api/auth/admin/change-username", headers=roles["admin"],
                        json={"new_username": "admin", "current_password": "SecureRegression!123"})
    assert reset.status_code == 200
