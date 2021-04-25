import discord
import pymongo
import datetime
import re
import json
from os import environ
from discord.ext import commands

#settingup MongoDB
mongoCredURL = environ["MONGODB_PASS"]
myclient = pymongo.MongoClient(mongoCredURL)
db = myclient["SAR6C_DB"]
dbCol = db["users_col"]
matchesCol = db["matches_col"]

#Global Variables
baseELO = 2000
embedSideColor = 0x2425A2
embedTitleColor = 0xF64C72
footerText = "SAR6C | Use .h for help!"
footerIcoURL = "https://media.discordapp.net/attachments/822432464290054174/832871738030817290/sar6c1.png"
thumbnailURL = "https://media.discordapp.net/attachments/822432464290054174/832871738030817290/sar6c1.png"

#Global variables
playersPerLobby = 10

#Discord Values
with open("ServerInfo.json") as jsonFile:
    discServInfo = json.load(jsonFile)

infoRegTC = discServInfo["TextChannels"]["helpRegInfo"]
quickStartTC = discServInfo["TextChannels"]["quickstart"]
adminTC = discServInfo["TextChannels"]["admin"]
ticketsTC = discServInfo["TextChannels"]["tickets"]
completeChannelList = [infoRegTC, quickStartTC, adminTC, ticketsTC]
#Roles
adminRole = "R6C Admin"
userRole = "R6C"


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
	@commands.command(name = "register")
	@commands.guild_only()
	@checkCorrectChannel(channelID = infoRegTC)
	async def registerUser(self, ctx, uplayIGN):

		print(f"{ctx.author} used register")

		author = ctx.author

		#Logging purposes
		print(f"Author: {author.name}#{author.discriminator} requested to register.\nAuthor's ID: {author.id}")

		#await ctx.send(f"{type(author)} is straight. {type(str(author))} is str") #Ignore


		if dbCol.find_one({"discID": author.id}):				#Checks if user is already registered
			await ctx.send(f'\N{Cross Mark} {author} is already registered!')

		else:													#If not registered, prepares dictionary for mongodb insert
			tempDict = 	{	"discID": author.id ,
							"discName" : f"{str(author)}" ,
							"dateRegistered" : datetime.datetime.now(),
							"uplayIGN" : uplayIGN,
							"ELO" : baseELO,
						}
			try:						#Inserts data
				x = dbCol.insert_one(tempDict)
				await ctx.send(f"\N{White Heavy Check Mark} {author} succesfully registered!")
				print(f" {author} succesfully registered. ID: {x.inserted_id}")


				#quickStartCh = self.client.fetch_channel(quickStartTC)
				dmEmbed = discord.Embed(title = "Welcome to SAR6 Customs", 
                                                description = f"Click <#{quickStartTC}> to know the commands and how to get started",
                                                color = embedSideColor)
				dmEmbed.set_thumbnail(url = thumbnailURL)
				await ctx.author.send(embed = dmEmbed)

			except:
				await ctx.send("Error 103: Contact Admin")
				print(f"Failed to register user: {author}")

	@registerUser.error
	async def register_error(self, ctx, error):
		if isinstance(error, commands.MissingRequiredArgument):
			await ctx.send('Usage: ".register <Uplay Username>" Eg. ".register F.lanker"')
		if isinstance(error, commands.NoPrivateMessage):
			pass



	@commands.command(name = "info")
	@commands.guild_only()
	@checkCorrectChannel(channelIDList = completeChannelList)
	async def getUserInfo(self, ctx, givenID = ""):

		print(f"{ctx.author} used info")

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

		userDiscName = ""		#Later used to check if data extracted successfully

		#Extract Data from collection

		if mydoc is None:
			await ctx.send(embed = discord.Embed(description = "User not found"))
			return None

		#if not None

		#Get user info
		userDiscID = mydoc["discID"]
		userDiscName = mydoc["discName"]
		userUplayID = mydoc["uplayIGN"]
		userELO = mydoc["ELO"]

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
			WLString = "No matches found"


		myEmbed = discord.Embed(title = f"{userDiscName}", color = embedSideColor)
		myEmbed.add_field(name = "Uplay ID: ", value = userUplayID, inline = True)
		myEmbed.add_field(name = "ELO: ", value = userELO, inline = True)
		myEmbed.add_field(name = "Join Date:", value = userJoinDate, inline = False)
		myEmbed.add_field(name = "Rank: ", value = globalRank, inline = False)
		myEmbed.add_field(name = "Win-Loss (last 10):", value = WLString, inline = False)
		myEmbed.set_footer(text = footerText, icon_url = footerIcoURL)
		await ctx.send(embed = myEmbed)


	@getUserInfo.error
	async def info_retrieve_error(self, ctx, error):
		if isinstance(error, commands.NoPrivateMessage):
			pass		#To prevent clogging up terminal
		elif isinstance(error, commands.MissingRequiredArgument):
			await ctx.send("Usage: .info <@DiscordID> | Eg.: .info @Carl\nOptional uplayID search mode: .info <uplayID> uplay| Eg.: .info Pengu.G2 uplay")
		else:
			print(error)

	#Forceregister is basically the same as .register except only for high-permission users/admins
	@commands.command(name = "forceregister")
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
							"uplayIGN" : uplayIGN,								#
							"ELO" : startingELO,								#
						}
			try:
				x = dbCol.insert_one(tempDict)
				await ctx.send(f"\N{White Heavy Check Mark} {member} succesfully force-registered!")
				print(f"{member} succesfully registered. ID: {x.inserted_id}, uplay: {uplayIGN}, ELO:{startingELO}")
			except:
				await ctx.send("Error: Contact admin")			#Let's pray this doesn't happen
				print(f"Failed to register user: {member}")


	@forceRegister.error
	async def forceRegister_error(self, ctx, error):
		if isinstance(error, commands.MissingRequiredArgument):
			await ctx.send('Usage: !forceregister <@discordID> <uplayID> <startingELO>')


	#Updates Uplay ID
	@commands.command(aliases = ["updateUplay", "uUplay", "updateuplay", "uuplay"])
	@checkCorrectChannel(channelID = infoRegTC)
	async def update_Uplay(self, ctx, newUplayID):

		authorID = ctx.author.id

		myQuery = {"discID" : authorID}					#To query database based on author's discord ID
		targetUpdate = {"uplayIGN" : newUplayID}		#Preps dictionary for MongoDB update

		myDoc = dbCol.find_one(myQuery)					#
		if myDoc is None:
			myEmbed = discord.Embed(description = "Please register first using `.register`", color = embedSideColor)
			await ctx.send(embed = myEmbed)
			return None

		dbCol.update_one(myQuery, { '$set': targetUpdate})

		print(f"{ctx.author} requested to change uplayID to {newUplayID}")	#logging


		#Creates embed object
		myEmbed = discord.Embed(title = "Changed Uplay ID", color = embedSideColor)
		myEmbed.add_field(name = "Previous Uplay ID:", value = myDoc["uplayIGN"], inline = False)
		myEmbed.add_field(name = "Requested Uplay ID:", value = newUplayID, inline = False)
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
            "ELO": -1
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
            'arr.discID': 1,
            'arr.ELO': -1,
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
