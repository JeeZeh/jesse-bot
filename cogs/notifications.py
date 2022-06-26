import asyncio
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from textwrap import dedent
from time import time
from typing import Optional

from discord import Member, Message
from discord.channel import TextChannel, VoiceChannel
from discord.errors import HTTPException
from discord.ext.commands import Cog, command, group  # type: ignore
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context
from discord.invite import Invite

from lib.data import firebase
from lib.logger import logger


@dataclass
class VoiceMovement:
    left: Optional[VoiceChannel] = None
    joined: Optional[VoiceChannel] = None
    is_first_joiner = False


@dataclass
class Helpers:
    VC_DELAY = 60
    SUB_NOTIF = dedent(
        """
            **{user}** joined a voice channel you're subscribed to!
            _P.S. - I'll wait an hour before notifying you again of any new voice sessions!_
            {invite}

            To unsubscribe from these notifications, type `!unsubscribe {channel_id}`
        """
    )
    TRIGGER_HELP = dedent(
        """
            JesseBot can help you feel safer in servers by letting you know if any
            text-based triggers are mentioned in channels you both share. The bot
            will watch for mentions of your trigger(s) in messages and notify you
            if any are spotted (the actual trigger is censored in the notification).

            NOTE: This does not detect triggers in links, images, embeds, videos, voice, etc.
            Only mentions of a trigger, in the text of a message, can be detected.

            You can add single-word triggers (separated by a space) or whole-phrase triggers
            (wrapped in "double quotes" to treat as a single trigger).
              - To view your saved triggers, use the "!triggers list" command
              - To add a trigger, use the "!triggers add"
              - To remove a trigger, use the "!triggers remove" command
        """
    )
    TRIGGER_NOTIF = dedent(
        """
            Hey!

            A trigger ({censored}) you've registered with me was just mentioned in `#{channel}` (server: `{server}`).
            Here's the link to the message if you'd like to engage with it now or later: {link}.

            _I'll wait an hour before notifying you again of any other triggers._
        """
    )
    NOTIFICATION_COOLDOWN = 3600


class Notifications(Cog):
    local_triggers: list[tuple[re.Pattern, list[str]]] = []
    subscribers: dict[str, list[str]] = defaultdict(list)
    subscriber_notified: dict[str, float] = defaultdict(float)
    trigger_notified: dict[str, float] = defaultdict(float)

    def __init__(self, bot: Bot):
        self.bot = bot

    async def load_subscribers(self):
        self.subscribers = defaultdict(list)
        self.subscribers.update(**firebase.database().child("subscribers").get().val())

    async def update_subscribers(self):
        firebase.database().child("subscribers").update(self.subscribers)

    async def sync_triggers(self):
        """
        Local trigger format:
          List[Tuple[RegExp, List[str]]]

        Remote trigger format:
          Dict[str, Dict[str, str]]
        """
        remote_triggers: dict[str, dict[str, str]] = firebase.database().child("triggers").get().val()
        self.local_triggers = []

        for trigger_phrase, users in remote_triggers.items():
            pattern = re.compile(rf"\b{trigger_phrase}\b")
            user_ids = list(users.keys())
            self.local_triggers.append((pattern, user_ids))

    def get_within_guild_movement(self, before, after) -> VoiceMovement:
        movement = VoiceMovement(before.channel, after.channel)
        if movement.joined is not None and len(movement.joined.members) == 1:
            movement.is_first_joiner = True

        return movement

    async def channel_still_populated(self, channel: VoiceChannel):
        await asyncio.sleep(Helpers.VC_DELAY)
        if len(channel.members) >= 1:
            return True

        return False

    async def maybe_notify_subscribers(self, joiner: Member, channel: VoiceChannel):
        if not await self.channel_still_populated(channel):
            return

        members_in_channel = set(map(lambda x: str(x.id), self.bot.get_channel(channel.id).members))
        for subscriber in self.subscribers.get(str(channel.id), []):
            if str(joiner.id) == subscriber:
                continue

            if subscriber in members_in_channel:
                continue

            logger.debug("Notifying user", self.bot.get_user(subscriber))
            # Only notify if we haven't notified the subscriber in over an hour
            if time() - self.subscriber_notified[subscriber] < Helpers.NOTIFICATION_COOLDOWN:
                continue

            invite: Optional[Invite] = None
            try:
                invite = await channel.create_invite(
                    reason=f"{joiner.display_name} joined a voice channel you're subscribed to",
                    max_age=14400,
                    max_uses=1,
                )
            except HTTPException:
                logger.exception(f"Maybe no permission to create an invite for {channel.name}?", exc_info=True)
                return

            user = self.bot.get_user(int(subscriber))  # Only treat user IDs as ints for API calls

            if subscriber is not None and invite is not None:
                await user.send(
                    Helpers.SUB_NOTIF.format(
                        user=joiner.display_name,
                        invite=invite.url,
                        channel_id=channel.id,
                    )
                )

            self.subscriber_notified[subscriber] = time()

    def get_channels_from_str(self, ids: str) -> list[VoiceChannel]:
        channel_ids = map(int, filter(str.isnumeric, map(str.strip, ids.split())))
        ids_as_channels = map(self.bot.get_channel, channel_ids)
        return [channel for channel in ids_as_channels if channel is not None and isinstance(channel, VoiceChannel)]

    def format_voice_channel_list(self, channels: list[VoiceChannel]):
        return "\n".join([f"  - `{channel.id}` - {channel.name} ({channel.guild.name})" for channel in channels])

    @command(description="Get notified when someone joins a voice channel: `!subscribe CHANNEL_ID_HERE`")
    async def subscribe(self, ctx: Context, *, message):
        to_subscribe = str(ctx.author.id)
        channels = self.get_channels_from_str(message)
        new_subscriptions: list[VoiceChannel] = []

        for channel in channels:
            if to_subscribe not in self.subscribers[str(channel.id)]:
                new_subscriptions.append(channel)
                self.subscribers[str(channel.id)].append(to_subscribe)

        if new_subscriptions:
            await self.update_subscribers()
            subscription_info = self.format_voice_channel_list(new_subscriptions)
            await ctx.send(f"You have been subscribed to:\n{subscription_info}")
        else:
            await ctx.send("You were not subscribed to any new channels")

    @command(description="Lets you unsubscribe from one or more voice channels: `!unsubscribe CHANNEL_ID_HERE`")
    async def unsubscribe(self, ctx, *, message):
        to_unsubscribe = str(ctx.author.id)
        channels = self.get_channels_from_str(message)
        removed = []

        for channel in channels:
            if to_unsubscribe in self.subscribers[str(channel.id)]:
                self.subscribers[str(channel.id)] = list(
                    filter(
                        lambda sub: sub != to_unsubscribe,
                        self.subscribers[str(channel.id)],
                    )
                )

                removed.append(channel)

        if removed:
            await self.update_subscribers()
            removed_info = self.format_voice_channel_list(removed)
            await ctx.send(f"You have been unsubscribed from:\n{removed_info}")
        else:
            await ctx.send("You weren't subscribed to any of those channels")

    @command(description="Lists voice channels you are subscribed to")
    async def subscribed(self, ctx: Context):
        sub = str(ctx.author.id)
        vc_ids = (vc_id for vc_id, subs in self.subscribers.items() if sub in subs)
        subbed_channels = self.format_voice_channel_list(self.get_channels_from_str(" ".join(vc_ids)))

        if subbed_channels:
            await ctx.send(f"You are subscribed to:\n{subbed_channels}")
        else:
            await ctx.send("You are not subscribed to any channels")

    def member_joined_a_channel(self, member: Member, before, after) -> Optional[VoiceChannel]:
        # Check for actual channel movement
        if after.channel is None or before.channel == after.channel:
            return None

        # Check user's current VC is the one they joined
        if member.voice is None or member.voice.channel != after.channel:
            return None

        # Check user is the only person in the channel right now
        if len(member.voice.channel.members) != 1:
            return None

        return after.channel

    @Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # If they joined a new channel and didn't come from another in the guild
        if channel := self.member_joined_a_channel(member, before, after):
            await self.maybe_notify_subscribers(member, channel)

    @group(name="triggers", pass_context=True, help=Helpers.TRIGGER_HELP, aliases=["trigger"])
    async def triggers(self, ctx: Context):
        print(ctx.invoked_subcommand)
        if ctx.invoked_subcommand is self.triggers:
            await ctx.reply(
                f"Unknown subcommand, available commands for `!trigger` are `{', '.join(self.triggers.commands)}`"
            )

    @triggers.command(
        description="Add one or more triggers to be tracked across servers you share with JesseBot",
        help="Add one or more triggers to be tracked across servers you share with JesseBot",
    )
    async def add(self, ctx: Context, *args):
        """
        Triggers are stored as a mapping of `triggers => [users]` so we can perform quick
        lookup of triggers against messages.
        """
        timestamp = datetime.now().isoformat()
        user_id = str(ctx.author.id)
        for trigger in args:
            firebase.database().child("triggers").child(trigger).child(user_id).set(timestamp)

        await self.sync_triggers()
        await ctx.reply(f"Successfully added {len(args)} trigger(s)")

    @triggers.command(
        description="Remove one or more triggers registered with JesseBot",
        help="Remove one or more triggers registered with JesseBot",
    )
    async def remove(self, ctx: Context, *args):
        user_id = str(ctx.author.id)
        for trigger in args:
            firebase.database().child("triggers").child(trigger).child(user_id).remove()

        await self.sync_triggers()
        await ctx.reply(f"Successfully removed {len(args)} trigger(s)")

    @triggers.command(
        description="List triggers registered with JesseBot",
        help="List triggers registered with JesseBot",
    )
    async def list(self, ctx: Context):
        user_id = str(ctx.author.id)

        registered_triggers = []
        triggers = firebase.database().child("triggers").get().val() or {}
        for trigger, users in triggers.items():
            if user_id in users:
                registered_triggers.append(trigger)

        if not registered_triggers:
            await ctx.reply("No regisered triggers. Type `!help triggers` to see how to manage triggers")
        else:
            print(registered_triggers)
            trigger_list = "\n".join(f" - {t}" for t in map(self.censor_phrase, registered_triggers))
            await ctx.reply(f"You have {len(registered_triggers)} registered trigger(s):\n{trigger_list}")

    async def check_triggers(self, message: Message):
        # Only check for triggers in TextChannels
        if not isinstance(message.channel, TextChannel):
            return

        channel: TextChannel = message.channel

        for trigger, users in self.local_triggers:
            if (match := trigger.search(message.content)) is not None:
                start, end = match.span()
                phrase = message.content[start:end]
                for user_id in users:
                    last_notified = self.trigger_notified.get(user_id, 0)
                    user = self.bot.get_user(int(user_id))

                    # Don't notify if we can't find user (maybe deleted, changed ID, etc.)
                    if user is None:
                        continue

                    # Don't notify of triggers in trigger commands
                    if message.content.startswith("!triggers"):
                        continue

                    # Only apply notification filters to non-admins (for testing)
                    if not self.bot.is_owner(message.author):

                        # Don't notify user if they've been notified within the last cooldown period
                        if time() - last_notified < Helpers.NOTIFICATION_COOLDOWN:
                            continue

                        # Don't notify if the user cannot see the channel in which the trigger was mentioned.
                        # Only TextChannels have members, Threads do not.
                        if isinstance(channel, TextChannel):
                            if user_id not in map(lambda m: str(m.id), channel.members):
                                continue

                        # Don't notify a user about their own message
                        if str(message.author.id) == user_id:
                            continue

                    notification = Helpers.TRIGGER_NOTIF.format(
                        censored=self.censor_phrase(phrase, True),
                        channel=channel.name,
                        server=channel.guild.name,
                        link=message.jump_url,
                    )
                    if user := self.bot.get_user(int(user_id)):
                        await user.send(notification)
                        self.trigger_notified[user_id] = time()

    @staticmethod
    def censor_phrase(phrase: str, full_censor=False):
        parts = []
        for word in phrase.split():
            if full_censor or len(word) <= 3:
                parts.append(f"||{word}||")
            else:
                parts.append(f"{word[0]}||{word[1:-1]}||{word[-1]}")

        return " ".join(parts)


def setup(bot):
    bot.add_cog(Notifications(bot))
