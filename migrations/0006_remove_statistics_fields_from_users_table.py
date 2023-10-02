name = "Remove statistics fields from users table"
query = """
                    ALTER TABLE users
                    DROP COLUMN IF EXISTS amount_of_messages,
                    DROP COLUMN IF EXISTS total_tokens_used,
                    DROP COLUMN IF EXISTS prompt_tokens,
                    DROP COLUMN IF EXISTS completion_tokens
                """