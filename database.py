import datetime
import json
import sys

import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
import os
import importlib
import logs
import math

from config import SINGLE_USER_USERNAME, SINGLE_USER_DISPLAY_NAME, SINGLE_USER_PASSWORD
from configuration_page.settings_util import is_single_user

logger = logs.Log("database", "database.log").get_logger()


class Database:
    def __init__(self):
        self.DATABASE_URL = os.environ["DATABASE_URL"]
        self.PRODUCTION = os.environ["PRODUCTION"]
        self.single_user = is_single_user()
        self.conn = None
        self.cursor = None
        self.migrations_dir = "migrations"
        if getattr(sys, "frozen", False):
            # If the application is frozen (bundled)
            sys.path.append(os.path.join(sys._MEIPASS, "migrations"))

    def open(self):
        if self.PRODUCTION == "false":
            self.conn = psycopg2.connect(self.DATABASE_URL)
        else:
            self.conn = psycopg2.connect(self.DATABASE_URL, sslmode="require")
        self.cursor = self.conn.cursor()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def load_migrations(self):
        migrations = []
        from utils import get_root

        filenames = sorted(os.listdir(get_root(self.migrations_dir)))
        for filename in filenames:
            if filename.endswith(".py") and filename != "__init__.py":
                module = importlib.import_module(
                    f"{self.migrations_dir}.{filename[:-3]}"
                )
                migrations.append({"name": module.name, "query": module.query})
        return migrations

    def create_table(self):
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            session_token VARCHAR(255) NOT NULL,
            role VARCHAR(255) DEFAULT 'user'
        )
        """
        )
        self.conn.commit()

    def create_migrations_table(self):
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        self.conn.commit()

    def log_migration(self, name):
        self.cursor.execute(
            """
        INSERT INTO migrations (name) VALUES (%s)
        """,
            (name,),
        )
        self.conn.commit()

    def has_migration_been_executed(self, migration_name):
        self.cursor.execute(
            "SELECT * FROM migrations WHERE name = %s", (migration_name,)
        )
        return self.cursor.fetchone() is not None

    def execute_migration(self, migration):
        if not self.has_migration_been_executed(migration["name"]):
            logger.info(f'Executing migration: {migration["name"]}')
            self.cursor.execute(migration["query"])
            self.conn.commit()
            self.log_migration(migration["name"])
        else:
            logger.info(f'Migration already executed: {migration["name"]}')

    def migrate_table(self):
        migrations = self.load_migrations()
        for migration in migrations:
            self.execute_migration(migration)

    def setup_database(self):
        self.open()
        self.create_table()
        self.create_migrations_table()
        self.migrate_table()
        if self.single_user:
            self.create_default_user()
        self.close()

    def get_user_count(self):
        self.cursor.execute("SELECT COUNT(*) FROM users")
        return self.cursor.fetchone()[0]

    def create_default_user(self):
        user_count = self.get_user_count()
        if user_count > 0:
            return
        from authentication import Authentication

        Authentication().register(
            username=SINGLE_USER_USERNAME,
            password=SINGLE_USER_PASSWORD,
            display_name=SINGLE_USER_DISPLAY_NAME,
        )
        user_id = self.get_user_id(SINGLE_USER_USERNAME)
        self.update_user(
            user_id=user_id,
            access="true",
            role="admin",
        )

    def get_user(self, username):
        self.cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return self.cursor.fetchone()

    def get_user_role(self, username):
        self.cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
        return self.cursor.fetchone()

    def get_user_access(self, username):
        self.cursor.execute(
            "SELECT has_access FROM users WHERE username = %s", (username,)
        )
        return self.cursor.fetchone()[0]

    def get_tab_data(self, user_id):
        dict_cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        dict_cursor.execute(
            "SELECT * FROM chat_tabs WHERE user_id = %s ORDER BY id", (user_id,)
        )
        rows = dict_cursor.fetchall()
        return rows

    def get_tab_count(self, user_id):
        self.cursor.execute(
            "SELECT COUNT(*) FROM chat_tabs WHERE user_id = %s", (user_id,)
        )
        return self.cursor.fetchone()[0]

    def get_tab_description(self, tab_id):
        self.cursor.execute(
            "SELECT chat_name FROM chat_tabs WHERE tab_id = %s", (tab_id,)
        )
        return self.cursor.fetchone()[0]

    def get_active_tab_data(self, user_id):
        dict_cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        dict_cursor.execute(
            "SELECT * FROM chat_tabs WHERE user_id = %s AND is_active = true LIMIT 1",
            (user_id,),
        )
        row = dict_cursor.fetchone()
        return row

    def update_created_at(self, user_id, chat_id):
        now = datetime.datetime.now()
        self.cursor.execute(
            """
            UPDATE chat_tabs
            SET created_at = %s
            WHERE user_id = %s AND chat_id = %s
        """,
            (now, user_id, chat_id),
        )
        self.conn.commit()

    def insert_tab_data(self, user_id, chat_id, chat_name, tab_id, is_active):
        self.cursor.execute(
            """
        INSERT INTO chat_tabs (user_id, chat_id, chat_name, tab_id, is_active) 
        VALUES (%s, %s, %s, %s, %s)
        """,
            (user_id, chat_id, chat_name, tab_id, is_active),
        )
        self.conn.commit()

    def update_tab_data(self, user_id, chat_name, tab_id, is_active):
        self.cursor.execute(
            """
            UPDATE chat_tabs
            SET chat_name = %s, tab_id = %s, is_active = %s
            WHERE user_id = %s
        """,
            (chat_name, tab_id, is_active, user_id),
        )
        self.conn.commit()

    def update_tab_description(self, tab_id, chat_name):
        self.cursor.execute(
            """
            UPDATE chat_tabs
            SET chat_name = %s
            WHERE tab_id = %s
        """,
            (chat_name, tab_id),
        )
        self.conn.commit()

    def set_active_tab(self, user_id, tab_id):
        # Convert user_id and tab_id to integers if they are not already
        try:
            # set the active tab to false for all other tabs except
            self.cursor.execute(
                """
                UPDATE chat_tabs
                SET is_active = false
                WHERE user_id = %s AND chat_id != %s
                """,
                (user_id, tab_id),
            )
            self.conn.commit()

            # set the active tab to true for the given tab_id
            self.cursor.execute(
                """
                UPDATE chat_tabs
                SET is_active = true, is_enabled = true
                WHERE user_id = %s AND chat_id = %s
                """,
                (user_id, tab_id),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(e)

    def delete_tab_data(self, user_id):
        self.cursor.execute("DELETE FROM chat_tabs WHERE user_id = %s", (user_id,))
        self.conn.commit()

    def disable_tab(self, user_id, tab_id):
        self.cursor.execute(
            """
            UPDATE chat_tabs
            SET is_enabled = false
            WHERE user_id = %s AND chat_id = %s
        """,
            (user_id, tab_id),
        )
        self.conn.commit()

    def get_username(self, user_id):
        self.cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        return self.cursor.fetchone()

    def get_user_id(self, username):
        self.cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        return self.cursor.fetchone()

    def update_user(self, user_id, access, role):
        if access == "true":
            access = True
        else:
            access = False
        self.cursor.execute(
            """
            UPDATE users
            SET has_access = %s, role = %s
            WHERE id = %s
        """,
            (access, role, user_id),
        )
        self.conn.commit()

    def get_admin_controls(self):
        dict_cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        dict_cursor.execute("SELECT * FROM admin_controls")
        rows = dict_cursor.fetchall()
        if not rows:
            return json.dumps({"id": 1, "daily_spending_limit": 10}, default=str)
        return json.dumps(rows[0], default=str)

    def get_daily_limit(self):
        self.cursor.execute("SELECT daily_spending_limit FROM admin_controls")
        row = self.cursor.fetchone()
        if row is not None:
            daily_limit = row[0]
        else:
            daily_limit = 1
        return daily_limit

    def update_admin_controls(
        self, id, daily_spending_limit, allow_access, maintenance
    ):
        self.cursor.execute(
            """
            INSERT INTO admin_controls (id, daily_spending_limit, allow_access, maintenance)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET daily_spending_limit = EXCLUDED.daily_spending_limit, allow_access = EXCLUDED.allow_access, maintenance = EXCLUDED.maintenance
        """,
            (id, daily_spending_limit, allow_access, maintenance),
        )
        self.conn.commit()

    def get_maintenance_mode(self):
        self.cursor.execute("SELECT maintenance FROM admin_controls")
        row = self.cursor.fetchone()
        if row is not None:
            maintenance = row[0]
        else:
            maintenance = False
        return maintenance

    def get_global_statistics(self):
        """Get the global statistics.

        returns: a dictionary containing the global statistics
        """
        dict_cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        dict_cursor.execute(
            "SELECT SUM(amount_of_messages) as total_messages, SUM(total_tokens_used) as total_tokens, SUM(prompt_tokens) as total_prompt_tokens, SUM(completion_tokens) as total_completion_tokens, SUM(voice_usage) as total_voice_usage, SUM(total_spending_count) as total_spending, AVG(total_average_response_time) as average_response_time FROM statistics"
        )
        row = dict_cursor.fetchone()
        return json.dumps(row, default=str)

    def get_all_statistics(self):
        dict_cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        dict_cursor.execute("SELECT * FROM statistics")
        rows = dict_cursor.fetchall()

        # replace the user_id with the username
        for row in rows:
            row["username"] = self.get_username(row["user_id"])[0]
        return json.dumps(rows, default=str)

    def get_user_statistics(self, user_id):
        dict_cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        dict_cursor.execute(
            "SELECT * FROM daily_stats WHERE user_id = %s ORDER BY timestamp DESC",
            (user_id,),
        )
        rows = dict_cursor.fetchall()
        return json.dumps(rows, default=str)

    def get_user_profile(self, username):
        dict_cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        dict_cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = dict_cursor.fetchone()
        return json.dumps(row, default=str)

    def get_statistics(self, page, items_per_page):
        dict_cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        offset = (page - 1) * items_per_page
        dict_cursor.execute(
            """
            SELECT users.id AS user_id, users.username, users.role, users.has_access, statistics.user_id as user_sid, statistics.amount_of_messages, statistics.total_tokens_used, statistics.prompt_tokens, statistics.completion_tokens, statistics.voice_usage, statistics.total_spending_count, statistics.total_average_response_time
            FROM users 
            LEFT JOIN statistics 
            ON users.id = statistics.user_id 
            ORDER BY users.id LIMIT %s OFFSET %s
            """,
            (items_per_page, offset),
        )
        rows = dict_cursor.fetchall()
        return json.dumps(rows, default=str)

    def get_total_statistics_pages(self, items_per_page):
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total_items = self.cursor.fetchone()[0]
        return math.ceil(total_items / float(items_per_page))

    def get_statistic(self, username):
        """Get the statistic for the given username.
        username: the name of the user

        returns: a dictionary containing the statistic
        """
        user_id = self.get_user(username)[0]
        dict_cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        dict_cursor.execute("SELECT * FROM statistics WHERE user_id = %s", (user_id,))
        return dict_cursor.fetchone()

    def update_statistic(self, username, **kwargs):
        """Update the statistic for the given username.
        username: the name of the user

        kwargs: a dictionary containing the rows update

        "id","user_id","message_characters","message_tokens","message_length","message_amount",
        "prompt_tokens","generation_tokens","brain_tokens","average_input_msg_tokens","spending_count",
        "average_response_time","time_per_session","time_between_calls","addons_used","settings_used",
        "timestamp","total_response_time","response_count"

        Example usage:\n
        db.update_statistic(user_id, amount_of_messages=10, total_tokens_used=200)
        """
        user_id = self.get_user(username)[0]
        set_clause = ", ".join([f"{k} = %s" for k in kwargs.keys()])
        query = f"UPDATE statistics SET {set_clause} WHERE user_id = %s"
        params = (*kwargs.values(), user_id)
        self.cursor.execute(query, params)
        self.conn.commit()

    def delete_statistic(self, user_id):
        self.cursor.execute("DELETE FROM statistics WHERE user_id = %s", (user_id,))
        self.conn.commit()

    def get_daily_stats(self, username):
        """Get the daily stats for the given username.
        username: the username of the user

        returns: a dictionary containing the daily stats
        "message_characters",
        "message_tokens",
        "message_length",
        "message_amount",
        "prompt_tokens",
        "generation_tokens",
        "brain_tokens",
        "average_input_msg_tokens",
        "spending_count",
        "average_response_time",
        "time_per_session",
        "time_between_calls",
        "id",
        "settings_used",
        "addons_used"

        example usage:\n
        db.get_daily_stats(username)['average_response_time']
        """

        user_id = self.get_user(username)[0]
        dict_cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # get the current date
        current_date = datetime.datetime.now().date()

        # execute the SQL query with the user_id and the current date
        dict_cursor.execute(
            "SELECT * FROM daily_stats WHERE user_id = %s AND DATE(timestamp) = %s",
            (user_id, current_date),
        )
        return dict_cursor.fetchone()

    def add_daily_stats(self, user_id, **kwargs):
        columns = ", ".join(kwargs.keys())
        values = ", ".join(["%s"] * len(kwargs))
        self.cursor.execute(
            f"""
        INSERT INTO daily_stats (user_id, {columns}) 
        VALUES (%s, {values})
        """,
            (user_id, *kwargs.values()),
        )
        self.conn.commit()

    def update_daily_stats_token_usage(self, username, **kwargs):
        """Update the token usage for the given username.
        username: the username of the user

        kwargs: a dictionary containing the rows update

        "message_characters",
        "message_tokens",
        "message_length",
        "message_amount",
        "prompt_tokens",
        "generation_tokens",
        "brain_tokens",
        "average_input_msg_tokens",
        "spending_count",
        "average_response_time",
        "time_per_session",
        "time_between_calls",
        "id",
        "settings_used",
        "addons_used"
        """
        # get the user_id for the given username
        user_id = self.get_user(username)[0]

        # get the current timestamp
        current_timestamp = datetime.datetime.now()

        # check if a record for the current date exists
        self.cursor.execute(
            "SELECT 1 FROM daily_stats WHERE user_id = %s AND DATE(timestamp) = DATE(%s)",
            (user_id, current_timestamp),
        )
        record_exists = self.cursor.fetchone() is not None

        # update or insert the token usage in the daily stats table
        if record_exists:
            set_clause = ", ".join([f"{k} = {k} + %s" for k in kwargs.keys()])
            query = f"""
            UPDATE daily_stats SET {set_clause} 
            WHERE user_id = %s AND DATE(timestamp) = DATE(%s)
            """
            params = (*kwargs.values(), user_id, current_timestamp)
        else:
            columns = ", ".join(kwargs.keys())
            values = ", ".join(["%s"] * len(kwargs))
            query = f"""
            INSERT INTO daily_stats (user_id, {columns}) 
            VALUES (%s, {values})
            """
            params = (user_id, *kwargs.values())

        self.cursor.execute(query, params)
        self.conn.commit()

        # get the token usage
        self.cursor.execute(
            f"SELECT {', '.join(kwargs.keys())} FROM daily_stats WHERE user_id = %s AND DATE(timestamp) = DATE(%s)",
            (user_id, current_timestamp),
        )
        return self.cursor.fetchone()

    def replace_daily_stats_token_usage(self, username, **kwargs):
        """Replace the token usage for the given username.
        username: the username of the user

        kwargs: a dictionary containing the rows update

        "message_characters",
        "message_tokens",
        "message_length",
        "message_amount",
        "prompt_tokens",
        "generation_tokens",
        "brain_tokens",
        "average_input_msg_tokens",
        "spending_count",
        "average_response_time",
        "time_per_session",
        "time_between_calls",
        "id",
        "settings_used",
        "addons_used"
        """
        # get the user_id for the given username
        user_id = self.get_user(username)[0]

        # get the current timestamp
        current_timestamp = datetime.datetime.now()

        # check if a record for the current date exists
        self.cursor.execute(
            "SELECT 1 FROM daily_stats WHERE user_id = %s AND DATE(timestamp) = DATE(%s)",
            (user_id, current_timestamp),
        )
        record_exists = self.cursor.fetchone() is not None

        # update or insert the token usage in the daily stats table
        if record_exists:
            set_clause = ", ".join([f"{k} = %s" for k in kwargs.keys()])
            query = f"""
            UPDATE daily_stats SET {set_clause} 
            WHERE user_id = %s AND DATE(timestamp) = DATE(%s)
            """
            params = (*kwargs.values(), user_id, current_timestamp)
        else:
            columns = ", ".join(kwargs.keys())
            values = ", ".join(["%s"] * len(kwargs))
            query = f"""
            INSERT INTO daily_stats (user_id, {columns}) 
            VALUES (%s, {values})
            """
            params = (user_id, *kwargs.values())

        self.cursor.execute(query, params)
        self.conn.commit()

        # get the token usage
        self.cursor.execute(
            f"SELECT {', '.join(kwargs.keys())} FROM daily_stats WHERE user_id = %s AND DATE(timestamp) = DATE(%s)",
            (user_id, current_timestamp),
        )
        return self.cursor.fetchone()

    def delete_daily_stats(self, user_id):
        self.cursor.execute("DELETE FROM daily_stats WHERE user_id = %s", (user_id,))
        self.conn.commit()

    def get_admin_control(self, id):
        self.cursor.execute("SELECT * FROM admin_controls WHERE id = %s", (id,))
        return self.cursor.fetchone()

    def add_admin_control(self, **kwargs):
        columns = ", ".join(kwargs.keys())
        values = ", ".join(["%s"] * len(kwargs))
        self.cursor.execute(
            f"""
        INSERT INTO admin_controls ({columns}) 
        VALUES ({values})
        """,
            (*kwargs.values(),),
        )
        self.conn.commit()

    def update_admin_control(self, id, **kwargs):
        set_clause = ", ".join([f"{k} = %s" for k in kwargs.keys()])
        self.cursor.execute(
            f"""
        UPDATE admin_controls SET {set_clause} 
        WHERE id = %s
        """,
            (*kwargs.values(), id),
        )
        self.conn.commit()

    def delete_admin_control(self, id):
        self.cursor.execute("DELETE FROM admin_controls WHERE id = %s", (id,))
        self.conn.commit()

    def update_token_usage(self, username, **kwargs):
        """Update the token usage for the given username.
        username: the username of the user

        kwargs: a dictionary containing the rows update

        "total_tokens_used",
        "prompt_tokens",
        "completion_tokens"

        Returns: total_tokens_used, prompt_tokens, completion_tokens
        """
        # get the user_id for the given username=
        user_id = self.get_user(username)[0]

        # update or insert the token usage in the statistics table
        set_clause = ", ".join([f"{k} = statistics.{k} + %s" for k in kwargs.keys()])
        query = f"""
        INSERT INTO statistics (user_id, {', '.join(kwargs.keys())}) 
        VALUES (%s, {', '.join(['%s'] * len(kwargs))})
        ON CONFLICT (user_id) DO UPDATE SET {set_clause}
        """
        params = (user_id, *kwargs.values(), *kwargs.values())
        self.cursor.execute(query, params)
        self.conn.commit()

        # get the token usage
        self.cursor.execute(
            "SELECT total_tokens_used, prompt_tokens, completion_tokens FROM statistics WHERE user_id = %s",
            (user_id,),
        )
        return self.cursor.fetchone()

    def get_display_name(self, username):
        """Get the display name for the given username.
        username: the username of the user

        returns: a dictionary containing the display name
        """
        # get the user_id for the given username
        user_id = self.get_user(username)[0]

        # get the display name
        self.cursor.execute("SELECT display_name FROM users WHERE id = %s", (user_id,))
        return self.cursor.fetchone()

    def update_display_name(self, username, display_name):
        """Update the display name for the given username.
        username: the username of the user

        returns: a dictionary containing the display name
        """
        # get the user_id for the given username
        user_id = self.get_user(username)[0]

        # update the display name
        self.cursor.execute(
            "UPDATE users SET display_name = %s WHERE id = %s", (display_name, user_id)
        )
        self.conn.commit()

    def get_token_usage(self, username, daily=False):
        """Get the token usage for the given username.
        username: the username of the user

        daily: if True, get the daily token usage, otherwise get the total token usage

        returns: a dictionary containing the token usage
        """
        # get the user_id for the given username
        user_id = self.get_user(username)[0]

        # get the token usage
        if daily:
            # get the current date
            current_date = datetime.datetime.now().date()

            # execute the SQL query with the user_id and the current date
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            self.cursor.execute(
                "SELECT * FROM daily_stats WHERE user_id = %s AND DATE(timestamp) = %s",
                (user_id, current_date),
            )
            row = self.cursor.fetchone()
            if row is None:
                prompt_tokens = 0
                completion_tokens = 0
                total_cost = 0
            else:
                prompt_tokens = row["prompt_tokens"]
                completion_tokens = row["generation_tokens"]
                total_cost = row["spending_count"]
            return prompt_tokens + completion_tokens, round(total_cost, 5)
        else:
            # execute the SQL query with the user_id
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            self.cursor.execute(
                "SELECT total_tokens_used, prompt_tokens, completion_tokens FROM statistics WHERE user_id = %s",
                (user_id,),
            )
            row = self.cursor.fetchone()
            if row is None:
                prompt_tokens = 0
                completion_tokens = 0
                total_tokens_used = 0
            else:
                prompt_tokens = row["prompt_tokens"]
                completion_tokens = row["completion_tokens"]
                total_tokens_used = row["total_tokens_used"]
            prompt_cost = round(prompt_tokens * 0.03 / 1000, 5)
            completion_cost = round(completion_tokens * 0.06 / 1000, 5)
            total_cost = round(prompt_cost + completion_cost, 5)
            return total_tokens_used, total_cost

    def update_message_count(self, username):
        """Update the message count for the given username."""
        # get the user_id for the given username
        user_id = self.get_user(username)[0]

        # get the current timestamp
        current_timestamp = datetime.datetime.now()

        # check if a record for the current date exists
        self.cursor.execute(
            "SELECT 1 FROM daily_stats WHERE user_id = %s AND DATE(timestamp) = DATE(%s)",
            (user_id, current_timestamp),
        )
        record_exists = self.cursor.fetchone() is not None

        # update or insert the message count in the daily stats table
        if record_exists:
            query = """
            UPDATE daily_stats SET message_amount = daily_stats.message_amount + 1 
            WHERE user_id = %s AND DATE(timestamp) = DATE(%s)
            """
            params = (user_id, current_timestamp)
        else:
            query = """
            INSERT INTO daily_stats (user_id, message_amount) 
            VALUES (%s, 1)
            """
            params = (user_id,)

        self.cursor.execute(query, params)
        self.conn.commit()

        # get the daily message count
        self.cursor.execute(
            "SELECT message_amount FROM daily_stats WHERE user_id = %s AND DATE(timestamp) = DATE(%s)",
            (user_id, current_timestamp),
        )
        daily_messages_count = self.cursor.fetchone()

        # update or insert the message count in the statistics table
        query = """
        INSERT INTO statistics (user_id, amount_of_messages) 
        VALUES (%s, 1)
        ON CONFLICT (user_id) DO UPDATE SET amount_of_messages = statistics.amount_of_messages + 1
        """
        self.cursor.execute(query, (user_id,))
        self.conn.commit()

        # get the total message count
        self.cursor.execute(
            "SELECT amount_of_messages FROM statistics WHERE user_id = %s", (user_id,)
        )
        total_messages_count = self.cursor.fetchone()

        return daily_messages_count, total_messages_count

    def add_voice_usage(self, username, text_lenght):
        """Add the voice usage for the given username to the statistics table."""
        # get the user_id for the given username
        user_id = self.get_user(username)[0]

        # 0.30$ per 1000 characters
        voice_usage = round(text_lenght * 0.30 / 1000, 5)

        # update or insert the voice usage in the statistics table
        query = """
        INSERT INTO statistics (user_id, voice_usage) 
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET voice_usage = statistics.voice_usage + %s
        """
        self.cursor.execute(query, (user_id, voice_usage, voice_usage))
        self.conn.commit()

        # get the voice usage
        self.cursor.execute(
            "SELECT voice_usage FROM statistics WHERE user_id = %s", (user_id,)
        )
        return self.cursor.fetchone()
