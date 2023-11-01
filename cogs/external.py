from dataclasses import dataclass
from random import choice
from string import ascii_lowercase, digits
from typing import Optional

from discord.ext import commands
from discord.ext.commands.context import Context
from requests import post

from lib.config import SONG_TRANSLATE_DOMAINS
from lib.logger import logger
from lib.utils import secrets_disabled

SONGWHIP_URL = "https://songwhip.com/"


@dataclass
class SongwhipResponse:
    status: int
    link: Optional[str]
    name: str


class External(commands.Cog, description="Commands that talk to the outside world"):  # type: ignore
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_songwhip(self, url: str) -> SongwhipResponse:
        # curl --request POST --data '{"url":"MY_SOURCE_MUSIC_LINK"}'
        req = post(SONGWHIP_URL, json={"url": url})
        try:
            res_json = req.json()
            return SongwhipResponse(req.status_code, link=res_json.get("url"), name=res_json.get("name"))
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

    @commands.command(
        description="Provides cross-platform song link using Songwhip for the provided URL. "
        + f"Supported domains: {', '.join(SONG_TRANSLATE_DOMAINS)}"
    )
    async def song(
        self,
        ctx: Context,
        song: str = commands.parameter(description="A song link from one of the supported domains."),
    ):
        url = song.strip()
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
            try:
                thread = await ctx.message.create_thread(name=response.name)
                await thread.send(response.link)
            except:
                logger.error(f"Could not create thread from message id='{ctx.message.id}'", exc_info=True)
                await ctx.reply(f"Converted: {response.link}", suppress_embeds=True)

        return await ctx.message.remove_reaction("🔃", self.bot.user)


async def setup(bot):
    await bot.add_cog(External(bot))
