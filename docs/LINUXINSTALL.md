# How to run Charlie Mnemonic on Linux/Raspberry Pi

## Prerequisites
Ensure that you have Git, Docker, and Python installed on your system. For Debian-based systems like Raspberry Pi's Raspbian, you can install them by running:

```bash
sudo apt-get update
sudo apt-get install -y git docker.io python3-pip python3-venv
```
If Docker is not available through your package manager, you may need to follow additional installation steps from the official Docker website.

## 1. Cloning the Repository
Open your terminal and execute the following command to clone the repository:

```bash
git clone https://github.com/GoodAI/charlie-mnemonic.git
cd charlie-mnemonic
```

## 2. Install Dependencies
Before running the script, you need to have docker running, visit https://docs.docker.com/get-docker/ for instructions


## 4. Modify Permissions for start_local.sh
To ensure the script `start_local.sh` can be executed, modify its permissions to make it executable:

```bash
chmod +x start_local.sh
```

## 5. Running the Script
Now that everything is set up, you can run the script using:

```bash
./start_local.sh
```

## Info
User data are stored in:

- User home directory at `${HOME}/.local/share/charlie-mnemonic/users` (`${HOME}` being `/home/<user>/` or `/root/` depending on your user executing the app)
- Database is saved in Docker volume named `postgres-data`
- More information about persistence can be found in the [Persistence](PERSISTENCE.md) document.

## Troubleshooting

If something goes wrong, please copy the text from the terminal or take a screenshot and send it to us. You can create issues on [GitHub](https://github.com/GoodAI/charlie-mnemonic/issues)
