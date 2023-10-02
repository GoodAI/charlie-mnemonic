name = "Create statistics table"
query = """
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