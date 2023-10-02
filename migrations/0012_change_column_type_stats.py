name = "Change column types in daily stats and statistics 2"
query = """
    ALTER TABLE daily_stats
    ALTER COLUMN spending_count TYPE FLOAT,
    ALTER COLUMN total_response_time TYPE FLOAT;

    ALTER TABLE statistics 
    ALTER COLUMN total_spending_count TYPE FLOAT,
    ALTER COLUMN voice_usage TYPE FLOAT;
"""
