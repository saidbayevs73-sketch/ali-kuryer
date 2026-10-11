"""Super Admin dashboard: permissions and opt-in page; uses isolated test DB."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/ali_kuryer_ci_customer.db")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "only-for-regression-tests")
from fastapi.testclient import TestClient
from main import app
from app import models, security
from app.database import SessionLocal

client = TestClient(app)


def test_admin_portal_is_opt_in(monkeypatch):
    monkeypatch.delenv("ENABLE_STAFF_WEB_PANELS", raising=False)
    assert client.get("/admin").status_code == 404
    monkeypatch.setenv("ENABLE_STAFF_WEB_PANELS", "1")
    page = client.get("/admin")
    assert page.status_code == 200
    assert "ALI KURYER" in page.text
    assert "loginForm" in page.text
    assert page.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]


def test_dashboard_endpoints_require_admin_and_support_application_review():
    assert client.get("/api/admin/overview").status_code == 401
    phone_c = "+998900009921"
    phone_a = "+998900009922"
    with SessionLocal() as db:
        db.query(models.User).filter(models.User.phone.in_([phone_c, phone_a])).delete(
            synchronize_session=False
        )
        admin = models.User(name="Dashboard Admin", phone=phone_a,
            password_hash=security.hash_password("Test-Dashboard-Password#2026!"),
            role="admin", is_active=True)
        customer = models.User(name="Dashboard customer", phone=phone_c,
            password_hash="not-used", role="customer", is_active=True)
        db.add_all([admin, customer]); db.commit()
        db.refresh(admin); db.refresh(customer)
        aid, cid = admin.id, customer.id
        admin_token = security.admin_access_token(admin)
        customer_token = security.create_access_token(
            {"sub": str(customer.id), "role": "customer"}
        )
    try:
        h_admin = {"Authorization": "Bearer " + admin_token}
        h_customer = {"Authorization": "Bearer " + customer_token}
        for path in (
            "/api/admin/overview", "/api/admin/people?role=courier",
            "/api/admin/people?role=customer",
        ):
            assert client.get(path, headers=h_customer).status_code == 403
            assert client.get(path, headers=h_admin).status_code == 200
        data = client.get("/api/admin/overview", headers=h_admin).json()
        assert "total_orders" in data and "last_7_days" in data
        assert len(data["last_7_days"]) == 7
        listed = client.get("/api/admin/people?role=customer",
            headers=h_admin).json()
        assert any(x["id"] == cid and "password_hash" not in x for x in listed)

        with SessionLocal() as db:
            item = models.PartnerApplication(
                kind="courier", full_name="Applicant Test", phone="+998900009923",
                city="Namangan", detail="Test", status="new"
            )
            db.add(item); db.commit(); db.refresh(item); application_id = item.id
        try:
            url = f"/api/admin/partner-applications/{application_id}"
            assert client.patch(url, json={"status": "approved"},
                headers=h_customer).status_code == 403
            assert client.patch(url, json={"status": "untrusted"},
                headers=h_admin).status_code == 422
            accepted = client.patch(url, json={"status": "reviewing"},
                headers=h_admin)
            assert accepted.status_code == 200, accepted.text
            assert accepted.json()["status"] == "reviewing"
        finally:
            with SessionLocal() as db:
                db.query(models.PartnerApplication).filter_by(
                    id=application_id
                ).delete()
                db.commit()
    finally:
        with SessionLocal() as db:
            db.query(models.User).filter(
                models.User.id.in_([aid, cid])
            ).delete(synchronize_session=False)
            db.commit()
