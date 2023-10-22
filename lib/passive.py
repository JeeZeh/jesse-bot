from enum import Enum
from glob import glob
from os import path
from random import choice
from re import IGNORECASE, compile
from string import ascii_letters
from typing import Any, Callable, Coroutine, List, Optional, Tuple

import isodate
import validators
from discord import File, Message
from discord.errors import HTTPException
from discord.ext.commands.bot import Bot
from yt_dlp import YoutubeDL, utils

from lib.api import dynamodb, spotify, youtube
from lib.config import COMMAND_PREFIX, SPOTIFY_REDIRECT_URL, VIDEO_GRABBER_DOMAINS
from lib.logger import logger
from lib.utils import secrets_disabled, try_compress_video

text_secrets = dynamodb.get_item(Key={"id": "text_secrets"}).get("Item", {})

regex_secrets = {
    compile(rf"^{k}$", flags=IGNORECASE): v
    for k, v in dynamodb.get_item(Key={"id": "regex_secrets"}).get("Item", {}).items()
}
SPOTIFY_URL_IDENTIFIER = "open.spotify.com"
YOUTUBE_URL_PREFIX = "https://youtu.be"


class SpecialType(Enum):
    VIDEO = 1
    TEXT = 2


AwaitableSpecialFunc = Callable[[Message], Coroutine[Any, Any, Optional[str]]]


def spotify_redirect(message: Message) -> Optional[str]:
    urls = [line.strip() for line in message.content.splitlines() if SPOTIFY_URL_IDENTIFIER in line]

    to_send = []

    for url in urls:
        track = spotify.track(url)
        redirect_link = f"{SPOTIFY_REDIRECT_URL}?type={track['type']}&item={track['id']}"

        to_send.append(f"🎶 Open **{track['name']}** in-app: {redirect_link}")

    if to_send:
        return "\n".join(to_send)

    return None


def get_spotify_track_info_from_url(url: str) -> Optional[Tuple[str, str, int]]:
    if SPOTIFY_URL_IDENTIFIER not in url:
        return None

    track = spotify.track(url)
    return track["artists"][0]["name"], track["name"], track["duration_ms"] // 1000


def try_match_spotify_track_for_youtube_video(url: str):
    # Not sure if we should do this, video -> track is ambiguous (might not be a song)
    pass


def try_match_youtube_video_for_spotify_track(url: str) -> Optional[str]:
    track_info = get_spotify_track_info_from_url(url)
    if not track_info:
        logger.warn(f"No track info found for Spotify URL: {url}")
        return None

    artist, title, target_seconds = track_info

    search_results = (
        youtube.search()
        .list(
            q=f"{artist} - {title}",
            part="snippet",
            maxResults=3,
            type="video",
            topicId="/m/04rlf",
        )
        .execute()
    )

    # Filter by videos without "Album" in title
    video_ids_to_search = [item["id"]["videoId"] for item in search_results["items"]]

    video_results = (
        youtube.videos()
        .list(
            id=",".join(video_ids_to_search),
            part="id,contentDetails",
        )
        .execute()
    )
    video_ids_and_durations: List[Tuple[str, int]] = [
        (str(item["id"]), isodate.parse_duration(item["contentDetails"]["duration"]).total_seconds())
        for item in video_results["items"]
    ]

    # Filter by videos within target duration length +/- 10%
    possible_videos = [
        (_id, duration)
        for _id, duration in video_ids_and_durations
        if target_seconds * 0.9 <= duration <= target_seconds * 1.1
    ]

    if possible_videos:
        return possible_videos[0][0]

    return None


async def spotify_youtube_converter(message: Message) -> Optional[str]:
    if SPOTIFY_URL_IDENTIFIER in message.content:
        video_id = try_match_youtube_video_for_spotify_track(message.content)
        if video_id:
            return f"I think I found a YouTube link for this: {YOUTUBE_URL_PREFIX}/{video_id}"

    return None


async def _send_video_file(bot: Bot, message: Message, path: str):
    try:
        await message.reply(file=File(path), content="📽️ Grabbed the video!")
        return await message.add_reaction("✅")
    except HTTPException as he:
        if he.status == 413:
            await message.reply("Video was too large to send :(")
        else:
            raise he


async def video_grabber(message: Message) -> Optional[str]:
    link = message.content.strip()
    for domain in VIDEO_GRABBER_DOMAINS:
        if domain not in link:
            continue
        if not validators.url(link):
            continue

        id = "jessebot_" + "".join(choice(ascii_letters) for _ in range(8))

        with YoutubeDL({"outtmpl": f"tmp/{id}.%(ext)s", "f": "best[filesize<8M]"}) as ytdl:
            try:
                await message.add_reaction("🔃")
                ytdl.download([link])
                filepath = glob(f"./tmp/{id}.*")[0]

                # Compress videos greater than 7.5MB so they can be set by Discord regular user
                filepath = try_compress_video(filepath)

                return path.abspath(filepath)
            except utils.DownloadError as de:
                logger.warn(de)
                raise de

    return None


async def ligma(message: Message) -> Optional[str]:
    if secrets_disabled(message):
        return None

    words = message.content.split()
    if not 1 < len(words) < 8:
        return None

    if words[0].lower().replace("'", "") == "whats":
        return f"{' '.join(words[1:])} balls lmao".capitalize()

    return None


async def good_bot(message: Message):
    if message.content.strip().lower().startswith("good bot"):
        await message.add_reaction("💖")

    return None


def check_text_secrets(content: str) -> Optional[str]:
    for regex, response in regex_secrets.items():
        if regex.search(content) is not None:
            return response

    for text, response in text_secrets.items():
        if text in content:
            return response

    return None


async def check_specials(content: Message) -> Optional[Tuple[str, SpecialType]]:
    text_specials: List[AwaitableSpecialFunc] = [ligma, good_bot, spotify_youtube_converter]
    video_specials: List[AwaitableSpecialFunc] = [video_grabber]

    for text_special in text_specials:
        check = await text_special(content)
        if check is not None:
            return check, SpecialType.TEXT

    for video_special in video_specials:
        check = await video_special(content)
        if check is not None:
            return check, SpecialType.VIDEO

    return None


async def check_passive(bot: Bot, message: Message):
    # Don't check commands
    if message.content.startswith(COMMAND_PREFIX):
        return None

    if bot.user and bot.user.id == message.author.id:
        return

    special = None
    try:
        if special := await check_specials(message):
            ret_val, special_type = special
            if special_type is SpecialType.VIDEO:
                await _send_video_file(bot, message, ret_val)
            elif special_type is SpecialType.TEXT and ret_val:
                await message.reply(ret_val, suppress_embeds=True)
    except:
        await message.add_reaction("❌")
    finally:
        if bot.user:
            await message.remove_reaction("🔃", bot.user)
        # We already processed this message
        if special:
            return

    if text_secret := check_text_secrets(message.content):
        return await message.channel.send(text_secret)
