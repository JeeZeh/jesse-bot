import discord
from discord.ext.commands import Bot as _Bot
from discord_slash import SlashCommand

from cogs.passive import check_passive
from lib.config import COG_EXTENSIONS, config
from lib.utils import cleanup

intents = discord.Intents.default()
intents.typing = False
intents.members = True


class Bot(_Bot):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        await self.get_cog("Notifications").load_subscribers()
        await self.get_cog("Notifications").sync_triggers()

    async def on_message(self, message):
        await check_passive(self, message)
        return await super().on_message(message)


token = config.get("token")

if not token:
    print("No token found!")
    exit()

bot = Bot(
    command_prefix="!",
    description="Jesse's custom bot, rewritten in Python!",
    intents=intents,
)

slash = SlashCommand(bot, sync_commands=True, override_type=True)

if __name__ == "__main__":
    cleanup()
    for extension in COG_EXTENSIONS:
        bot.load_extension(f"cogs.{extension}")
    bot.run(token)

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
