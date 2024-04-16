# How to run Charlie Mnemonic on Mac


## Prerequisites
Ensure that you have Git installed on your Mac. If not, you can install it via the Homebrew package manager by running:

```
brew install git
```
## 1. Cloning the Repository
Open your terminal and execute the following command to clone the repository:

```
git clone https://github.com/GoodAI/charlie-mnemonic.git
cd charlie-mnemonic
```
## 2. Install Dependencies
Before running the script, you need to install the dependencies, make sure Python is installed:

```
brew install python
```
Make sure pip is installed
```
python3 -m pip install --upgrade pip
```
Then, install the required Python libraries using pip

```
pip install -r requirements.txt
```
## 3. Modify Permissions for start_local.sh
To ensure the script start_local.sh can be executed, you need to modify its permissions to make it executable:

```
chmod +x start_local.sh
```
## 4. Running the Script
Now that everything is set up, you can run the script using:

```
./start_local.sh
```

## Info
User data are in:

- User home directory in {HOME}/.local/share/charlie-mnemonic/users
- Database are saved in Docker volume named `postgres-data`
- More information about persistence can be found in [Persistence](PERSISTENCE.md) document.

## Troubleshooting

If something goes wrong, please copy the text from the terminal or take a screenshot and send it to us. You can either
create issues on [GitHub](https://github.com/GoodAI/charlie-mnemonic/issues) or email us
at [charlie-mnemonic@goodai.com](mailto:charlie-mnemonic@goodai.com).
