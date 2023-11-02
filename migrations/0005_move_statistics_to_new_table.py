name = "Move statistics to new table"
query = """
                    INSERT INTO statistics (user_id, amount_of_messages, total_tokens_used, prompt_tokens, completion_tokens)
                    SELECT id, amount_of_messages, total_tokens_used, prompt_tokens, completion_tokens FROM users
                """
