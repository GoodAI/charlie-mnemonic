name = "Add more user stats"
query = """
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS prompt_tokens INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS completion_tokens INTEGER DEFAULT 0
                """
