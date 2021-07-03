# Rengo-Bot
Discord bot to play Rengo on the OGS server

## Commands
Below is a list of currently supported commands. All commands are run by prefixing their name with an exclamation point (!). Commands prefixed by an asterisk (\*) are admin-only.
* **rengo <player ...>**: Challenge the mentioned players to a game of rengo. The first half of the players will make up your team and play black, while the second half will play as white.
* **play <move>**: Play a given move. Valid moves are **pass**, **resign**, or a coordinate that matches the labeling provided by the OGS web UI.
* **\*rengo_shutdown**: Disconnect from the API and shutdown the bot.

## Setup
### Python Setup
This project uses python 3 and requires several modules. These can be installed using pip with the command `pip install -r requirements.txt`.

### Discord Setup
To setup the Discord bot, you first must setup a discord bot account. Upon adding the bot to your server, you should be given a token.

## Running
To run the bot, perform setup if you have not already. Once setup is completed run ```python main.py```

### Settings
The bot will prompt you for settings the first time that you run it. These settings can be modified from the `settings.json` and `players.json` files.
