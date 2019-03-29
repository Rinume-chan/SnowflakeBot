import discord
from discord.ext import commands
from config import GOOGLE_API_KEY, GOOGLE_CUSTOM_SEARCH_ENGINE

from google_images_search import GoogleImagesSearch


class GoogleImage(commands.Cog, name='General Commands'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='gi')
    async def google_image(self, ctx, *, search_param: str = 'cat'):
        gis = GoogleImagesSearch(GOOGLE_API_KEY, GOOGLE_CUSTOM_SEARCH_ENGINE)

        _search_params = {'q': search_param,
                          'num': 1,
                          'searchType': 'image',
                          'safe': 'medium'}

        try:
            gis.search(_search_params)
        except:
            return await ctx.send(
                'My daily search limit has been reached and cannot search anymore due to Google\'s restrictions... \n'
                'Sorry, please try again tomorrow.')

        if gis.results():
            image_url = gis.results()[0].url
        else:
            return await ctx.send(f'Error: Image search for `{search_param}` failed.')

        e = discord.Embed(colour=discord.Colour.green())
        e.set_image(url=image_url)
        e.set_footer(text=f'Google Image Search for: {search_param} — Safe Search: Medium')

        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(GoogleImage(bot))
