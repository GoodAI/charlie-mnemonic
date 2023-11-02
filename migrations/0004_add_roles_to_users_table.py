name = "Add roles to users table"
query = """
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS role VARCHAR(255) DEFAULT 'user'
                """
