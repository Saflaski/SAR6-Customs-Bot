import discord
import pymongo
import datetime
import asyncio
import time
import math
from discord.ext import commands, tasks
from os import environ

#settingup MongoDB
mongoCredURL = environ["MONGODB_PASS"]
myclient = pymongo.MongoClient(mongoCredURL)
db = myclient["SAR6C_DB"]
dbCol = db["users_col"]

#Global Variables
baseELO = 2000
autoLBrefresh = 20

#For embed messages
embedSideColor = 0x2425A2
footerText = "SAR6C Leaderboards - Only author can flip pages | Use .h for help!"
thumbnailURL= "https://cdn.discordapp.com/attachments/780358458993672202/780363791875440690/Untitled_design.gif"
footerIcoURL = "https://media.discordapp.net/attachments/780358458993672202/785365594714275840/APAC_SOUTH_LOGO.png"

#Unicode reaction emojis
left_arrow = '\u23EA'
right_arrow = '\u23E9'
place_medals = ['🥇', '🥈', '🥉']

#Discord Values
leaderBoardTC = 822347088057991208
autoLeaderboardTC = 822784280387518504
autoLeaderboardMessage = None
autoLBInfoChannel = None

class Leaderboard(commands.Cog):
	def __init__(self, client):
		self.client = client

	@commands.Cog.listener()
	async def on_ready(self):
		print('Cog: "leaderboard" is ready.')
		self.autoLBGen.start()

	#Channel Checks
	def checkCorrectChannel(channelID = None, channelIDList = []):
		def function_wrapper(ctx):
			givenChannelID = ctx.message.channel.id
			if givenChannelID in channelIDList or givenChannelID == channelID:
				return True
			else:
				return False
		return commands.check(function_wrapper)

	@commands.command(aliases = ["leaderboard", "leaderboards"])
	@commands.guild_only()
	@checkCorrectChannel(channelID = leaderBoardTC)
	async def lb(self, ctx, myPos = None):

		print(f"{ctx.author} used lb")

		aliveTime = 60					#How long to enable page switching (seconds)

		currentSkip = 0					#No. of documents currently skipped
		limitPerPage = 10				#No. of documents to show per page

		#mydoc = dbCol.find().skip(currentSkip).limit(limitPerPage).sort("ELO",1)

		maxLimit = dbCol.count_documents({})		#Total no. of users or documents
		print(f"No. of documents: {maxLimit}")

		"""
		Function getEmbedObject() :-
			->Queries database and returns limitPerPage no. of docs by skipping over currentSkip no. of docs
			->Searches those docs to find individual details (uplayID, discName, ELO etc)
			->Generates an Embed Object after parsing the details
			->Returns Embed Object

		"""
		def getEmbedObject():
			#global Currentskip
			global currentPage
			global totalPages

			currentPage = currentSkip//limitPerPage + 1			#Finds current page number based on how many skipped yet
			totalPages = math.ceil(maxLimit/limitPerPage)		#Finds total pages based on how many docs there are

			mydoc = dbCol.find().skip(currentSkip).limit(limitPerPage).sort("ELO",-1)

			embedContentString = ""			#Body of Embed Content
			tempCounter = 0					#tempCounter used to assign rank to each user
											#tempCounter + currentSkip = Actual rank of user

			for x in mydoc:
				tempCounter += 1
				if tempCounter + currentSkip <= 3:
					uRank = place_medals[tempCounter - 1] + '.'
				else:
					uRank = str(currentSkip + tempCounter) + '.'

				#To query each doc and append details to the body of Embed Object
				embedContentString += f"{uRank.ljust(4)} **{x['discName']}** | Uplay: `{x['uplayIGN']}` \tELO: `{x['ELO']}`\t\t\n\n"


			#Generate Embed Object
			myEmbed = discord.Embed(title = "Leaderboards", color = embedSideColor)
			myEmbed.add_field(name = f"Tier 1 ({currentPage}/{totalPages})", value = embedContentString)
			myEmbed.set_footer(text = footerText, icon_url = footerIcoURL)
			myEmbed.set_thumbnail(url = thumbnailURL)

			return myEmbed


		lb_msg = await ctx.send(embed = getEmbedObject())	# Gives embed of n documents
															# n = maxLimit


		#Bot reacts to the lb_msg so that user can easily react to the message
		await lb_msg.add_reaction(left_arrow)
		await lb_msg.add_reaction(right_arrow)


		#Page flipping:


		timeout = 30					#Waits for 30 seconds then removes page flipping function
		timeout_start = time.time()		#Starts keeping track of time

		def check(reaction, user):		#Checks if author (and not anybody else) is reacting with the correct arrows
			return user == ctx.author and (str(reaction.emoji) == right_arrow or str(reaction.emoji) == left_arrow)

		while time.time() < timeout_start + timeout:		#While time limit has not elapsed

			try:
				#Watches out for author to add the proper reaction
				reaction, user = await self.client.wait_for('reaction_add', timeout = 60.0, check = check)

			except asyncio.TimeoutError:
				pass					#I forgot why I added timeout above and asyncio.TimeoutError here
				#print("Timed_Out")		#Useless

			if str(reaction.emoji) == right_arrow:
				#print(f"Currentskip = {currentSkip}, limitPerPage = {limitPerPage}")

				if currentSkip + limitPerPage >= maxLimit:			#Checks if it will go over limit i.e, the beginning
					pass											#Doesn't update page if it goes over limit
				else:
					currentSkip += limitPerPage						#Updates pages if it doesn't

				#print(f"Currentskip = {currentSkip}, limitPerPage = {limitPerPage}")	#debugging
				await lb_msg.edit(embed = getEmbedObject())
				await lb_msg.remove_reaction(right_arrow, ctx.author)

			elif str(reaction.emoji) == left_arrow:

				if currentSkip - limitPerPage <= 0:					#Checks if it will go over limit i.e, beginning
					currentSkip = 0									#sets page to 1, ie skipped docs to 0, if it does
				else:
					currentSkip -= limitPerPage						#Updates page if it doesn't

				#print(f"Currentskip = {currentSkip}, limitPerPage = {limitPerPage}")	#debugging
				await lb_msg.edit(embed = getEmbedObject())
				await lb_msg.remove_reaction(left_arrow, ctx.author)

			time.sleep(1)		#To avoid resource hogging (by looping continously)

		await lb_msg.clear_reactions()	#Clears reactions after timeout has happened/time limit has elapsed


	@lb.error
	async def lb_pvtmsg_error(self, ctx, error):
		if isinstance(error, commands.NoPrivateMessage):		#Not to be used in pvt message
			pass		#To prevent clogging up terminal


	@tasks.loop(seconds = autoLBrefresh)
	async def autoLBGen(self):
		global autoLeaderboardMessage
		global autoLBInfoChannel

		def checkIfBotMsg(botMsg):
			return botMsg.author == self.client.user

		if autoLeaderboardMessage == None and autoLBInfoChannel == None:
			#The LB and Info Message haven't been sent yet

			autoLBInfoChannel = self.client.get_channel(autoLeaderboardTC)

			#Purge previous messages
			await autoLBInfoChannel.purge(check = checkIfBotMsg)

			#Send Info
			with open("commands.txt") as f:
				commandsTextFile = f.read()
			infoEmbed = discord.Embed(title = "Help", color = embedSideColor)
			infoEmbed.add_field(name = f"Commands:", value = commandsTextFile)
			infoEmbed.set_footer(text = footerText, icon_url = footerIcoURL)
			infoEmbed.set_thumbnail(url = thumbnailURL)
			await autoLBInfoChannel.send(embed = infoEmbed)

			#Send the new LB
			autoLBEmbed = getAutoLBEmbed()
			autoLeaderboardMessage = await autoLBInfoChannel.send(embed = autoLBEmbed)


		else:
			autoLBEmbed = getAutoLBEmbed()
			await autoLeaderboardMessage.edit(embed = autoLBEmbed)



def getAutoLBEmbed():

	mydoc = dbCol.find().limit(20).sort("ELO",-1)

	embedContentString = ""			#Body of Embed Content
	tempCounter = 0					#tempCounter used to assign rank to each user
									#tempCounter + currentSkip = Actual rank of user

	for x in mydoc:
		tempCounter += 1
		if tempCounter <= 3:
			uRank = place_medals[tempCounter - 1] + '.'
		else:
			uRank = str(tempCounter) + '.'

		#To query each doc and append details to the body of Embed Object
		embedContentString += f"{uRank.ljust(4)} **{x['discName']}** | Uplay: `{x['uplayIGN']}` \tELO: `{x['ELO']}`\t\t\n\n"


	#Generate Embed Object
	myEmbed = discord.Embed(title = "Auto Leaderboard", color = embedSideColor)
	myEmbed.add_field(name = f"Top 20 list:", value = embedContentString)
	myEmbed.set_footer(text = f"Refreshes every {autoLBrefresh} seconds", icon_url = footerIcoURL)
	myEmbed.set_thumbnail(url = thumbnailURL)

	return myEmbed

def setup(client):
	client.add_cog(Leaderboard(client))
