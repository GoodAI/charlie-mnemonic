# How to run Charlie Mnemonic on Windows



## Install docker

Install docker as per instructions from [docker.com](https://docs.docker.com/desktop/install/windows-install/).

TODO: what about docker GPU support on windows? Does it require GPU or is it really just optional? Is docker gpu support automatic or needs additional setup?

## Download Charlie Mnemonic

Download our latest release for windows from [github releases](TODO) and extract it to a folder.

## Start the agent

Run `start.bat` from the extracted folder.
This opens black terminal screen, that starts Charlie Mnemonic.
After Charlie Mnemonic starts, it will open a browser window with the initial page.
First run is slow as it downloads everything, so please be patient.


# Troubleshooting

If something goes wrong, please check copy text from the terminal or take a screenshot and send it to us.
You can either create issues on [github](https://github.com/GoodAI/charlie-mnemonic/issues) or send us an email to [charlie-mnemonic@goodai.com](mailto:charlie-mnemonic@goodai.com)


Typical output is as follows:

```
Starting Charlie Mnemonic using Docker Compose...
First run takes a while
[+] Running 2/2
 ✔ Container psdb              Running                                                                             0.0s
 ✔ Container charlie-mnemonic  Started                                                                             0.3s
Checking if the Charlie Mnemonic started
Not available yet. Retrying in 5 seconds...
Checking if the Charlie Mnemonic started
Charlie Mnemonic is up! Opening http://localhost:8002 in the default browser!
[nltk_data] Downloading package punkt to /root/nltk_data...
[nltk_data]   Unzipping tokenizers/punkt.zip.
INFO:     Started server process [1]
```