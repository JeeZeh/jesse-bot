from dataclasses import dataclass
from enum import Enum
from random import choice
from string import ascii_lowercase, digits
from typing import Optional

from discord.ext import commands
from discord.ext.commands.context import Context
from requests import post
from lib.logger import logger
from lib.config import SONG_TRANSLATE_DOMAINS

from lib.utils import secrets_disabled

SONGWHIP_URL = "https://songwhip.com/"


@dataclass
class SongwhipResponse:
    status: int
    link: Optional[str]


class External(commands.Cog, description="Commands that talk to the outside world"):  # type: ignore
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_songwhip(self, url: str) -> SongwhipResponse:
        # curl --request POST --data '{"url":"MY_SOURCE_MUSIC_LINK"}'
        req = post(SONGWHIP_URL, json={"url": url})
        try:
            return SongwhipResponse(req.status_code, link=req.json().get("url"))
        except:
            logger.error("Failed to get link from Songwhip", exc_info=True)
            return SongwhipResponse(req.status_code)

    @commands.command(description="Gives a random image from prnt.sc")
    async def prntsc(self, ctx: Context):
        if secrets_disabled(ctx.message):
            return await ctx.reply("`prntsc` is disabled for this guild/chat as results are potentially NSFW")

        prefix = choice("3456789abcdefghij")
        suffix = "".join(choice(digits + ascii_lowercase) for _ in range(5))

        await ctx.send(f"https://prnt.sc/{prefix}{suffix}")

    @commands.command(description="Provides cross-platform song link using Songwhip for the provided URL.")
    async def song(self, ctx: Context, arg: str):
        url = arg.strip()
        if not any(domain in url for domain in SONG_TRANSLATE_DOMAINS):
            return await ctx.reply(f"Unsupported link. Supported links: {', '.join(SONG_TRANSLATE_DOMAINS)}")

        await ctx.message.add_reaction("🔃")
        response = self.get_songwhip(url)
        if response.status == 429:
            await ctx.message.add_reaction("⏳")
            await ctx.reply("Rate-limited by Songwhip, please try again later.")
        elif response.status != 200:
            await ctx.message.add_reaction("❌")
            await ctx.message.author.send(
                f"An unknown error occurred when converting your link with `!song`: {url}", suppress_embeds=True
            )
        else:
            await ctx.message.add_reaction("✅")
            await ctx.reply(f"Converted: {response.link}")

        return await ctx.message.remove_reaction("🔃", self.bot.user)


async def setup(bot):
    await bot.add_cog(External(bot))
