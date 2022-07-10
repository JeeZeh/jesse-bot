from enum import Enum
from glob import glob
from os import path
from pathlib import Path
from re import IGNORECASE, compile
from typing import Any, Callable, Coroutine, List, Optional, Tuple
from urllib import parse

from bs4 import BeautifulSoup
from discord import File, Message
from discord.errors import HTTPException
from discord.ext.commands.bot import Bot
from requests.api import get
from youtube_dl import YoutubeDL, utils

from lib.config import SPOTIFY_REDIRECT_URL, VIDEO_GRABBER_DOMAINS
from lib.data import firebase
from lib.logger import logger
from lib.utils import try_compress_video

text_secrets = {**firebase.database().child("text_secrets").get().val()}

regex_secrets = {
    compile(rf"^{k}$", flags=IGNORECASE): v for k, v in firebase.database().child("regex_secrets").get().val().items()
}


def spotify_redirect(message: Message) -> Optional[str]:
    urls = [line.strip() for line in message.content.splitlines() if line.startswith("https://open.spotify.com/")]

    to_send = []

    for url in urls:
        page = get(url)
        soup = BeautifulSoup(page.text, features="html.parser")
        title = soup.title.contents[0].split(" - ")[0]

        resource_type, resource_id = parse.urlparse(url).path.split("/")[1:]
        redirect_link = f"{SPOTIFY_REDIRECT_URL}?type={resource_type}&item={resource_id}"

        to_send.append(f"🎶 Open **{title}** in-app: {redirect_link}")

    if to_send:
        return "\n".join(to_send)

    return None


async def _send_video_file(bot: Bot, message: Message, path: str):
    try:
        await message.reply(file=File(path), content="📽️ Grabbed the video!")
        return await message.remove_reaction(member=bot.user, emoji="🔃")
    except HTTPException as he:
        await message.remove_reaction(member=bot.user, emoji="🔃")
        await message.add_reaction(emoji="❌")
        if he.status == 413:
            await message.reply("Video was too large to send :(")
        else:
            raise he


async def video_grabber(message: Message) -> Optional[str]:
    for domain in VIDEO_GRABBER_DOMAINS:
        if f"{domain}/" not in message.content:
            continue

        id = message.content.split(domain)[1].replace("/", "_").split("?")[0]

        with YoutubeDL({"outtmpl": f"tmp/{id}.%(ext)s", "f": "best[filesize<8M]"}) as ytdl:
            try:
                ytdl.download([message.content])
                await message.add_reaction(emoji="🔃")
                filepath = glob(f"../tmp/{id}.*")[0]

                # Compress videos greater than 7.5MB so they can be set by Discord regular user
                size = Path(path.abspath(filepath)).stat().st_size / (1024 * 1000)
                if size > 7.5:
                    filepath = try_compress_video(filepath)

                return path.abspath(filepath)
            except utils.DownloadError as de:
                logger.warn(de)
                raise de

    return None


def ligma(message: Message) -> Optional[str]:
    words = message.content.split()
    if not 1 < len(words) < 8:
        return None

    if words[0].lower().replace("'", "") == "whats":
        return f"{' '.join(words[1:])} balls lmao".capitalize()

    return None


def check_text_secrets(content: str) -> Optional[str]:
    for regex, response in regex_secrets.items():
        if regex.search(content) is not None:
            return response

    for text, response in text_secrets.items():
        if text in content:
            return response

    return None


class SpecialType(Enum):
    VIDEO = 1
    TEXT = 2


SpecialTextFunc = Callable[[Message], Optional[str]]
SpecialVideoFunc = Callable[[Message], Coroutine[Any, Any, Optional[str]]]


async def check_specials(content: Message) -> Optional[Tuple[str, SpecialType]]:
    text_specials: List[SpecialTextFunc] = [ligma]
    video_specials: List[SpecialVideoFunc] = [video_grabber]

    for text_special in text_specials:
        check = text_special(content)
        if check is not None:
            return check, SpecialType.TEXT

    for video_special in video_specials:
        check = await video_special(content)
        if check is not None:
            return check, SpecialType.VIDEO

    return None


async def check_passive(bot: Bot, message: Message):
    if bot.user.id == message.author.id:
        return

    await bot.get_cog("Notifications").check_triggers(message)

    if special := await check_specials(message):
        ret_val, special_type = special
        if special_type is SpecialType.VIDEO:
            return await _send_video_file(bot, message, ret_val)
        else:
            return await message.channel.send(ret_val)

    if text_secret := check_text_secrets(message.content):
        return await message.channel.send(text_secret)
