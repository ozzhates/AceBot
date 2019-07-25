import asyncio
import logging

log = logging.getLogger(__name__)


class GuildConfig:
	bot = None
	guilds = dict()
	lock = asyncio.Lock()

	def __init__(self, guild_id, record):
		self.id = record.get('id')
		self.guild_id = guild_id
		self.prefix = record.get('prefix')
		self.mod_role_id = record.get('mod_role_id')
		self.mute_role_id = record.get('mute_role_id')
		self.star_channel_id = record.get('star_channel_id')
		self.star_limit = record.get('star_limit')

	async def set(self, key, value):
		await self.bot.db.execute(f'UPDATE config SET {key}=$1 WHERE id=$2', value, self.id)
		setattr(self, key, value)

	@classmethod
	async def get_guild(cls, guild_id):
		async with cls.lock:
			if guild_id in cls.guilds:
				return cls.guilds[guild_id]

			record = await cls.bot.db.fetchrow('SELECT * FROM config WHERE guild_id=$1', guild_id)

			if record is None:
				await cls.bot.db.execute('INSERT INTO config (guild_id) VALUES ($1)', guild_id)
				record = await cls.bot.db.fetchrow('SELECT * FROM config WHERE guild_id=$1', guild_id)

			ins = cls(guild_id, record)
			cls.guilds[guild_id] = ins

			return ins

	@classmethod
	def set_bot(cls, bot):
		cls.bot = bot