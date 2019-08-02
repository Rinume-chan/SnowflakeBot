import discord
from discord.ext import commands

from typing import Optional
from jishaku.codeblocks import Codeblock, codeblock_converter
from global_utils import copy_context

command_attrs = {'hidden': True}


class OwnerCog(commands.Cog, name='Owner', command_attrs=command_attrs):
    def __init__(self, bot):
        self.bot = bot

    # Applies commands.is_owner() check for all methods in this cog
    async def cog_check(self, ctx):
        if not await ctx.bot.is_owner(ctx.author):
            raise commands.NotOwner('Only my owner can use this command.')
        return True

    @commands.command(name='load')
    async def load_cog(self, ctx, *, cog: str):
        """Command which Loads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send(f'**`SUCCESS:`** loaded {cog}')

    @commands.command(name='unload')
    async def unload_cog(self, ctx, *, cog: str):
        """Command which Unloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send(f'**`SUCCESS:`** unloaded {cog}')

    @commands.command(name='reload')
    async def reload_cog(self, ctx, *, cog: str):
        """Command which Reloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            self.bot.unload_extension(cog)
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send(f'**`SUCCESS`** reloaded {cog}')

    @commands.command(name='presence')
    async def change_presence(self, ctx, type: str, *, name: Optional[str]):
        activities = {'L': discord.Activity(name=name, type=discord.ActivityType.listening),
                      'P': discord.Game(name=name),
                      'S': discord.Streaming(name=name, url='https://www.twitch.tv/directory'),
                      'W': discord.Activity(name=name, type=discord.ActivityType.watching),
                      'N': None,
                      'Default': discord.Activity(type=discord.ActivityType.listening, name='you :)')}

        statuses = {'Online': discord.Status.online,
                    'Offline': discord.Status.invisible,
                    'Idle': discord.Status.idle,
                    'DND': discord.Status.dnd}

        if type in activities:
            await self.bot.change_presence(activity=activities[type])
            await ctx.send('Changing my activity...')
        elif type in statuses:
            await self.bot.change_presence(status=statuses[type])
            await ctx.send('Changing my status...')
        else:
            await ctx.send('The specified presence cannot be found\n'
                           '```Activity: L | P | S | W | N | Default\n'
                           'Status: Online | Offline | Idle | DND```')

    @commands.command(name='eval')
    async def _eval(self, ctx, *, args: codeblock_converter):
        """Evaluates python code in a single line or code block"""
        await ctx.invoke(self.bot.get_command("jsk py"), argument=args)

    @commands.command(name='su')
    async def _su(self, ctx: commands.Context, target: discord.User, *, command_string: str):
        """
        Run a command as someone else.
        Try to resolve to a Member, but will use a User if it can't find one.
        """
        if ctx.guild:
            # Try to upgrade to a Member instance
            # This used to be done by a Union converter, but doing it like this makes
            #  the command more compatible with chaining, e.g. `jsk in .. jsk su ..`
            target = ctx.guild.get_member(target.id) or target

        alt_ctx = await copy_context(ctx, author=target, content=ctx.prefix + command_string)

        if alt_ctx.command is None:
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        return await alt_ctx.command.invoke(alt_ctx)



def setup(bot):
    bot.add_cog(OwnerCog(bot))
