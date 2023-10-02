name = "Add fields to users table"
query = """
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS amount_of_messages INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS total_tokens_used INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS message_history TEXT,
                    ADD COLUMN IF NOT EXISTS has_access BOOLEAN DEFAULT FALSE
                """