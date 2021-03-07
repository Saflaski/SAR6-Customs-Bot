import discord
import pymongo
import datetime
import re
import secrets
import string
import time
import asyncio
import random
from discord.ext import commands, tasks
from itertools import combinations


#settingup MongoDB
myclient = pymongo.MongoClient("mongodb+srv://SFSI1:JJJQb7a9hHNbiYw@cluster0.9oihh.mongodb.net/TM_DB?retryWrites=true&w=majority")
db = myclient["TM_DB"]
dbCol = db["users_col"]
matchesCol = db["matches_col"]

#Global Variables
embedSideColor = 0x2425A2
embedTitleColor = 0xF64C72
footerText = "R6TM Bot v0.1 | Use .h for help!"
footerIcoURL = "https://cdn.discordapp.com/attachments/813715902028840971/813716545627881482/idk.png"
thumbnailURL = "https://media.discordapp.net/attachments/780358458993672202/785365594714275840/APAC_SOUTH_LOGO.png"

#Global Queue list
GQL = []

#Test Queues



#Dictionary of generated lobbies (but not matches)
generatedLobby = {}

#Players In Ongoing Matches
PIOM = {}


#Generated Voice Channels
GVC = {}



#Global Variables
matchGenerationChannel = 813695785928884267     #Channel for Embeds to go to
playersPerLobby = 4                             #Cannot be odd number
myGuildID = 813695785928884264                  #Used later to get myGuild
myGuild = None                                  #Guild for which Bot is run
voiceChannelCategoryID = 816634104362827786     #Used later to get voiceChannelCategory
voiceChannelCategory = None                     #Category into which to make VCs


#Points won in Matches
pOTWin = 20
pOTLoss = 0
pNonOTWin = 30
pNonOTLoss = -30

#Unicode Reaction Emojis
check_mark = '\u2705'
digitArr = ["1\u20E3", "2\u20E3", "3\u20E3"]

#SAR6C Map Pool
MAP_POOL = ["Villa", "Clubhouse", "Oregon", "Coastline", "Consulate", "Kafe", "Theme Park"]

"""
Queue system v0.1
Status : INCOMPLETE
As of right now, v0.1 works like:
    .joinq adds the user to the queue
    .leaveq removes the user from the queue
    .showq displays the queue

    Once playersPerLobby people have joined the queue, the program takes them from the queue
    and adds them to a match list.


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


        #Set guild and VC Category
        global myGuild
        global voiceChannelCategory
        myGuild = self.client.get_guild(813695785928884264)
        voiceChannelCategory = discord.utils.get(myGuild.categories, id = voiceChannelCategoryID)


    @commands.command(aliases = ["joinq","join"])
    async def joinQueue(self, ctx, member: discord.Member):

        global GQL

        #Adds user to the queue
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

        """
        if discID not in GQL:               #Checks if user is in Global Queue
            if discID not in PIOM:          #Checks if user is in Match
                GQL.append(discID)
                print(f"{member} has joined the Global Queue")

                #queueEmbed = discord.Embed(color = embedSideColor)
                #queueEmbed.add_field(name = f"Added to Global Queue ({len(GQL)}/{playersPerLobby})" , value = f"<@{member.id}>", inline = True)
                await ctx.message.add_reaction(check_mark)
                #await ctx.send(embed = queueEmbed)
            else:
                queueEmbed = discord.Embed(description = f"You are already in a match", color = embedSideColor)
                await ctx.send(embed = queueEmbed)
        else:
            queueEmbed = discord.Embed(description = f"You are already in the  Global Queue", color = embedSideColor)
            await ctx.send(embed = queueEmbed)
        """

    @commands.command(aliases = ["showq", "queue"])
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





    @commands.command(aliases = ["leaveq","leave"])
    async def leaveQueue(self, ctx, member: discord.Member):

        global GQL

        #Removes user to the queue
        queueEmbed = discord.Embed(color = embedSideColor)
        if member.id in GQL:
            GQL.remove(member.id)
            #queueEmbed.add_field(name = "Removed from Global Queue", value = "** **")
            await ctx.message.add_reaction(check_mark)

        else:
            queueEmbed.add_field(name = "You weren't in Global Queue", value = "** **")
            await ctx.send(embed = queueEmbed)



    @commands.command(aliases = ["showM", "getMatch", "getM", "match"])
    async def showMatch(self, ctx, matchID):


        matchDoc = matchesCol.find_one({"MID": matchID})

        if matchDoc is not None:
            MID = matchDoc["MID"]
            matchScore = matchDoc["score"]
            teamAList = matchDoc["matchList"][:playersPerLobby//2]
            teamBList = matchDoc["matchList"][playersPerLobby//2:]
            teamACaptain = teamAList[0]
            teamBCaptain = teamBList[0]


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

        embedDescription = ( "**ID:** " + str(matchID) + "\n**Score:** "
                                + "A " +str(matchScore[0]) + "-" + str(matchScore[2]) + " B" )

        myEmbed = discord.Embed(title = "Match Found", description = embedDescription, color = embedSideColor)
        #myEmbed.add_field(name = "Details:", value = f"ID: {matchID}\nScore:{matchScore}", inline = True)
        myEmbed.add_field(name = f"Team A: {CaptNameA}", value = teamStringA, inline = False)
        myEmbed.add_field(name = f"Team B: {CaptNameB}", value = teamStringB, inline = False)

        await ctx.send(embed = myEmbed)

    @showMatch.error
    async def register_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Invalid Usage, try: `.getMatch <match ID>`")


    @commands.command(name = "setELO")
    async def setELO(self, ctx, member : discord.Member, ELO : int):

        opResult = dbCol.update_one({"discID" : member.id}, { "$set" : {"ELO" : ELO}})

        if opResult.matched_count == 0:
            failEmbed = discord.Embed(description = "User not found", color = 0xff0000)
            await ctx.send(embed = failEmbed)
            return None

        elif opResult.modified_count != 0:
            successEmbed = discord.Embed(description = f"Succesfully set ELO: {ELO}", color = 0x00ff00)
            await ctx.send(embed = successEmbed)

    @setELO.error
    async def register_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.send("Invalid Usage, try: `.setELO <@discord ID> <ELO>`")

    @commands.command(name = "changepoints")
    async def changePoints(self, ctx, givenMode, matchID, givenScore ):

        givenScore = checkCorrectScore(givenScore)

        if "incorrect" in givenScore:
            await ctx.send(embed = discord.Embed(description = "Score in wrong format", color = 0xff0000))
            return None

        givenModeCheck = (givenMode == "set") or (givenMode == "revert")
        if not givenModeCheck:
            myEmbed = discord.Embed(description = "Invalid mode, use \"revert\" or \"set\"", color = 0xff0000)
            await ctx.send(embed = myEmbed)
            return None

        if "OT" in givenScore:
            if givenMode == "revert":
                awardedPoints = pOTLoss
                deductedPoints = pOTWin

            elif givenMode == "set":
                awardedPoints = pOTWin
                deductedPoints = pOTLoss

        elif "nonOT":
            if givenMode == "revert":
                awardedPoints = pNonOTLoss
                deductedPoints = pNonOTWin

            elif givenMode == "set":
                awardedPoints = pNonOTWin
                deductedPoints = pNonOTLoss


        #Prepare queries to find players
        matchDoc = matchesCol.find_one({"MID": matchID})

        if matchDoc is not None:
            teamAList = matchDoc["matchList"][:playersPerLobby//2]
            teamBList = matchDoc["matchList"][playersPerLobby//2:]

        else:
            myEmbed = discord.Embed(description = "Invalid Match ID", color = 0xff0000)
            await ctx.send(embed = myEmbed)
            return None

        queryListA = []
        queryListB = []

        for playerDiscID in teamAList:
            dbPlayerDic = {"discID" : playerDiscID}
            queryListA.append(dbPlayerDic)

        for playerDiscID in teamBList:
            dbPlayerDic = {"discID" : playerDiscID}
            queryListB.append(dbPlayerDic)



        dbCol.update_many({"$or" : queryListA}, { "$inc" : {"ELO" : awardedPoints}})
        dbCol.update_many({"$or" : queryListB}, { "$inc" : {"ELO" : deductedPoints}})

        myEmbed = discord.Embed(description = "Succesfully changed points", color = 0x00ff00)
        await ctx.send(embed = myEmbed)

    @changePoints.error
    async def register_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Invalid Usage, try: `.changepoints <set/revert> <match ID> <score>`")


    @commands.command(name = "updatescore")
    async def updateScore(self, ctx, matchID, givenScore):

        #Prepare queries to find players
        matchDoc = matchesCol.find_one({"MID": matchID})

        if matchDoc is not None:
            teamAList = matchDoc["matchList"][:playersPerLobby//2]
            teamBList = matchDoc["matchList"][playersPerLobby//2:]

        else:
            myEmbed = discord.Embed(description = "Invalid Match ID", color = 0xff0000)
            await ctx.send(embed = myEmbed)
            return None

        if "incorrect" not in checkCorrectScore(givenScore) or givenScore == "C-C" or givenScore == "0-0":
            matchesCol.update_one({"MID" : matchID}, {"$set" : {"score" : givenScore}})
            await ctx.send(embed = discord.Embed(description = f"Succesfully set score: {givenScore}", color = 0x00ff00))

        else:
            await ctx.send(embed = discord.Embed(description = "Incorrect score format", color = 0xff0000))


    @updateScore.error
    async def register_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Invalid Usage, try: `.updatescore <match ID> <score>`")

    @commands.command(name = "closematch")
    async def closematch(self, ctx, matchID):              #Free players of a certain match from PIOM

        global PIOM

        matchDoc = matchesCol.find_one({"MID": matchID})

        if matchDoc is not None:
            matchList = matchDoc["matchList"]
            currentResult = matchDoc["score"]

        else:
            myEmbed = discord.Embed(description = "Invalid Match ID", color = 0xff0000)
            await ctx.send(embed = myEmbed)
            return None

        del PIOM[matchID]
        await ctx.send(embed = discord.Embed(title = f"Closed match: {matchID}", color = 0x00ff00))


    @closematch.error
    async def register_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Invalid Usage, try: `.closematch <match ID>`")

    @commands.command(name = "delvc")
    async def deleteVC(self, ctx, matchID = ""):        #Deletes voice channels generated because of a certain match

        global GVC
        matchDoc = matchesCol.find_one({"MID": matchID})

        if matchDoc is not None:
            matchList = matchDoc["matchList"]

        else:
            myEmbed = discord.Embed(description = "Invalid Match ID", color = 0xff0000)
            await ctx.send(embed = myEmbed)
            return None

        teamACaptain = matchDoc["matchList"][:playersPerLobby//2][0]
        teamBCaptain = matchDoc["matchList"][playersPerLobby//2:][0]

        try:
            VC1 = self.client.get_channel(GVC[teamACaptain])
            VC2 = self.client.get_channel(GVC[teamBCaptain])
        except Exception as e:
            print(e)

        await VC1.delete()
        await VC2.delete()

        del GVC[teamACaptain]
        del GVC[teamBCaptain]

        print(f"Deleted VCs generated by match: {matchID}")

    @commands.command(name = "freeQ")
    async def freeQueue(self, ctx):

        global GQL
        GQL.clear()
        await ctx.send("Cleared Global Queue")
        print("Removed players from GQL")

    @commands.command(name = "rpg")
    async def remFromQueue(self, ctx, member: discord.Member):
        global GQL

        GQL.remove(member.id)

        await ctx.send(f"Removed {member} from Global Queue")
        print(f"Removed from GQL: {member}")

    @remFromQueue.error
    async def register_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.send("Invalid Usage, try: `.rpg <@discord ID>`")

    @commands.command(name = "result")
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
                print("\n\nFATAL ERROR: Failure at addManualResult\n\n")

            print(f"Sending Match Result Pending Panel:{MID} ")

            #Find which team author was in

            if ctx.author.id in teamAList:
                authorTeamList = teamAList
                oppTeamList = teamBList
            else:
                authorTeamList = teamBList
                oppTeamList = teamAList

            #Fetch the member objects for each captain
            authorTeamCaptain = await self.client.fetch_user(authorTeamList[0])
            oppTeamCaptain = await self.client.fetch_user(oppTeamList[0])

            #Prepare pending match embed

            winningTeam = []
            losingTeam = []
            winCapt = ""
            lossCapt = ""
            isOT = False

            #getResultEmbed(MID, winTeam, lossTeam, winCapt, lossCapt, isOT, isPending)

            #Assign winning team, losing team, their captains, and scores to appropriate variables

            print(teamResult)
            if "nonOT" in teamResult:
                isOT = False
                if teamResult[1] > teamResult[2]:
                    #Author's team won in nonOT
                    winningTeam, losingTeam = authorTeamList, oppTeamList
                    winCapt, lossCapt = authorTeamCaptain, oppTeamCaptain

                elif teamResult[1] < teamResult[2]:
                    #Author's team lost in nonOT
                    winningTeam, losingTeam = oppTeamList, authorTeamList
                    winCapt, lossCapt = oppTeamCaptain, authorTeamCaptain


            elif "OT" in teamResult:
                isOT = True
                if teamResult[1] > teamResult[2]:
                    #Author's team won in OT
                    winningTeam, losingTeam = authorTeamList, oppTeamList
                    winCapt, lossCapt = authorTeamCaptain, oppTeamCaptain

                elif teamResult[1] < teamResult[2]:
                    #Author's team lost in OT
                    winningTeam, losingTeam = oppTeamList, authorTeamList
                    winCapt, lossCapt = oppTeamCaptain, authorTeamCaptain

            #print(winningTeam, losingTeam, winCapt, lossCapt, isOT)

            #Send Pending match Embed for result verification
            try:
                embed = getResultEmbed(MID, winningTeam, losingTeam, winCapt, lossCapt, isOT, isPending = True)
                sentEmbed = await ctx.send(content = f"Captains: <@{authorTeamCaptain.id}> , <@{oppTeamCaptain.id}>", embed = embed)
                await sentEmbed.add_reaction(check_mark)
            except Exception as e:
                print(e)


            async def confirmMatch():

                #Update Embed Message
                await sentEmbed.edit(embed = getResultEmbed(MID, winningTeam, losingTeam, winCapt, lossCapt, isOT, isPending = False))

                global GVC

                #Update Database
                queryListWon = []          #Lists for MongoDB Query
                queryListLost = []


                if isOT:
                    awardedPoints = pOTWin
                    deductedPoints = pOTLoss
                else:
                    awardedPoints = pNonOTWin
                    deductedPoints = pNonOTLoss

                #Building queryList


                try:
                    for playerDiscID in winningTeam:
                        dbPlayerDic = {"discID" : playerDiscID}
                        queryListWon.append(dbPlayerDic)
                except Exception as e:
                    print(e)

                for playerDiscID in losingTeam:
                    dbPlayerDic = {"discID" : playerDiscID}
                    queryListLost.append(dbPlayerDic)


                #For Won
                try:
                    dbCol.update_many({"$or" : queryListWon}, { "$inc" : {"ELO" : awardedPoints}})
                    print("Updated DB for winning team")
                except Exception as e:
                    print(e)

                #For Lost
                dbCol.update_many({"$or" : queryListLost}, { "$inc" : {"ELO" : deductedPoints}})
                print("Updated DB for losing team")

                #Update Match Score
                match_score = str(f"{teamResult[1]}-{teamResult[2]}")
                matchesCol.update({"MID" : MID},{"$set" : {"score" : match_score}})
                print(f"Updated DB for score: {match_score}")

                #Remove the matchID from PIOM

                del PIOM[MID]

                #Remove VCs

                try:
                    VC1 = self.client.get_channel(GVC[winningTeam[0]])
                    VC2 = self.client.get_channel(GVC[losingTeam[0]])
                except Exception as e:
                    print(e)

                await VC1.delete()
                await VC2.delete()

                del GVC[winningTeam[0]]
                del GVC[losingTeam[0]]

                print(f"Removed players and VCs from ongoing list \nMatch Closed: {MID}")

            #To check that captain has used correct reaction
            def check(myreaction, myuser):

                userCond = (myuser == authorTeamCaptain) or (myuser == oppTeamCaptain)
                reactionCond = str(myreaction.emoji) == check_mark
                return (userCond and reactionCond)

            #Captain confirmation boolean values for each team
            oppTeamConf = False
            authTeamConf = False

            timeout = 120
            timeout_start = time.time()		#Starts keeping track of time

            while time.time() < timeout_start + timeout:
                try:
                    myreaction, myuser = await self.client.wait_for('reaction_add', check = check)
                except Exception as e:
                    print(e)
                #print(f"{myuser} did {myreaction}")

                if check(myreaction, myuser):
                    if myuser == authorTeamCaptain:
                        authTeamConf = True
                    elif myuser == oppTeamCaptain:
                        oppTeamConf = True

                #Check if captains have verified
                if authTeamConf and oppTeamConf:
                    print("Match Result Confirmed")

                    #Get Embed, Update Databse, Remove from PIOM
                    await confirmMatch()
                    #Clear reactions from result embed object
                    await sentEmbed.clear_reactions()
                    break


                time.sleep(1)		#To avoid resource hogging (by looping continously)

            await sentEmbed.clear_reactions()	#Clears reactions after timeout has happened/time limit has elapsed



    @addManualResult.error
    async def register_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.send("Invalid Usage, try: `.result #-#` ,Eg.: `.result 7-5`")


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
                channel = self.client.get_channel(matchGenerationChannel)
                msg = await channel.send(embed = embeddedContent)

                #Make Voice Channels with captains' names
                VC_A = await myGuild.create_voice_channel(name = f"Team: {teamA_VCName}", category = voiceChannelCategory)
                VC_B = await myGuild.create_voice_channel(name = f"Team: {teamB_VCName}", category = voiceChannelCategory)

                #Add VCs to Global VC Dict: GVC
                GVC[CapA_ID] = VC_A.id
                GVC[CapB_ID] = VC_B.id

                #Start the map ban
                await self.mapbanSystem(matchID, embeddedContent, msg, CapA_ID, CapB_ID)

                break


    async def mapbanSystem(self, MID, embedMessage, msg : discord.Message, capA_ID, capB_ID ):

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
        async def genNewEmbed():
            mapString = ""
            for mapIndex in someDict:
                mapString += f"{mapIndex} -> {someDict[mapIndex]}\n"
            embedMessage.set_field_at(3, name = "Map Ban Phase:", value = mapString)
            await msg.edit(embed = embedMessage)


        embedMessage.add_field(name = "Map Ban Phase:", value = mapString)
        await msg.edit(embed = embedMessage)

        #Check that only captains have reacted and only to the correct emojis

        switcherList = []   #List to see who can ban next

        def check(myreaction, myuser):

            userCond = (myuser.id == capA_ID) or (myuser.id == capB_ID)
            reactionCond = str(myreaction.emoji) in someDict.keys()
            return (userCond and reactionCond)

        #30 second timer for banning maps
        timeout = 300
        timeout_start = time.time()     #Starts keeping track of time

        lastMap = ""

        while time.time() < timeout_start + timeout:
            try:
                myreaction, myuser = await self.client.wait_for('reaction_add',timeout = 300.0, check = check)
            except asyncio.TimeoutError:
                print("Map Ban timed out")

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
                    await genNewEmbed()
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
            print(f"Map set: {lastMap}")
        else:
            print("Map not set")

    #### TESTING PURPOSES ####

    @commands.command(name = "QSTest")
    async def queueTest(self, ctx):

       await ctx.send(embed = discord.Embed(description = f"{PIOM}"))

    #### TESTING PURPOSES ####



def generateMatchID():
    """
    Generates unique alphanumeric token of length 8
    Total possible permutations: (26 + 26 + 10) ^ 8
    Therefore, collision probability is at 50% only at 62^4

    """
    alphabet = string.ascii_letters + string.digits
    matchID = ''.join(secrets.choice(alphabet) for i in range(8))
    return matchID

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


def getResultEmbed(MID, winTeam, lossTeam, winCapt, lossCapt, isOT, isPending):
    #Recieves the winning team, losing team, their captains and whether it is OT

    winTeamStr = ""
    lossTeamStr = ""

    if isOT:
        awardedPoints = pOTWin
        deductedPoints = pOTLoss
    else:
        awardedPoints = pNonOTWin
        deductedPoints = pNonOTLoss

    for player in winTeam:
        winTeamStr += f"<@{player}> : `+ {awardedPoints}`\n"

    for player in lossTeam:
        lossTeamStr += f"<@{player}> : `- {abs(deductedPoints)}`\n"

    embedTitle = ""
    embedFooterText = ""
    if isPending :
        embedTitle = f"Match Result Update Pending: {MID}"
        embedFooterText = f"Captains, react with {check_mark} to confirm"
    else:
        embedTitle = f"Match Result Confirmed: {MID}"
        embedFooterText = f"Results confirmed: {check_mark}"

    myEmbed = discord.Embed(title = embedTitle)
    myEmbed.add_field(name = f"Team: {winCapt}", value = winTeamStr)
    myEmbed.add_field(name = f"Team: {lossCapt}", value = lossTeamStr)
    myEmbed.set_footer(text = embedFooterText)

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
    myEmbed.set_footer(text = footerText, icon_url = footerIcoURL)

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
