# How to run Charlie Mnemonic on Windows

## Install Docker

Install Docker as per instructions from [docker.com](https://docs.docker.com/desktop/install/windows-install/).

## Download Charlie Mnemonic

- Download the latest release, `charlie-mnemonic-x.y.z.zip`, from
  our [GitHub releases page](https://github.com/GoodAI/charlie-mnemonic/releases).
- Extract the contents of the zip file to a preferred folder.

## Starting the Agent

- Run `start.bat` from the extracted folder. This opens a black terminal screen, which starts Charlie Mnemonic.
- After Charlie Mnemonic starts, it will open a browser window with the initial page.
- The first run might be slow as it downloads necessary components, so please be patient.

### Handling Windows Security Alerts

- When running `start.bat`, you might encounter the "Windows protected your PC" alert from Microsoft Defender
  SmartScreen.
- To proceed, click on "More info", and then select "Run anyway".
- This alert occurs as Windows tries to protect your PC from unrecognized applications.

## Done!

You can now use Charlie Mnemonic. If you run into any issues, please see sections below.

# Other maintenance

## Stopping the Agent

- If you close the terminal window, the agent will not stop. First, you need to stop the agent by pressing `Ctrl+C` in
  the terminal window.
- You can always stop the agent even if you closed the terminal window by running `stop.bat` from the extracted folder.

## Updating the Agent

By default, once the agent is downloaded, it doesn't explicitly update. To update the agent to the latest version,
run `update.bat` from the extracted folder.
This updates only the agent, but not all the update scripts. Once in a while it's good to head over
to [GitHub releases page](https://github.com/GoodAI/charlie-mnemonic/releases) and download the latest version.

## Uninstalling the Agent

To uninstall the agent, run `uninstall.bat` from the extracted folder. User data will be preserved.

## Purging All the user Data

To purge all the data, run `purge.bat` from the extracted folder.

User data are in:

- User home directory in AppData\Roaming\charlie-mnemonic
- Database are saved in Docker volume named `postgres-data`
- More information about persistence can be found in [Persistence](PERSISTENCE.md) document.

## Troubleshooting

If something goes wrong, please copy the text from the terminal or take a screenshot and send it to us. You can either
create issues on [GitHub](https://github.com/GoodAI/charlie-mnemonic/issues) or email us
at [charlie-mnemonic@goodai.com](mailto:charlie-mnemonic@goodai.com).
