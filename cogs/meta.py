import os
import time
import inspect

import discord
from discord.ext import commands

from utils.time import human_timedelta
from utils.global_utils import copy_context
from utils.converters import CaseInsensitiveMember


class MetaCog(commands.Cog, name='Meta'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='timeit', hidden=True)
    async def _timeit(self, ctx: commands.Context, *, command_string: str):
        """
        Run a command timing execution and catching exceptions.
        """
        alt_ctx = await copy_context(ctx, content=ctx.prefix + command_string)
        if alt_ctx.command is None:
            return await ctx.send(f'Command "{alt_ctx.invoked_with}" is not found')

        start = time.perf_counter()
        await alt_ctx.command.invoke(alt_ctx)
        end = time.perf_counter()

        return await ctx.send(f'Command `{alt_ctx.command.qualified_name}` finished in {end - start:.3f}s.')

    @commands.command(brief='Checks latency to Discord.')
    async def ping(self, ctx):
        cmd = self.bot.get_command('jsk ping')
        if cmd is not None:
            return await cmd(ctx)
        start = time.perf_counter()
        msg = await ctx.send('boop')
        end = time.perf_counter()
        await msg.edit(content=f'(WS) Latency: `{self.bot.latency*1000:.2f}ms`\n'
                               f'Response time: `{(end - start)*1000:.2f}ms`')

    @commands.command()
    async def invite(self, ctx, id: int = None):
        """
        The invite link to add me to your server.
        """
        if not id:
            user = 'me'
            url = f'https://discordapp.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands'
        else:
            try:
                fetch = await self.bot.fetch_user(id)
                if not fetch.bot:
                    return await ctx.send('That ID is not a bot!')
            except discord.NotFound:
                return await ctx.send('Invalid ID! Please try again')
            except discord.DiscordException as e:
                return await ctx.send(f'An error occurred\n```{e}```')
            else:
                user = str(fetch)

            url = f'https://discordapp.com/oauth2/authorize?client_id={id}&permissions=1024&guild_id={ctx.guild.id}&scope=bot'

        e = discord.Embed(title=f'Invite {user} to your server!',
                          color=discord.Colour(0x00FFFF),
                          description=f'[Click here to invite {user}]({url})')
        await ctx.send(embed=e)

    @commands.command()
    async def uptime(self, ctx, simple: bool = False):
        """Returns the bot's uptime
        Pass in True to view simplified time"""
        await ctx.send(f'Uptime: {human_timedelta(self.bot.starttime, accuracy=None, brief=simple, suffix=False)}')

    @commands.command(name='shared')
    async def shared_guilds(self, ctx, member: CaseInsensitiveMember=None):
        """Returns the number of guilds a member shares with the bot"""
        member = member or ctx.author
        count = 0
        for guild in self.bot.guilds:
            if guild.get_member(member.id):
                count += 1
        await ctx.send(f'I share {count} server{"s" if count > 1 else ""} with {member}')

    # Credits to Danny:
    @commands.command()
    async def source(self, ctx, *, command: str = None):
        """Displays  source code or for a specific command.

        To display the source code of a subcommand you can separate it by
        periods or space eg. highlight.mention or highlight mention
        """
        url = 'https://github.com/Rinume-chan/SnowflakeBot'
        branch = 'master'
        if command is None:
            return await ctx.send(url)

        if command == 'help':
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            cmd = self.bot.get_command(command.replace('.', ' '))
            if cmd is None:
                return await ctx.send('Sorry. I am unable to find that command.')

            src = cmd.callback.__code__
            module = cmd.callback.__module__
            filename = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)
        if not module.startswith('discord'):
            # not a built-in command
            location = os.path.relpath(filename).replace('\\', '/')
        else:
            location = module.replace('.', '/') + '.py'
            url = 'https://github.com/Rapptz/discord.py'
            branch = 'v1.x'  # master is 2.0 development

        final_url = f'<{url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'
        await ctx.send(final_url)


async def setup(bot):
    await bot.add_cog(MetaCog(bot))
