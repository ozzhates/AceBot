import discord
import logging

from discord.ext import commands, tasks
from datetime import datetime, timedelta

from cogs.mixins import AceMixin
from utils.string_helpers import shorten
from utils.time import pretty_seconds
from utils.pager import Pager


log = logging.getLogger(__name__)

SUCCESS_EMOJI = '\U00002705'
CHECK_EVERY = 60
DEFAULT_REMINDER_MESSAGE = 'Hey, wake up!'
MAX_DELTA = timedelta(days=365)
MAX_REMINDERS = 12


class TimeMultConverter(commands.Converter):
	async def convert(self, ctx, mult):
		# TODO: try/catch this
		mult = float(mult)

		if mult < 0.0:
			raise commands.CommandError('Unit has to be more than 0.')

		return mult


class TimeDeltaConverter(commands.Converter):
	async def convert(self, ctx, unit):
		unit = unit.lower()

		if unit in ('m', 'min', 'mins', 'minute', 'minutes'):
			return timedelta(minutes=1)
		elif unit in ('h', 'hr', 'hrs', 'hour', 'hours'):
			return timedelta(hours=1)
		elif unit in ('d', 'day', 'days'):
			return timedelta(days=1)
		elif unit in ('w', 'wk', 'week', 'weeks'):
			return timedelta(weeks=1)
		else:
			raise commands.BadArgument('Unknown time type.')


class RemindPager(Pager):
	async def craft_page(self, e, page, entries):
		now = datetime.utcnow()

		e.set_author(name=self.member.name, icon_url=self.member.avatar_url)
		e.description = 'All your reminders for this server.'

		for id, guild_id, channel_id, user_id, remind_on, made_on, message in entries:
			delta = (remind_on - now).total_seconds()
			time_text = 'Soon...' if delta < 15 else pretty_seconds(delta)
			e.add_field(
				name=f'{id}: {time_text}',
				value=shorten(message, 256, 2) if message is not None else DEFAULT_REMINDER_MESSAGE,
				inline=False
			)


class Reminders(AceMixin, commands.Cog):
	'''Set, view and delete reminders.

	Valid time types are: `minutes`, `hours`, `days` or `weeks`
	'''

	def __init__(self, bot):
		super().__init__(bot)
		self.check_reminders.start()

	@tasks.loop(minutes=1)
	async def check_reminders(self):
		res = await self.db.fetch('SELECT * FROM remind WHERE remind_on <= $1', datetime.utcnow())

		for id, guild_id, channel_id, user_id, remind_on, made_on, message in res:

			channel = self.bot.get_channel(channel_id)
			user = self.bot.get_user(user_id)

			e = discord.Embed(
				title='Reminder:',
				description=message or DEFAULT_REMINDER_MESSAGE,
				timestamp=made_on
			)

			# Encapsulate the reminder message in the prefix/suffix, and send it to the user
			try:
				if channel is not None:
					await channel.send(content=f'<@{user_id}>', embed=e)
				elif user is not None:
					await user.send(embed=e)
			except discord.HTTPException as exc:
				log.info(f'Failed sending reminder #{id} for {user.id} - {exc}')

			# Get the record we just sent the message for, and delete it so it isn't sent again
			await self.db.execute('DELETE FROM remind WHERE id=$1', id)

	@commands.command()
	async def reminders(self, ctx):
		'''List your reminders in this guild.'''

		res = await self.db.fetch(
			'SELECT * FROM remind WHERE guild_id=$1 AND user_id=$2 ORDER BY id DESC',
			ctx.guild.id, ctx.author.id
		)

		if not len(res):
			raise commands.CommandError('Couldn\'t find any reminders.')

		p = RemindPager(ctx, res, per_page=6)
		p.member = ctx.author
		await p.go()

	@commands.command()
	async def remindme(self, ctx, amount: TimeMultConverter, unit: TimeDeltaConverter, *, message=None):
		'''Create a new reminder.'''

		now = datetime.utcnow()
		delta = unit * amount

		if delta > MAX_DELTA:
			raise commands.CommandError('Sorry. Can\'t remind in more than a year!')

		if message is not None and len(message) > 1024:
			raise commands.CommandError('Sorry, keep the message below 1024 characters!')

		count = await self.db.fetchval('SELECT COUNT(id) FROM remind WHERE user_id=$1', ctx.author.id)
		if count > MAX_REMINDERS:
			raise commands.CommandError(f'Sorry, you can\'t have more than {MAX_REMINDERS} active reminders at once.')

		await self.db.execute(
			'INSERT INTO remind (guild_id, channel_id, user_id, made_on, remind_on, message) VALUES ($1, $2, $3, $4, $5, $6)',
			ctx.guild.id, ctx.channel.id, ctx.author.id, now, now + delta, message
		)

		await ctx.message.add_reaction(SUCCESS_EMOJI)

	@commands.command()
	async def delreminder(self, ctx, reminder_id: int):
		'''Delete a reminder. Must be your own reminder.'''

		res = await self.db.execute(
			'DELETE FROM remind WHERE id=$1 AND guild_id=$2 AND user_id=$3',
			reminder_id, ctx.guild.id, ctx.author.id
		)

		if res == 'DELETE 1':
			await ctx.send('Reminder deleted.')
		else:
			raise commands.CommandError('Reminder not found, or you do not own it.')


def setup(bot):
	bot.add_cog(Reminders(bot))
