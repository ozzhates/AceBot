import discord, logging

from discord.ext import commands
from datetime import datetime

from utils.checks import is_manager
from utils.database import db, LogGuild
from utils.lol import bot_deleted
from cogs.base import TogglableCogMixin

log = logging.getLogger(__name__)

CHANNEL_TYPES = {discord.TextChannel: 'Text', discord.VoiceChannel: 'Voice', discord.CategoryChannel: 'Category'}


class Logger(TogglableCogMixin):
	'''Log interesting events like message deletion.'''

	def __init__(self, bot):
		super().__init__(bot)

	async def __local_check(self, ctx):
		return await self._is_used(ctx)

	async def _check(self, guild_id):
		return await self.bot.uses_module(guild_id, 'logger')

	def get_message_embed(self, message):
		'''
		Stolen from Rapptz with minor tweaks, thanks!
		https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/stars.py#L168-L193
		'''

		embed = discord.Embed(description=message.content)
		if message.embeds:
			data = message.embeds[0]
			if data.type == 'image':
				embed.set_image(url=data.url)

		if message.attachments:
			file = message.attachments[0]
			if file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
				embed.set_image(url=file.url)
			else:
				embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)

		embed.set_author(
			name=message.author.display_name,
			icon_url=message.author.avatar_url_as(format='png'),
			# url=f'https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id}'
		)

		embed.set_footer(text=f'ID: {message.id}')
		embed.timestamp = message.created_at
		return embed

	async def log(self, guild, content=None, embed=None):
		if isinstance(guild, discord.Guild):
			guild = guild.id

		channel_id = await db.scalar('SELECT channel_id FROM logguild WHERE guild_id=$1', guild)

		channel = self.bot.get_channel(channel_id)
		if channel is None:
			return

		try:
			await channel.send(content=content, embed=embed)
		except:
			pass

	async def on_message_delete(self, message):
		if message.author.bot or message.channel.id in (509530286481080332, 378602386404409344):
			return

		if not await self._check(message.guild.id):
			return

		if bot_deleted(message.id): # STUPID STUPID STUPID STUPID STUPIDDDDD
			return

		embed = self.get_message_embed(message)

		embed.color = 0xFF4000

		await self.log(
			guild=message.guild,
			content=f'Message deleted in {message.channel.mention} (Author ID: {message.author.id})',
			embed=embed
		)

	async def on_guild_channel_create(self, channel):
		if not await self._check(channel.guild.id):
			return

		e = discord.Embed(
			title=f'{CHANNEL_TYPES[type(channel)]} channel created',
			description=f'{channel.mention}'
		)

		e.set_footer(text=f'ID: {channel.id}')
		e.timestamp = channel.created_at

		await self.log(
			guild=channel.guild,
			embed=e
		)

	async def on_guild_channel_delete(self, channel):
		if not await self._check(channel.guild.id):
			return

		e = discord.Embed(
			title=f'{CHANNEL_TYPES[type(channel)]} channel deleted',
			description=f'#{channel.name}'
		)

		e.set_footer(text=f'ID: {channel.id}')
		e.timestamp = datetime.now()
		e.color = 0xFF4000

		await self.log(
			guild=channel.guild,
			embed=e
		)

	async def on_guild_channel_update(self, before, after):
		if not await self._check(before.guild.id):
			return

		changed = {}

		for attr in dir(before):
			if attr.startswith('_'):
				continue
			b, a = getattr(before, attr), getattr(after, attr)
			if not isinstance(b, (str, int)):
				continue
			if b != a:
				changed[attr.replace('_', ' ').title()] = str(a)

		# should probably try to support more changes but cba for now
		if not len(changed):
			return

		e = discord.Embed(
			title='Channel edited',
			description=before.mention
		)

		for attr, a in changed.items():
			e.add_field(
				name=attr,
				value=a,
				inline=False
			)

		e.set_footer(text=f'ID: {before.id}')
		e.timestamp = datetime.now()

		await self.log(
			guild=before.guild,
			embed=e
		)

	async def on_member_remove(self, member):
		if not await self._check(member.guild.id):
			return

		e = discord.Embed(
			title='Member left'
		)

		e.set_author(name=member.name, icon_url=member.avatar_url)
		e.timestamp = datetime.now()
		e.set_footer(text=f'ID: {member.id}')

		await self.log(guild=member.guild, embed=e)

	async def on_voice_state_update(self, member, before, after):
		if not await self._check(member.guild.id):
			return

		changed = {}

		for attr in ('deaf', 'mute'):
			b, a = getattr(before, attr), getattr(after, attr)
			if b != a:
				changed[attr.title()] = a

		if not len(changed):
			return

		e = discord.Embed(
			title='Member voice state update'
		)

		e.set_author(name=member.name, icon_url=member.avatar_url)
		e.timestamp = datetime.now()
		e.set_footer(text=f'ID: {member.id}')
		e.color = 0xFF4000

		for attr, a in changed.items():
			e.add_field(name=attr, value='yes' if a else 'no')

		await self.log(guild=member.guild, embed=e)


	async def on_member_ban(self, guild, user):
		if not await self._check(guild.id):
			return

		e = discord.Embed(
			title='Member banned'
		)

		e.set_author(name=user.name, icon_url=user.avatar_url)
		e.timestamp = datetime.now()
		e.set_footer(text=f'ID: {user.id}')
		e.color = 0xFF4000

		await self.log(guild=guild, embed=e)

	async def on_member_unban(self, guild, user):
		if not await self._check(guild.id):
			return

		e = discord.Embed(
			title='Member unbanned'
		)

		e.set_author(name=user.name, icon_url=user.avatar_url)
		e.timestamp = datetime.now()
		e.set_footer(text=f'ID: {user.id}')
		e.color = 0xFF4000

		await self.log(guild=guild, embed=e)

	@commands.group(name='log', hidden=True, invoke_without_command=True)
	async def _log(self, ctx):
		pass

	@_log.command()
	@is_manager()
	async def channel(self, ctx, channel: discord.TextChannel = None):
		'''
		Set the starboard channel.

		Remember only the bot should be allowed to send messages in this channel!
		'''

		async def announce():
			await ctx.send(f'Log channel set to {channel.mention}')

		lg = await LogGuild.query.where(LogGuild.guild_id == ctx.guild.id).gino.first()

		if channel is None:
			if lg is None:
				await ctx.send('No log channel set.')
			else:
				channel = self.bot.get_channel(lg.channel_id)
				if channel is None:
					await ctx.send('Log channel is set, but I didn\'t manage to find the channel.')
				else:
					await announce()
		else:
			if lg is None:
				await LogGuild.create(
					guild_id=ctx.guild.id,
					channel_id=channel.id
				)
			else:
				await lg.update(channel_id=channel.id).apply()

			await announce()


def setup(bot):
	bot.add_cog(Logger(bot))
