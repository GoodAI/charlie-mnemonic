import os
import unittest
import psycopg2
from unittest.mock import patch, MagicMock
from psycopg2.extras import RealDictCursor
from database import Database
from dotenv import load_dotenv

load_dotenv()


class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Use the test database for the tests
        self.db = Database()
        self.db.DATABASE_URL = os.getenv("TEST_DATABASE_URL")
        self.db.open()
        # Save the original DATABASE_URL
        self.original_database_url = self.db.DATABASE_URL
        self.db.setup_database()
        self.truncate_tables()

    def tearDown(self):
        # Revert to the original DATABASE_URL
        self.db.DATABASE_URL = self.original_database_url
        self.db.close()

    def truncate_tables(self):
        self.db.open()
        self.db.cursor.execute("TRUNCATE TABLE users CASCADE")
        self.db.cursor.execute("TRUNCATE TABLE admin_controls CASCADE")

    def test_check_table(self):
        self.db.open()
        self.db.cursor.execute("SELECT * FROM users")
        columns = [desc[0] for desc in self.db.cursor.description]
        self.assertListEqual(
            columns,
            [
                "id",
                "username",
                "password",
                "session_token",
                "role",
                "message_history",
                "has_access",
                "session_time",
                "addons_used",
                "settings_used",
                "banned",
                "google_id",
                "display_name",
                "can_use_avatar",
                "avatar_usage",
                "whisper_usage",
                "first_visit",
                "use_custom_system_prompt",
                "cot_loops",
                "receive_mails",
                "password_reset_token",
            ],
        )

    def test_create_migrations_table(self):
        self.db.open()
        self.db.create_migrations_table()
        self.db.cursor.execute("SELECT * FROM migrations")
        columns = [desc[0] for desc in self.db.cursor.description]
        self.assertListEqual(columns, ["id", "name", "executed_at"])

    def test_log_migration(self):
        self.db.open()
        self.db.log_migration("test_migration")
        self.db.cursor.execute("SELECT * FROM migrations WHERE name = 'test_migration'")
        row = self.db.cursor.fetchone()
        self.assertIsNotNone(row)

    def test_has_migration_been_executed(self):
        self.db.open()
        self.db.log_migration("test_migration")
        self.assertTrue(self.db.has_migration_been_executed("test_migration"))
        self.assertFalse(self.db.has_migration_been_executed("non_existent_migration"))

    def test_execute_migration(self):
        migration = {
            "name": "test_migration",
            "query": "CREATE TABLE test_table (id SERIAL PRIMARY KEY)",
        }
        self.db.open()
        self.db.execute_migration(migration)
        self.db.cursor.execute("SELECT * FROM test_table")
        columns = [desc[0] for desc in self.db.cursor.description]
        self.assertListEqual(columns, ["id"])

    def test_migrate_table(self):
        migration = {
            "name": "test_migration",
            "query": "CREATE TABLE test_table (id SERIAL PRIMARY KEY)",
        }
        with patch.object(self.db, "load_migrations", return_value=[migration]):
            self.db.open()
            self.db.migrate_table()
            self.db.cursor.execute("SELECT * FROM test_table")
            columns = [desc[0] for desc in self.db.cursor.description]
            self.assertListEqual(columns, ["id"])

    def test_add_user(self):
        self.db.open()
        self.truncate_tables()
        self.db.add_user("test_user", "test_password", "test_session_token")
        self.db.cursor.execute("SELECT * FROM users WHERE username = 'test_user'")
        row = self.db.cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "test_user")
        self.assertEqual(row[2], "test_password")
        self.assertEqual(row[3], "test_session_token")
        self.assertEqual(row[4], "user")

    def test_update_user(self):
        self.db.open()
        self.truncate_tables()
        self.db.add_user("test_user", "test_password", "test_session_token")
        user_id = self.db.get_user_id("test_user")[0]
        self.db.update_user(user_id, "true", "admin")
        self.db.cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = self.db.cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[4], "admin")

    def test_delete_user(self):
        self.db.open()
        self.truncate_tables()
        self.db.add_user("test_user", "test_password", "test_session_token")
        self.db.delete_user("test_user")
        self.db.cursor.execute("SELECT * FROM users WHERE username = 'test_user'")
        row = self.db.cursor.fetchone()
        self.assertIsNone(row)

    def test_get_admin_controls(self):
        self.db.open()
        self.db.cursor.execute("DELETE FROM admin_controls")
        self.db.cursor.execute(
            "INSERT INTO admin_controls (id, daily_spending_limit, user_admin, allow_access, server_reboot, maintenance, allow_avatar_usage, welcome_message, allowed_addons) VALUES (1, 10, true, true, false, false, true, 'Welcome!', 'addon1,addon2')"
        )
        result = self.db.get_admin_controls()
        self.assertEqual(
            result,
            '{"id": 1, "daily_spending_limit": 10, "user_admin": true, "allow_access": true, "server_reboot": false, "maintenance": false, "allow_avatar_usage": true, "welcome_message": "Welcome!", "allowed_addons": "addon1,addon2"}',
        )

    def test_get_daily_limit(self):
        self.db.open()
        self.db.cursor.execute("DELETE FROM admin_controls")
        self.db.cursor.execute(
            "INSERT INTO admin_controls (id, daily_spending_limit, allow_access, maintenance) VALUES (1, 10, true, false)"
        )
        result = self.db.get_daily_limit()
        self.assertEqual(result, 10)

    def test_get_user(self):
        self.db.open()
        self.db.add_user("test_user", "test_password", "test_session_token")
        result = self.db.get_user("test_user")
        self.assertIsNotNone(result)
        self.assertEqual(result[1], "test_user")
        self.assertEqual(result[2], "test_password")
        self.assertEqual(result[3], "test_session_token")
        self.assertEqual(result[4], "user")

    def test_get_user_role(self):
        self.db.open()
        self.truncate_tables()
        self.db.add_user("test_user", "test_password", "test_session_token")
        result = self.db.get_user_role("test_user")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "user")

    def test_get_user_access(self):
        self.db.open()
        self.truncate_tables()
        self.db.add_user("test_user", "test_password", "test_session_token")
        result = self.db.get_user_access("test_user")
        self.assertIsNotNone(result)
        self.assertEqual(result, False)

    def test_get_username(self):
        self.db.open()
        self.truncate_tables()
        self.db.add_user("test_user", "test_password", "test_session_token")
        user_id = self.db.get_user_id("test_user")[0]
        result = self.db.get_username(user_id)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "test_user")

    def test_get_user_id(self):
        self.db.open()
        self.truncate_tables()
        self.db.add_user("test_user", "test_password", "test_session_token")
        result = self.db.get_user_id("test_user")
        self.assertIsNotNone(result)
        # assert the is as number
        self.assertIsInstance(result[0], int)


if __name__ == "__main__":
    unittest.main()
