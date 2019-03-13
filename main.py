import discord
from discord.ext import commands

import sys, traceback, platform
from typing import Union
import datetime

import config
import error_handler

DESCR = 'This bot is a small side project and still very WIP'
TOKEN = config.BOT_TOKEN

# List of cogs with 'cogs.NAME' where NAME is the name of the cog's file name.
startup_extensions = []


def get_prefix(bot, message):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""

    prefixes = ['?', '! ', '%']

    # Check to see if we are outside of a guild. e.g DM's etc.
    if not message.guild:
        # Only allow ? to be used in DMs
        return '?'

    # If we are in a guild, we allow for the user to mention us or use any of the prefixes in our list.
    return commands.when_mentioned_or(*prefixes)(bot, message)


bot = commands.Bot(command_prefix=get_prefix, description=DESCR)

if __name__ == '__main__':
    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
            print(f'Successfully loaded extension {extension}.')
        except Exception as e:
            print(f'Failed to load extension {extension}.')
            # traceback.print_exc()


@bot.event
async def on_ready():
    print(f'\nLogged in as: {bot.user.name} - {bot.user.id}\n'
          f'Python Version: {platform.python_version()}\n'
          f'Library Version: {discord.__version__}\n')

    activity = discord.Activity(type=discord.ActivityType.listening, name='you :)')
    await bot.change_presence(activity=activity)
    print(f'Ready! {datetime.datetime.now()}')


bot.run(TOKEN, bot=True, reconnect=True)