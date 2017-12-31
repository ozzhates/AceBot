import discord
from discord.ext import commands

import random, time
from peewee import *

db = SqliteDatabase('lib/reps.db')

class Reputation:
	"""Handles the highlight command."""

	def __init__(self, bot):
		self.bot = bot
		self.timeout = 5
		self.times = {}
		self.good_emoji = ['pray', 'raised_hands', 'clap', 'ok_hand', 'tongue', 'heart_eyes']
		self.bad_emoji = ['cry', 'disappointed_relieved', 'sleepy', 'sob', 'thinking']

	@commands.command()
	async def replist(self, ctx, amount: int = 8):
		"""Show a list of the most respected users."""

		if amount > 20:
			amount = 20
		elif amount < 3:
			amount = 3

		list = RepUser.select()\
			.where(RepUser.guild_id == ctx.guild.id)\
			.order_by(RepUser.count.desc())

		users, counts, added = '', '', 0
		for rep_user in list:
			if added >= amount:
				break
			user = ctx.guild.get_member(rep_user.user_id)
			if not user:
				continue
			users += f'{user.display_name}\n'
			counts += f'{rep_user.count}\n'
			added += 1

		if not added:
			return await ctx.send('No users with any reputation in this server.')

		e = discord.Embed()
		e.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
		e.add_field(name='Users', value=users, inline=True)
		e.add_field(name='Reputation', value=counts, inline=True)

		await ctx.send(embed=e)

	@commands.command()
	async def rep(self, ctx, member: discord.Member = None):
		"""Send some love!"""

		# get self-rep
		if member is None:
			try:
				user = RepUser.get(RepUser.user_id == ctx.author.id, RepUser.guild_id == ctx.guild.id)
			except RepUser.DoesNotExist:
				return await ctx.send(f'You have 0 reputation... :{random.choice(self.bad_emoji)}:')
			return await ctx.send(f'You have {user.count} reputation! :{random.choice(self.good_emoji)}:')

		# nah fam
		if member == ctx.author:
			return await ctx.send(':japanese_goblin: :thumbsdown:')

		# time check
		try:
			since_last = time.time() - self.times[ctx.guild][ctx.author]
			if since_last < self.timeout:
				return await ctx.send(f'You have to wait {round(since_last)} more seconds until you can rep again.')
		except:
			pass

		# get user
		try:
			user = RepUser.get(RepUser.user_id == member.id, RepUser.guild_id == ctx.guild.id)
		except RepUser.DoesNotExist:
			user = RepUser.create(user_id=member.id, guild_id=ctx.guild.id)

		# increment and save
		user.count += 1
		user.save()

		# check if guild/author is in times obj
		if ctx.guild not in self.times:
			self.times[ctx.guild] = {}
			if ctx.author not in self.times[ctx.guild]:
				self.times[ctx.guild][ctx.author] = 0

		# set current time
		self.times[ctx.guild][ctx.author] = time.time()

		await ctx.send(f'{member.mention} now has {user.count} reputation! :{random.choice(self.good_emoji)}:')


class RepUser(Model):
	user_id = BigIntegerField()
	guild_id = BigIntegerField()
	count = IntegerField(default=0)

	class Meta:
		database = db
		primary_key = CompositeKey('user_id', 'guild_id')

def setup(bot):
	db.connect()
	db.create_tables([RepUser], safe=True)
	bot.add_cog(Reputation(bot))