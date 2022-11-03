import asyncio
import audioop as ao
from pathlib import Path
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, Optional, Set

import numpy as np
from discord import AudioSource, FFmpegPCMAudio, Member, PCMVolumeTransformer
from discord.channel import VocalGuildChannel
from discord.ext.commands import Cog, command, is_owner  # type: ignore
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context
from discord.member import VoiceState
from discord.message import Message
from discord.voice_client import VoiceClient

from lib.api import firebase


def current_milli_time():
    return round(time.time() * 1000)


SAMPLE_READ_SIZE = 3840
SAMPLE_WIDTH_BYTES = 2


@dataclass
class Helpers:
    BAD_JOIN = "You have to be in a voice channel in this server for me to join it"
    BAD_LEAVE = "I'm not in a voice channel in this server"


class Operators:
    @staticmethod
    def combine_samples(a: Optional[bytes] = None, b: Optional[bytes] = None) -> bytes:
        if a and b:
            return ao.add(a, b, SAMPLE_WIDTH_BYTES)

        return a or b or b""


@dataclass
class Buffer:
    data: np.ndarray
    ptr: int = 0

    # effects = field(default_factory=list)

    def read(self) -> bytes:
        if self.ptr < self.data.size:
            self.ptr += SAMPLE_READ_SIZE
            return bytes(self.data[self.ptr - SAMPLE_READ_SIZE : self.ptr])

        return b""

    def reverse(self):
        self.data = np.array(bytearray(ao.reverse(bytes(self.data), SAMPLE_WIDTH_BYTES)), dtype=np.int8)
        self.ptr += ((self.data.size // 2) - self.ptr) * 2


class AudioBufferWrapper(AudioSource):
    def __init__(self, buffer: Buffer):
        self.buffer = buffer

    def _process(self):
        return super()._process()

    def cleanup(self):
        pass

    @staticmethod
    def from_file(path):
        data = FFmpegPCMAudio(path, before_options="-guess_layout_max 0", stderr=subprocess.PIPE)

        # Copy buffer data from real audio source to an ndarray
        buffer_data: bytearray = []
        while next_ := data.read():
            buffer_data += bytearray(next_)

        new_wrapper_instance = AudioBufferWrapper(Buffer(np.array(buffer_data, dtype=np.int8)))
        data.cleanup()
        buffer_data = None

        return new_wrapper_instance

    @staticmethod
    def from_buffer_data(buffer_data: np.ndarray):
        return AudioBufferWrapper(Buffer(buffer_data))

    def read(self):
        return self.buffer.read()

    def reverse(self):
        self.buffer.reverse()

    def __add__(self, other):
        """Combine this AudioBufferWrapper with another. Adds the audio buffers in each
        wrapper together by merging samples of both. Takes the largest of the two buffers
        as the reference buffer and layers the smaller buffer on top of this.

        Args:
            other (AudioBufferWrapper): The other AudioBufferWrapper to be added to this one.
        """
        # Start the copying some samples ahead to allow for processing delay (~40ms)
        initial_ptr = self.buffer.ptr + SAMPLE_READ_SIZE * 2

        data_a = self.buffer.data[initial_ptr:]
        data_b = other.buffer.data

        # TODO: Tidy this up. There must be a simpler and/or more efficient way to do this with Numpy
        if data_a.size < data_b.size:
            b_overlap, b_extra = data_b[: data_a.size], data_b[data_a.size :]
            new_data = np.append(
                np.array(bytearray(Operators.combine_samples(bytes(data_a), bytes(b_overlap))), dtype=np.int8),
                b_extra,
            )
        elif data_b.size < data_a.size:
            a_overlap, a_extra = data_a[: data_b.size], data_a[data_b.size :]
            new_data = np.append(
                np.array(bytearray(Operators.combine_samples(bytes(a_overlap), bytes(data_b))), dtype=np.int8),
                a_extra,
            )
        else:
            new_data = np.array(bytearray(Operators.combine_samples(bytes(data_a), bytes(data_b))), dtype=np.int8)

        self.buffer.data = np.append(
            self.buffer.data[:initial_ptr],
            new_data,
        )

        # Manually clear to avoid GC?
        new_data = None


class Voice(Cog, description="Commands related to voice"):  # type: ignore
    voice_client: Optional[VoiceClient] = None
    voice_secrets: Dict[str, str] = {}
    cached_voice_secrets: Dict[str, np.ndarray] = {}

    def __init__(self, bot: Bot):
        self.bot = bot
        self._update_secrets()

    @property
    def client_source(self) -> Optional[AudioBufferWrapper]:
        if not self.voice_client:
            return None

        if self.voice_client._player is not None:
            if isinstance(self.voice_client._player.source, PCMVolumeTransformer):
                return self.voice_client._player.source.original

        return None

    def _update_secrets(self) -> Set[str]:
        before: set[str] = set(self.voice_secrets)
        self.voice_secrets = firebase.database().child("secrets").get().val()
        self.cached_voice_secrets = {}

        return set(self.voice_secrets) - before

    async def join_in_response(self, message) -> bool:
        """Tries to join the voice channel of the message author.

        Args:
            message (discord.Message): Message object.

        Returns:
            bool: True if the bot joined a voice channel.
        """

        member: Member = message.author

        # User not in VC
        if member.voice is None or member.voice.channel is None:
            return False

        voice_channel: VocalGuildChannel = member.voice.channel

        # Bot needs to join VC?
        if self.voice_client is None:
            self.voice_client = await voice_channel.connect()

        # User not in the same VC as bot
        if voice_channel != self.voice_client.channel:
            return False

        return True

    def _play(self, source: AudioBufferWrapper):
        if self.voice_client is None:
            return

        self.voice_client.stop()
        self.voice_client.play(PCMVolumeTransformer(source, 0.5))

    def _download_missing_sound_file(self, path: str) -> str:
        """Downloads a missing sound file from firebase and returns the local
        storage location.

        Args:
            path (str): Firebase path.

        Returns:
            str: Location of locally downloaded file.
        """
        filename = path.split("/")[-1]
        location = Path("tmp") / filename
        print(f"Downloading missing file '{location}'...")
        firebase.storage().child(path).download(str(location), filename)

        return location

    def _get_audio_wrapper_from_sound_name(self, name: str) -> Optional[AudioBufferWrapper]:
        """Attempts to retrieve the audio buffer for a given sound name by:
            1. Checking if it is a known voice_secret
            2. Checking if it is already cached
            3. Downloading from Firebase and caching the buffer data

        Args:
            name (str): Name of the sound to be played.

        Returns:
            Optional[np.ndarray]: Buffer data of the sound, if found.
        """

        path = self.voice_secrets.get(name)

        if path is None:
            return None

        if (buffer_data := self.cached_voice_secrets.get(path)) is not None:
            return AudioBufferWrapper(Buffer(buffer_data))

        location = self._download_missing_sound_file(path)
        audio_wrapper = AudioBufferWrapper.from_file(location)
        self.cached_voice_secrets[path] = audio_wrapper.buffer.data.copy()

        return audio_wrapper

    async def play_sound_by_file_name(self, message, requested: str, stack=False, auto_join=True):
        """Tries to play an audio file by its requested name. Allows for stacking audio
        if prefix is included in original message (indicated by stack=True).

        Args:
            message (discord.Message): Message object
            requested (str): The requested sound file, by secret name.
            stack (bool, optional): Play the requested file on top of an already-playing sound. Defaults to False.
            auto_join (bool, optional): Should the bot join in response to the request. Defaults to True.
        """

        audio_wrapper = self._get_audio_wrapper_from_sound_name(requested)
        if audio_wrapper is None:
            return

        # Try join VC
        if auto_join and not await self.join_in_response(message):
            return
        elif not auto_join and self.voice_client is None:
            return

        if not stack or self.voice_client is None or not self.voice_client.is_playing():
            # New file
            self._play(audio_wrapper)
        elif self.client_source is not None:
            # Combine the existing (playing) audio buffer with the buffer of the new file
            self.client_source + audio_wrapper

    async def apply_audio_operation_from_message(self, message: Message):
        """Entrypoint to filtering/adding effects to currently-playing audio.

        Currently only supports reversing the playing audio.

        Args:
            message (Message): The message which may contain a filter to apply.
        """
        # Not in VC, abort.
        if self.voice_client is None:
            return

        op = message.content[1:]

        if op.startswith("rev") and self.client_source is not None:
            self.client_source.reverse()

    async def check_for_voice_secret_triggers(self, message):
        if len(message.content) == 0:
            return

        if message.content[0] == "&":
            await self.play_sound_by_file_name(message, message.content[1:], stack=True)
        elif message.content[0] == "+":
            await self.apply_audio_operation_from_message(message)
        else:
            await self.play_sound_by_file_name(message, message.content)

    @Cog.listener()
    async def on_message(self, message: Message):
        await self.check_for_voice_secret_triggers(message)

    @is_owner()
    @command(description="Runs an audio test")
    async def audio_test(self, ctx: Context, loops=1, all=False, sleep=0.01):
        sent = None
        await asyncio.sleep(1)

        played = 0
        if all:
            clamped = min(20, loops)
            sent = await ctx.send(f"Running all sounds audio test 🎧 ({clamped} times(s))")
            for _ in range(min(20, loops)):
                await asyncio.sleep(sleep)
                for secret in self.voice_secrets:
                    played += 1
                    await self.play_sound_by_file_name(ctx.message, secret, stack=True, auto_join=False)
        else:
            clamped = min(200, loops)
            sent = await ctx.send(f"Running stacked audio test 🎧 ({clamped} times(s))")
            for _ in range(clamped):
                await asyncio.sleep(sleep)
                await self.play_sound_by_file_name(ctx.message, "50cal", stack=True, auto_join=False)
                await self.play_sound_by_file_name(ctx.message, "mute", stack=True, auto_join=False)
                played += 2

        await sent.reply(f"Test complete, played {played} sounds")

    @command(aliases=["j"], description="Joins a voice channel if the user is in one")
    async def join(self, ctx: Context):
        member: Member = ctx.author
        voice_state: Optional[VoiceState] = member.voice

        if voice_state is None:
            await ctx.send(Helpers.BAD_JOIN)
            return

        voice_channel: Optional[VocalGuildChannel] = voice_state.channel

        if voice_channel is None or voice_channel.guild != ctx.guild:
            await ctx.send(Helpers.BAD_JOIN)
            return

        self.voice_client = await voice_channel.connect()

    @command(
        aliases=["l"],
        description="Leaves a voice channel if the user is in the same server",
    )
    async def leave(self, ctx: Context):
        member: Member = ctx.author

        if self.voice_client is None or self.voice_client.guild != member.guild:
            await ctx.send(Helpers.BAD_LEAVE)
            return

        await self.voice_client.disconnect()
        self.voice_client = None

    @command(description="Lists the secret voice commands")
    async def secrets(self, ctx: Context):
        commands = sorted([f"`{s}`" for s in self.voice_secrets])
        await ctx.send("\n".join(commands))

    @command(description="Updates the local voice secrets")
    async def update_secrets(self, ctx: Context):
        if diff := self._update_secrets():
            added_commands = ", ".join(f"`{d}`" for d in diff)
            await ctx.send(f"Added new commands: {added_commands}")
        else:
            await ctx.send("No commands were added.")

    async def leave_if_alone(self, before, after):
        if (
            self.voice_client is not None
            and self.voice_client.channel in [before.channel, after.channel]
            and len(self.voice_client.channel.members) == 1
            and self.voice_client.channel.members[0].id == self.bot.user.id
        ):
            self.voice_client = await self.voice_client.disconnect()

    @Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        await self.leave_if_alone(before, after)


async def setup(bot):
    await bot.add_cog(Voice(bot))
