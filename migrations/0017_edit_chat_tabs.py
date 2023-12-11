name = "Edit Chat Tabs - chat id"
query = """
    ALTER TABLE chat_tabs
    ALTER COLUMN chat_id TYPE TEXT;
"""
