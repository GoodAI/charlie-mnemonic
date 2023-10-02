name = "Add response time tracking to daily stats"
query = """
    ALTER TABLE daily_stats
    ADD COLUMN IF NOT EXISTS total_response_time INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS response_count INTEGER DEFAULT 0;
"""
