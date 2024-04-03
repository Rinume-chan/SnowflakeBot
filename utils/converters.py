import typing

import discord

from discord.ext import commands
from utils import errors


class CaseInsensitiveMember(commands.MemberConverter):
    async def convert(self, ctx, argument):
        try:
            member = await super().convert(ctx, argument)
        except commands.BadArgument:
            member = discord.utils.find(lambda m: m.name.lower() == argument.lower(), ctx.guild.members)
            if member is None:  # Nickname search
                member = discord.utils.find(lambda m: m.display_name.lower() == argument.lower(), ctx.guild.members)

        if member is None:
            raise errors.CaseInsensitiveMemberNotFound()
        return member


class Member(commands.MemberConverter):
    async def convert(self, ctx, argument):
        try:
            return await super().convert(ctx, argument)
        except commands.BadArgument:
            raise errors.MemberNotFound()


class User(commands.UserConverter):
    async def convert(self, ctx, argument):
        try:
            return await super().convert(ctx, argument)
        except commands.BadArgument:
            raise errors.UserNotFound()


class CaseInsensitiveUser(commands.UserConverter):
    async def convert(self, ctx, argument):
        try:
            user = await super().convert(ctx, argument)
        except commands.BadArgument:
            user = discord.utils.find(lambda u: u.name.lower() == argument.lower(), ctx.bot.users)

        if user is None:
            raise errors.CaseInsensitiveUserNotFound()
        return user

# ID only
class CachedUserID(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            user = ctx.bot.get_user(int(argument))
        except ValueError:
            raise commands.BadArgument('That is not a valid ID')

        if user is None:
            raise commands.BadArgument(f'Unable to find User with ID {argument}')
        return user

# ID only
class CachedMemberID(commands.Converter):
    """Gets member object from an ID, no guarantees which guild the member obj belongs to"""
    async def convert(self, ctx, argument):
        try:
            _id = int(argument)
            for guild in ctx.bot.guilds:
                member = guild.get_member(_id)
                if member is not None:
                    break
        except ValueError:
            raise commands.BadArgument('That is not a valid ID')

        if member is None:
            raise commands.BadArgument(f'Unable to find Member with ID {argument}')
        return member


# ID only
class CachedGuildID(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            guild = ctx.bot.get_guild(int(argument))
        except ValueError:
            raise commands.BadArgument('That is not a valid ID')

        if guild is None:
            raise commands.BadArgument(f'Unable to find server with ID {argument}')
        return guild


class UserID(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            await ctx.bot.fetch_user(int(argument))
        except ValueError:
            raise commands.BadArgument('That is not a valid ID')
        except discord.NotFound:
            raise commands.BadArgument(f'Unable to find User with ID {argument}')


class CaseInsensitiveTextChannel(commands.TextChannelConverter):
    async def convert(self, ctx, argument):
        try:
            channel = await super().convert(ctx, argument)
        except commands.BadArgument:
            if ctx.guild:
                channel = discord.utils.find(lambda c: c.name.lower() == argument.lower(), ctx.guild.text_channels)
            else:
                # Doing case insensitive search across many guilds leads to too much ambiguity
                raise errors.ChannelNotFound('A channel with that ID cannot be found')

        if channel is None:
            raise errors.ChannelNotFound(f'Channel `{argument}` not found.')
        return channel


class CaseInsensitiveVoiceChannel(commands.VoiceChannelConverter):
    async def convert(self, ctx, argument):
        try:
            channel = await super().convert(ctx, argument)
        except commands.BadArgument:
            if ctx.guild:
                channel = discord.utils.find(lambda c: c.name.lower() == argument.lower(), ctx.guild.voice_channels)
            else:
                # Doing case insensitive search across many guilds leads to too much ambiguity
                raise errors.ChannelNotFound('A channel with that ID cannot be found')

        if channel is None:
            raise errors.ChannelNotFound(f'Channel `{argument}` not found.')
        return channel


class CaseInsensitiveCategoryChannel(commands.CategoryChannelConverter):
    async def convert(self, ctx, argument):
        try:
            channel = await super().convert(ctx, argument)
        except commands.BadArgument:
            if ctx.guild:
                channel = discord.utils.find(lambda c: c.name.lower() == argument.lower(), ctx.guild.categories)
            else:
                # Doing case insensitive search across many guilds leads to too much ambiguity
                raise errors.ChannelNotFound('A channel with that ID cannot be found')

        if channel is None:
            raise errors.ChannelNotFound(f'Channel `{argument}` not found.')
        return channel


CaseInsensitiveChannel = typing.Union[CaseInsensitiveTextChannel,
                                      CaseInsensitiveVoiceChannel,
                                      CaseInsensitiveCategoryChannel]


class BannedUser(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            try:
                return await ctx.guild.fetch_ban(discord.Object(argument))
            except discord.NotFound:
                raise commands.BadArgument('Unable to find ban for this ID')

        bans = await ctx.guild.bans()
        entry = discord.utils.find(lambda u: str(u.user) == argument, bans)

        if entry is None:
            raise commands.BadArgument('Unable to find ban for this user')
        return entry


class MessageConverter(commands.MessageConverter):
    async def convert(self, ctx, argument):
        try:
            return await super().convert(ctx, argument)
        except commands.MessageNotFound:
            raise errors.MessageNotFound


class CaseInsensitiveRole(commands.RoleConverter):
    async def convert(self, ctx, argument):
        try:
            role = await super().convert(ctx, argument)
        except commands.BadArgument:
            role = discord.utils.find(lambda r: r.name.lower() == argument.lower(), ctx.guild.roles)
        except commands.NoPrivateMessage:
            raise

        if role is None:
            raise errors.RoleNotFound()
        return role


class CurrencyConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        try:
            amount = float(argument.replace(',', ''))
        except ValueError:
            raise commands.BadArgument(f'{argument} is not a valid number')
        else:
            if amount < 0:
                raise commands.BadArgument(f'Amount cannot be negative')
            return round(amount, 2)


MoneyConverter = typing.Union[CurrencyConverter, typing.Literal['half'], typing.Literal['all']]
