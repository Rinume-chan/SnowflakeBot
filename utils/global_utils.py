import discord
from discord.ext import commands

import copy
import colorsys
import random
from asyncio import TimeoutError


async def copy_context(ctx: commands.Context, *, author=None, channel=None, **kwargs):
    """
    Makes a new :class:`Context` with changed message properties.
    """
    # copy the message and update the attributes
    alt_message: discord.Message = copy.copy(ctx.message)
    alt_message._update(kwargs)  # pylint: disable=protected-access

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


async def confirm_prompt(ctx: commands.Context, msg):
    cont = False

    def confirm(msg):
        nonlocal cont
        if ctx.author.id != msg.author.id or ctx.channel.id != msg.channel.id:
            return False
        if msg.content in ('**confirm**', '**Confirm**', 'confirm', 'Confirm'):
            cont = True
            return True
        elif msg.content in ('**abort**', '**Abort**', 'abort', 'Abort'):
            cont = False  # don't continue
            return True
        return False  # author typed something else in the same channel, keep waiting

    prompt = await ctx.send(f'{msg}\n'
                            f'Please type **confirm** within 1 minute to continue or type **abort** if you change your mind.')

    try:
        reply = await ctx.bot.wait_for('message', check=confirm, timeout=60)
        await reply.delete()
    except TimeoutError:
        await ctx.send('1 minute has passed. Aborting...', delete_after=5)
        return False
    except discord.HTTPException:
        pass
    finally:
        await prompt.delete()

    if not cont:  # Author typed abort, don't continue
        await ctx.send('Aborting...', delete_after=5)

    return cont

def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')
