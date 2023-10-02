name = "Change column types in daily stats and statistics"
query = """
    ALTER TABLE daily_stats
    ALTER COLUMN average_input_msg_tokens TYPE FLOAT,
    ALTER COLUMN average_response_time TYPE FLOAT,
    ALTER COLUMN time_per_session TYPE FLOAT,
    ALTER COLUMN time_between_calls TYPE FLOAT;

    ALTER TABLE statistics 
    ALTER COLUMN total_average_response_time TYPE FLOAT;
"""
