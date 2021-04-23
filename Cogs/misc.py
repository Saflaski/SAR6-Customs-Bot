import discord
from discord.ext import commands

class Example(commands.Cog):

	def __init__(self, client):
		self.client = client

	@commands.Cog.listener()
	async def on_ready(self):
		print('Cog: "misc" is ready.')

	@commands.command(aliases = ["Hi", "ping"])
	async def _hi(self, ctx):
		await ctx.send(f"Pong! {(round(self.client.latency * 1000))}ms")


	"""
	@commands.command(aliases = ["omgomg"])
	async def _omgomg(self, ctx):

		def check(msg):
			if msg.channel.id == 832817275052621834:
				return True
			else:
				return False

		while True:
			authorReply = await self.client.wait_for('message', check = check)

			content = authorReply.content

			channel = self.client.get_channel(302692676099112960)
			await channel.send(content)

	"""

def setup(client):
	client.add_cog(Example(client))