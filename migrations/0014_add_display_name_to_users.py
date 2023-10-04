name = "Add Display Name to users"
query = """
    ALTER TABLE users
    ADD COLUMN display_name VARCHAR(255);
"""
