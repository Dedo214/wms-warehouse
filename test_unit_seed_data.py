"""Unit tests — app.seed_data helpers and guard"""
import datetime
import re

from app.seed_data import date_ago, days_ago, rng, ref, seed_all


def test_rng_within_bounds_and_two_decimals():
    for _ in range(20):
        value = rng(1, 5)
        assert 1 <= value <= 5
        assert round(value, 2) == value


def test_ref_format():
    assert re.fullmatch(r"PO-\d{8}-\d{3}", ref("PO"))


def test_days_ago_and_date_ago():
    elapsed = (datetime.datetime.utcnow() - days_ago(3)).total_seconds()
    assert abs(elapsed - 3 * 86400) < 5
    assert date_ago(3) == days_ago(3).date()


def test_seed_all_refuses_to_overwrite_existing_data(app):
    """The seeded test database already has users, so a non-forced seed is a no-op."""
    with app.app_context():
        result = seed_all()
        assert result["ok"] is False
        assert result["msg"]
