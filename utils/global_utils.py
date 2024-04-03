import copy
import secrets
import random
import colorsys
import datetime
import traceback

import discord
from discord.ext import commands
from aiohttp import InvalidURL


async def copy_context(ctx: commands.Context, *, author=None, channel=None, **kwargs):
    """
    Returns a new Context with changed message properties.
    """
    # copy the message and update the attributes
    alt_message: discord.Message = copy.copy(ctx.message)
    alt_message._update(kwargs)

    if author is not None:
        alt_message.author = author
    if channel is not None:
        alt_message.channel = channel

    # obtain and return a context of the same type
    return await ctx.bot.get_context(alt_message, cls=type(ctx))


def bright_color():
    """
    Returns a random discord.Color that does not look ugly or dull
    """
    values = [int(x*255) for x in colorsys.hsv_to_rgb(random.random(), 1, 1)]
    color = discord.Color.from_rgb(*values)
    return color


def cleanup_code(content):
    """
    Automatically removes code blocks from the code.
    """
    if content.startswith('```'):
        split = content.split('\n')
        if ' ' not in split[0][3:].rstrip():  # Is language
            split = split[1:]
        else:
            split[0] = split[0][3:]  # Accidentally started coding on first line

        return '\n'.join(split).rstrip('` ')
    return content.strip('` \n')


async def last_image(ctx):
    """
    Tries to find the last image in chat and return its url.
    """
    async for message in ctx.channel.history(limit=50):
        for embed in message.embeds:
            if embed.thumbnail and embed.thumbnail.proxy_url:
                return embed.thumbnail.proxy_url
        for attachment in message.attachments:
            if attachment.proxy_url:
                return attachment.proxy_url


async def is_image(ctx, url, gif=False):
    image_formats = ('image/png', 'image/jpeg', 'image/jpg')
    if gif:
        image_formats += ('image/gif',)
    try:
        async with ctx.bot.session.head(url) as resp:
            return resp.headers['Content-Type'] in image_formats
    except (InvalidURL, KeyError):
        return False


async def upload_hastebin(ctx_or_bot, content, url='https://mystb.in'):
    """
    Uploads content to hastebin
    """
    bot = ctx_or_bot if isinstance(ctx_or_bot, commands.Bot) else ctx_or_bot.bot
    try:
        password = secrets.token_urlsafe(8)
        paste = await bot.mb_client.create_paste(
            filename=f'traceback.py',
            content=content,
            password=password,
        )
        return f'{paste.url} Password: `{password}`'
    except:
        try:
            url = 'https://hastebin.com'
            async with bot.session.post(f'{url}/documents', data=content.encode('utf-8')) as post:
                return f'{url}/{(await post.json())["key"]}'
        except Exception:
            traceback.print_exc()


async def send_or_hastebin(ctx, content, code=None, url='https://mystb.in'):
    """
    Sends to ctx.channel if possible, upload to hastebin if too long
    """
    if code is not None:
        cb = f'```{code}\n{content}\n```'
    else:
        cb = content
    if len(cb) <= 2000:
        await ctx.send(cb)
    else:
        hastebin_url = await upload_hastebin(ctx, content, url)
        await ctx.send(f'Output too long to send to discord, uploaded here instead: {hastebin_url}')





async def toggle_role(member, role):
    if not isinstance(member, discord.Member):
        raise commands.BadArgument(f'A member is expected but a {type(member)} is passed')
    if not isinstance(role, discord.Role):
        raise commands.BadArgument(f'A role is expected but a {type(role)} is passed')

    if role in member.roles:
        await member.remove_roles(role)
    else:
        await member.add_roles(role)


def make_naive(dt: datetime.datetime):
    """Returns a naive datetime
    This is mainly for our database as it does not deal with timezones"""
    return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
