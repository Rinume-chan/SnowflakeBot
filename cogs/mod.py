import discord
from discord.ext import commands

from utils.global_utils import confirm_prompt

from collections import Counter
import asyncio


# Checks


def can_manage_messages():
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.channel.permissions_for(ctx.author).manage_messages:
            return True
        raise commands.MissingPermissions(['Manage Messages'])
    return commands.check(predicate)

def can_kick():
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.channel.permissions_for(ctx.author).kick_members:
            return True
        raise commands.MissingPermissions(['Kick Members'])
    return commands.check(predicate)

def can_ban():
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.channel.permissions_for(ctx.author).ban_members:
            return True
        raise commands.MissingPermissions(['Ban Members'])
    return commands.check(predicate)

def can_manage_roles():
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.channel.permissions_for(ctx.author).manage_roles:
            return True
        raise commands.MissingPermissions(['Manage Roles'])
    return commands.check(predicate)

def can_manage_channels():
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.channel.permissions_for(ctx.author).manage_channels:
            return True
        raise commands.MissingPermissions(['Manage Channels'])
    return commands.check(predicate)

def can_mute():
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.channel.permissions_for(ctx.author).manage_roles:
            return True
        raise commands.MissingPermissions(['Manage Roles'])
    return commands.check(predicate)

def can_move_members():
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.channel.permissions_for(ctx.author).move_members:
            return True
        raise commands.MissingPermissions(['Move Members'])
    return commands.check(predicate)

def hierarchy_check(ctx, user, target):
    return (user.id == ctx.bot.owner_id or user == ctx.guild.owner or user.top_role > target.top_role) \
           and target != ctx.guild.owner \
           and ctx.guild.me.top_role > target.top_role


# Cog


class ModCog(commands.Cog, name='Mod'):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='delmsg', hidden=True)
    @commands.bot_has_permissions(manage_messages=True)
    @can_manage_messages()
    async def del_msg(self, ctx, message: discord.Message):
        """Deletes a specific message"""
        try:
            await message.delete()
        except discord.HTTPException:
            await ctx.send('Discord is being dumb, try again later')
        else:
            await ctx.message.add_reaction('\U00002705')  # React with checkmark

    @commands.command(name='suppress', hidden=True)
    @commands.bot_has_permissions(manage_messages=True)
    @can_manage_messages()
    async def suppress_embed(self, ctx, message: discord.Message, toggle: bool=True):
        """Suppresses embeds in a given message. Can pass in False to bring embeds back"""
        try:
            await message.edit(suppress=toggle)
        except (discord.HTTPException, discord.Forbidden) as e:
            await ctx.send(f'An error has occurred: `{e}`')
        else:
            await ctx.message.add_reaction('\U00002705')  # React with checkmark

    @del_msg.error
    @suppress_embed.error
    async def msg_convert_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            ctx.local_handled = True
            return await ctx.send('```I am unable to find the specified message.\n'
                                  'I will search in the following order:\n\n'
                                  '1. By {channel ID}-{message ID}\n'
                                  'This can be retrieved by shift-clicking on “Copy ID”\n\n'
                                  '2. Lookup by message ID\n'
                                  'The message must be in the current channel\n\n'
                                  '3. Lookup by message URL\n\n'
                                  'Note: You need Developer Mode enabled to retrieve message IDs```')

    async def _sad_clean(self, ctx, limit): # No manage message permission, only delete bot's message
        counter = 0
        async for msg in ctx.history(limit=limit, before=ctx.message):
            if msg.author == ctx.me:
                await msg.delete()
                counter += 1
        return {str(self.bot.user): counter}

    async def _good_clean(self, ctx, limit): # Do have permission, so delete any invocation messages as well
        def check(m):
            return m.author == ctx.me or m.content.startswith(ctx.prefix)
        deleted = await ctx.channel.purge(limit=limit, check=check, before=ctx.message)
        return Counter(str(msg.author) for msg in deleted)

    @commands.command()
    @can_manage_messages()
    async def clean(self, ctx, limit: int = 10):
        """Clean's up the bot's messages"""
        if ctx.me.permissions_in(ctx.channel).manage_messages:
            spam = await self._good_clean(ctx, limit)
        else:
            spam = await self._sad_clean(ctx, limit)

        deleted = sum(spam.values())

        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed']
        if deleted:
            messages.append('')
            spammers = sorted(spam.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f'- **{author}**: {count}' for author, count in spammers)

        await ctx.send('\n'.join(messages), delete_after=10)
        await ctx.message.add_reaction('\U00002705')  # React with checkmark

    @commands.command()
    @commands.bot_has_permissions(kick_members=True)
    @can_kick()
    @commands.guild_only()
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """Kicks member from server"""
        if not hierarchy_check(ctx, ctx.author, member):
            return await ctx.send('You cannot kick this person due to role hierarchy')
        if reason is None:
            reason = f'Done by: {ctx.author} ({ctx.author.id})'
        else:
            reason = f'{ctx.author} ({ctx.author.id}): {reason}'

        try:
            await member.kick(reason=reason)
        except discord.HTTPException:
            await ctx.send('\U0001f44e')  # Thumbs down
        else:
            await ctx.send('\U0001f44d')  # Thumbs up

    @commands.command()
    @commands.bot_has_permissions(ban_members=True)
    @can_ban()
    @commands.guild_only()
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Bans someone from the server"""
        if not hierarchy_check(ctx, ctx.author, member):
            return await ctx.send('You cannot ban this person due to role hierarchy')
        if reason is None:
            reason = f'Done by: {ctx.author} ({ctx.author.id})'
        else:
            reason = f'{ctx.author} ({ctx.author.id}): {reason}'

        try:
            await ctx.guild.ban(member, reason=reason, delete_message_days=0)
        except discord.HTTPException:
            await ctx.send('\U0001f44e')
        else:
            await ctx.send('\U0001f44d')

    @commands.command()
    @commands.bot_has_permissions(ban_members=True)
    @can_ban()
    @commands.guild_only()
    async def unban(self, ctx, id: int, *, reason=None):
        """Unbans someone from the server. Must provide user's ID"""
        if reason is None:
            reason = f'Done by: {ctx.author} ({ctx.author.id})'
        else:
            reason = f'{ctx.author} ({ctx.author.id}): {reason}'

        try:
            await ctx.guild.unban(discord.Object(id=id), reason=reason)
        except discord.HTTPException:
            await ctx.send('\U0001f44e')
        else:
            await ctx.send('\U0001f44d')


    @commands.command()
    @commands.bot_has_permissions(ban_members=True)
    @can_kick()
    @commands.guild_only()
    async def softban(self, ctx, member: discord.Member, *, reason=None):
        """Soft bans a member from the server
        Essentially kicks the member while deleting all messages from the last week"""
        if not hierarchy_check(ctx, ctx.author, member):
            return await ctx.send('You cannot softban this person due to role hierarchy')
        if reason is None:
            reason = f'Done by: {ctx.author} ({ctx.author.id})'
        else:
            reason = f'{ctx.author} ({ctx.author.id}): {reason}'

        try:
            await ctx.guild.ban(member, reason=reason, delete_message_days=7)
            await ctx.guild.unban(member, reason=reason)
        except discord.HTTPException:
            await ctx.send('\U0001f44e')
        else:
            await ctx.send('\U0001f44d')


    async def set_muterole_perms(self, ctx, role):
        reason = f'Setting mute role permissions. Done by: {ctx.author} ({ctx.author.id})'
        done = 0
        failed = []
        no_perm = []
        await ctx.trigger_typing()
        for channel in ctx.guild.text_channels:
            my_perms = channel.permissions_for(ctx.me)
            if my_perms.manage_channels:
                ow = channel.overwrites_for(role)
                ow.send_messages = False
                ow.add_reactions = False
                try:
                    await channel.set_permissions(role, overwrite=ow, reason=reason)
                except discord.HTTPException:
                    failed.append(channel.name)
                else:
                    done += 1
            else:
                no_perm.append(channel.name)

        if failed:
            fail_msg = f'\n{len(failed)} channels failed, please try again: {", ".join(no_perm)}'
        else:
            fail_msg = ''

        if no_perm:
            missing = f'\n{len(no_perm)} channels skipped because I am missing `Manage Channel` permission for: {", ".join(no_perm)}'
        else:
            missing = ''

        await ctx.send(f'Successfully updated permission overwrites for {done} channels{fail_msg}{missing}')

        if failed or missing:
            await ctx.send(f'Use {ctx.prefix}updatemute to try and apply permission overwrites again')

        # Move the role as high as I can(just below the bot's top role with manage roles)
        for _role in ctx.guild.me.roles:
            if _role.permissions.manage_roles or _role.permissions.administrator:
                if role > _role:
                    break
                await role.edit(position=_role.position-1)
                break

    @commands.command(name='createmute')
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    @can_manage_roles()
    @commands.guild_only()
    async def create_mute_role(self, ctx):
        """Creates a role name 'Muted' and denies Send Message permission to all text channels"""
        muted_role = discord.utils.get(ctx.guild.roles, name='Muted')
        if muted_role is not None:
            return await ctx.send(f'A Muted role already exist! Please use `{ctx.prefix}updatemute` to apply permission overwrites.')

        cont = await confirm_prompt(ctx, 'You are about to create the `Muted` role')
        if not cont:
            return

        try:
            muted_role = await ctx.guild.create_role(name='Muted',
                                                     reason=f'Muted role created. Done by: {ctx.author} ({ctx.author.id})')
        except discord.HTTPException as e:
            return await ctx.send(f'An unknown error has occurred..\n'
                                  f'{e}')
        else:
            await ctx.send('Success! Mute role created')

        await self.set_muterole_perms(ctx, muted_role)

    @commands.command()
    @commands.bot_has_permissions(manage_channels=True)
    @can_manage_roles()
    @commands.guild_only()
    async def updatemute(self, ctx):
        """
        Denies Send Message permissions to all text channels.
        Useful if permissions failed to set on role creation, when new channels were created or role was manually created
        """

        role = discord.utils.get(ctx.guild.roles, name='Muted')
        if role is None:
            return await ctx.send(f'Unable to find `Muted` role, if you believe this is an error please contact my owner\n'
                                  f'Use {ctx.prefix}createmute to create the role and set the appropriate permissions')

        cont = await confirm_prompt(ctx, 'You are about to update permissions for the `Muted` role in all text channels')
        if not cont:
            return

        await self.set_muterole_perms(ctx, role)

    @commands.command()
    @commands.bot_has_permissions(manage_roles=True)
    @can_mute()
    @commands.guild_only()
    async def mute(self, ctx, member: discord.Member, *, reason=None):
        role = discord.utils.get(ctx.guild.roles, name='Muted')

        if role is None:
            return await ctx.send(f'Unable to find Muted role, please use {ctx.prefix}createmute to create the role and set the appropriate permissions\n'
                                  f'If you believe this is an error please contact my owner')

        if not hierarchy_check(ctx, ctx.author, member):
            return await ctx.send('You cannot mute this person due to role hierarchy')

        if ctx.me.top_role < role:
            return await ctx.send(f'Unable to mute, please move my role above the Muted role')

        if reason is None:
            reason = f'Muted. Done by: {ctx.author} ({ctx.author.id})'
        else:
            reason = f'{ctx.author} ({ctx.author.id}): {reason}'
        try:
            await member.add_roles(role, reason=reason)
        except discord.HTTPException:
            await ctx.send('\U0001f44e')
        else:
            await ctx.send('\U0001f44d')

    @commands.command()
    @commands.bot_has_permissions(manage_roles=True)
    @can_mute()
    @commands.guild_only()
    async def unmute(self, ctx, member: discord.Member, *, reason=None):
        role = discord.utils.get(ctx.guild.roles, name='Muted')
        if role is None:
            return await ctx.send(f'Unable to find `Muted` role\n'
                                  f'If you believe this is an error please contact my owner')

        if ctx.me.top_role < role:
            return await ctx.send(f'Unable to unmute, please move my role above the Muted role')

        if not hierarchy_check(ctx, ctx.author, member):
            return await ctx.send('You cannot mute this person due to role hierarchy')

        if role not in member.roles:
            return await ctx.send(f'{member} is not muted.\n'
                                  f'If you believe this is an error please contact my owner')

        if reason is None:
            reason = f'Unmuted. Done by: {ctx.author} ({ctx.author.id})'
        else:
            reason = f'{ctx.author} ({ctx.author.id}): {reason}'

        try:
            await member.remove_roles(role, reason=reason)
        except discord.HTTPException:
            await ctx.send('\U0001f44e')
        else:
            await ctx.send('\U0001f44d')

    @commands.command()
    @commands.bot_has_permissions(manage_channels=True)
    @can_manage_channels()
    @commands.guild_only()
    async def block(self, ctx, member: discord.Member, *, reason=None):
        """Blocks a user from sending messages to the current channel"""

        if reason is None:
            reason = f'Blocked {member}. Done by: {ctx.author} ({ctx.author.id})'
        else:
            reason = f'{ctx.author} ({ctx.author.id}): {reason}'


        try:
            ow = ctx.channel.overwrites_for(member)
            ow.send_messages = False
            ow.add_reactions = False
            await ctx.channel.set_permissions(member, overwrite=ow, reason=reason)
        except:
            await ctx.send('\U0001f44e') # Thumbs Down
        else:
            await ctx.send('\U0001f44d') # Thumbs Up

    @commands.command()
    @commands.bot_has_permissions(manage_channels=True)
    @can_manage_channels()
    @commands.guild_only()
    async def unblock(self, ctx, member: discord.Member, *, reason=None):
        """Unblocks a user from the current channel"""

        if reason is None:
            reason = f'Unblocked {member}. Done by: {ctx.author} ({ctx.author.id})'
        else:
            reason = f'{ctx.author} ({ctx.author.id}): {reason}'

        try:
            ow = ctx.channel.overwrites_for(member)
            ow.send_messages = None
            ow.add_reactions = None
            await ctx.channel.set_permissions(member, overwrite=ow, reason=reason) # Doing this first instead of just deleting when empty so it shows up on audit logs
            if ow.is_empty():
                await ctx.channel.set_permissions(member, overwrite=None) # reason does not work here
        except:
            await ctx.send('\U0001f44e') # Thumbs Down
        else:
            await ctx.send('\U0001f44d') # Thumbs Up

    @commands.command(hidden=True)
    @commands.bot_has_permissions(manage_channels=True)
    @can_manage_channels()
    @commands.guild_only()
    async def tempblock(self, ctx, member: discord.Member, seconds: int, *, reason=None):
        if reason is None:
            reason = f'Tempblocked {member} for {seconds}s. Done by: {ctx.author} ({ctx.author.id})'
        else:
            reason = f'{ctx.author} ({ctx.author.id}) tempblock for {seconds}s: {reason}'

        try:
            ow = ctx.channel.overwrites_for(member)
            ow.send_messages = False
            await ctx.channel.set_permissions(member, overwrite=ow, reason=reason)
        except:
            await ctx.send('\U0001f44e') # Thumbs Down
        else:
            await ctx.send('\U0001f44d') # Thumbs Up

        await asyncio.sleep(seconds)

        ow = ctx.channel.overwrites_for(member)
        ow.send_messages = None
        await ctx.channel.set_permissions(member, overwrite=ow, reason=f'{member} auto unblocked after {seconds}s | by {ctx.author} ({ctx.author.id})')
        if ow.is_empty():
            await ctx.channel.set_permissions(member, overwrite=None)

    @commands.command(hidden=True)
    @can_move_members()
    async def move(self, ctx, member: discord.Member, *, channel: discord.VoiceChannel = None):
        """Move a user to another voice channel.
        Disconnects user if channel is None.
        """
        if not ctx.guild.me.guild_permissions.move_members:
            return
        try:
            await member.move_to(channel)
        except discord.HTTPException as e:
            await ctx.send(f'Unable to move: `{e}`')
        else:
            await ctx.message.add_reaction('\U00002705')  # React with checkmark

    @commands.Cog.listener()
    async def on_message(self, message):
        pass

    # Purge group:

    @commands.group()
    @commands.bot_has_permissions(manage_messages=True)
    @can_manage_messages()
    @commands.guild_only()
    async def purge(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    async def purge_messages(self, ctx, limit, check):
        if limit > 200:
            return await ctx.send('Limit too high! Max: 200')

        try:
            deleted = await ctx.channel.purge(limit=limit, before=ctx.message, check=check)
        except discord.Forbidden as e:
            return await ctx.send('I do not have permissions to delete messages.')
        except discord.HTTPException as e:
            return await ctx.send(f'Error: {e}')

        authors = Counter(str(msg.author) for msg in deleted)
        deleted = len(deleted)
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']

        if deleted:
            messages.append('')
            spammers = sorted(authors.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f'**{name}**: {count}' for name, count in spammers)

        await ctx.send('\n'.join(messages), delete_after=10)

    @purge.command(name='user', aliases=['member'])
    async def user(self, ctx, member: discord.Member, limit=20):
        """Delete messages from a user.
        If no search limit is given, defaults to 20
        Ex. %purge user Snowflake 10"""
        await self.purge_messages(ctx, limit, lambda m: m.author == member)
        await ctx.message.add_reaction('\U00002705')  # React with checkmark


    @purge.command(name='bot', aliases=['bots'])
    async def bots(self, ctx, limit=20, prefix=None):
        """Deletes messages from bots and messages that begin with prefix if given
        If no search limit is given, defaults to 20
        If no prefix is given, will not delete any non-bot messages
        Ex. %purge bots 10 $"""
        def check(m):
            return (m.author.bot and m.webhook_id is None) or (prefix and m.content.startswith(prefix))
        await self.purge_messages(ctx, limit, check)
        await ctx.message.add_reaction('\U00002705')  # React with checkmark

    @purge.command(name='contains')
    async def _contains(self, ctx, *, substring):
        """Deletes messages that contain a substring
        Will always search within the last 25 messages
        Ex. %purge contains hello"""
        await self.purge_messages(ctx, 25, lambda m: substring in m.content)
        await ctx.message.add_reaction('\U00002705')  # React with checkmark

    @purge.command(name='content')
    async def content_equals(self, ctx, *, _content):
        """Deletes messages with content matching exactly with given content
        Will always search within the last 25 messages
        Ex. %purge content hello there'"""
        await self.purge_messages(ctx, 25, lambda m: m.content == _content)
        await ctx.message.add_reaction('\U00002705')  # React with checkmark

    @purge.command(name='all')
    async def everything(self, ctx, limit=20):
        """Deletes the last `limit` messages in the channel
        If no limit is given, defaults to 20"""
        if not await confirm_prompt(ctx, f'Delete {limit} messages?'):
            return
        await self.purge_messages(ctx, limit, lambda m: True)
        await ctx.message.add_reaction('\U00002705')  # React with checkmark


def setup(bot):
    bot.add_cog(ModCog(bot))
