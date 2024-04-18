## Installation

Also check out the [Windows](WININSTALL.md), [Mac](MACINSTALL.md) or [Linux](LINUXINSTALL.md) instructions for an alternative way to run the application if you prefer using docker.

### Prerequisites

- Python 3.10 or higher
- pip
- PostgreSQL database
- Uvicorn `sudo apt-get install uvicorn`
- ffmpeg `sudo apt-get install ffmpeg` (On Windows: Download ffmpeg from the official
  website (https://ffmpeg.org/download.html) and add it to your system’s PATH.)

### Addon prerequisites

- Docker

### Setup

1. Clone this repository:

```bash
git clone git@github.com:GoodAI/charlie-mnemonic.git # or https://github.com/GoodAI/charlie-mnemonic.git
cd charlie-mnemonic
```


2. build the pythondocker\Dockerfile

```bash
cd pythondocker
docker build -t python-env .
```

3. Setup virtualenv
   It is recommended to run the application in a virtual environment. You can set it up and activate it using the
   following commands:

```bash
python3 -m venv venv
source venv/bin/activate
```

4. Install the required Python packages.

```bash
pip install -r requirements.txt
```

5. Copy the .env_sample file to .env and fill in your API keys and other settings:

```bash
cp .env_sample .env
nano .env
```

In the .env file, set the `PRODUCTION` variable to `false` for local development or `true` for a live setup.

```bash
# Set to true when deployed
PRODUCTION = false
```

6. You will also need to set up a PostgreSQL database. The connection string for this database should be added to the
   .env file as follows:

```bash
DATABASE_URL=postgresql://user:pwd@host:port/db
```

Replace `user`, `pwd`, `host`, `port`, and `db` with your PostgreSQL username, password, host, port, and database name
respectively.

If you are using docker, you can just start the database with docker-compose:

```bash
docker-compose up -d psdb
```

In that case, you can use the following connection string:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
```


7. Start the application:

```bash
python launcher.py
```

> Note: You can replace `8002` with the port of your choice.

## Usage

Once the application is running, you can interact with it through the API endpoints. The application includes a
FastAPI-generated interactive API documentation available at http://127.0.0.1:8002/docs.
The chatbot UI is at http://localhost:8002/