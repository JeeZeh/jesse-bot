from discord import Message
from discord.ext.commands import Cog, command, is_owner  # type: ignore
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context

from cogs.voice import Voice
from lib.config import COG_EXTENSIONS


class Testing(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.voice_cog: Voice = self.bot.get_cog("Voice")

    async def audio_simple_test(self, message: Message):
        message.content = "🔨"
        await self.voice_cog.check_voice_secrets(message)

    @is_owner()
    @command(description="Reloads all Cogs for quick testing", aliases=["r"])
    async def reload(self, ctx: Context, routine: str = None):
        # Reloads the file, thus updating the Cog class.
        for extension in COG_EXTENSIONS:
            print("   > Reloading", f"cogs.{extension}")
            self.bot.reload_extension(f"cogs.{extension}")

        if routine == "s":
            await self.audio_simple_test(ctx.message)

        await ctx.reply(f"Reloaded {len(COG_EXTENSIONS)} extension(s)")


async def setup(bot: Bot):
    await bot.add_cog(Testing(bot))
