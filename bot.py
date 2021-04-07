#!/usr/bin/env python3

import discord
import os
import pymongo
import logging
from os import environ

from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions
#set bot prefix
client = commands.Bot(command_prefix = '.')

#remove default help
client.remove_command('help')

#Global Variables
footerText = "SAR6C | Use .h for help!"
footerIcoURL = "https://cdn.discordapp.com/attachments/813715902028840971/822427952888676372/APAC_SOUTH_FOOTER.png"
thumbnailURL = "https://media.discordapp.net/attachments/780358458993672202/785365594714275840/APAC_SOUTH_LOGO.png"
embedSideColor = 0x2425A2

#logging errors
							#Not being used because unable to install logging on Windows #nvm
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

#End of log

#MongoDB setup
mongoCredURL = environ["MONGODB_PASS"]
myclient = pymongo.MongoClient(mongoCredURL)
db = myclient["SAR6C_DB"]
dbCol = db["users_col"]

#TOKEN SETUP
TOKEN = environ["DISCORD_TOKEN"]


#Say Hi
@client.event
async def on_ready():
	print("Bot is ready.")


@client.command(aliases = ['h','commands'])
async def help(ctx):
	with open("commands.txt") as f:
		commandsTextFile = f.read()

	myEmbed = discord.Embed(title = "Help", color = embedSideColor)
	myEmbed.add_field(name = f"Commands:", value = commandsTextFile)
	myEmbed.set_footer(text = footerText, icon_url = footerIcoURL)
	myEmbed.set_thumbnail(url = thumbnailURL)

	await ctx.send(embed = myEmbed)

@client.command(aliases = ['adminh','admincommands'])
async def adminhelp(ctx):
	with open("admincommands.txt") as f:
		commandsTextFile = f.read()

	myEmbed = discord.Embed(title = "Admin Commands", color = embedSideColor)
	myEmbed.add_field(name = f"Commands:", value = commandsTextFile)
	myEmbed.set_footer(text = footerText, icon_url = footerIcoURL)
	myEmbed.set_thumbnail(url = thumbnailURL)

	await ctx.send(embed = myEmbed)


#Setup Cogs
@client.command()
@has_permissions(ban_members=True)
async def load(ctx, extension):
	client.load_extension(f'Cogs.{extension}')

@client.command()
@has_permissions(ban_members=True)
async def unload(ctx,extension):
	client.unload_extension(f'Cogs.{extension}')

@load.error
async def load_error(ctx, error):
	if isinstance(error, MissingPermissions):
		print(f"{ctx.author} tried to use LOAD")

@unload.error
async def unload_error(ctx, error):
	if isinstance(error, MissingPermissions):
		print(f"{ctx.author} tried to use UNLOAD")

for filename in os.listdir('./Cogs'):
	if filename.endswith('.py'):
		print(f'Cog found: {filename}')
		client.load_extension(f'Cogs.{filename[:-3]}')
#End of Cog setup




client.run(TOKEN)
