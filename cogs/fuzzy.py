import discord
import rapidfuzz
from discord.ext import commands
from utils.global_utils import copy_context
from typing import List, Tuple, Optional
from asyncio import TimeoutError


class Levenshtein(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_all_runnable_commands(self, ctx: commands.Context, include_aliases=False) -> List[str]:
        """Returns a list of command names that the user can run. This does not include aliases and subcommands."""
        all_command_names = []
        is_owner = await self.bot.is_owner(ctx.author)
        for command in self.bot.commands:
            try:
                can_run = await command.can_run(ctx)
            except commands.CommandError:
                continue
            else:
                if can_run:
                    if not is_owner and command.hidden:
                        continue
                    all_command_names.append(command.name)
                    if include_aliases:
                        for alias in command.aliases:
                            all_command_names.append(alias)

        return all_command_names

    async def correct_command_name(self, ctx: commands.Context) -> Optional[Tuple[str, int, int]]:
        """Returns an Optional[Tuple] for closest command name matched within 2 levenshtein distance.
        Returns (command name, similarity score (levenshtein distance here), index of command in list of commands)
        Returns None if no match found within 2 levenshtein distance"""
        runnable_commands = await self.get_all_runnable_commands(ctx, include_aliases=False)
        if not runnable_commands:
            return

        return rapidfuzz.process.extractOne(ctx.invoked_with,
                                            runnable_commands,
                                            scorer=rapidfuzz.string_metric.levenshtein,
                                            score_cutoff=2)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            if len(ctx.invoked_with) < 3:
                return
            correction = await self.correct_command_name(ctx)
            if not correction:
                return
            corrected_ctx = await copy_context(ctx,
                                               content=ctx.message.content.replace(ctx.invoked_with, correction[0], 1))

            do_correct = await ctx.confirm_reaction(f'Did you mean `{correction[0]}` instead of `{ctx.invoked_with}`?',
                                                    extra=False)

            if not do_correct:
                return

            await self.bot.invoke(corrected_ctx)


def setup(bot):
    bot.add_cog(Levenshtein(bot))


