import discord
import pymongo
import datetime
import time
import re
import json
import asyncio
import string
import secrets
import re
from os import environ
from discord.ext import commands

#settingup MongoDB
mongoCredURL = environ["MONGODB_PASS"]
myclient = pymongo.MongoClient(mongoCredURL)
db = myclient["SAR6C_DB"]
dbCol = db["users_col"]
matchesCol = db["matches_col"]
ticketsCol = db["tickets_col"]

#Global Variables
baseELO = 2000
embedSideColor = 0x2425A2
embedTitleColor = 0xF64C72
footerText = "SAR6C | Use .h for help!"
footerIcoURL = "https://cdn.discordapp.com/attachments/813715902028840971/822427952888676372/APAC_SOUTH_FOOTER.png"
thumbnailURL = "https://cdn.discordapp.com/attachments/780358458993672202/780363791875440690/Untitled_design.gif"

#Global variables
ticketTimeOut = 120

#Discord Values
with open("ServerInfo.json") as jsonFile:
    discServInfo = json.load(jsonFile)

discTextChannels = discServInfo["TextChannels"]
infoRegTC = discTextChannels["helpRegInfo"]
helpDeskTC = discTextChannels["help"]

#Roles
adminRole = "R6C Admin"
userRole = "R6C"


class TicketSystem(commands.Cog):

	def __init__(self, client):
		self.client = client

	@commands.Cog.listener()
	async def on_ready(self):
		print('Cog: "ticketSystem" is ready.')

	#Channel Checks
	def checkCorrectChannel(channelID = None, channelIDList = []):
		def function_wrapper(ctx):
			givenChannelID = ctx.message.channel.id
			if givenChannelID in channelIDList or givenChannelID == channelID:
				return True
			else:
				return False
		return commands.check(function_wrapper)

	@commands.has_any_role(userRole, adminRole)
	@commands.command(name = "openticket")
	@checkCorrectChannel(channelID = helpDeskTC)
	async def openTicket(self, ctx, matchID = None):
		
		#DM the user
		playerObj = ctx.author

		timeout = ticketTimeOut			#Gets time limit
		ticketID = ""
		prepMsg = 	(
					"__**Preparing Ticket**__"

					"\nPlease enter a valid subject/title alternatively" 
					" choose (copy-paste) one of the following options"
					" *(you can give a description after this step)*:"
					)

		subjectOptions = (
						"```\n"
						"Report Player for Cheating\n"
						"Report Player for High Ping\n"
						"Report Player Absence \n"
						"Report Player for other reasons\n"
						"Report Delay in Lobby Formation\n"
						"Report Match Fixing\n"
						"```"
						)
		cancelNote = "*Note: You can use* `cancel` *at anytime of the ticket process to cancel the ticket*"


		dmMsg = await playerObj.send(prepMsg)
		await playerObj.send(f"{subjectOptions}\n{cancelNote}")

		def checkIfAuthorDM(message):					#Only accepting messages from the author's DMs
			
			if message.channel == dmMsg.channel and message.author != dmMsg.author:			#To not capture bot's messages
				return True
			else:
				return False
			

		async def checkIfCancel(message):				#Check if user used cancel
			if message.content == "cancel":
				await playerObj.send("*Ticket Cancelled. Use* `.openticket` *in the server's channel to open a new ticket*")
				return True
			else:
				return False



		def checkEvidence(msg):							#Check if message either has an attachment or a URL
			if len(msg.attachments[0].url) != 0:
				return msg.attachments[0].url, "attachment"
			elif urlValidator(msg.content):
				return msg.content, "extURL"
			else:
				return None
			
		
		"""
		while time.time() < timeout_start + timeout:
			prepReply = await self.client.wait_for('message', check = checkIfAuthorDM)
			print(f"Content: {prepReply.content}")
			print(f"Attachments: {prepReply.attachments}")
		"""
		#Get Subject and Description

		currentStage = 1

		ticketSubject = ""
		ticketDesc = ""
		ticketEvidences = []

		



		
		while currentStage <= 3:
			try:
				authorReply = await self.client.wait_for('message', timeout = timeout, check = checkIfAuthorDM)
			except asyncio.TimeoutError:
				await playerObj.send("Ticket cancelled due to timeout (2 minutes crossed since last message)."
									" Use `.openticket` in the server's channel to open a new ticket")
				return

			if await checkIfCancel(authorReply):
				return
			
			if currentStage == 1:
				ticketSubject = authorReply.content
				if len(ticketSubject) < 10:
					await playerObj.send("Ticket Length inadequate")
				else:
					#Upload to DB
					await playerObj.send("Please enter a complete description of the problem, try "
										"to include as much info as possible (eg. Discord IDs, uPlay IGNs)."
										"\nYou can add proofs/evidences as attachments later."
										" To skip current step, use `none`")
					currentStage += 1
			
			elif currentStage == 2:
				ticketDesc = authorReply.content
				
				if len(ticketDesc) > 10 or ticketDesc == "none":					
					currentStage += 1
					print("reached")
					#Send instructions for attachments
					await playerObj.send("You can now add attachments. To stop attaching attachments or"
									" if you want to skip this step, use `done`")
				else:
					await playerObj.send("Inadequate description length, try again.")
				

			elif currentStage == 3:
				try:
					if authorReply.content == "done":
						#generateTicket()
						ticketID = genTicketID()
						await playerObj.send(f"Generated ticket with ID: `{ticketID}`")
						#show embed of ticket
						currentStage += 1
					elif checkEvidence(authorReply) is not None:
						#Append the evidence
						#print(authorReply.attachments[0].url)
						pass

					else:
						await playerObj.send("You didn't attach anything, try again.")
				except Exception as e:
					print(e)


		print(ticketSubject)
		print(ticketDesc)
		print(ticketEvidences)
		print(currentStage)
		

		
			

	@openTicket.error
	async def openTicketError(self, ctx, error):
		if isinstance(error, commands.CheckFailure):
			pass
		
def genTicketID():
    """
    Generates unique alphanumeric token of length 8
    Total possible permutations: (26 + 26 + 10) ^ 8
    Therefore, collision probability is at 50% only at 62^4

    """
    alphabet = string.ascii_letters + string.digits
    ticketID = ''.join(secrets.choice(alphabet) for i in range(6))
    return ticketID

def urlValidator(givenURL):
	regex = re.compile(
		r'^(?:http|ftp)s?://' # http:// or https://
		r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
		r'localhost|' #localhost...
		r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
		r'(?::\d+)?' # optional port
		r'(?:/?|[/?]\S+)$', re.IGNORECASE)

	return (re.match(regex, givenURL) is not None)		#If no URL found, then it returns False, otherwise True



def setup(client):
	client.add_cog(TicketSystem(client))
