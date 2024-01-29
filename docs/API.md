# API Endpoints
CLANG provides several API endpoints for managing users, handling messages, and managing data. Here are a few key endpoints:

- `/register/`: Register a new user.
- `/login/`: Log in an existing user.
- `/logout/`: Log out a user.
- `/check_token/`: Check if a user’s session token is valid.
- `/load_settings/`: Retrieve a user’s settings.
- `/update_settings/`: Update a user’s settings.
- `/message/`: Process a text message from a user.
- `/message_no_modules/`: Process a text message from a user without using any additional modules.
- `/message_audio/`: Process an audio message from a user.
- `/generate_audio/`: Generate an audio message from text.
- `/save_data/`: Save a user’s data to a .zip file.
- `/delete_data/`: Delete a user’s data. (WIP)
- `/upload_data/`: Upload a .zip file of a user’s data. (WIP)

For more details on using these endpoints, refer to the FastAPI-generated API documentation at http://127.0.0.1:8002/docs when the application is running.
