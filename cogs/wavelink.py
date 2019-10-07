"""
Myst Open License - Version 0.1.
=====================================
Copyright (c) 2019 EvieePy(MysterialPy)
 This Source Code Form is subject to the terms of the Myst Open License, v. 0.1.
 If a copy of the MOL was not distributed with this file, You can obtain one at
 https://gist.github.com/EvieePy/bfe0332ad7bff98691f51686ded083ea.
"""
import asyncio
import datetime
import discord
import humanize
import itertools
import math
import random
import re
import json
import wavelink
from collections import deque
from async_timeout import timeout
from discord.ext import commands, tasks

RURL = re.compile(r'https?:\/\/(?:www\.)?.+')


class Track(wavelink.Track):
    __slots__ = ('requester', 'channel', 'message')

    def __init__(self, id_, info, *, ctx=None):
        super(Track, self).__init__(id_, info)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.message = ctx.message

    @property
    def is_dead(self):
        return self.dead


class Player(wavelink.Player):

    def __init__(self, bot: commands.Bot, guild_id: int, node: wavelink.Node):
        super(Player, self).__init__(bot, guild_id, node)

        self.queue = asyncio.Queue()
        self.next_event = asyncio.Event()

        self.volume = 40
        self.controller_message = None
        self.reaction_task = None
        self.update = False
        self.updating = False
        self.inactive = False
        self.looping = False

        self.controls = {'⏯': 'rp',
                         '⏹': 'stop',
                         '⏭': 'skip',
                         '🔀': 'shuffle',
                         '🔂': 'repeat',
                         '🔁': 'loop',
                         '➖': 'vol_down',
                         '➕': 'vol_up',
                         'ℹ': 'queue'}

        self.pauses = set()
        self.resumes = set()
        self.stops = set()
        self.shuffles = set()
        self.skips = set()
        self.repeats = set()

        self.eq = 'Flat'

        bot.loop.create_task(self.player_loop())
        bot.loop.create_task(self.updater())

    @property
    def entries(self):
        return list(self.queue._queue)

    async def updater(self):
        while not self.bot.is_closed():
            if self.update and not self.updating:
                self.update = False
                await self.invoke_controller()

            await asyncio.sleep(10)

    async def player_loop(self):
        await self.bot.wait_until_ready()

        await self.set_preq('Flat')
        # We can do any pre loop prep here...
        await self.set_volume(self.volume)

        while True:
            self.next_event.clear()

            self.inactive = False

            try:
                async with timeout(300):
                    song = await self.queue.get()
            except asyncio.TimeoutError:
                await self.destroy_controller()
                await self.destroy()
                return

            if not song:
                continue

            self.current = song
            self.paused = False

            if self.looping:
                await self.queue.put(song)

            await self.play(song)

            # Invoke our controller if we aren't already...
            if not self.update:
                await self.invoke_controller()

            # Wait for TrackEnd event to set our event...
            await self.next_event.wait()

            # Clear votes...
            self.pauses.clear()
            self.resumes.clear()
            self.stops.clear()
            self.shuffles.clear()
            self.skips.clear()
            self.repeats.clear()

    async def invoke_controller(self, track: wavelink.Track = None):
        """Invoke our controller message, and spawn a reaction controller if one isn't alive."""
        if not track:
            track = self.current
        if track is None:
            return
        self.updating = True

        embed = discord.Embed(title='Music Controller',
                              description=f'{"<a:eq:628825184941637652> Now Playing:" if self.is_playing and not self.paused else "⏸ PAUSED"}```ini\n{track.title}\n\n'
                                          f'[EQ]: {self.eq}```',
                              colour=0xffb347)
        embed.set_thumbnail(url=track.thumb)

        if track.is_stream:
            embed.add_field(name='Duration', value='🔴`Streaming`')
        else:
            embed.add_field(name='Duration', value=str(datetime.timedelta(milliseconds=int(track.length))))
        embed.add_field(name='Video URL', value=f'[Click Here!]({track.uri})')
        embed.add_field(name='Requested By', value=track.requester.mention)
        embed.add_field(name='Queue Length', value=str(len(self.entries)))
        embed.add_field(name='Volume', value=f'**`{self.volume}%`**')
        embed.add_field(name='Looping', value='ON' if self.looping else 'OFF')

        if len(self.entries) > 0:
            data = '\n'.join(f'**-** `{t.title[0:45]}{"..." if len(t.title) > 45 else ""}`\n{"-"*10}'
                             for t in itertools.islice([e for e in self.entries if not e.is_dead], 0, 3, None))
            embed.add_field(name='Coming Up:', value=data, inline=False)

        if not await self.is_current_fresh(track.channel) and self.controller_message:
            try:
                await self.controller_message.delete()
            except discord.HTTPException:
                pass

            self.controller_message = await track.channel.send(embed=embed)
        elif not self.controller_message:
            self.controller_message = await track.channel.send(embed=embed)
        else:
            self.updating = False
            return await self.controller_message.edit(embed=embed, content=None)

        try:
            self.reaction_task.cancel()
        except Exception:
            pass

        self.reaction_task = self.bot.loop.create_task(self.reaction_controller())
        self.updating = False

    async def add_reactions(self):
        """Add reactions to our controller."""
        for reaction in self.controls:
            try:
                await self.controller_message.add_reaction(str(reaction))
            except discord.HTTPException:
                return

    async def reaction_controller(self):
        """Our reaction controller, attached to our controller.
        This handles the reaction buttons and it's controls.
        """
        self.bot.loop.create_task(self.add_reactions())

        def check(r, u):
            if not self.controller_message:
                return False
            elif str(r) not in self.controls.keys():
                return False
            elif u.id == self.bot.user.id or r.message.id != self.controller_message.id:
                return False
            elif u not in self.bot.get_channel(int(self.channel_id)).members:
                return False
            return True

        while self.controller_message:
            if self.channel_id is None:
                return self.reaction_task.cancel()

            react, user = await self.bot.wait_for('reaction_add', check=check)
            control = self.controls.get(str(react))

            if control == 'rp':
                if self.paused:
                    control = 'resume'
                else:
                    control = 'pause'

            try:
                await self.controller_message.remove_reaction(react, user)
            except discord.HTTPException:
                pass
            cmd = self.bot.get_command(control)

            ctx = await self.bot.get_context(react.message)
            ctx.author = user

            try:
                if cmd.is_on_cooldown(ctx):
                    pass
                if not await self.invoke_react(cmd, ctx):
                    pass
                else:
                    self.bot.loop.create_task(ctx.invoke(cmd))
            except Exception as e:
                ctx.command = self.bot.get_command('reactcontrol')
                await cmd.dispatch_error(ctx=ctx, error=e)

        await self.destroy_controller()

    async def destroy_controller(self):
        """Destroy both the main controller and it's reaction controller."""
        try:
            await self.controller_message.delete()
            self.controller_message = None
        except (AttributeError, discord.HTTPException):
            pass

        try:
            self.reaction_task.cancel()
        except Exception:
            pass

    async def invoke_react(self, cmd, ctx):
        if not cmd._buckets.valid:
            return True

        if not (await cmd.can_run(ctx)):
            return False

        bucket = cmd._buckets.get_bucket(ctx)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return False
        return True

    async def is_current_fresh(self, chan):
        """Check whether our controller is fresh in message history."""
        try:
            async for m in chan.history(limit=8):
                if m.id == self.controller_message.id:
                    return True
        except (discord.HTTPException, AttributeError):
            return False
        return False


class Music(commands.Cog):
    """Our main Music Cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players = {}
        with open('data/playlists.json') as f:
            self._playlists = json.load(f)
        self.save_playlists_to_json.start()

        if not hasattr(bot, 'wavelink'):
            self.bot.wavelink = wavelink.Client(bot)

        bot.loop.create_task(self.initiate_nodes())

    def cog_unload(self):
        if not any([player.is_playing for player in self.bot.wavelink.players.values()]):
            for player in self.bot.wavelink.players.values():
                self.bot.loop.create_task(player.destroy())
            self.bot.loop.create_task(self.bot.wavelink.destroy_node(identifier='MAIN'))
        else:
            for player in self.bot.wavelink.players.values():
                if not player.is_connected:
                    self.bot.loop.create_task(player.destroy())

        self.save_playlists_to_json.cancel()
        self.save_playlists()

    async def initiate_nodes(self):
        _main = self.bot.wavelink.get_node('MAIN')
        if _main:
            return _main.set_hook(self.event_hook)

        nodes = {'MAIN': {'host': '127.0.0.1',
                          'port': 2333,
                          'rest_url': 'http://127.0.0.1:2333',
                          'password': "testpassword",
                          'identifier': 'MAIN',
                          'region': 'us_central'}}

        for n in nodes.values():
            node = await self.bot.wavelink.initiate_node(host=n['host'],
                                                         port=n['port'],
                                                         rest_uri=n['rest_url'],
                                                         password=n['password'],
                                                         identifier=n['identifier'],
                                                         region=n['region'],
                                                         secure=False)

            node.set_hook(self.event_hook)

    def event_hook(self, event):
        """Our event hook. Dispatched when an event occurs on our Node."""
        if isinstance(event, wavelink.TrackEnd):
            event.player.next_event.set()
        elif isinstance(event, wavelink.TrackException):
            print(event.error)

    def required(self, player, invoked_with):
        """Calculate required votes."""
        channel = self.bot.get_channel(int(player.channel_id))
        if invoked_with == 'stop':
            if len(channel.members) - 1 == 2:
                return 2

        return math.ceil((len(channel.members) - 1) / 2.5)

    async def has_perms(self, ctx, **perms):
        """Check whether a member has the given permissions."""
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        ch = ctx.channel
        permissions = ch.permissions_for(ctx.author)

        missing = [perm for perm, value in perms.items() if getattr(permissions, perm, None) != value]

        if not missing:
            return True

        return False

    async def vote_check(self, ctx, command: str):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        vcc = len(self.bot.get_channel(int(player.channel_id)).members) - 1
        votes = getattr(player, command + 's', None)

        if vcc < 3 and not ctx.invoked_with == 'stop':
            votes.clear()
            return True
        else:
            votes.add(ctx.author.id)

            if len(votes) >= self.required(player, ctx.invoked_with):
                votes.clear()
                return True
        return False

    async def do_vote(self, ctx, player, command: str):
        attr = getattr(player, command + 's', None)
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if ctx.author.id in attr:
            await ctx.send(f'{ctx.author.mention}, you have already voted to {command}!', delete_after=5)
        elif await self.vote_check(ctx, command):
            await ctx.send(f'Vote request for {command} passed!', delete_after=10)
            to_do = getattr(self, f'do_{command}')
            await to_do(ctx)
        else:
            await ctx.send(f'{ctx.author.mention}, has voted to {command} the song!'
                           f' **{self.required(player, ctx.invoked_with) - len(attr)}** more votes needed!',
                           delete_after=5)

    @commands.command(name='reactcontrol', hidden=True)
    async def react_control(self, ctx):
        """Dummy command for error handling in our player."""
        pass

    @commands.command(name='connect', aliases=['join'])
    async def connect_(self, ctx, *, channel: discord.VoiceChannel = None):
        """Connect to voice.
        Parameters
        ------------
        channel: discord.VoiceChannel [Optional]
            The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
            will be made.
        """
        # try:
        #     await ctx.message.delete()
        # except discord.HTTPException:
        #     pass

        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                return await ctx.send('No channel to join. Please either specify a valid channel or join one.')

        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if player.is_connected:
            if ctx.author.voice.channel == ctx.guild.me.voice.channel:
                return

        await player.connect(channel.id)

    @commands.command(name='play', aliases=['p'])
    async def play_(self, ctx, *, query: str):
        """Queue a song or playlist for playback.
        Aliases
        ---------
            sing
        Parameters
        ------------
        query: simple, URL [Required]
            The query to search for a song. This could be a simple search term or a valid URL.
            e.g Youtube URL or Spotify Playlist URL.
        Examples
        ----------
        <prefix>play <query>
            {ctx.prefix}play What is love?
            {ctx.prefix}play https://www.youtube.com/watch?v=XfR9iY5y94s
        """
        await ctx.trigger_typing()

        # await ctx.invoke(self.connect_)
        query = query.strip('<>')

        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected or (player.is_connected and ctx.author.voice and ctx.author.voice.channel != ctx.guild.me.voice.channel):
            await ctx.invoke(self.connect_)

        if not RURL.match(query):
            query = f'ytsearch:{query}'

        tracks = await self.bot.wavelink.get_tracks(query)
        if not tracks:
            return await ctx.send('No songs were found with that query. Please try again.')

        if isinstance(tracks, wavelink.TrackPlaylist):
            for t in tracks.tracks:
                await player.queue.put(Track(t.id, t.info, ctx=ctx))

            await ctx.send(f'```ini\nAdded the playlist {tracks.data["playlistInfo"]["name"]}'
                           f' with {len(tracks.tracks)} songs to the queue.\n```', delete_after=15)
        else:
            track = tracks[0]
            await ctx.send(f'```ini\nAdded {track.title} to the Queue\n```', delete_after=8)
            await player.queue.put(Track(track.id, track.info, ctx=ctx))

        if player.controller_message and player.is_playing:
            await player.invoke_controller()

        await asyncio.sleep(5)
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    @commands.command(name='now_playing', aliases=['np', 'current', 'currentsong'])
    async def now_playing(self, ctx):
        """Invoke the player controller.
        Aliases
        ---------
            np
            current
            currentsong
        Examples
        ----------
        <prefix>now_playing
            {ctx.prefix}np
        The player controller contains various information about the current and upcoming songs.
        """
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not player:
            return

        if not player.is_connected:
            return

        if player.updating or player.update:
            return

        await player.invoke_controller()

    @commands.command(name='pause')
    async def pause_(self, ctx):
        """Pause the currently playing song.
        Examples
        ----------
        <prefix>pause
            {ctx.prefix}pause
        """
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not player:
            return

        if not player.is_connected:
            await ctx.send('I am not currently connected to voice!')

        if player.paused:
            return

        await ctx.send(f'{ctx.author} has paused the music!', delete_after=5)

        return await self.do_pause(ctx)

    async def do_pause(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        player.paused = True
        await player.set_pause(True)

        if not player.updating and not player.update:
            await player.invoke_controller()

    @commands.command(name='resume')
    async def resume_(self, ctx):
        """Resume a currently paused song.
        Examples
        ----------
        <prefix>resume
            {ctx.prefix}resume
        """
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            await ctx.send('I am not currently connected to voice!')

        if not player.paused:
            return

        await ctx.send(f'{ctx.author} has resumed the music!', delete_after=5)

        return await self.do_resume(ctx)

    async def do_resume(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.set_pause(False)

        if not player.updating and not player.update:
            await player.invoke_controller()

    @commands.command(name='skip')
    async def skip_(self, ctx):
        """Skip the current song.
        Examples
        ----------
        <prefix>skip
            {ctx.prefix}skip
        """
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return await ctx.send('I am not currently connected to voice!')

        await ctx.send(f'{ctx.author} has skipped the song!', delete_after=5)

        return await self.do_skip(ctx)

    async def do_skip(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        await player.stop()

    @commands.command(name='stop')
    async def stop_(self, ctx):
        """Stop the player, disconnect and clear the queue.
        Examples
        ----------
        <prefix>stop
            {ctx.prefix}stop
        """
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return await ctx.send('I am not currently connected to voice!')

        await ctx.send(f'{ctx.author} has stopped the music!', delete_after=5)

        return await self.do_stop(ctx)

    async def do_stop(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        await player.destroy_controller()
        await player.destroy()

    @commands.command(name='volume', aliases=['vol'])
    async def volume_(self, ctx, *, value: int):
        """Change the player volume.
        Aliases
        ---------
            vol
        Parameters
        ------------
        value: [Required]
            The volume level you would like to set. This can be a number between 1 and 100.
        Examples
        ----------
        <prefix>volume <value>
            {ctx.prefix}volume 50
        """
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return await ctx.send('I am not currently connected to voice!')

        if not 0 <= value <= 100:
            return await ctx.send('Please enter a value between 1 and 100.')

        await player.set_volume(value)
        await ctx.send(f'Set the volume to **{value}**%')

        if not player.updating and not player.update:
            await player.invoke_controller()

    @commands.command(name='queue', aliases=['q', 'que'])
    async def queue_(self, ctx):
        """Retrieve a list of currently queued songs.
        Aliases
        ---------
            que
            q
        Examples
        ----------
        <prefix>queue
            {ctx.prefix}queue
            {ctx.prefix}q
        """
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return await ctx.send('I am not currently connected to voice!')

        upcoming = list(itertools.islice(player.entries, 0, 15))

        if not upcoming:
            return await ctx.send('```\nNo more songs in the Queue!\n```')
        numbered = [f'{i+1}. **`{str(song)}`**' for i, song in enumerate(upcoming)]
        fmt = '\n'.join(numbered)
        # fmt = '\n'.join(f'**`{str(song)}`**' for song in upcoming)
        embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)

        await ctx.send(embed=embed)

    @commands.command(name='shuffle', aliases=['mix'])
    async def shuffle_(self, ctx):
        """Shuffle the current queue.
        Aliases
        ---------
            mix
        Examples
        ----------
        <prefix>shuffle
            {ctx.prefix}shuffle
            {ctx.prefix}mix
        """
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return await ctx.send('I am not currently connected to voice!')

        await ctx.send(f'{ctx.author} has shuffled the queue!', delete_after=5)

        return await self.do_shuffle(ctx)

    async def do_shuffle(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        random.shuffle(player.queue._queue)

        await ctx.send('Shuffling..', delete_after=5)
        if not player.updating and not player.update:
            await player.invoke_controller()

    @commands.command(name='repeat')
    async def repeat_(self, ctx):
        """Repeat the currently playing song.
        Examples
        ----------
        <prefix>repeat
            {ctx.prefix}repeat
        """
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return

        await ctx.send(f'{ctx.author} repeated the current song!', delete_after=5)

        return await self.do_repeat(ctx)

    async def do_repeat(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.entries:
            await player.queue.put(player.current)
        else:
            player.queue._queue.appendleft(player.current)

        if not player.updating and not player.update:
            await player.invoke_controller()

    @commands.command(name='loop')
    async def loop_(self, ctx, toggle: bool=None):
        """Toggles repeat for whole queue
        Examples
        ---------
        <prefix>loop (will toggle)
        <prefix>loop on/off
        """
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if toggle:
            player.looping = toggle
        else:
            player.looping = not player.looping

        if player.looping and player.is_playing:
            await player.queue.put(player.current)

        await ctx.send(f'Looping is now {"on" if player.looping else "off"}!', delete_after=5)
        if not player.updating and not player.update:
            await player.invoke_controller()

    @commands.command(name='vol_up', hidden=True)
    async def volume_up(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return

        vol = int(math.ceil((player.volume + 10) / 10)) * 10

        if vol > 100:
            vol = 100
            await ctx.send('Maximum volume reached', delete_after=7)

        await ctx.send(f'{ctx.author} has raised the volume!', delete_after=5)

        await player.set_volume(vol)
        if not player.updating and not player.update:
            await player.invoke_controller()

    @commands.command(name='vol_down', hidden=True)
    async def volume_down(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return

        vol = int(math.ceil((player.volume - 10) / 10)) * 10

        if vol < 0:
            vol = 0
            await ctx.send('Player is currently muted', delete_after=10)

        await ctx.send(f'{ctx.author} has lowered the volume!', delete_after=5)

        await player.set_volume(vol)
        if not player.updating and not player.update:
            await player.invoke_controller()

    @commands.command(name='eq')
    async def set_eq(self, ctx, *, eq: str):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if eq.upper() not in player.equalizers:
            return await ctx.send(f'`{eq}` - Is not a valid equalizer!\nTry Flat, Boost, Metal, Piano.')

        await player.set_preq(eq)
        player.eq = eq.capitalize()
        await ctx.send(f'The player Equalizer was set to - {eq.capitalize()} - {ctx.author}')

    @commands.command()
    async def wlinfo(self, ctx):
        """Retrieve various Node/Server/Player information."""
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        node = player.node

        used = humanize.naturalsize(node.stats.memory_used)
        total = humanize.naturalsize(node.stats.memory_allocated)
        free = humanize.naturalsize(node.stats.memory_free)
        cpu = node.stats.cpu_cores

        fmt = f'**WaveLink:** `{wavelink.__version__}`\n\n' \
              f'Connected to `{len(self.bot.wavelink.nodes)}` nodes.\n' \
              f'Best available Node `{self.bot.wavelink.get_best_node().__repr__()}`\n' \
              f'`{len(self.bot.wavelink.players)}` players are distributed on nodes.\n' \
              f'`{node.stats.players}` players are distributed on server.\n' \
              f'`{node.stats.playing_players}` players are playing on server.\n\n' \
              f'Server Memory: `{used}/{total}` | `({free} free)`\n' \
              f'Server CPU: `{cpu}`\n\n' \
              f'Server Uptime: `{datetime.timedelta(milliseconds=node.stats.uptime)}`'
        await ctx.send(fmt)

    @commands.command()
    async def seek(self, ctx, time):
        """Jump to a certain time of the song
        ex. seek 0 (jump to 0s - beginning)
            seek 4:30 (jump to 4m30s)
            seek 1:15:10 (jump to 1h15m10s)"""
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return await ctx.send('I am not currently connected to voice!')
        if not player.is_playing:
            return await ctx.send('I am not currently playing anything!')

        *_, h, m, s = f"::{time}".split(':')
        if all([not t.isdigit() for t in [h, m, s]]):
            return await ctx.send('Invalid time inputted! Ex:\n'
                                  'seek 0 (jump to 0s - beginning)\n'
                                  'seek 4:30 (jump to 4m30s)\n'
                                  'seek 1:15:10 (jump to 1h15m10s)')

        h = 0 if not h.isdigit() else int(h)
        m = 0 if not m.isdigit() else int(m)
        s = 0 if not s.isdigit() else int(s)

        ms = h*60*60*1000 + m*60*1000 + s*1000

        if ms == 0:
            await ctx.send(f'{ctx.author} moved the song to the beginning', delete_after=10)
        elif ms > player.current.length:
            return await ctx.send('The inputted time is longer than the song!')
        else:
            await ctx.send(f'{ctx.author} skipped the song to {f"{h}h" if h else ""}{f"{m}m" if m else ""}{f"{s}s" if s else ""}', delete_after=10)

        await player.seek(ms)

    # Custom playlist stuff:

    @commands.group(invoke_without_command=True)
    async def playlist(self, ctx, *, name):
        url = self._playlists.get(name)
        if url:
            await ctx.invoke(self.play_, query=url)
        else:
            await ctx.send(f'Unable to find a saved playlist/song with that name. All saved playlists are listed here:')
            await ctx.invoke(self.list)

    @playlist.command()
    async def add(self, ctx, name, link):
        """Add a new playlist/song to save.
        Names with multiple words must be quoted ex. add "cool playlist" youtube.com/..."""
        name = name.lower()
        if name in self._playlists:
            return await ctx.send('Sorry that name is already taken, please try again with a different name')
        else:
            try:
                self._playlists[name] = link
            except:
                return await ctx.send('An error has occurred.')
            else:
                await ctx.message.add_reaction('\U00002705')  # React with checkmark
                await ctx.send(f'Added playlist `{name}`, with link: `{link}`')

    @playlist.command()
    async def remove(self, ctx, *, name):
        """Remove a saved playlist/song by name"""
        if name not in self._playlists:
            return await ctx.send('Sorry, I am unable to find the playlist with that name.')
        try:
            del self._playlists[name]
        except:
            await ctx.send('An error has occurred.')
        else:
            await ctx.message.add_reaction('\U00002705')  # React with checkmark
            await ctx.send(f'Removed playlist `{name}`')

    @playlist.command()
    async def list(self, ctx):
        """List all saved playlists/songs"""
        formatted = '\n'.join([f'[{k}]({v})' for k, v in self._playlists.items()])

        e = discord.Embed(title="Saved Playlists",
                          colour=discord.Color.red(),
                          description=formatted)

        await ctx.send(embed=e)

    @playlist.command()
    @commands.is_owner()
    async def save(self, ctx):
        try:
            self.save_playlists()
        except Exception as e:
            await ctx.send(f'An error has occurred: `{e}` ')
        else:
            await ctx.message.add_reaction('\U00002705')

    def save_playlists(self):
        with open('data/playlists.json', 'w') as f:
            json.dump(self._playlists, f, indent=2)

    # noinspection PyCallingNonCallable
    @tasks.loop(hours=6)
    async def save_playlists_to_json(self):
        self.save_playlists()


def setup(bot):
    bot.add_cog(Music(bot))