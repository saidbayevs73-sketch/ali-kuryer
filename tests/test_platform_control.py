"""Super Admin feature flags, Google-link privacy, safe banners and customer rewards.
Uses an isolated local SQLite database; never calls outside services.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/ali_kuryer_ci_customer.db")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "only-for-regression-tests")

from fastapi.testclient import TestClient
from app import models, security
from app.database import SessionLocal
from app.routers.platform_control import PlatformFlag, PromotionalBanner, AdminAuditEvent
from main import app

client = TestClient(app)


def test_platform_control_access_flags_photos_and_bonus():
    with SessionLocal() as db:
        admin = models.User(name="Feature test admin", phone=None, role="admin",
                            password_hash=security.hash_password("Test-Feature-Admin#2026!"),
                            is_active=True)
        customer = models.User(name="Customer Test", phone=None, role="customer",
                               is_active=True)
        db.add_all([admin, customer])
        db.flush()
        restaurant = models.Restaurant(name="Real photo test restaurant",
                                       is_approved=True)
        db.add(restaurant)
        db.flush()
        db.add(models.Order(customer_id=customer.id, restaurant_id=restaurant.id,
                            address="Namangan, test", total=23500,
                            status="delivered", payment_method="cash"))
        db.add(models.GoogleIdentity(google_sub="testgoogle-feature-2026-" +
                                    str(customer.id), user_id=customer.id))
        db.commit()
        admin_id, customer_id, restaurant_id = admin.id, customer.id, restaurant.id
        h_admin = {"Authorization": "Bearer " + security.admin_access_token(admin)}
        h_customer = {"Authorization": "Bearer " + security.create_access_token(
            {"sub": str(customer.id), "role": "customer"})}

    banner_id = None
    try:
        public = client.get("/api/platform/public")
        assert public.status_code == 200
        assert "features" in public.json()
        assert client.get("/api/admin/platform/features").status_code == 401
        assert client.get("/api/admin/platform/features", headers=h_customer).status_code == 403
        assert client.get("/api/admin/platform/linked-accounts", headers=h_customer).status_code == 403
        assert client.get("/api/admin/platform/audit", headers=h_customer).status_code == 403

        forbidden = client.put("/api/admin/platform/features/wallet",
                               json={"enabled": True}, headers=h_admin)
        assert forbidden.status_code == 409
        for setting in ("orders", "promotions"):
            update = client.put("/api/admin/platform/features/" + setting,
                                json={"enabled": False}, headers=h_admin)
            assert update.status_code == 200, update.text
            assert client.get("/api/platform/public").json()["features"][setting] is False
            revert = client.put("/api/admin/platform/features/" + setting,
                                json={"enabled": True}, headers=h_admin)
            assert revert.status_code == 200

        assert client.post("/api/admin/platform/banners", headers=h_admin,
            json={"title": "Sinov", "subtitle": "Test", "image_url": "http://unsafe",
                  "cta_label": "Ko‘rish", "is_active": True}).status_code == 422
        ok = client.post("/api/admin/platform/banners", headers=h_admin,
            json={"title": "Taom rasmi", "subtitle": "Ruxsatli foto",
                  "image_url": "https://example.com/meal.webp",
                  "cta_label": "Tanlash", "is_active": True})
        assert ok.status_code == 201, ok.text
        banner_id = ok.json()["id"]
        assert any(x["id"] == banner_id for x in client.get(
            "/api/platform/public").json()["banners"])

        linked = client.get("/api/admin/platform/linked-accounts?provider=google",
                            headers=h_admin)
        assert linked.status_code == 200
        user = next(x for x in linked.json() if x["user_id"] == customer_id)
        assert user["provider"] == "google"
        assert "google_sub" not in user and "password" not in user and "access_token" not in user
        account = client.get("/api/customer/me/summary", headers=h_customer)
        assert account.status_code == 200
        assert account.json()["bonus"]["points"] == 2
        assert account.json()["wallet"]["available"] is False
        assert account.json()["history"][0]["status"] == "delivered"
        assert client.get("/api/customer/me/summary", headers=h_admin).status_code == 403

        log = client.get("/api/admin/platform/audit", headers=h_admin)
        assert log.status_code == 200
        assert any(x["action"] == "feature_changed" for x in log.json())
    finally:
        with SessionLocal() as db:
            if banner_id:
                db.query(PromotionalBanner).filter_by(id=banner_id).delete()
            db.query(PlatformFlag).filter(
                PlatformFlag.key.in_(["orders", "promotions"])
            ).delete(synchronize_session=False)
            db.query(AdminAuditEvent).filter_by(actor_id=admin_id).delete()
            db.query(models.GoogleIdentity).filter_by(user_id=customer_id).delete()
            db.query(models.Order).filter_by(customer_id=customer_id).delete()
            db.query(models.Restaurant).filter_by(id=restaurant_id).delete()
            db.query(models.User).filter(models.User.id.in_(
                [admin_id, customer_id]
            )).delete(synchronize_session=False)
            db.commit()
