import discord
import pymongo
import datetime
import re
import secrets
import string
from discord.ext import commands, tasks
from itertools import combinations


#settingup MongoDB
myclient = pymongo.MongoClient("mongodb+srv://SFSI1:JJJQb7a9hHNbiYw@cluster0.9oihh.mongodb.net/TM_DB?retryWrites=true&w=majority")
db = myclient["TM_DB"]
dbCol = db["users_col"]

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

#Dictionray of generated matches ()

#Global Variables
matchGenerationChannel = 813695785928884267     #Channel for Embeds to go to
playersPerLobby = 4                             #Cannot be odd number



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
        self.printQueue.start()
        self.findGeneratedLobby.start()

    @commands.command(aliases = ["joinq","join"])
    async def joinQueue(self, ctx, member: discord.Member):

        global GQL

        #Adds user to the queue
        discID = member.id
        if discID not in GQL:
            if discID not in PIOM:
                GQL.append(discID)
                print(f"{member} has joined the Global Queue")
            else:
                await ctx.send("You are already in a match")
        else:
            await ctx.send("You are already in Global Queue")


    @commands.command(aliases = ["showq", "queue"])
    async def showQueue(self, ctx):

        print(GQL)

        """
        for member in GQL:
            print(f"Position:{GQL.index(member)} - {member}")
        """

    @commands.command(aliases = ["leaveq","leave"])
    async def leaveQueue(self, ctx, member: discord.Member):

        global GQL

        #Removes user to the queue
        discID = member.id
        print(f"{member} has left the Global Queue")
        GQL.remove(discID)


    #### TESTING PURPOSES ####
    @commands.command(name = "queueTest")
    async def queueTest(self, ctx):

        playerList = dbCol.find({"$or" : [{"discID" : "187236546431287296" }, {"discID" : "813695157232861194"}]})

        for x in playerList:
            print(x["discName"])
    #### TESTING PURPOSES ####

    @tasks.loop(seconds = 1)
    async def printQueue(self):
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


    @tasks.loop(seconds = 1)
    async def findGeneratedLobby(self):
        global generatedLobby

        if len(generatedLobby) >= 0:
            for matchID in generatedLobby:
                pList = generatedLobby[matchID]
                del generatedLobby[matchID]
                channel = self.client.get_channel(matchGenerationChannel)
                await channel.send(embed = generateTeams(matchID, pList))

                break



def generateMatchID():
    alphabet = string.ascii_letters + string.digits
    matchID = ''.join(secrets.choice(alphabet) for i in range(8))
    return matchID

def getMatchEmbed(matchID, playerInfo , dicTeamA, dicTeamB):

    teamAstr = ""
    teamBstr = ""

    for player in playerInfo:
        if player in dicTeamA:
            playerName = playerInfo[player][0]
            playerELO = playerInfo[player][1]
            playerUplayID = playerInfo[player][2]
            teamAstr += f"<@{player}> : {playerUplayID} : `{playerELO}` \n"

        elif player in dicTeamB:
            playerName = playerInfo[player][0]
            playerELO = playerInfo[player][1]
            playerUplayID = playerInfo[player][2]
            teamBstr += f"<@{player}> : {playerUplayID} : `{playerELO}` \n"

        else:
            print("FATAL ERROR: getMatchEmbed in queueSystem.py has FAILED")


    myEmbed = discord.Embed(title = "Match Generated", color = embedSideColor)
    myEmbed.add_field(name = "MatchID: ", value = matchID, inline = True)
    myEmbed.add_field(name = "Team A:", value = teamAstr, inline = False)
    myEmbed.add_field(name = "Team B:", value = teamBstr, inline = False)
    myEmbed.set_footer(text = footerText, icon_url = footerIcoURL)

    return myEmbed


def getBalancedTeams(lobbyDic):

    teamA = []
    teamB = []

    playersPerSide = playersPerLobby // 2

    averageScore = 0
    playerELOList = []
    for playerELO in lobbyDic:
    	averageScore += lobbyDic[playerELO]
    	playerELOList.append(lobbyDic[playerELO])



    averageScore = averageScore//playersPerLobby

    comb = list(combinations(playerELOList,playersPerSide))

    diffFromAVG = abs(averageScore - sum(comb[0])//playersPerSide)

    teamA = []
    for i in comb:
    	if diffFromAVG > abs(averageScore - (sum(i)//playersPerSide)):
    		teamA = list(i)
    		diffFromAVG = abs(averageScore - (sum(i)//playersPerSide))

    teamB = playerELOList.copy()
    for i in teamA:
    	teamB.remove(i)

    dicTeamA = {}
    dicTeamB = {}

    mydic = lobbyDic.copy()

    tempListA = []
    for x in mydic:
    	if mydic[x] in teamA and len(dicTeamA) < playersPerSide:
    		dicTeamA.update({x:mydic[x]})

    for i in mydic:
    	if i not in dicTeamA:
    		dicTeamB.update({i:mydic[i]})



    return dicTeamA, dicTeamB


def generateTeams(matchID, pList):


    #pList = [###############, ############, ##############, #####################, ##################, ###################]

    #query a dictionary of users from database in the format of {discID : ELO}
    #playerList = dbCol.find({"$or" : [{"discID" : "187236546431287296" }, {"discID" : "813695157232861194"}]})

    queryList = []          #List for MongoDB Query
    lobbyDic = {}           #This dictionary goes to the balancing function
    embedDictionary = {}    #This dictionary goes to the embedGenerator function

    for playerDiscID in pList:
        playerDic = {"discID" : playerDiscID}
        queryList.append(playerDic)

    playerDocs = dbCol.find({"$or" : queryList})

    for x in playerDocs:
        lobbyDic[x["discID"]] = x["ELO"]
        embedDictionary[x["discID"]] = [ x["discName"] , x["ELO"], x["uplayIGN"] ]


    dicTeamA, dicTeamB = getBalancedTeams(lobbyDic)

    print(f"Generated match with ID: {matchID}")
    print(f"Team A: {dicTeamA}")
    print(f"Team B: {dicTeamB}")

    embeddedObject = getMatchEmbed(matchID, embedDictionary , dicTeamA, dicTeamB)

    return embeddedObject



def setup(client):
	client.add_cog(QueueSystem(client))
