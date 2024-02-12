import json
import os

import pytest

from user_management.dao import UsersDAO
from user_management.models import Users
from user_management.session import session_factory

# Use an in-memory SQLite database for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def dao_session():
    os.environ["NEW_DATABASE_URL"] = "sqlite:///:memory:"
    session_factory.get_refreshed()

    dao = UsersDAO()
    dao.create_tables()

    yield dao

    dao.drop_tables()
    dao.close_session()


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


def test_allow_user_access(dao_session):
    test_username = "testuser"
    test_password = "testpassword"
    test_display_name = "Test User"
    dao_session.add_user(test_username, test_password, "token", test_display_name)

    user_id = dao_session.get_user_id(test_username)
    assert user_id is not None, "Test user should exist"

    # Update user access and role
    dao_session.update_user(user_id, True, "admin")

    # Fetch updated role and access
    updated_user = dao_session.get_user(test_username)
    assert updated_user.role == "admin"
    assert updated_user.has_access is True


def test_update_display_name(dao_session):
    # Setup: create a test user
    test_username = "testuser"
    test_password = "testpassword"
    test_display_name = "Original Name"
    dao_session.add_user(test_username, test_password, "token", test_display_name)

    # Test updating the display name
    new_display_name = "New Name"
    success = dao_session.update_display_name(test_username, new_display_name)
    assert success, "Update should be successful"

    updated_user = dao_session.get_user(test_username)
    assert (
        updated_user.display_name == new_display_name
    ), "Display name should be updated"

    non_existent_update = dao_session.update_display_name("nonexistentuser", "Name")
    assert not non_existent_update, "Update should fail for non-existent user"


def test_get_total_statistics_pages(dao_session):
    # Add some test users
    for i in range(10):  # Add 10 users for testing
        dao_session.add_user(f"testuser{i}", "testpassword", "token", f"Test User {i}")

    # Test with 2 items per page, expecting 5 pages for 10 users
    pages = dao_session.get_total_statistics_pages(2)
    assert pages == 5, "Should be 5 pages for 10 users with 2 users per page"

    # Test with 5 items per page, expecting 2 pages for 10 users
    pages = dao_session.get_total_statistics_pages(5)
    assert pages == 2, "Should be 2 pages for 10 users with 5 users per page"

    # Test with more items per page than total users
    pages = dao_session.get_total_statistics_pages(15)
    assert pages == 1, "Should be 1 page for 10 users with 15 users per page"


def test_get_user_profile(dao_session):
    # Setup: create a test user
    test_username = "testuser"
    test_password = "testpassword"
    test_display_name = "Test User"
    dao_session.add_user(test_username, test_password, "token", test_display_name)

    # Fetch user profile
    profile_json = dao_session.get_user_profile(test_username)
    profile = json.loads(profile_json)

    # Assertions to ensure the profile contains expected data
    assert profile["username"] == test_username
    assert profile["display_name"] == test_display_name

    non_existent_profile = dao_session.get_user_profile("nonexistentuser")
    assert non_existent_profile == json.dumps({})
