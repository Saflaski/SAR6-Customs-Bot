# SAR6 Customs Bot
<table><tr><td>
SAR6 Customs Bot or SAR6C is a Python based Discord bot to conduct Customs or "Pug" style competitions for the SA-R6 Community Discord Server. The bot registers users, performs matchmaking operations and keeps track of player scores and other match specific details.
</td></tr><table>

## Features

* Matchmaking System based on Elo Rating System
* Lobby generation
* Ticket generation and handling
* Leaderboards
* User Profiles
* Automatic channel management
<br>

## Current Commands

1. Player Usable commands:

  * `.info` : Displays author's own info
  * `.info <@DiscordID / Uplay ID>` : Matches user with given ID and displays their info. If Discord ID mode is used, then the user needs to be @'d
  * `.lb` : Displays complete leaderboard from Rank 1. Page flipping implemented with emoji reactions and can only be done by the user who called .lb
  * `.register <Uplay ID>` : Registers author with given Uplay ID and base ELO of 2000
  * `.help` : Displays player usable Commands
  * `.updateuplay <Uplay ID>` : Updates author's Uplay ID with given Uplay ID
  * `.joinq` : Join global queue
  * `.leaveq` : Leave global queue
  * `.showq` : Show global queue
  * `.result <score>` : Upload score for a match you're in\
    *Score should be in the format <your team's score>-<their team's score>\
    Eg. If you win 7-5, then it's `.result 7-5` and if you lose 5-7 then it's
    `.result 5-7`*
  * `.ongoing` : Shows list of ongoing matches\
    *List is in descending chronological order*
  * `.showMatch <match ID>` : Shows info about a certain match with given match ID



2. Admin-Exclusive commands:
  * `.forceregister <@Discord ID> <Uplay ID> <Starting ELO>` : Admin-facing command that registers another user with given Uplay ID and a custom starting ELO.
  * `.forceresult <match ID> <score>` : Closes a match, changes Elo, deletes VC
  * `.cancelmatch <match ID>` : Cancels a match, deletes VC
  * `.freeglobal` : Clears Global Queue
  * `.removeplayer  <@discord ID>`: Removes player with given discord ID from Global Queue
  * `.setELO <@discord ID> <target Elo>` :  Sets a player's Elo to target Elo
  * `.QSTest <match ID>` : Diagnostics test that prints internal vals; GVC, GQL, PIOM into console\
    *Also prints match info from ONGOING_MATCHES.txt if match ID given*

## Gameplay cycle
Let's say this is a given list of channels:

<p align="center">
  <img src="https://i.imgur.com/HXRiQ4J.png" width="200">
</p>

A completely new user has to go through the following steps to get started:

 * **Registration**
   1. Get the appropriate role (`R6C`) to start registering via external means (usually react-to-get-role via another bot, eg. Carl-bot or Dynobot)
   2. Register in `#reg-info-lb` with `.register <Uplay ID>`


* **Joining Queue**
  1. Join the global queue in `#queue` with `.joinq`
  2. When enough players have joined, a match will be generated in `#generated-matches`


* **Pre-match**  
  1. If the player has the highest Elo amongst their team, they will be designated the  captain of that team.
  2. The captain has to add the appropriate reaction on the embed panel (3 randomized maps from the 7 map map-pool will be given as options) to ban that certain map. Since there are 3 maps and 2 captains, each captain can only ban 1 map. The last remaining map will be set as map for the given match.
  3. After maps have been banned, the player needs to go to the VC named `Team <Captain of team>` which will be created under the Lobby VC
  4. From here onwards, the match needs to be played out


* **Post-match**
  1. Once a match has finished, any single player of a team (or in this case, let's use our new player) needs to go to `#post-match` and use `.result X-Y` where `X` is the score of the player's team and `Y` is the score of the opponent's team.
  2. Once the Results panel is sent by the bot, the captains of each team need to click on ✅ to verify the score. On the other hand, if any *one* of the captains want to deny the result, then clicking on ❌ will deny the results panel.\
    *Note: The match results panel can be requested as many times as needed but the panel which gets confirmed will be the one to send the scores to database.*
  3. Once the results have been confirmed, the players are free to queue again in `#queue` or basically, go back to step 1 of **Joining Queue**


## Elo Rating System

The current Elo rating system is based on the [Elo Rating System](https://www.geeksforgeeks.org/elo-rating-algorithm/) developed by [Arpad Elo](https://en.wikipedia.org/wiki/Arpad_Elo)

###### The two important values in the calculation system is the *Exponent* value (usually `400`) and the *K* value. For our purposes, the Exponent value is set to `800` and the K value set to `75`
<br>

*Expected Win Probability Calculation:*
<p align="center">
  <img  style="max-height:200px;height:auto;width:auto;" src="https://i.imgur.com/kIhrhap.png">
</p>

*New Player Rating Calculation:*
<p align="center">
  <img  style="max-height:200px;height:auto;width:auto;" src="https://i.imgur.com/lIWfQXU.png">
</p>

<br>

If a case arises where the new Elo is within a margin of `10` from the old Elo (in cases where a player of Elo `2000` lost against a team of average Elo `5000` and the player would undergo a change of something like `-0`), then the change in Elo is set to `10` or `-10` depending on if they won or lost the match.

*Note: Given exponent and K values updated as of version 1.0*

---
### Potential Features
* OCR/Image Processing to automatically process endgame screenshots
* Microsoft TrueSkill system
* Integration into R6S API (based on how useful it is)
* Multi-server integration

### Built with
* DiscordPy
* MongoDB
* Deployed on Heroku
