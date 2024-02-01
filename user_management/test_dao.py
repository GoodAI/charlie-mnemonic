import json

import pytest

from user_management.dao import UsersDAO
from user_management.models import Base, Users

# Use an in-memory SQLite database for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def dao_session():
    db_url = "sqlite:///:memory:?mode=memory&cache=shared"

    dao = UsersDAO(db_url)
    dao.create_tables()

    yield dao

    dao.drop_tables()


def test_add_user(dao_session):
    username = "testuser"
    password = "testpass"
    session_token = "testtoken"
    display_name = "Test User"

    dao_session.add_user(username, password, session_token, display_name)

    user = dao_session.session.query(Users).filter_by(username=username).first()
    assert user is not None
    assert user.username == username
    assert user.password == password
    assert user.session_token == session_token
    assert user.display_name == display_name


def test_delete_user(dao_session):
    username = "testuser"
    password = "testpass"
    session_token = "testtoken"
    display_name = "Test User"

    # Add a user, then delete them
    dao_session.add_user(username, password, session_token, display_name)
    deleted = dao_session.delete_user_by_username(username)

    user = dao_session.session.query(Users).filter_by(username=username).first()

    assert deleted
    assert user is None


def test_update_session_token(dao_session):
    username = "testuser"
    password = "password"
    session_token = "old_token"
    display_name = "Test User"
    new_session_token = "new_token"

    dao_session.add_user(username, password, session_token, display_name)
    dao_session.update_session_token(username, new_session_token)

    assert dao_session.get_password_by_username(username) == password
    user = dao_session.session.query(Users).filter_by(username=username).first()
    assert user.session_token == new_session_token


def test_add_or_update_google_user(dao_session):
    google_id = "123"
    username = "googleuser@example.com"
    hashed_password = "hashed_password"
    session_token = "session_token"
    display_name = "Google User"

    dao_session.add_or_update_google_user(
        google_id, username, hashed_password, session_token, display_name
    )
    user = dao_session.session.query(Users).filter_by(username=username).first()
    assert user is not None
    assert user.google_id == google_id


def test_validate_and_clear_session_token(dao_session):
    username = "testuser"
    password = "password"
    session_token = "session_token"
    display_name = "Test User"

    dao_session.add_user(username, password, session_token, display_name)
    assert dao_session.validate_and_clear_session_token(username)
    user = dao_session.session.query(Users).filter_by(username=username).first()
    assert user.session_token == ""


def test_check_session_token(dao_session):
    username = "testuser"
    password = "password"
    session_token = "session_token"
    display_name = "Test User"

    dao_session.add_user(username, password, session_token, display_name)
    assert dao_session.check_session_token(username, session_token)
    assert not dao_session.check_session_token(username, "wrong_token")


def test_get_username(dao_session):
    username = "testuser"
    password = "password"
    session_token = "session_token"
    display_name = "Test User"

    # Add a user to retrieve later
    dao_session.add_user(username, password, session_token, display_name)
    user_id = dao_session.get_user_id(username)

    retrieved_username = dao_session.get_username(user_id)
    assert retrieved_username == username


def test_get_user_id(dao_session):
    username = "testuser"
    password = "password"
    session_token = "session_token"
    display_name = "Test User"

    # Add a user to retrieve their ID later
    dao_session.add_user(username, password, session_token, display_name)
    retrieved_user_id = dao_session.get_user_id(username)

    # Ensure the retrieved ID corresponds to an existing user
    assert retrieved_user_id is not None
    user = (
        dao_session.session.query(Users).filter(Users.id == retrieved_user_id).first()
    )
    assert user.username == username


def test_get_user_profile(dao_session):
    # Sample user data
    username = "testuser"
    password = "password"
    session_token = "session_token"
    display_name = "Test User"

    # Add a user to retrieve their profile
    dao_session.add_user(username, password, session_token, display_name)

    # Retrieve user profile
    profile_json = dao_session.get_user_profile(username)
    profile = json.loads(profile_json)

    # Assertions to ensure the profile matches expected values
    assert profile["username"] == username
    assert profile["display_name"] == display_name
    # Add more assertions as needed for other fields

    # Test for a non-existent user
    non_existent_profile = dao_session.get_user_profile("non_existent_user")
    assert non_existent_profile == json.dumps({})
