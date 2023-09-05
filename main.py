import asyncio

import discord
from discord.ext.commands import Bot as _Bot  # type: ignore

from cogs.passive import check_passive
from lib.config import COG_EXTENSIONS, TOKEN
from lib.utils import cleanup

intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.members = True


class Bot(_Bot):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        await self.get_cog("Notifications").load_subscribers()

    async def on_message(self, message):
        await check_passive(self, message)
        return await super().on_message(message)

if not TOKEN:
    print("No token found!")
    exit()

bot = Bot(
    command_prefix="!",
    description="Jesse's custom bot, rewritten in Python!",
    intents=intents,
)


def load_bot(bot: Bot):
    cleanup()
    for extension in COG_EXTENSIONS:
        asyncio.run(bot.load_extension(f"cogs.{extension}"))

    bot.run(TOKEN)
    return bot


if __name__ == "__main__":
    load_bot(bot)

# ==== VOICE ====
# TODO: "broadcast": "If the bot is in a voice channel it will automatically play any sent audio files",
# TODO: "play": "The _play_ command should be formatted as: 'play [sound]'\nUse 'list sounds' for available sounds.",
# TODO: Allow mixing multiple sounds from message, e.g. "!mix csgo+0.05(delay)+3(50cal)+2(1(delay)+(augh))"

# ==== UTILITY ====
# TODO: "clear": "Clears the previous x messages (up to 30 if specified) in the last 100 messages: '!clear [x]'",
# TODO: "prev": "This command will execute the previously used command again. This is user-specific. `!prev or !!`",

# ==== EXTERNAL ====
# TODO: Crypto integration
# TODO: "youtube": "The yt command should be formatted as: '!yt n/c/s/link",
# TODO: "cringe": "Posts a random giphy from a list of cringe terms (e.g. coffee, shopping, epic)",
