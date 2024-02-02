import json
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from user_management.dao import AdminControlsDAO
from user_management.models import Base, AdminControls
from user_management.session import session_factory

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def dao_session():
    os.environ["NEW_DATABASE_URL"] = "sqlite:///:memory:"
    session_factory.get_refreshed()

    dao = AdminControlsDAO()
    dao.create_all_tables()

    yield dao

    dao.drop_all_tables()


def test_get_admin_controls(dao_session):
    # Assuming the AdminControls table is initially empty
    controls_json = dao_session.get_admin_controls()
    assert controls_json == json.dumps({"id": 1, "daily_spending_limit": 10})

    # Add an admin control record
    dao_session.add_admin_control(
        id=1, daily_spending_limit=100, allow_access=True, maintenance=False
    )
    controls_json = dao_session.get_admin_controls()
    controls = json.loads(controls_json)
    assert controls["daily_spending_limit"] == 100
    assert controls["allow_access"] is True
    assert controls["maintenance"] is False


def test_get_daily_limit(dao_session):
    # Test default daily limit
    assert dao_session.get_daily_limit() == 1

    # Update the daily limit
    dao_session.add_admin_control(
        id=1, daily_spending_limit=100, allow_access=True, maintenance=False
    )
    assert dao_session.get_daily_limit() == 100


def test_update_admin_controls(dao_session):
    dao_session.update_admin_controls(1, 150, False, True)
    admin_control = dao_session.session.query(AdminControls).first()
    assert admin_control.daily_spending_limit == 150
    assert admin_control.allow_access is False
    assert admin_control.maintenance is True


def test_get_maintenance_mode(dao_session):
    assert dao_session.get_maintenance_mode() is False
    dao_session.add_admin_control(
        id=1, daily_spending_limit=100, allow_access=True, maintenance=True
    )
    assert dao_session.get_maintenance_mode() is True


def test_add_admin_control(dao_session):
    dao_session.add_admin_control(
        id=2, daily_spending_limit=200, allow_access=False, maintenance=True
    )
    admin_control = dao_session.session.query(AdminControls).filter_by(id=2).first()
    assert admin_control is not None
    assert admin_control.daily_spending_limit == 200


def test_update_admin_control(dao_session):
    dao_session.add_admin_control(
        id=3, daily_spending_limit=300, allow_access=True, maintenance=False
    )
    dao_session.update_admin_control(
        3, daily_spending_limit=350, allow_access=False, maintenance=True
    )
    admin_control = dao_session.session.query(AdminControls).filter_by(id=3).first()
    assert admin_control.daily_spending_limit == 350
    assert admin_control.allow_access is False
    assert admin_control.maintenance is True


def test_delete_admin_control(dao_session):
    dao_session.add_admin_control(
        id=4, daily_spending_limit=400, allow_access=True, maintenance=True
    )
    dao_session.delete_admin_control(4)
    admin_control = dao_session.session.query(AdminControls).filter_by(id=4).first()
    assert admin_control is None
