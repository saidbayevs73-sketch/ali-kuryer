"""Only configuration shape is tested; no production services or secrets."""
import json

from scripts.check_admin_readiness import _is_valid_phone, _strong_password, nonsecret_configuration


def test_readiness_phone_and_password_policy():
    assert _is_valid_phone("+998901234567")
    assert not _is_valid_phone("901234567")
    assert not _strong_password("admin")
    assert not _strong_password("Password123")
    assert _strong_password("MuchStronger#AdminPassword2026")


def test_readiness_never_exposes_credentials(monkeypatch):
    test_password = "PrivateAdmin#2026Secure"
    test_id = "PrivateResetIdentifier0123456789abcdef"
    monkeypatch.setenv("ADMIN_PHONE", "+998901234567")
    monkeypatch.setenv("ADMIN_PASSWORD", test_password)
    monkeypatch.setenv("ALI_ADMIN_RESET_REQUEST_ID", test_id)
    monkeypatch.setenv("ALI_ADMIN_RESET_PASSWORD", test_password)
    config = nonsecret_configuration()
    output = json.dumps({k: v for k, v in config.items() if not k.startswith("_")})
    assert config["admin_phone_valid"]
    assert config["initial_password_valid"]
    assert config["recovery_password_valid"]
    assert config["recovery_id_valid"]
    assert "998901234567" not in output
    assert test_password not in output
    assert test_id not in output
