name = "Add Chat Tabs"
query = """
    CREATE TABLE IF NOT EXISTS chat_tabs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        tab_id TEXT NOT NULL,
        chat_id INTEGER DEFAULT 0,
        chat_name TEXT DEFAULT 'new chat',
        is_active BOOLEAN DEFAULT TRUE,
        is_enabled BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    )
"""
