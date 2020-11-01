import discord
from discord.ext import commands

import contextlib
from asyncio import TimeoutError
from utils.converters import CaseInsensitiveVoiceChannel


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def secure(self, ctx, voicechannel: CaseInsensitiveVoiceChannel = None):
        if (not ctx.guild or not ctx.author.voice) and voicechannel is None:
            return await ctx.send('You are not in a voice channel!')
        voicechannel = voicechannel or ctx.author.voice.channel
        if not voicechannel.guild.me.guild_permissions.mute_members:
            return await ctx.send('I do not have permission to mute!')
        if not ctx.guild:
            ctx.author = voicechannel.guild.get_member(ctx.author.id)

        await ctx.message.add_reaction('<a:typing:559157048919457801>')
        await ctx.message.add_reaction('<:greenTick:602811779835494410>')

        current_members = voicechannel.members

        def check(member, before, after):
            return (member != ctx.author
                    and before.channel != voicechannel
                    and after.channel == voicechannel
                    and ctx.author in voicechannel.members
                    and member not in current_members) \
                   or (member == ctx.author
                       and before.channel == voicechannel
                       and after.channel != voicechannel)
        try:
            member, _ , _ = await self.bot.wait_for('voice_state_update', check=check, timeout=43200)
        except TimeoutError:
            pass
        else:
            if member != ctx.author:
                await ctx.author.edit(mute=True)
                await ctx.message.add_reaction('\U0000203c')
                await ctx.message.remove_reaction('<:greenTick:602811779835494410>', ctx.me)
        finally:
            with contextlib.suppress(discord.HTTPException):
                await ctx.message.remove_reaction('<a:typing:559157048919457801>', ctx.me)







def setup(bot):
    bot.add_cog(Voice(bot))
