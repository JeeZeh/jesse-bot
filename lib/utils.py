from glob import glob
from os import remove, replace
from posixpath import abspath
from textwrap import wrap
from traceback import print_exc

import ffmpeg
from discord import Message

from lib.config import DISABLE_SECRETS_FOR_GUILDS, MAX_MESSAGE_LENGTH


class Constants:
    owo = [
        (r"n(?=[a|e|i|o|u]{1})", "ny"),
        ("r", "w"),
        ("ove", "uv"),
        ("l", "w"),
    ]

    regional_indicators = {
        "0": ":zero:",
        "1": ":one:",
        "2": ":two:",
        "3": ":three:",
        "4": ":four:",
        "5": ":five:",
        "6": ":six:",
        "7": ":seven:",
        "8": ":eight:",
        "9": ":nine:",
        "-": ":heavy_minus_sign:",
        " ": "  ",
    }


def batch(iterable, n=1):
    length = len(iterable)
    for ndx in range(0, length, n):
        yield iterable[ndx : min(ndx + n, length)]


def char_to_block(char: str):
    """Converts a character to block-emoji.

    Args:
        char (str): The character to be converted to emo ji

    Returns:
        str | None: Returns the block emoji version of the character, or None if not convertible
    """

    if char.isalpha():
        return f":regional_indicator_{char}:"

    return Constants.regional_indicators.get(char)


def partition_message(text: str):
    """Useful for breaking long messages (>2000 chars) into smaller message parts

    Args:
        text (str): text to be partitioned

    Returns:
        list[str]: a list of message parts
    """

    if len(text) <= 2000:
        return [text]

    escaped = text.replace("\n", "%newline%")
    wrapped = wrap(escaped, width=MAX_MESSAGE_LENGTH - 200)

    return [w.replace("%newline%", "\n") for w in wrapped]


def try_compress_video(filepath) -> str:
    # ffmpeg -i input.mp4 -vcodec libx264 -crf 20 output.mp4
    output_path = f"{filepath.split('.mp4')[0]}_ffmpeg.mp4"

    if glob(output_path):
        return output_path

    try:
        (
            ffmpeg.input(filepath)
            .output(
                output_path,
                vcodec="libx264",
                crf="35",
                preset="veryfast",
                acodec="copy",
                pix_fmt="yuv420p",
                loglevel="quiet",
            )
            .run()
        )
        replace(output_path, filepath)
        return filepath
    except:
        print_exc()
        return filepath


# TODO: Make per-server configurable commands
def secrets_disabled(message: Message):
    if hasattr(message, "guild") and message.guild is not None:
        return message.guild.id in DISABLE_SECRETS_FOR_GUILDS

    # Secrets are disabled in DMs by default
    return True


def cleanup_temp():
    for file in glob("./tmp/*.mp4"):
        remove(abspath(file))
