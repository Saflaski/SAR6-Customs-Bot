import discord
from discord.ext import commands

class Example(commands.Cog):

	def __init__(self, client):
		self.client = client

	@commands.Cog.listener()
	async def on_ready(self):
		print('Cog: "Example" is ready.')

	@commands.command(aliases = ["Hi", "ping"])
	async def _hi(self, ctx):
		await ctx.send(f"HI! {(round(self.client.latency * 1000))}ms")

def setup(client):
	client.add_cog(Example(client))