import discord
from matplotlib.style import use
from psutil import users
import pymongo
import datetime
import re
import json
from os import environ
from discord.ext import commands

#Setting up serverconfig
with open("ServerInfo.json") as jsonFile:
    discServInfo = json.load(jsonFile)

with open("mainconfig.json") as configFile:
	mainConfig = json.load(configFile)

#settingup MongoDB
mongoCredURL = mainConfig["MONGODB_PASS"]
myclient = pymongo.MongoClient(mongoCredURL)
db = myclient[discServInfo["MongoDB Database"]]
#db = myclient["TM_DB"]
dbCol = db[discServInfo["MongoDB usersCol"]]
matchesCol = db["MongoDB matchesCol"]


discordMessageTexts = discServInfo["messages"]
userSystemMessages = discServInfo["messages"]["userSystemMessages"]


#Global Variables
baseELO = 2000
embedSideColor = 0xFAAF41
embedTitleColor = 0xF64C72
footerText = discServInfo["messages"]["queueSystemMessages"]["footerTextHelp"]
thumbnailURL= discServInfo["logoURLs"]["thumbnailURL"]
footerIcoURL = discServInfo["logoURLs"]["footerURL"]

#Global variables
playersPerLobby = 10


discTextChannels = discServInfo["TextChannels"]
infoRegTC = discTextChannels["helpRegInfo"]
quickStartTC = discTextChannels["quickstart"]
queueTC = discTextChannels["queue"]
adminTC = discTextChannels["admin"]
completeChannelList = [infoRegTC, quickStartTC, adminTC, queueTC]
#Roles
adminRole = discServInfo["roleNames"]["adminRole"]
userRole = discServInfo["roleNames"]["userRole"]

#importedCommandsAliasList
commandsList = discServInfo["commandNames"]
regCommand = commandsList["register"]
infoCommand = commandsList["info"]
forceRegisterCommand = commandsList["forceRegister"]
updateUplayCommand = commandsList["updateGameName"]


class Users(commands.Cog):

	def __init__(self, client):
		self.client = client

	@commands.Cog.listener()
	async def on_ready(self):
		print('Cog: "users" is ready.')

	#Channel Checks
	def checkCorrectChannel(channelID = None, channelIDList = []):
		def function_wrapper(ctx):
			givenChannelID = ctx.message.channel.id
			if givenChannelID in channelIDList or givenChannelID == channelID:
				return True
			else:
				return False
		return commands.check(function_wrapper)

	#Register user
	@commands.command(name = regCommand)
	@commands.guild_only()
	@checkCorrectChannel(channelID = infoRegTC)
	async def registerUser(self, ctx, uplayIGN):

		print(f"{ctx.author} used register")

		author = ctx.author

		#Logging purposes
		print(f"Author: {author.name}#{author.discriminator} requested to register.\nAuthor's ID: {author.id}")

		#await ctx.send(f"{type(author)} is straight. {type(str(author))} is str") #Ignore


		if dbCol.find_one({"discID": author.id}):				#Checks if user is already registered
			await ctx.send(embed = discord.Embed(
				description = f"\N{Cross Mark} {author} {userSystemMessages['isAlreadyRegistered']}",
				colour = 0xFF0000))

		else:													#If not registered, prepares dictionary for mongodb insert
			tempDict = 	{	"discID": author.id ,
							"discName" : f"{str(author)}" ,
							"dateRegistered" : datetime.datetime.now(),
							"ign" : uplayIGN,
							"ELO" : baseELO,
							"wins" : 0,
							"loss" : 0
						}
			try:						#Inserts data
				x = dbCol.insert_one(tempDict)
				await ctx.send(f"\N{White Heavy Check Mark} {author} succesfully registered!")
				print(f" {author} succesfully registered. ID: {x.inserted_id}")


				#quickStartCh = self.client.fetch_channel(quickStartTC)
				dmEmbed = discord.Embed(title = userSystemMessages["Welcome"], 
                                                description = f"{userSystemMessages['getStarted']} <#{quickStartTC}>",
                                                color = embedSideColor)
				dmEmbed.set_thumbnail(url = thumbnailURL)
				await ctx.author.send(embed = dmEmbed)

			except:
				await ctx.send("Error 103: Contact Admin")
				print(f"Failed to register user: {author}")

	@registerUser.error
	async def register_error(self, ctx, error):
		if isinstance(error, commands.MissingRequiredArgument):
			await ctx.send(userSystemMessages['registerError'])
		if isinstance(error, commands.NoPrivateMessage):
			pass



	@commands.command(name = infoCommand)
	@commands.guild_only()
	@checkCorrectChannel(channelIDList = completeChannelList)
	async def getUserInfo(self, ctx, givenUser : discord.Member = None):

		print(f"{ctx.author} used info")

		"""
		#LEGACY SYSTEM THAT FINDS FOR UPLAY + DISCORD + SELF MODE

		myRegex = re.compile("<.*\d{18}>$")				#Discord ID format is <!@000000000000000000>
		rawList = myRegex.findall(givenID)				#Performs regex search to see if Discord ID was included

		if len(rawList) == 1:							#@DiscordID mode

			givenID = int(str(givenID)[3:-1])			#convert from <!@######> to ###### ;# is digit
			print(f"@Discord mode: {givenID}")
			mydoc = dbCol.find_one({"discID" : givenID})

		elif len(givenID) == 0:							#Self mode

			print(f"Self mode: {ctx.author.id}")
			givenID = ctx.author.id
			mydoc = dbCol.find_one({"discID" : givenID})

		elif len(givenID) >=0 :							#Uplay mode

			print(f"Uplay mode: {ctx.author.id}")
			mydoc = dbCol.find_one({"uplayIGN" : givenID})
		"""

		if givenUser is not None:
			mydoc = dbCol.find_one({"discID" : givenUser.id})
			print(f"@Discord mode: {givenUser}")
		else:
			mydoc = dbCol.find_one({"discID" : ctx.author.id})
			print(f"@Self mode")


		
		userDiscName = ""		#Later used to check if data extracted successfully

		#Extract Data from collection

		if mydoc is None:
			await ctx.send(embed = discord.Embed(description = userSystemMessages["User not found"]))
			return None

		#if not None

		#Get user info
		userDiscID = mydoc["discID"]
		userDiscName = mydoc["discName"]
		userUplayID = mydoc["ign"]
		userELO = mydoc["ELO"]
		userWins = mydoc["wins"]
		userLoss = mydoc["loss"]

		userTotalMatches = userWins + userLoss
		if userTotalMatches != 0:
			userWinPercent = "{:.2f}".format((userWins/userTotalMatches)*100) + "%"
		else:
			userWinPercent = "N/A"
		userWinDiff = userWins - userLoss

		statString = f"```yaml\n{userSystemMessages['Wins']}: {userWins}\n{userSystemMessages['Matches played']}: {userTotalMatches}\n{userSystemMessages['Win Percentage']}: {userWinPercent}\n```"


		userJoinDate = mydoc["dateRegistered"]
		userJoinDate = userJoinDate.date()

		#Get user rank
		globalRank = getUserRank(userDiscID)

		#Get match history info
		matchHistoryDoc = matchesCol.find({"matchList" : userDiscID}).sort([("_id", -1)]).limit(10)

		if matchHistoryDoc.count() != 0:
			WLString = ""
			for match in matchHistoryDoc:
				matchScore = match["score"]

				if matchScore != "C-C" and matchScore != "0-0":
					if userDiscID in match["matchList"][playersPerLobby//2:]:
						matchScore = matchScore[::-1]		#Reverse the score

					authScore, oppScore = matchScore.split("-")
					authScore, oppScore = int(authScore), int(oppScore)

					if authScore > oppScore:
						WLString += "W-"
					else:
						WLString += "L-"

				elif matchScore == "C-C":
					WLString += "C-"

				elif matchScore == "0-0":
					WLString += "GNO-"		#When reversed, this will spell "ONG" ie, Ongoing

				else:
					print("\nERROR: Invalid match score in database at getUserInfo in users.py\n")
					return None

			WLString = WLString.rstrip("-")[::-1]
		else:
			WLString = userSystemMessages["No matches found"]


		myEmbed = discord.Embed(title = f"{userDiscName}", color = embedSideColor)
		myEmbed.add_field(name = "game ID: ", value = userUplayID, inline = False)
		myEmbed.add_field(name = "Rank: ", value = globalRank, inline = True)
		myEmbed.add_field(name = "ELO: ", value = userELO, inline = True)
		myEmbed.add_field(name = "Win/Loss stats: ", value = statString, inline = False)
		myEmbed.add_field(name = "Last 10 matches:", value = WLString, inline = False)
		myEmbed.add_field(name = "Join Date:", value = userJoinDate, inline = False)
		myEmbed.set_footer(text = footerText, icon_url = footerIcoURL)
		await ctx.send(embed = myEmbed)


	@getUserInfo.error
	async def info_retrieve_error(self, ctx, error):
		if isinstance(error, commands.NoPrivateMessage):
			pass		#To prevent clogging up terminal
		elif isinstance(error, commands.MissingRequiredArgument):
			await ctx.send(userSystemMessages['userInfoError'])
		else:
			print(error)

	#Forceregister is basically the same as .register except only for high-permission users/admins
	@commands.command(name = forceRegisterCommand)
	@commands.has_any_role(adminRole)
	async def forceRegister(self, ctx, member: discord.Member, uplayIGN, startingELO = baseELO):


		print(f"{ctx.author} used forceregister")

		discID = member.id

		if dbCol.find_one({"discID": discID}) is not None:							#Checks if user is already registered
			await ctx.send(f'\N{Cross Mark} {member} is already registered!')
		else:
			tempDict = 	{	"discID": discID ,									#
							"discName" : f"{str(member)}" ,						#
							"dateRegistered" : datetime.datetime.now(),			#
							"ign" : uplayIGN,								#
							"ELO" : startingELO,								#
						}
			try:
				x = dbCol.insert_one(tempDict)
				await ctx.send(f"\N{White Heavy Check Mark} {member} succesfully force-registered!")
				print(f"{member} succesfully registered. ID: {x.inserted_id}, uplay: {uplayIGN}, ELO:{startingELO}")
			except:
				await ctx.send("Error: Contact admin - 114")			#Let's pray this doesn't happen
				print(f"Failed to register user: {member}")


	@forceRegister.error
	async def forceRegister_error(self, ctx, error):
		if isinstance(error, commands.MissingRequiredArgument):
			await ctx.send('Usage: !forceregister <@discordID> <game ID> <startingELO>')


	#Updates Uplay ID
	@commands.command(name=updateUplayCommand)
	@checkCorrectChannel(channelID = infoRegTC)
	async def update_Uplay(self, ctx, newUplayID):

		authorID = ctx.author.id

		myQuery = {"discID" : authorID}					#To query database based on author's discord ID
		targetUpdate = {"ign" : newUplayID}		#Preps dictionary for MongoDB update

		myDoc = dbCol.find_one(myQuery)					#
		if myDoc is None:
			myEmbed = discord.Embed(description = userSystemMessages["pleaseRegisterFirst"] , color = embedSideColor)
			await ctx.send(embed = myEmbed)
			return None

		dbCol.update_one(myQuery, { '$set': targetUpdate})

		print(f"{ctx.author} requested to change uplayID to {newUplayID}")	#logging


		#Creates embed object
		myEmbed = discord.Embed(title = userSystemMessages["Changed Game ID"], color = embedSideColor)
		myEmbed.add_field(name = userSystemMessages["Previous Game ID:"], value = myDoc["ign"], inline = False)
		myEmbed.add_field(name = userSystemMessages["Request Game ID"], value = newUplayID, inline = False)
		await ctx.send(embed = myEmbed)

def getUserRank(discID):
	rankCursor = dbCol.aggregate([
    {
        "$project": {
        "_id": 1,
        "discID": "$discID",
        "ELO": "$ELO"
        }
    }, {
        "$sort": {
            "ELO": pymongo.DESCENDING,
			"discID": pymongo.ASCENDING
        }
    }, {
        "$group" : {
            "_id" : {},
            "arr": {
                "$push": {
                    "discID": "$discID",
                    "ELO": "$ELO"
                }
            }
        }
    }, {
        "$unwind": {
            "path" : "$arr",
            "includeArrayIndex": 'globalRank'
        }
    },{
        "$sort" : {
            'arr.discID': pymongo.ASCENDING,
            'arr.ELO': pymongo.DESCENDING,
        }
    }, {
        '$match': { 'arr.discID': discID}
    }
	])

	cursorObjects = list(rankCursor)
	globalRank = cursorObjects[0]['globalRank'] + 1

	return globalRank

def setup(client):
	client.add_cog(Users(client))
