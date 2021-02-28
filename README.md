# TM-Bot
<table><tr><td>
TM-Bot is a Python based Discord bot to conduct Ten-Man competitions for the SA-R6 Community Discord Server. The bot registers users, performs matchmaking operations and keeps track of player scores. The bot is currently on version 0.1 as all the base features have not been added yet.
</td></tr><table>

### Prerequisites
MongoDB setup:\
*Currently the server is setup to accept connections from anywhere*

Python setup:
```shell
pip install pymongo
pip install discord
pip install dnspython
pip install asyncio
```

Bot Token:\
The `TOKEN` file contains the Token for the discord bot. To setup the file,
create a file named `TOKEN` without any file extensions. Insert your bot's token as the only string of text in the file. You don't have to worry about `\n` at the end of the string as it's sliced out.


Starting the bot: \
` ./bot.py ` from shell

### Current Commands
1. Player Usable commands:

  * `.info` : Displays author's own info
  * `.info <@DiscordID / Uplay ID>` : Matches user with given ID and displays their info. If Discord ID mode is used, then the user needs to be @'d
  * `.lb` : Displays complete leaderboard from Rank 1. Page flipping implemented with emoji reactions and can only be done by the user who called .lb
  * `.register <Uplay ID>` : Registers author with given Uplay ID and base ELO of 2000
  * `.help` : Displays player usable Commands
  * `.updateuplay <Uplay ID>` : Updates author's Uplay ID with given Uplay ID


2. Admin-Exclusive commands:
  * `.forceregister <@Discord ID> <Uplay ID> <Starting ELO>` : *Admin-facing* command that registers another user with given Uplay ID and a custom starting ELO (Integer).

## Built with
* DiscordPy
* MongoDB
