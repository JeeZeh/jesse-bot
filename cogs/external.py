from random import choice
from string import ascii_lowercase, digits

from discord.ext import commands
from discord.ext.commands.context import Context


class External(commands.Cog, description="Commands that talk to the outside world"):  # type: ignore
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(description="Gives a random image from prnt.sc")
    async def prntsc(self, ctx: Context):
        prefix = choice("3456789abcdefghij")
        suffix = "".join(choice(digits + ascii_lowercase) for _ in range(5))

        await ctx.send(f"https://prnt.sc/{prefix}{suffix}")


async def setup(bot):
    await bot.add_cog(External(bot))
