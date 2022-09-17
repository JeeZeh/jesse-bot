import re
from copy import copy
from functools import wraps
from random import randint, random
from typing import Any, Optional

from discord.ext.commands import Bot, Cog, Command, Context, command  # type: ignore

from lib.api import firebase
from lib.utils import Constants, char_to_block, partition_message


async def batch_send(ctx: Context, to_send: str):
    for part in partition_message(to_send):
        await ctx.send(part)


class Text(Cog, description="Commands which mostly manipulate/send text"):  # type: ignore
    def __init__(self, bot: Bot):
        self.bot = bot
        self.pastas = list(firebase.database().child("pastas").get().val())

    def chainable(command: Any):
        """Used to indicate, and create, a chainable command. A chainable command is one
        which can be placed in a 'chain' of commands through which an initial message,
        and the subsequent output of each chained command, can be passed.

        **NOTE**: All commands that indicate chainable should take a single, un-interpreted
        argument `message: str` (i.e. args `self, ctx: Context, *, message: str`), or nothing
        (i.e. args `self, ctx: Context`). Any necessary parsing of the incoming message should be done
        inside the function itself. This is to maintain consistency between all chainable command APIs to
        ensure the chaining of commands works reliably.

        0. Commands "!a", "!b", "!c" etc. are all @chainable
        1. Message is received by the bot: "!a x -> !b -> !c -> ..."
        2. Command "!a" is run with message argument "x", returning result "y"
            - "x" is optional if the initial command does not require an incoming message
        3. Result "y" is now passed to the next command by modifying the remaining chain
        4. Bot is requested to process the message "!b y -> !c -> ..."
        5. The chaining process is repeated


        Args:
            command (Coroutine[Command]): The command that supports chaining.

        Returns:
            Coroutine[Command]: The underlying command, wrapped in the chainable function.
        """

        @wraps(command)
        async def wrapper(_self, ctx: Context, *args, **kwargs):
            # Get the message arg passed to the command. For all chains, there should be a message arg present,
            # but some commands that can be chained do not take input messages (text generators). For this,
            # we need to strip out the chains from the initial message and call the text generator by itself.
            # If we do not do this, we will try to call the generator with a message (the remaining chains),
            # and the bot will not invoke the command as the arguments do not match.
            message: str = kwargs.get("message", ctx.message.content[len(ctx.prefix) + len(ctx.invoked_with) :])

            # No chains (left), run the underlying command and return the result if the function didn't already reply
            if not message or " -> " not in message:
                result = await command(_self, ctx, *args, **kwargs)
                if result is not None:
                    return await batch_send(ctx, result)

            # Split message without the initial command (e.g. "fizz -> !bar -> !buzz") into (["fizz", "!bar", "!buzz"])
            first_message, *rest = message.split(" -> ")

            # Process the first command in the chain to get the output that should be piped to the next command
            # Here, we overwrite the message field of kwargs with the first message content in the chain (if present)
            new_kwargs = {**kwargs, "message": first_message} if "message" in kwargs else kwargs
            this_command_result = await command(_self, ctx, *args, **new_kwargs)

            # Get the next command in the chain and strip prefix if present
            next_command = rest.pop(0).strip()
            if next_command[0] == _self.bot.command_prefix:
                next_command = next_command[1:]

            # If next command is not valid, stop processing the chain and send the result of the first command
            next_command_ref: Optional[Command] = _self.bot.get_command(next_command)
            if not next_command_ref:
                return await batch_send(ctx, this_command_result)

            # Otherwise, take the result of the first command and call the next function
            # (which invokes this chainable wrapper again)
            remaining_message = " -> ".join([f"!{next_command} {this_command_result}"] + rest)
            message_copy = copy(ctx.message)
            message_copy.content = remaining_message

            await _self.bot.process_commands(message_copy)

        return wrapper

    @command(
        description="Inserts a clap emoji after each word of input e.g. boi 👏 you 👏 gonna 👏 catch 👏 these 👏 hands 👏",
        aliases=["c"],
    )
    @chainable
    async def clap(self, ctx: Context, *, message: str):
        return re.sub(r"\s+", " 👏 ", message)

    @command(
        description="The SpongeBob text i.e. alternate input text in upper and lower case",
        aliases=["m", "spongebob"],
    )
    @chainable
    async def mock(self, ctx: Context, *, message: str):
        upper = True
        out_chars = []

        for m in message:
            if random() > 0.2:
                upper = not upper

            out_chars.append(m.upper() if upper else m.lower())

        return "".join(out_chars)

    @command(description="Capitalises first letter of input e.g. What Are You Talking About")
    @chainable
    async def title(self, ctx: Context, *, message: str):
        return message.title()

    @command(
        description="Owo-ifies provided text: !owo 'try again' -> 'twy again'",
        aliases=["o"],
    )
    @chainable
    async def owo(self, ctx: Context, *, message: str):
        for match, replace in Constants.owo:
            message = re.sub(match, replace, message.lower())

        return message

    @command(
        description="Makes your message 🇧🇮🇬",
        aliases=["b", "emojify"],
    )
    @chainable
    async def big(self, ctx: Context, *, message: str):
        message = message.lower()

        out_chars = []

        for char in message:
            as_block = char_to_block(char)

            if as_block is not None:
                out_chars.append(as_block)

        return "  ".join(out_chars)

    @command(description="Gives a random copy-pasta from local database")
    @chainable
    async def pasta(self, ctx):
        pasta = self.pastas[randint(0, len(self.pastas) - 1)]

        return pasta

    @command(description="Roll some dice")
    async def roll(self, ctx, *, message: str):
        if not message.count("d") in {0, 1}:
            ctx.send("Bad")

        parts = message.split("d")

        if len(parts) == 2:
            rolls = int(parts[0])
            sides = int(parts[1])
        else:
            rolls = 1
            sides = int(parts[0])

        results = []

        for _ in range(rolls):
            results.append(randint(1, sides))

        wanted = f"You roll: {char_to_block(message)}"
        explanation = f" from `{'`, `'.join(map(str, results))}`" if rolls > 1 else ""
        outcome = f"Result: {char_to_block(str(sum(results)))}{explanation}"

        ctx.send(f"{wanted}\n{outcome}")


async def setup(bot):
   await bot.add_cog(Text(bot))
