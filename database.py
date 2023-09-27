import psycopg2
import os
import logs

logger = logs.Log(__name__, 'database.log').get_logger()

DATABASE_URL = os.environ['DATABASE_URL']
PRODUCTION = os.environ['PRODUCTION']

class Database:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.migrations = [
            {
                'name': 'Add fields to users table',
                'query': """
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS amount_of_messages INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS total_tokens_used INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS message_history TEXT,
                    ADD COLUMN IF NOT EXISTS has_access BOOLEAN DEFAULT FALSE
                """
            },
            {
                'name': 'Add more user stats',
                'query': """
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS prompt_tokens INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS completion_tokens INTEGER DEFAULT 0
                """
            },
            {
                'name': 'Create statistics table',
                'query': """
                    CREATE TABLE IF NOT EXISTS statistics (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        amount_of_messages INTEGER DEFAULT 0,
                        total_tokens_used INTEGER DEFAULT 0,
                        prompt_tokens INTEGER DEFAULT 0,
                        completion_tokens INTEGER DEFAULT 0,
                        voice_usage INTEGER DEFAULT 0
                    )
                """
            },
            {
                'name': 'Add roles to users table',
                'query': """
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS role VARCHAR(255) DEFAULT 'user'
                """
            },
            {
                'name': 'Move statistics to new table',
                'query': """
                    INSERT INTO statistics (user_id, amount_of_messages, total_tokens_used, prompt_tokens, completion_tokens)
                    SELECT id, amount_of_messages, total_tokens_used, prompt_tokens, completion_tokens FROM users
                """
            },
            {
                'name': 'Remove statistics fields from users table',
                'query': """
                    ALTER TABLE users
                    DROP COLUMN IF EXISTS amount_of_messages,
                    DROP COLUMN IF EXISTS total_tokens_used,
                    DROP COLUMN IF EXISTS prompt_tokens,
                    DROP COLUMN IF EXISTS completion_tokens
                """
            },
            {
                'name': 'Add voice_usage to statistics table',
                'query': """
                    ALTER TABLE statistics 
                    ADD COLUMN IF NOT EXISTS voice_usage INTEGER DEFAULT 0
                """
            },
            {
                'name': 'Add unique constraint to user_id in statistics table',
                'query': """
                    ALTER TABLE statistics 
                    ADD CONSTRAINT statistics_user_id_key UNIQUE (user_id)
                """
            },
            # future migrations go here
        ]

    def open(self):
        if PRODUCTION == 'false':
            self.conn = psycopg2.connect(DATABASE_URL)
        else:
            self.conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        self.cursor = self.conn.cursor()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def create_table(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            session_token VARCHAR(255) NOT NULL,
            role VARCHAR(255) DEFAULT 'user'
        )
        """)
        self.conn.commit()

    def create_migrations_table(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.conn.commit()

    def log_migration(self, name):
        self.cursor.execute("""
        INSERT INTO migrations (name) VALUES (%s)
        """, (name,))
        self.conn.commit()

    def has_migration_been_executed(self, migration_name):
        self.cursor.execute("SELECT * FROM migrations WHERE name = %s", (migration_name,))
        return self.cursor.fetchone() is not None

    def execute_migration(self, migration):
        if not self.has_migration_been_executed(migration['name']):
            logger.info(f'Executing migration: {migration["name"]}')
            self.cursor.execute(migration['query'])
            self.conn.commit()
            self.log_migration(migration['name'])
        else:
            logger.info(f'Migration already executed: {migration["name"]}')

    def migrate_table(self):
        for migration in self.migrations:
            self.execute_migration(migration)

    def setup_database(self):
        self.open()
        self.create_table()
        self.create_migrations_table()
        self.migrate_table()
        self.close()
