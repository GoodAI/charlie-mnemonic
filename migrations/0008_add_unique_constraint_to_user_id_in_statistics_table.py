name = "Add unique constraint to user_id in statistics table"
query = """
                    ALTER TABLE statistics 
                    ADD CONSTRAINT statistics_user_id_key UNIQUE (user_id)
                """
