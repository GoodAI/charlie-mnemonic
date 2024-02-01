import os

import pytest

from chat_tabs.dao import ChatTabsDAO


@pytest.fixture(scope="function")
def chat_tabs_dao():
    os.environ["NEW_DATABASE_URL"] = "sqlite:///:memory:?mode=memory&cache=shared"

    dao = ChatTabsDAO()
    dao.create_tables()

    yield dao

    dao.drop_tables()


def test_get_tab_data(chat_tabs_dao):
    # Add a chat tab for testing
    chat_tabs_dao.insert_tab_data(1, "chat123", "Test Chat", "tab123", True)
    tabs = chat_tabs_dao.get_tab_data(1)
    assert len(tabs) > 0, "Should have at least one tab"


def test_get_tab_count(chat_tabs_dao):
    count = chat_tabs_dao.get_tab_count(1)
    assert count >= 0, "Tab count should be non-negative"


def test_insert_and_get_tab_data(chat_tabs_dao):
    user_id, tab_id, chat_id, chat_name = 1, "tab1", "chat1", "Test Chat"
    chat_tabs_dao.insert_tab_data(user_id, chat_id, chat_name, tab_id, True)
    tab_data = chat_tabs_dao.get_tab_data(user_id)
    assert any(tab.tab_id == tab_id for tab in tab_data)


def test_get_tab_count(chat_tabs_dao):
    user_id, tab_id, chat_id, chat_name = 1, "tab1", "chat1", "Test Chat"
    chat_tabs_dao.insert_tab_data(user_id, chat_id, chat_name, tab_id, True)

    user_id = 1
    count = chat_tabs_dao.get_tab_count(user_id)
    assert count >= 1


def test_get_tab_description(chat_tabs_dao):
    user_id, tab_id, chat_id, chat_name = 1, "tab1", "chat1", "Test Chat"
    chat_tabs_dao.insert_tab_data(user_id, chat_id, chat_name, tab_id, True)

    tab_id = "tab1"
    description = chat_tabs_dao.get_tab_description(tab_id)
    assert description == "Test Chat"


def test_get_active_tab_data(chat_tabs_dao):
    user_id, tab_id, chat_id, chat_name = 1, "tab1", "chat1", "Test Chat"
    chat_tabs_dao.insert_tab_data(user_id, chat_id, chat_name, tab_id, True)

    user_id = 1
    active_tab = chat_tabs_dao.get_active_tab_data(user_id)
    assert active_tab and active_tab.is_active


def test_update_tab_data(chat_tabs_dao):
    user_id, tab_id, chat_id, chat_name = 1, "tab1", "chat1", "Test Chat"
    chat_tabs_dao.insert_tab_data(user_id, chat_id, chat_name, tab_id, True)

    user_id, tab_id, new_name = 1, "tab1", "Updated Chat"
    chat_tabs_dao.update_tab_data(user_id, new_name, tab_id, True)
    updated_tab = chat_tabs_dao.get_tab_data(user_id)[0]
    assert updated_tab.chat_name == new_name


def test_update_tab_description(chat_tabs_dao):
    user_id, tab_id, chat_id, chat_name = 1, "tab1", "chat1", "Test Chat"
    chat_tabs_dao.insert_tab_data(user_id, chat_id, chat_name, tab_id, True)

    tab_id, new_description = "tab1", "Updated Description"
    chat_tabs_dao.update_tab_description(tab_id, new_description)
    updated_description = chat_tabs_dao.get_tab_description(tab_id)
    assert updated_description == new_description


def test_set_active_tab(chat_tabs_dao):
    user_id, tab_id, chat_id, chat_name = 1, "tab1", "chat1", "Test Chat"
    chat_tabs_dao.insert_tab_data(user_id, chat_id, chat_name, tab_id, True)

    user_id, tab_id = 1, "tab1"
    chat_tabs_dao.set_active_tab(user_id, tab_id)
    active_tab = chat_tabs_dao.get_active_tab_data(user_id)
    assert active_tab.tab_id == tab_id


def test_delete_tab_data(chat_tabs_dao):
    user_id, tab_id = 1, "tab1"
    chat_tabs_dao.delete_tab_data(user_id)
    tab_count = chat_tabs_dao.get_tab_count(user_id)
    assert tab_count == 0


def test_disable_tab(chat_tabs_dao):
    user_id, tab_id = 1, "tab1"
    chat_tabs_dao.insert_tab_data(user_id, "chat1", "Test Chat", tab_id, True)
    chat_tabs_dao.disable_tab(user_id, tab_id)
    disabled_tab = chat_tabs_dao.get_tab_data(user_id)[0]
    assert not disabled_tab.is_enabled
