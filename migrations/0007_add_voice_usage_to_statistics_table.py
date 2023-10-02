name = "Add voice_usage to statistics table"
query = """
                    ALTER TABLE statistics 
                    ADD COLUMN IF NOT EXISTS voice_usage INTEGER DEFAULT 0
                """