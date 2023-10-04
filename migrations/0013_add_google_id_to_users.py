name = "Add Google ID to users"
query = """
    ALTER TABLE users
    ADD COLUMN google_id VARCHAR(255) UNIQUE;
"""
