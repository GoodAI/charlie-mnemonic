name = "Add avatar and other fields to users"
query = """
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS can_use_avatar BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS avatar_usage FLOAT,
    ADD COLUMN IF NOT EXISTS whisper_usage FLOAT,
    ADD COLUMN IF NOT EXISTS first_visit BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS use_custom_system_prompt BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS cot_loops INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS receive_mails BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(255);

    ALTER TABLE admin_controls
    ADD COLUMN IF NOT EXISTS allow_avatar_usage BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS welcome_message VARCHAR(255),
    ADD COLUMN IF NOT EXISTS allowed_addons VARCHAR(255);
"""
