# CLANG - Continual Learning Agent with Neural Growth

CLANG is a Python application that uses OpenAI’s GPT-4 model to provide an interactive conversational agent. It is designed to continually learn and grow through user interactions, extending the capabilities of GPT-4 with additional functionalities.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Contributing](#contributing)
- [License](#license)
- [Todo](#todo)

## Features
- User authentication and session management.
- Continual learning through user interactions.
- Ability to generate and process audio messages.
- User data management including import/export of data. (WIP)
- Extensible with additional modules (addons).
- WebSocket support for real-time communication.

## Installation
### Prerequisites
- Python 3.10 or higher
- pip
- PostgreSQL database
- Uvicorn `sudo apt-get install uvicorn`
- ffmpeg `sudo apt-get install ffmpeg` (On Windows: Download ffmpeg from the official website (https://ffmpeg.org/download.html) and add it to your system’s PATH.)


### Setup
1. It is recommended to run the application in a virtual environment. You can set it up and activate it using the following commands:
```bash
python3 -m venv venv
source venv/bin/activate
```
2. Clone this repository:
```bash
git clone https://github.com/airobinnet/CLANG.git
cd CLANG
```
3. Install the required Python packages.
```bash
pip install -r requirements.txt
```
4. Copy the .env_sample file to .env and fill in your API keys and other settings:
```bash
cp .env_sample .env
nano .env
```
In the .env file, set the `PRODUCTION` variable to `false` for local development or `true` for a live setup.
```bash
# Set to true when deployed
PRODUCTION = false
```

5. You will also need to set up a PostgreSQL database. The connection string for this database should be added to the .env file as follows:
```bash
DATABASE_URL = "postgres://user:pwd@host:port/db"
```
Replace `user`, `pwd`, `host`, `port`, and `db` with your PostgreSQL username, password, host, port, and database name respectively.


6. Start the application:
```bash
uvicorn main:app --port 8002
```
> Note: You can replace `8002` with the port of your choice.

## Usage
Once the application is running, you can interact with it through the API endpoints. The application includes a FastAPI-generated interactive API documentation available at http://127.0.0.1:8002/docs.
The chatbot UI is at http://localhost:8002/

## API Endpoints
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

## Contributing
Contributions are welcome! Please fork this repository and create a pull request with your changes.

## License
This project is the property of GoodAI. Unauthorized distribution or sharing of this code is strictly prohibited.

## TODO
- A lot
- more
