name = "Add daily stats and admin controls"
query = """
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        message_characters INTEGER DEFAULT 0,
                        message_tokens INTEGER DEFAULT 0,
                        message_length INTEGER DEFAULT 0,
                        message_amount INTEGER DEFAULT 0,
                        prompt_tokens INTEGER DEFAULT 0,
                        generation_tokens INTEGER DEFAULT 0,
                        brain_tokens INTEGER DEFAULT 0,
                        average_input_msg_tokens INTEGER DEFAULT 0,
                        spending_count INTEGER DEFAULT 0,
                        average_response_time INTEGER DEFAULT 0,
                        time_per_session INTEGER DEFAULT 0,
                        time_between_calls INTEGER DEFAULT 0,
                        addons_used VARCHAR(255),
                        settings_used VARCHAR(255),
                        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS admin_controls (
                        id SERIAL PRIMARY KEY,
                        daily_spending_limit INTEGER DEFAULT 0,
                        user_admin BOOLEAN DEFAULT FALSE,
                        allow_access BOOLEAN DEFAULT FALSE,
                        server_reboot BOOLEAN DEFAULT FALSE,
                        maintenance BOOLEAN DEFAULT FALSE
                    );
                    
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS session_time INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS addons_used VARCHAR(255),
                    ADD COLUMN IF NOT EXISTS settings_used VARCHAR(255),
                    ADD COLUMN IF NOT EXISTS banned BOOLEAN DEFAULT FALSE;
                    
                    ALTER TABLE statistics 
                    ADD COLUMN IF NOT EXISTS total_spending_count INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS total_average_response_time INTEGER DEFAULT 0;
                """
