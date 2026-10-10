"""Offline regression checks for the owner/admin brute-force guard.

No Render account, real password or production database is contacted.
"""
from app.admin_login_guard import AdminLoginThrottle


def test_owner_failed_logins_are_limited_and_recover_after_window():
    guard = AdminLoginThrottle(max_failures=3, window_seconds=300)
    for index in range(3):
        guard.fail("198.51.100.17", now=10 + index)
    assert guard.blocked("198.51.100.17", now=15) is True
    assert guard.blocked("198.51.100.18", now=15) is False
    assert guard.blocked("198.51.100.17", now=313) is False


def test_owner_success_clears_failed_attempts():
    guard = AdminLoginThrottle(max_failures=2)
    guard.fail("client-one", now=1)
    guard.fail("client-one", now=2)
    assert guard.blocked("client-one", now=3)
    guard.success("client-one")
    assert not guard.blocked("client-one", now=3)


def test_owner_rate_guard_avoids_unbounded_ip_state():
    guard = AdminLoginThrottle(max_failures=2, max_peers=3)
    for index in range(20):
        guard.fail("client-" + str(index), now=float(index))
    assert len(guard._attempts) <= 3
    guard.fail("client-21", now=250)
    assert len(guard._attempts) <= 3


def test_owner_rate_guard_does_not_store_passwords_or_raw_requests():
    guard = AdminLoginThrottle(max_failures=1)
    guard.fail("peer-only", now=1)
    assert set(guard._attempts.keys()) == {"peer-only"}
    assert guard.blocked("peer-only", now=2)
