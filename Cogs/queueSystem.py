import discord
import pymongo
import datetime
import re
import secrets
import string
import time
import asyncio
import os
import sys
import ast
import random
import math
import statistics
import json
from os import environ
from discord.ext import commands, tasks
from itertools import combinations


#settingup MongoDB
mongoCredURL = environ["MONGODB_PASS"]
myclient = pymongo.MongoClient(mongoCredURL)
db = myclient["SAR6C_DB"]
dbCol = db["users_col"]
matchesCol = db["matches_col"]

#Global Variables
embedSideColor = 0x2425A2
embedTitleColor = 0xF64C72
footerText = "SAR6C | Use .h for help!"
thumbnailURL= "https://media.discordapp.net/attachments/822432464290054174/832871738030817290/sar6c1.png"
footerIcoURL = "https://media.discordapp.net/attachments/822432464290054174/832871738030817290/sar6c1.png"

#Global Queue list
GQL = []


#Dictionary of generated lobbies (but not matches)
generatedLobby = {}

#Players In Ongoing Matches
PIOM = {}

#Generated Voice Channels
GVC = {}

##Discord Values##

with open("ServerInfo.json") as jsonFile:
    discServInfo = json.load(jsonFile)


playersPerLobby = 10                                        #Cannot be odd number
myGuildID = discServInfo["guildID"]                         #Used later to get myGuild
myGuild = None                                              #Guild for which Bot is run
voiceChannelCategoryID = discServInfo["vcCategoryID"]       #Used later to get voiceChannelCategory
voiceChannelCategory = None                                 #Category into which to make VCs

#Text Channel IDs
discTextChannels = discServInfo["TextChannels"]
helpRegInfoLbTC = discTextChannels["helpRegInfo"]
queueTC = discTextChannels["queue"]
matchGenTC = discTextChannels["matchGen"]
postMatchTC = discTextChannels["postMatch"]
adminTC = discTextChannels["admin"]
completeChannelList = [helpRegInfoLbTC, queueTC, matchGenTC, postMatchTC, adminTC]

#Roles
adminRole = "R6C Admin"
userRole = "R6C"

#Unicode Reaction Emojis
check_mark = '\u2705'
cross_mark = '\u274C'
digitArr = ["1\u20E3", "2\u20E3", "3\u20E3"]

#SAR6C Map Pool
MAP_POOL = ["Villa", "Clubhouse", "Oregon", "Coastline", "Consulate", "Kafe", "Chalet"]

#ELO System Values
K_VAL = 75                  #K value for awarding Elo change based on Expected Win Probability
EXPO_VAL = 800              #400 value for calculating Expected Win Probability
MIN_ELO_CHANGE = 10         #minmium ELO change possible

#Message Links
LOBBY_SETTINGS = "https://discord.com/channels/302692676099112960/825059186592710726/834730773210333184"


"""
Queue system v1.0
Status : COMPLETE
As of right now, v1.0 works like:
    .joinq adds the user to the queue
    .leaveq removes the user from the queue
    .showq displays the queue


    Once playersPerLobby no. of players have joined the queue (GQL), findPossibleLobby removes them from GQL,
    adds them to PIOM and generatedLobby with key as unique match ID.

    The other loop, findGeneratedLobby, checks generatedLobby. If it finds a generated lobby, it removes them from that
    dict, generates balanced teams, uploads the match with a score of 0-0 to database, sends the match embed, creates VCs,
    and starts the map ban process. The end of the map ban process signifies the end of the the match generation cycle.


    Match results:
    See addManualResult()
"""

class QueueSystem(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print('Cog: "queueSystem" is ready.')

        #Loops every 1 second
        self.findPossibleLobby.start()
        self.findGeneratedLobby.start()

        self.setBotStatus.start()
        #self.testLoop.start()


        #Set guild and VC Category
        global myGuild
        global voiceChannelCategory
        myGuild = self.client.get_guild(myGuildID)
        voiceChannelCategory = discord.utils.get(myGuild.categories, id = voiceChannelCategoryID)

    #Check if Correct Channel
    def checkCorrectChannel(channelID = None, channelIDList = []):
        def function_wrapper(ctx):
            givenChannelID = ctx.message.channel.id
            if givenChannelID in channelIDList or givenChannelID == channelID:
                return True
            else:
                return False
        return commands.check(function_wrapper)


    @commands.has_any_role(userRole, adminRole)
    @commands.command(aliases = ["joinq","join"])
    @checkCorrectChannel(channelID = queueTC)
    async def joinQueue(self, ctx):

        global GQL

        #Adds user to the queue
        member = ctx.author
        discID = member.id


        userDoc = dbCol.find({"discID" : discID})
        if userDoc.count() == 0:
            queueEmbed = discord.Embed(description = "Please register first using `.register`", color = embedSideColor)
            await ctx.send(embed = queueEmbed)
            print(f"Unregistered user {member} tried to join Global Queue")
            return None

        elif discID in GQL:
            queueEmbed = discord.Embed(description = f"You are already in the  Global Queue", color = embedSideColor)
            await ctx.send(embed = queueEmbed)
            return None

        for match in PIOM:
            if discID in PIOM[match]:
                queueEmbed = discord.Embed(description = f"You are already in a match", color = embedSideColor)
                await ctx.send(embed = queueEmbed)
                return None

        GQL.append(discID)
        print(f"{member} has joined the Global Queue")
        await ctx.message.add_reaction(check_mark)

    @joinQueue.error
    async def joinQueue_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.send(embed = discord.Embed(description = "Inadequate role"))
        elif isinstance(error, commands.NoPrivateMessage):
            pass


    @commands.has_any_role(userRole, adminRole)
    @commands.command(aliases = ["showq", "queue"])
    @checkCorrectChannel(channelIDList = completeChannelList)
    async def showQueue(self, ctx):
        global GQL
        tempGQL = GQL.copy()    #copies current state of GQL
        queryList = []          #List for MongoDB Query
        embedDictionary = {}    #Dict for Embed Message

        if len(tempGQL) != 0:
            for playerDiscID in tempGQL:
                playerDic = {"discID" : playerDiscID}
                queryList.append(playerDic)

            playerDocs = dbCol.find({"$or" : queryList})

            for x in playerDocs:
                embedDictionary[x["discID"]] = [ x["discName"] , x["ELO"]]

            queueEmbed = discord.Embed(title = f"Global Queue ({len(embedDictionary)}/{playersPerLobby})",  color = embedSideColor)
            queueString = ""
            for member in embedDictionary:
                queueString += f"<@{member}> : {embedDictionary[member][1]}\n"

            queueEmbed.add_field(name = "Queue List:   " , value = queueString)
            await ctx.send(embed = queueEmbed)

        else:
            queueEmbed = discord.Embed(color = embedSideColor)
            queueEmbed.add_field(name = "Players in Queue: 0", value = "** **")
            await ctx.send(embed = queueEmbed)

    @showQueue.error
    async def showQueue_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.send(embed = discord.Embed(description = "Inadequate role"))
        elif isinstance(error, commands.NoPrivateMessage):
            pass



    @commands.has_any_role(userRole, adminRole)
    @commands.command(aliases = ["leaveq","leave"])
    @checkCorrectChannel(channelID = queueTC)
    async def leaveQueue(self, ctx):

        member = ctx.author

        global GQL

        #Removes user to the queue
        queueEmbed = discord.Embed(color = embedSideColor)
        if member.id in GQL:
            GQL.remove(member.id)
            #queueEmbed.add_field(name = "Removed from Global Queue", value = "** **")
            await ctx.message.add_reaction(check_mark)
            print(f"{member} has left the Global Queue")

        else:
            queueEmbed.add_field(name = "You weren't in Global Queue", value = "** **")
            await ctx.send(embed = queueEmbed)

    @leaveQueue.error
    async def leaveQueue_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.send(embed = discord.Embed(description = "Inadequate role"))
        elif isinstance(error, commands.NoPrivateMessage):
            pass

    @commands.has_any_role(userRole, adminRole)
    @commands.command(aliases = ["showM", "getMatch", "getM", "match"])
    @checkCorrectChannel(channelIDList = completeChannelList)
    async def showMatch(self, ctx, matchID):


        matchDoc = matchesCol.find_one({"MID": matchID})

        if matchDoc is not None:
            MID = matchDoc["MID"]
            matchScore = matchDoc["score"]
            teamAList = matchDoc["matchList"][:playersPerLobby//2]
            teamBList = matchDoc["matchList"][playersPerLobby//2:]
            teamACaptain = teamAList[0]
            teamBCaptain = teamBList[0]

            try:
                matchMap = matchDoc["map"]
            except:
                matchMap = "Not Selected"

        else:
            myEmbed = discord.Embed(descripion = "Match not found", color = embedSideColor)
            await ctx.send(embed = myEmbed)
            return None

        #Get Discord Names of Captains
        CaptNameA = await self.client.fetch_user(teamACaptain)
        CaptNameB = await self.client.fetch_user(teamBCaptain)

        #Prepare Query List for dbCol collection
        queryList = []
        for playerDiscID in teamAList + teamBList:
            playerDic = {"discID" : playerDiscID}
            queryList.append(playerDic)

        playerDocs = dbCol.find({"$or" : queryList})

        lobbyDic = {}
        for x in playerDocs:
            lobbyDic[x["discID"]] = x["ELO"]



        #Preparing Embed Value strings
        teamStringA = ""
        teamStringB = ""

        for playerDiscID in teamAList:
            teamStringA += f"\t<@{playerDiscID}> - `{lobbyDic[playerDiscID]}`\n"

        for playerDiscID in teamBList:
            teamStringB += f"\t<@{playerDiscID}> - `{lobbyDic[playerDiscID]}`\n"

        embedDescription = (    "**ID:** " + str(matchID) + "\n"
                                + "**Score:** " + "A " +str(matchScore[0]) + "-" + str(matchScore[2]) + " B"+ "\n"
                                + "**Map:** " + matchMap
                             )

        myEmbed = discord.Embed(title = "Match Found", description = embedDescription, color = embedSideColor)
        #myEmbed.add_field(name = "Details:", value = f"ID: {matchID}\nScore:{matchScore}", inline = True)
        myEmbed.add_field(name = f"Team A: {CaptNameA}", value = teamStringA, inline = False)
        myEmbed.add_field(name = f"Team B: {CaptNameB}", value = teamStringB, inline = False)

        await ctx.send(embed = myEmbed)

    @showMatch.error
    async def showMatch_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.send(embed = discord.Embed(description = "Inadequate role"))
        elif isinstance(error, commands.NoPrivateMessage):
            pass
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Invalid Usage, try: `.getMatch <match ID>`")


    @commands.command(aliases = ["showongoing", "ongoingmatches", "ongoing"])
    @checkCorrectChannel(channelIDList = completeChannelList)
    async def showOngoingMatches(self, ctx):

        #Get all matches with 0-0 score with most recent as first
        matchDocs = matchesCol.find({"score": "0-0"}).sort([("_id", -1)])

        myEmbed = discord.Embed(title = "Ongoing Matches", color = embedSideColor)

        counter = 1
        if matchDocs.count() != 0:
            for match in matchDocs:
                matchID = match["MID"]
                try:
                    matchMap = match["map"]
                except:
                    matchMap = "Not selected"

                teamACap = match["matchList"][playersPerLobby//2:][0]
                teamBCap = match["matchList"][:playersPerLobby//2][0]

                #teamACap = await self.client.fetch_user(teamACap)
                #teamBCap = await self.client.fetch_user(teamBCap)

                myEmbed.add_field(name = f"{counter}. {matchID}", value = f"Team <@{teamACap}> vs Team <@{teamBCap}> \nMap: {matchMap}")
                counter += 1

            myEmbed.set_footer(text = "Most Recent matches at the top", icon_url = footerIcoURL)
        else:
            myEmbed.add_field(name = "None", value = "** **")
        await ctx.send(embed = myEmbed)



    @showOngoingMatches.error
    async def showOngoingMatches_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.send(embed = discord.Embed(description = "Inadequate role"))
        elif isinstance(error, commands.NoPrivateMessage):
            pass






    @commands.has_any_role(adminRole)
    @commands.command(aliases = ["setElo", "setelo"])
    async def setELO(self, ctx, member : discord.Member, ELO : int):

        opResult = dbCol.update_one({"discID" : member.id}, { "$set" : {"ELO" : ELO}})

        if opResult.matched_count == 0:
            failEmbed = discord.Embed(description = "User not found", color = 0xff0000)
            await ctx.send(embed = failEmbed)
            return None

        else:
            successEmbed = discord.Embed(description = f"Succesfully set ELO: {ELO}", color = 0x00ff00)
            await ctx.send(embed = successEmbed)

    @setELO.error
    async def setELO_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.send("Invalid Usage, try: `.setELO <@discord ID> <ELO>`")
        elif isinstance(error, commands.MissingAnyRole):
            await ctx.send(embed = discord.Embed(description = "Inadequate role"))
        elif isinstance(error, commands.NoPrivateMessage):
            pass


    @commands.has_any_role(adminRole)
    @commands.command(name = "cancelmatch")
    async def cancelMatch(self, ctx = None, matchID = None):
        
        if matchID is None:
            try:
                raise commands.MissingRequiredArgument(matchID)
            except Exception as e:
                print(e)
                return

        global PIOM
        global GVC
        #Sets the Database score to C-C
        #Doesn't update Elo
        #Check and remove from PIOM
        #Check and remove VCs

        #Update Match Score in Database
        fString = ""

        matchDoc = matchesCol.find_one({"MID" : matchID})
        if matchDoc is not None:
            matchesCol.update({"MID" : matchID},{"$set" : {"score" : "C-C"}})
            fString += "Updated score to C-C. "

        #Remove the matchID from PIOM
        if matchID in PIOM:
            del PIOM[matchID]
            print(f"Deleted {matchID} from PIOM")
            fString += "Freed players. "

        #Remove VCs
        if matchID in GVC:
                try:
                    for VC in GVC[matchID]:
                        VC_Object = self.client.get_channel(VC)
                        await VC_Object.delete()
                    del GVC[matchID]
                    fString += "Deleted VCs. "
                except Exception as e:
                    print(e)
                    fString +="Could not delete VCs"

        if ctx is not None:
            await ctx.send(embed = discord.Embed(description = fString, color = embedSideColor))
        else:
            #In cases where cancelMatch is called by an automated function
            matchgenchannel = self.client.get_channel(matchGenTC)
            msg = await matchgenchannel.send(embed = discord.Embed(description = fString, color = embedSideColor))


    @cancelMatch.error
    async def cancelMatch_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.send("Invalid Usage, try: `.cancelmatch <match ID>`")
        elif isinstance(error, commands.MissingAnyRole):
            await ctx.send(embed = discord.Embed(description = "Inadequate role"))
        elif isinstance(error, commands.NoPrivateMessage):
            pass

    @commands.has_any_role(adminRole)
    @commands.command(name = "freeglobal")
    async def freeQueue(self, ctx):

        global GQL
        GQL.clear()
        await ctx.send("Cleared Global Queue")
        print("Removed players from GQL")

    @freeQueue.error
    async def freeQueue_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.send(embed = discord.Embed(description = "Inadequate role"))
        elif isinstance(error, commands.NoPrivateMessage):
            pass

    @commands.has_any_role(adminRole)
    @commands.command(name = "removeplayer")
    async def remFromQueue(self, ctx, member: discord.Member):
        global GQL

        GQL.remove(member.id)

        await ctx.send(f"Removed {member} from Global Queue")
        print(f"Removed from GQL: {member}")

    @remFromQueue.error
    async def remFromQueue_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.send("Invalid Usage, try: `.removeplayer <@discord ID>`")
        elif isinstance(error, commands.MissingAnyRole):
            await ctx.send(embed = discord.Embed(description = "Inadequate role"))
        elif isinstance(error, commands.NoPrivateMessage):
            pass


    @commands.has_any_role(adminRole)
    @commands.command(name = "forceresult")
    async def forceAddResult(self, ctx, matchID, score):
        global GVC
        global PIOM

        #Verify the score given
        #Check if the match is still going on
        #Get values from Database (and ignore if it's finished) and files
        #Send a result embed with isPending = False
        #Update Elo
        #Update Match Score
        #Check and remove from PIOM
        #Check and remove VCs

        #Check score validity
        teamResult = checkCorrectScore(score)

        if "incorrect" in teamResult:
            await ctx.send("Invalid usage or incorrect score, try: `.result #-#` ,Eg.: `.result 7-5`")
            print(f"{ctx.author} tried invalid match result code")
            return None

        else:
            print(f"{ctx.author} used forceresult with correct match score")


        matchDoc = matchesCol.find_one({"MID" : matchID})
        MID = ""    #Match ID
        currentMatchScore = ""      #Used later to check if match is still going on
        teamACaptain = ""
        teamBCaptain = ""
        teamAList = []
        teamBList = []

        if matchDoc is not None:
            MID = matchDoc["MID"]
            teamAList = matchDoc["matchList"][:playersPerLobby//2]
            teamBList = matchDoc["matchList"][playersPerLobby//2:]
            currentMatchScore = matchDoc["score"]
            teamACaptain = teamAList[0]
            teamBCaptain = teamBList[0]

        else:
            myEmbed = discord.Embed(description = "Invalid Match ID", color = 0xff0000)
            await ctx.send(embed = myEmbed)
            print("\n\nFATAL ERROR: Failure 1 at forceAddResult\n\n")
            return None

        #Find which team won
        if teamResult[1] > teamResult[2]:
            #Team A won
            winningTeam = teamAList
            losingTeam = teamBList
            givenScore = score
        else:
            #Team B won
            winningTeam = teamBList
            losingTeam = teamAList
            givenScore = score[::-1]

        winCaptID = winningTeam[0]
        lossCaptID = losingTeam[0]

        winCapt = await self.client.fetch_user(winCaptID)
        lossCapt = await self.client.fetch_user(lossCaptID)



        print(f"Sending Match Result Confirmed (ADMIN) Panel:{MID} ")

        matchDict = ongMatchFileOps("R", MID)

        winTeamChange, lossTeamChange = getChangeDict(matchDict, winningTeam, losingTeam, True)


        try:
            embed = getResultEmbed(MID, winTeamChange, lossTeamChange, winCapt, lossCapt, givenScore, isPending = False )
            sentEmbed = await ctx.send(content = f"Captains: <@{winCapt.id}> , <@{lossCapt.id}>", embed = embed)

        except Exception as e:
            print(e)


        ## Check and update Internal and Database values
        fString = ""    #Used to send command result to admin

        #Check if the match is still going on
        if currentMatchScore != "0-0" and currentMatchScore != "C-C":        #Elo Reversion required before updation

            #Get appropriate Elo changes to 'revert' everyone's Elos according to pre-match Elos
            curTeamResult = checkCorrectScore(currentMatchScore)        #Parse the old match score

            if curTeamResult[1] > curTeamResult[2]:
                #Team A won
                curWinChange, curLossChange = getChangeDict(matchDict, teamAList, teamBList, False)
            else:
                #Team B won
                curWinChange, curLossChange = getChangeDict(matchDict, teamBList, teamAList, False)

            #Revert Player Elos in Database
            for playerID in curWinChange:
                dbCol.update_one({"discID" : playerID}, {"$inc" : {"ELO" : curWinChange[playerID]}})
            for playerID in curLossChange:
                dbCol.update_one({"discID" : playerID}, {"$inc" : {"ELO" : curLossChange[playerID]}})
            fString += "Reverted Elo. "

        for playerID in winTeamChange:
            dbCol.update_one({"discID" : playerID}, {"$inc" : {"ELO" : winTeamChange[playerID]}})
        for playerID in lossTeamChange:
            dbCol.update_one({"discID" : playerID}, {"$inc" : {"ELO" : lossTeamChange[playerID]}})
        fString += "Set new Elo. "

        #Update Match Score in Database
        match_score = str(f"{teamResult[1]}-{teamResult[2]}")
        matchesCol.update({"MID" : MID},{"$set" : {"score" : match_score}})
        (f"Updated DB for score: {match_score}")
        fString += "Updated Database for Score. "



        #Remove the matchID from PIOM
        if MID in PIOM:
            del PIOM[MID]
            print(f"Deleted {MID} from PIOM")
            fString += "Freed players. "

        #Remove VCs
        if matchID in GVC:
                try:
                    for VC in GVC[matchID]:
                        VC_Object = self.client.get_channel(VC)
                        await VC_Object.delete()
                    del GVC[matchID]
                    fString += "Deleted VCs. "
                except Exception as e:
                    print(e)
                    fString +="Could not delete VCs"

        await ctx.send(embed = discord.Embed(description = fString, color = embedSideColor))

    @forceAddResult.error
    async def forceAddResult_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.send("Invalid Usage, try: `.forceresult <match ID> <score>`")
        elif isinstance(error, commands.MissingAnyRole):
            await ctx.send(embed = discord.Embed(description = "Inadequate role"))
        elif isinstance(error, commands.NoPrivateMessage):
            pass


    @commands.has_any_role(userRole, adminRole)
    @commands.command(name = "result")
    @checkCorrectChannel(channelID = postMatchTC)
    async def addManualResult(self, ctx, score):
        global PIOM
        global GVC

        #Checks if author is in an ongoing match

        PIOMCheck = False
        for match in PIOM:
            if ctx.author.id in PIOM[match]:
                PIOMCheck = True

        if not PIOMCheck:
            await ctx.send("You aren't in an ongoing match")
            return None

        """
        addManualResult will now go through five stages:

                Preface:
                Example Usage: .result 7-5
                    Here, 7 is the author's team's score and 5 is the opponent team's score
                    This is the set standard.

            ->Check that the given score is in a correct format (including checking if it follows R6S standards)
                ->R6S Standards: Eg. 7-0, 7-5, 8-7, 8-6 etc.
                ->If correct, it will return scores (author's and opponents') and whether it went Overtime.

            ->If correct, it will query the matches_col MongoDB collection for ongoing matches, ie, ones that are score: 0-0
                Note: Each match document stores matches in the following way:
                ->MID : Unique match ID
                ->score: #-# where # is a number
                ->matchList:    List of length {playersPerLobby}. If there are 10 players per lobby, then
                                List[0] and List[5] are the captains of each team.
                                The members of those team follow after their resp. captains at 1-4, 6-9

            ->After the document is found, program will try to find which team author was in then assign variables in that way

            ->It will then generate an embed object with the appropriate details
                ->check_mark reaction will be added and bot will wait for captains of each team to react
                    to it to basically confirm the match.

            ->If captains confirm the match result by reacting, then bot will execute confirmMatch()
                confirmMatch has 3 functions:
                    ->Update the embed to reflect that the captains have confirmed the match result.
                    ->Update database and increment/decrement points as per global variables to players
                    ->Remove players from PIOM/Dict that stores which match players are in.

        """

        #Check score validity
        teamResult = checkCorrectScore(score)

        if "incorrect" in teamResult:
            await ctx.send("Invalid usage or incorrect score, try: `.result #-#` ,Eg.: `.result 7-5`")
            print(f"{ctx.author} tried invalid match result code")
            return None

        else:
            print(f"{ctx.author} tried valid match result code")

            #Query DB for match document

            matchDoc = matchesCol.find_one({"score" : "0-0", "matchList": ctx.author.id})
            MID = ""    #Match ID
            teamACaptain = ""
            teamBCaptain = ""
            teamAList = []
            teamBList = []

            if matchDoc is not None:
                MID = matchDoc["MID"]
                teamAList = matchDoc["matchList"][:playersPerLobby//2]
                teamBList = matchDoc["matchList"][playersPerLobby//2:]
                teamACaptain = teamAList[0]
                teamBCaptain = teamBList[0]

            else:
                print("\n\nFATAL ERROR: Failure 1 at addManualResult\n\n")
                return None

            print(f"Sending Match Result Pending Panel:{MID} ")

            #Find which team author was in

            if ctx.author.id in teamAList:
                authorTeamList = teamAList
                oppTeamList = teamBList
                DB_score = score
            else:
                authorTeamList = teamBList
                oppTeamList = teamAList
                DB_score = score[::-1]      #Reverse the score


            #Fetch the member objects for each captain
            authorTeamCaptain = await self.client.fetch_user(authorTeamList[0])
            oppTeamCaptain = await self.client.fetch_user(oppTeamList[0])

            #Prepare Match Embed

            winningTeam = []
            losingTeam = []
            winCapt = ""
            lossCapt = ""
            isOT = False

            #As of now, OT/nonOT has no effect

            print(teamResult)

            if teamResult[1] > teamResult[2]:
                #Author's team won
                winningTeam, losingTeam = authorTeamList, oppTeamList
                winCapt, lossCapt = authorTeamCaptain, oppTeamCaptain
                givenScore = score

            elif teamResult[1] < teamResult[2]:
                #Author's team lost
                winningTeam, losingTeam = oppTeamList, authorTeamList
                winCapt, lossCapt = oppTeamCaptain, authorTeamCaptain
                givenScore = score[::-1]


            if "nonOT" in teamResult:
                isOT = False
            elif "OT" in teamResult:
                isOT = True


            #Prepare a dict of playerIDs and their pre match ELOs

            matchDict = ongMatchFileOps("R", MID)

            winTeamChange, lossTeamChange = getChangeDict(matchDict, winningTeam, losingTeam, True)



            try:
                embed = getResultEmbed(MID, winTeamChange, lossTeamChange, winCapt, lossCapt, givenScore, isPending = True )
                sentEmbed = await ctx.send(content = f"Captains: <@{authorTeamCaptain.id}> , <@{oppTeamCaptain.id}>", embed = embed)
                await sentEmbed.add_reaction(check_mark)
                await sentEmbed.add_reaction(cross_mark)

            except Exception as e:
                print(e)

            async def confirmMatch():

                #Update Embed Message
                await sentEmbed.edit(embed = getResultEmbed(MID, winTeamChange, lossTeamChange, winCapt, lossCapt, givenScore, isPending = False))

                global GVC

                #Update Database
                queryListWon = []          #Lists for MongoDB Query
                queryListLost = []

                #Update Match Score in Database
                matchesCol.update({"MID" : MID},{"$set" : {"score" : DB_score}})
                print(f"Updated DB for score: {DB_score}")

                #Update Player Scores in Database
                for playerID in winTeamChange:
                    dbCol.update_one({"discID" : playerID}, {"$inc" : {"ELO" : winTeamChange[playerID]}})
                for playerID in lossTeamChange:
                    dbCol.update_one({"discID" : playerID}, {"$inc" : {"ELO" : lossTeamChange[playerID]}})

                #Remove the matchID from PIOM
                if MID in PIOM:
                    del PIOM[MID]
                    print(f"Deleted {MID} from PIOM")

                #Remove VCs
                if MID in GVC:
                    try:
                        for VC in GVC[MID]:
                            VC_Object = self.client.get_channel(VC)
                            await VC_Object.delete()
                        del GVC[MID]

                    except Exception as e:
                        print(e)

                print(f"Removed players and VCs from ongoing list \nMatch Closed: {MID}")

            #To check that captain has used correct reaction
            checkCaptainID = lambda userID: userID == winCapt.id or myuser == lossCapt.id

            def check(myreaction, myuser):

                userCond = myuser.id in winTeamChange or myuser.id in lossTeamChange
                reactionCond = str(myreaction.emoji) == check_mark or str(myreaction.emoji) == cross_mark
                return (userCond and reactionCond)

            #Captain confirmation boolean values for each team
            winTeamConf = False
            lossTeamConf = False

            timeout = 120
            timeout_start = time.time()     #Starts keeping track of time

            while time.time() < timeout_start + timeout:
                try:
                    myreaction, myuser = await self.client.wait_for('reaction_add', check = check)
                except Exception as e:
                    print(e)
                #print(f"{myuser} did {myreaction}")

                if check(myreaction, myuser):
                    if str(myreaction.emoji) == cross_mark and checkCaptainID(myuser.id):
                        embed.set_footer(text = f"Result denied by Captain: {myuser}", icon_url = footerIcoURL)
                        await sentEmbed.edit(embed = embed)
                        await sentEmbed.clear_reactions()
                        return None

                    elif myuser.id == winCapt.id:
                        winTeamConf = True
                        embed.set_footer(text = f"Result accepted by {winCapt}'s side", icon_url = footerIcoURL)
                        await sentEmbed.edit(embed = embed)
                    elif myuser.id == lossCapt.id:
                        lossTeamConf = True
                        embed.set_footer(text = f"Result accepted by {lossCapt}'s side", icon_url = footerIcoURL)
                        await sentEmbed.edit(embed = embed)


                #Check if captains have verified
                if winTeamConf and lossTeamConf:
                    print("Match Result Confirmed")

                    #Get Embed, Update Databse, Remove from PIOM
                    await confirmMatch()
                    #Clear reactions from result embed object
                    await sentEmbed.clear_reactions()
                    break


                time.sleep(1)       #To avoid resource hogging (by looping continously)

            await sentEmbed.clear_reactions()   #Clears reactions after timeout has happened/time limit has elapsed


    @addManualResult.error
    async def addManualResult_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.send("Invalid Usage, try: `.result #-#` ,Eg.: `.result 7-5`")
        elif isinstance(error, commands.MissingAnyRole):
            await ctx.send(embed = discord.Embed(description = "Inadequate role"))
        elif isinstance(error, commands.NoPrivateMessage):
            pass

    @tasks.loop(seconds = 15)
    async def setBotStatus(self):
        playersInGQL = len(GQL)
        await self.client.change_presence(activity = discord.Activity(name = f"{playersInGQL} players in queue", type = discord.ActivityType.watching))

    @tasks.loop(seconds = 1)
    async def findPossibleLobby(self):
        global generatedLobby
        global playersPerLobby
        global PIOM


        if len(GQL) >= playersPerLobby:
            print(f"Generating Match:")

            tempList = []
            playerList = []

            for i in range(playersPerLobby):
                playerList.append(GQL[i])
            for member in playerList:
                GQL.remove(member)
                tempList.append(member)

            matchID = generateMatchID()
            #Add list to PIOM, matchID : [listOfPlayers]

            PIOM[matchID] = tempList

            generatedLobby.update({matchID : playerList})


    #Finds Generated Lobby and then generates teams, VCs and uploads generated match to DB
    @tasks.loop(seconds = 1)
    async def findGeneratedLobby(self):
        global generatedLobby
        global GVC

        if len(generatedLobby) >= 0:
            for matchID in generatedLobby:
                pList = generatedLobby[matchID]
                del generatedLobby[matchID]

                #Generate Teams and Upload Match Document
                embeddedContent, teamA_VCName, teamB_VCName, CapA_ID, CapB_ID = generateTeams(matchID, pList)

                #Send Generated Match Embed
                channel = self.client.get_channel(matchGenTC)
                msg = await channel.send(embed = embeddedContent)
                msg_url = msg.jump_url
                #Make Voice Channels with captains' names
                VC_A = await myGuild.create_voice_channel(name = f"Team: {teamA_VCName}", category = voiceChannelCategory)
                VC_B = await myGuild.create_voice_channel(name = f"Team: {teamB_VCName}", category = voiceChannelCategory)

                #Add VCs to Global VC Dict: GVC
                GVC[matchID] = [VC_A.id, VC_B.id]

                #Start the map ban
                asyncio.create_task(self.mapbanSystem(matchID, embeddedContent, msg, CapA_ID, CapB_ID, teamA_VCName, teamB_VCName))

                #Send DMs to users
                for playerID in pList:
                    playerObj = await self.client.fetch_user(playerID)
                    if playerObj is not None:
                        dmEmbed = discord.Embed(title = "Match Found - SAR6", 
                                                description = f"Click [here]({msg_url}) to go straight to the match panel.\nClick [here]({LOBBY_SETTINGS}) for Lobby Settings",
                                                color = embedSideColor)
                        dmEmbed.set_thumbnail(url = thumbnailURL)
                        await playerObj.send(embed = dmEmbed)
                print("Match Gen Cycle complete")
                break


    async def mapbanSystem(self, MID, embedMessage, msg : discord.Message, capA_ID, capB_ID, teamA_VCName, teamB_VCName ):

        maplist = random.sample(MAP_POOL, k = 3)        #Randomly choose 3 unique maps from map pool

        for emoji in digitArr:
            await msg.add_reaction(emoji)               #Adds reactable emojis to match message

        #Prepare map dictionary in the form: {emoji : map}
        someDict = {}
        for i in range(len(maplist)):
            someDict[digitArr[i]] = maplist[i]


        #Prepare map string to display in embed content for initial run
        mapString = ""
        for mapIndex in someDict:
            mapString += f"{mapIndex} -> {someDict[mapIndex]}\n"

        #For when a map is banned/emoji is reacted to
        async def genNewEmbed(captBan):
            mapString = ""
            for mapIndex in someDict:
                mapString += f"{mapIndex} -> {someDict[mapIndex]}\n"
            embedMessage.set_field_at(3, name = "Map Ban Phase:", value = mapString)
            embedMessage.set_footer(text = f"Map banned by {captBan}", icon_url = footerIcoURL)
            await msg.edit(embed = embedMessage)


        embedMessage.add_field(name = "Map Ban Phase:", value = mapString)
        await msg.edit(embed = embedMessage)

        #Check that only captains have reacted and only to the correct emojis

        switcherList = []   #List to see who can ban next

        def check(myreaction, myuser):

            userCond = (myuser.id == capA_ID) or (myuser.id == capB_ID)
            reactionCond = str(myreaction.emoji) in someDict.keys()
            return (userCond and reactionCond)

        #420 second timer for banning maps
        timeout = 420
        timeout_start = time.time()     #Starts keeping track of time

        lastMap = ""

        while time.time() < timeout_start + timeout:
            try:
                myreaction, myuser = await self.client.wait_for('reaction_add',timeout = 600.0, check = check)
            except asyncio.TimeoutError:
                print("Map Ban timed out")
                break

            #If there has been a valid emoji reaction
            if myreaction is not None:

                #Check if the reacting captain has already banned in the previous run
                if myuser.id in switcherList:
                    await msg.remove_reaction(myreaction, myuser)
                    continue

                else:

                    #Remove previous captain and append new captain as latest map ban-er
                    switcherList.clear()
                    switcherList.append(myuser.id)

                    #Edit the embed to reflect the new ban
                    del someDict[str(myreaction.emoji)]
                    await genNewEmbed(myuser)
                    await msg.clear_reaction(myreaction)


            #When only one map if left
            if len(someDict) == 1:
                    lastMap = list(someDict.values())[0]        #Get the name of the remaining map
                    embedMessage.set_field_at(3, name = f"Map Ban Result: {lastMap}", value = f"** **")

                    #Clean up the embed
                    await msg.edit(embed = embedMessage)
                    await msg.clear_reactions()
                    break

            time.sleep(1)       #Avoid resource hogging

        if len(lastMap) != 0:
            matchesCol.update_one({"MID": MID },{"$set" : {"map" : lastMap}})
            attackTeam = teamA_VCName
            defenseTeam = teamB_VCName
            embedMessage.set_footer(text = f"GLHF! Attack Team: {attackTeam}, Defense Team: {defenseTeam}", icon_url = footerIcoURL)
            await msg.edit(embed = embedMessage)
            print(f"Map set: {lastMap}")
        else:
            print("Map not set")
            embedMessage.set_footer(text = f"Maps were not selected, match cancelled.", icon_url = footerIcoURL)
            await self.cancelMatch(matchID = MID)
            await msg.edit(embed = embedMessage)
            await msg.clear_reactions()




    #### TESTING PURPOSES ####
    @commands.has_any_role(adminRole)
    @commands.command(name = "QSTest")
    async def queueTest(self, ctx, MID = None):

        print(f"GVC: {GVC}")
        print(f"GQL: {GQL}")
        print(f"PIOM: {PIOM}")
        print("\n")
        if MID is not None:
            fileOpsResult = ongMatchFileOps("R", MID,)
            print(f"File Ops Result: {fileOpsResult}")
        print("Changing Status:")
        try:
            playersInGQL = len(GQL)
            await self.client.change_presence(activity = discord.Activity(name = f"{playersInGQL} players in queue", type = discord.ActivityType.watching))
            print("Changed Status")
        except Exception as e:
            print(e)

    @commands.command(name = "TESTTEST")
    async def TESTTEST(self = None, ctx = None, MID = None):
        print(self)
        print(ctx)
        print(MID)

    #### TESTING PURPOSES ####

    @tasks.loop(seconds = 10)
    async def testLoop(self):
        await self.TESTTEST(MID = "someMID")

    #Queue Start/Stop
    @commands.command(name = "queueStop")
    @commands.has_any_role(adminRole)
    async def queueStop(self, ctx):
        self.findPossibleLobby.stop()
        print(f"{ctx.author} has stopped the queue.")
    
    @commands.command(name = "queueStart")
    @commands.has_any_role(adminRole)
    async def queueStart(self, ctx):
        self.findPossibleLobby.start()
        print(f"{ctx.author} has started the queue.")
        



################################################################################################
################################################################################################
#################### Non-Async Functions #######################################################
################################################################################################
################################################################################################






def generateMatchID():
    """
    Generates unique alphanumeric token of length 8
    Total possible permutations: (26 + 26 + 10) ^ 8
    Therefore, collision probability is at 50% only at 62^4

    """
    alphabet = string.ascii_letters + string.digits
    matchID = ''.join(secrets.choice(alphabet) for i in range(8))
    return matchID

def getChangeDict(matchDict, winningTeam, losingTeam, setELO):

    if setELO:
        convFactor = 1
    else:
        convFactor = -1


    winTeamDict = {}
    lossTeamDict = {}
    winTeamChange = {}
    lossTeamChange = {}


    for playerID in winningTeam:
        winTeamDict[playerID] = matchDict[playerID]
    for playerID in losingTeam:
        lossTeamDict[playerID] = matchDict[playerID]


    #Use ELO Rating System to get new ELOs
    newWinTeamDict, newLossTeamDict = getIndivELO(winTeamDict, lossTeamDict)


    for playerID in newWinTeamDict:
        winTeamChange[playerID] = convFactor*(newWinTeamDict[playerID] - winTeamDict[playerID])
    for playerID in newLossTeamDict:
        lossTeamChange[playerID] = convFactor*(newLossTeamDict[playerID] - lossTeamDict[playerID])

    return winTeamChange, lossTeamChange


def getIndivELO(winTeam, lossTeam):

    winTeamNewRating = {}
    lossTeamNewRating = {}

    ExpecWProb = lambda A,B: round(1/(1+math.pow(10,(B-A)/EXPO_VAL)),2)

    newRating = lambda WL, Ra, Rb: round(Ra + K_VAL*(WL - ExpecWProb(Ra,Rb)))

    medianW = statistics.median(list(winTeam.values()))
    medianL = statistics.median(list(lossTeam.values()))



    for playerID in winTeam:
        curRatingW = winTeam[playerID]
        newRatingW = newRating(1, curRatingW, medianL)

        if newRatingW < MIN_ELO_CHANGE + curRatingW:
            winTeamNewRating[playerID] = winTeam[playerID] + MIN_ELO_CHANGE
        else:
            winTeamNewRating[playerID] = newRatingW

    for playerID in lossTeam:
        curRatingL = lossTeam[playerID]
        newRatingL = newRating(0, curRatingL, medianW)

        if newRatingL > curRatingL - MIN_ELO_CHANGE:
            lossTeamNewRating[playerID] = lossTeam[playerID] - MIN_ELO_CHANGE
        else:
            lossTeamNewRating[playerID] = newRatingL

    """
    print(f"Winning Team Changes: {winTeamNewRating}")
    print(f"Losing Team Changes: {lossTeamNewRating}")

    print("\n")

    print("\nWin changes:")
    for playerID in winTeam:
        print(str(playerID) + ": " + str(winTeamNewRating[playerID] - winTeam[playerID]))

    print("\nLoss changes:")
    for playerID in lossTeam:
        print(str(playerID) + ": " + str(lossTeamNewRating[playerID] - lossTeam[playerID]))
    """

    print("Completed ELO Rating System")
    return winTeamNewRating, lossTeamNewRating


def ongMatchFileOps(mode, MID, givenDict = None):
    #mode = W for Write, D for Delete, R for Read/Finding a match using MID
    MID = str(MID)
    if not os.path.exists("ONGOING_MATCHES.txt"):
        print("\nONGOING_MATCHES.txt doesn't exist" )
        print("Creating new file: ONGOING_MATCHES.txt\n")
        with open("ONGOING_MATCHES.txt", "a") as f:
            pass

    if mode == "D" or mode == "R":
        myIndex = None                      #Either Read or Delete or Invalid
        read_data = None
        with open('ONGOING_MATCHES.txt') as f:
            read_data = f.readlines()
        for data in read_data:
            if data.startswith(MID + "\n"):
                myIndex = read_data.index(MID + "\n")
                dictStr = read_data[myIndex + 1].rstrip("\n")
                dict = ast.literal_eval(dictStr)
        if myIndex == None:
            return None
        elif mode == "D":
            del read_data[myIndex]
            del read_data[myIndex]
            with open("ONGOING_MATCHES.txt", "w") as f:
                f.writelines(read_data)

            return "Deleted"
        elif mode == "R":
            dictStr = read_data[myIndex + 1].rstrip("\n")
            dict = ast.literal_eval(dictStr)
            return dict

    elif mode == "W":
        fString = ""
        fString += "\n" + MID + "\n"
        fString += str(givenDict) + "\n"

        with open('ONGOING_MATCHES.txt', "a") as f:
            f.write(fString)
        return "Written"

    else:
        return None
        print("FATAL ERROR: INVALID MODE IN ongMatchFileOps ")






def checkCorrectScore(score):
    myRegex = re.compile("^(\d)-(\d)$")
    rawList = myRegex.findall(score)
    if len(rawList) == 0:
        return "incorrect"
    else:
        selfScore, oppScore = rawList[0]
        selfScore, oppScore = int(selfScore), int(oppScore)


        nonOTcond = (selfScore == 7 and oppScore < 6) ^ (oppScore == 7 and selfScore < 6)
        OTcond = (6 <= selfScore < 8 and oppScore == 8) ^ (6 <= oppScore < 8 and selfScore == 8)
        if nonOTcond:
            return "nonOT", selfScore, oppScore
        elif OTcond:
            return "OT", selfScore, oppScore
        else:
            return "incorrect"


def getResultEmbed(MID, winTeamDict, lossTeamDict, winCapt, lossCapt, givenScore, isPending):
    #Recieves the winning team, losing team, their captains and whether it is OT

    winTeamStr = ""
    lossTeamStr = ""

    for player in winTeamDict:
        winTeamStr += f"<@{player}> : `+ {winTeamDict[player]}`\n"

    for player in lossTeamDict:
        lossTeamStr += f"<@{player}> : `- {abs(lossTeamDict[player])}`\n"

    embedTitle = ""
    embedFooterText = ""
    if isPending :
        embedTitle = f"Match Result Update Pending: {MID}"
        embedFooterText = f"Captains, react with {check_mark} to confirm, {cross_mark} to cancel"
    else:
        embedTitle = f"Match Result Confirmed: {MID}"
        embedFooterText = f"Results confirmed: {check_mark}"

    myEmbed = discord.Embed(title = embedTitle, description = f"**Given Score:** {givenScore}")
    myEmbed.add_field(name = f"Team: {winCapt}", value = winTeamStr)
    myEmbed.add_field(name = f"Team: {lossCapt}", value = lossTeamStr)
    myEmbed.set_footer(text = embedFooterText, icon_url = footerIcoURL)

    return myEmbed


#Get Embed Object to display after generating a match, called by generateTeams
def getMatchEmbed(matchID, playerInfo , dicTeamA, dicTeamB, captainTeamA, captainTeamB):

    teamAstr = ""
    teamBstr = ""

    #playerInfo is in the form: {discID = [discName, ELO, uplayIGN] , discID = ---}

    #Generate Embed Body Text for each team
    for player in playerInfo:
        if player in dicTeamA:
            playerName = playerInfo[player][0]
            playerELO = playerInfo[player][1]
            playerUplayID = playerInfo[player][2]
            teamAstr += f"<@{player}> : {playerUplayID} : `{playerELO}` \n"
            """
            if player == captainTeamA:
                teamAstr += f"C: <@{player}> : {playerUplayID} : `{playerELO}` \n"
            else:
                teamAstr += f"<@{player}> : {playerUplayID} : `{playerELO}` \n"
            """
        elif player in dicTeamB:
            playerName = playerInfo[player][0]
            playerELO = playerInfo[player][1]
            playerUplayID = playerInfo[player][2]
            teamBstr += f"<@{player}> : {playerUplayID} : `{playerELO}` \n"
            """
            if player == captainTeamB:
                teamBstr += f"C: <@{player}> : {playerUplayID} : `{playerELO}` \n"
            else:
                teamBstr += f"<@{player}> : {playerUplayID} : `{playerELO}` \n"
            """

        else:
            print("FATAL ERROR: getMatchEmbed in queueSystem.py has FAILED")

    #Generate Embed Object
    myEmbed = discord.Embed(title = "Match Generated", color = embedSideColor)
    myEmbed.add_field(name = "MatchID: ", value = matchID, inline = True)
    myEmbed.add_field(name = f"Team A (Captain: {playerInfo[captainTeamA][0]}):", value = teamAstr, inline = False)
    myEmbed.add_field(name = f"Team B (Captain: {playerInfo[captainTeamB][0]}):", value = teamBstr, inline = False)
    myEmbed.set_footer(text = "Captains, react with given emoji to BAN the corresponding map", icon_url = footerIcoURL)

    return myEmbed


def getBalancedTeams(lobbyDic):

    #List of ELOs on each team
    teamA = []
    teamB = []



    playersPerSide = playersPerLobby // 2

    averageScore = 0
    playerELOList = []
    for playerID in lobbyDic:
    	averageScore += lobbyDic[playerID]         #Summation of scores, will get averaged later
    	playerELOList.append(lobbyDic[playerID])   #Appending ELOs of all players to a list



    averageScore = averageScore//playersPerLobby    #Using mean average to calculate lobby's average ELO

    """
    Version 1.0 of balancing works by getting all combinations of 10 players' ELO
    on one side (5 spots). Therefore, there will be a total of 10C5 or 10!/(5!5!)
    or 252 combinations then finding the combination whose average mean ELO is
    closest to the lobby's average ELO.

    After assigning ELOs to lists TeamA and TeamB, it generates dictionaries where
    it matches players with ELOs and returns them

    """
    #Getting all 252 combinations
    comb = list(combinations(playerELOList,playersPerSide))

    #diff from Lobby average for first combination (only used for initial run of loop)
    diffFromAVG = abs(averageScore - sum(comb[0])//playersPerSide)
    teamA = []

    teamA = list(comb[0]).copy()
    for i in comb:
        try:
            if diffFromAVG > abs(averageScore - (sum(i)//playersPerSide)):
                #If diff higher than combination i's average, then assign to Team A
                teamA = list(i).copy()
                #New Diff from AVG
                diffFromAVG = abs(averageScore - (sum(i)//playersPerSide))
        except Exception as e:
            print(e)

    #Assign ELOs not in TeamA to TeamB
    teamB = playerELOList.copy()
    for i in teamA:
    	teamB.remove(i)


    #Prepare dictionaries for returning
    dicTeamA = {}
    dicTeamB = {}

    mydic = lobbyDic.copy()

    #Match ELOs in TeamA to Players and assign them to dicTeamA
    for x in mydic:
    	if mydic[x] in teamA and len(dicTeamA) < playersPerSide:
    		dicTeamA.update({x:mydic[x]})


    #Match remaining Players to TeamB
    for i in mydic:
    	if i not in dicTeamA:
    		dicTeamB.update({i:mydic[i]})


    return dicTeamA, dicTeamB


def generateTeams(matchID, pList):

    #pList = [###############, ############, ##############, #####################, ##################, ###################]

    queryList = []          #List for MongoDB Query
    lobbyDic = {}           #This dictionary goes to the balancing function
    embedDictionary = {}    #This dictionary goes to the embedGenerator function

    #Building queryList
    for playerDiscID in pList:
        playerDic = {"discID" : playerDiscID}
        queryList.append(playerDic)

    playerDocs = dbCol.find({"$or" : queryList})
    #Example: playerDocs = dbCol.find({"$or" : [{"discID" : "187236546431287296" }, {"discID" : "813695157232861194"}, etc]})

    #Building Dictionaries
    for x in playerDocs:
        lobbyDic[x["discID"]] = x["ELO"]
        embedDictionary[x["discID"]] = [ x["discName"] , x["ELO"], x["uplayIGN"] ]

    fileOpsResult = ongMatchFileOps("W", matchID, lobbyDic)
    if fileOpsResult == "Written":
        print(f"Added matchID: {matchID} to ONGOING_MATCHES.txt")
    else:
        print("\nFATAL ERROR: Failed to write to ONGOING_MATCHES.txt at generateTeams()\n")



    #Get dict of balanced teams in the form {playerDiscID: ELO, cont.}
    dicTeamA, dicTeamB = getBalancedTeams(lobbyDic)


    #Get captains of teams using highest ELO
    captainTeamA = max(dicTeamA, key=dicTeamA.get)
    captainTeamB = max(dicTeamB, key=dicTeamB.get)


    #Logging
    print(f"Generated match with ID: {matchID}")
    print(f"Team A: {dicTeamA}")
    print(f"Team B: {dicTeamB}")

    #Generate Embed Object
    embeddedObject = getMatchEmbed(matchID, embedDictionary , dicTeamA, dicTeamB, captainTeamA, captainTeamB)

    #Get discNames of team captain
    teamAVC = embedDictionary[captainTeamA][0][:-5]
    teamBVC = embedDictionary[captainTeamB][0][:-5]


    ##dicTeamA does not have discNames

    ##Upload Match to DB##

    #Captains at position 0 for both lists
    teamListA = [captainTeamA,]
    teamListB = [captainTeamB,]

    for member in dicTeamA:
        #Avoid inserting captain twice
        if member not in teamListA:
            teamListA.append(member)
    for member in dicTeamB:
        #Avoid inserting captain twice
        if member not in teamListB:
            teamListB.append(member)
    #Captains at position 0 and 5, with the players of teams A,B after 0 and 5 respectively
    fullLobbyList = teamListA + teamListB

    matchesCol.insert_one({"MID" : matchID, "score" : "0-0", "matchList" : fullLobbyList})
    print(f"Uploaded Generated Match: {matchID}")

    return (embeddedObject, teamAVC, teamBVC, captainTeamA, captainTeamB)
    #return (embeddedObject, teamAVC, teamBVC)


def setup(client):
	client.add_cog(QueueSystem(client))
