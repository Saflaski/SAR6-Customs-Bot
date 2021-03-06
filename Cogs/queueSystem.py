import discord
import pymongo
import datetime
import re
import secrets
import string
import time
import asyncio
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

#Dictionary of generated lobbies (but not matches)
generatedLobby = {}

#Players In Ongoing Matches
PIOM = []

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

        if discID not in GQL:               #Checks if user is in Global Queue
            if discID not in PIOM:          #Checks if user is in Match
                GQL.append(discID)
                print(f"{member} has joined the Global Queue")

                queueEmbed = discord.Embed(color = embedSideColor)
                queueEmbed.add_field(name = f"Added to Global Queue ({len(GQL)}/{playersPerLobby})" , value = f"<@{member.id}>", inline = True)
                await ctx.send(embed = queueEmbed)
            else:
                queueEmbed = discord.Embed(description = f"You are already in a match", color = embedSideColor)
                await ctx.send(embed = queueEmbed)
        else:
            queueEmbed = discord.Embed(description = f"You are already in the  Global Queue", color = embedSideColor)
            await ctx.send(embed = queueEmbed)


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
            queueEmbed.add_field(name = "Removed from Global Queue", value = "** **")
        else:
            queueEmbed.add_field(name = "You weren't in Global Queue", value = "** **")

        await ctx.send(embed = queueEmbed)



    @commands.command(aliases = ["showM", "getMatch"])
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
            myEmbed = discord.Embed(color = embedSideColor)
            myEmbed.add_field(name = "Match not found", value = "** **")
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




    @commands.command(name = "setELO")
    async def setELO(self, ctx, member : discord.Member, ELO : int):

        opResult = dbCol.update_one({"discID" : member.id}, { "$set" : {"ELO" : ELO}})

        if opResult.matched_count == 0:
            failEmbed = discord.Embed(description = "User not found", color = 0xff0000)
            await ctx.send(embed = failEmbed)
            return None

        elif opResult.modified_count != 0:
            successEmbed = discord.Embed(description = f"Succesfully set ELO: {ELO}", color = embedSideColor)
            await ctx.send(embed = successEmbed)






    @commands.command(name = "result")
    async def addManualResult(self, ctx, score):
        global PIOM
        global GVC

        #Checks if author is in an ongoing match
        if ctx.author.id not in PIOM:
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
                    ->Remove players from PIOM/Players In Ongoing Matches list.

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

                #Remove Players from PIOM
                for givenPlayer in (winningTeam + losingTeam):
                    try:
                        PIOM.remove(givenPlayer)
                    except ValueError:
                        print("FATAL ERROR: Value Error at confirmMatch")

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

            timeout = 90
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




    #### TESTING PURPOSES ####
    @commands.command(name = "QSTest")
    async def queueTest(self, ctx):

        print(GVC)


    #### TESTING PURPOSES ####

    @tasks.loop(seconds = 1)
    async def findPossibleLobby(self):
        global generatedLobby
        global playersPerLobby


        if len(GQL) >= playersPerLobby:
            print(f"Generating Match:")

            playerList = []

            for i in range(playersPerLobby):
                playerList.append(GQL[i])
            for member in playerList:
                GQL.remove(member)
                PIOM.append(member)

            matchID = generateMatchID()
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
                await channel.send(embed = embeddedContent)

                #Make Voice Channels with captains' names
                VC_A = await myGuild.create_voice_channel(name = f"Team: {teamA_VCName}", category = voiceChannelCategory)
                VC_B = await myGuild.create_voice_channel(name = f"Team: {teamB_VCName}", category = voiceChannelCategory)

                #Add VCs to Global VC Dict: GVC
                GVC[CapA_ID] = VC_A.id
                GVC[CapB_ID] = VC_B.id

                break

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
