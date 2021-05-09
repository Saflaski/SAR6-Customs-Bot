#!/usr/bin/env python3

import discord
import os
import pymongo
import logging
import json
from os import environ

from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions
#set bot prefix
client = commands.Bot(command_prefix = '.')

#remove default help
client.remove_command('help')

#Global Variables
footerText = "SAR6C | Use .h for help!"
footerIcoURL = "https://media.discordapp.net/attachments/822432464290054174/832871738030817290/sar6c1.png"
thumbnailURL = "https://media.discordapp.net/attachments/822432464290054174/832871738030817290/sar6c1.png"
embedSideColor = 0xFAAF41
check_mark = '\u2705'

#logging errors
							#Not being used

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
#db = myclient["TM_DB"]
dbCol = db["users_col"]

#TOKEN SETUP
TOKEN = environ["DISCORD_TOKEN"]

#Discord Server Vals
with open("ServerInfo.json") as jsonFile:
    discServInfo = json.load(jsonFile)

serverName = discServInfo["serverName"]



#Say Hi
@client.event
async def on_ready():
	print("Bot is ready.")
	print(f"Started operations in {serverName}")



@client.command(aliases = ['h','commands'])
async def help(ctx):
	with open("commands.txt") as f:
		commandsTextFile = f.read()

	myEmbed = discord.Embed(title = "Help", description = commandsTextFile, color = embedSideColor)
	#myEmbed.add_field(name = f"Commands:", value = commandsTextFile)
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
async def unload(ctx, extension):
	client.unload_extension(f'Cogs.{extension}')

@client.command()
@has_permissions(ban_members=True)
async def reloadcog(ctx,extension):
	client.unload_extension(f'Cogs.{extension}')
	client.load_extension(f'Cogs.{extension}')
	await ctx.message.add_reaction(check_mark)

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
