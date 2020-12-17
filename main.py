import asyncio

import discord

from discord.ext import commands

import os
import glob
import json

conf = None
with open('./conf.json') as f:
  conf = json.load(f)

base_path = os.path.abspath(os.path.expanduser(conf['path']))
token = conf['token']

def find_file(pat):
  def either(c):
    return'[%s%s]' % (c.lower(), c.upper()) if c.isalpha() else c
  path_search = base_path + '/*' + ''.join(map(either, pat)) + '*'
  print(path_search)
  l = glob.glob(path_search)
  if len(l) == 1:
    return l[0]
  else:
    return l

class Music(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command()
  async def join(self, ctx, *, channel: discord.VoiceChannel):
    """Joins a voice channel"""

    if ctx.voice_client is not None:
        return await ctx.voice_client.move_to(channel)

    await channel.connect()

  @commands.command()
  async def play(self, ctx, *, query):
    """Plays a file from the local filesystem"""

    f = find_file(query)

    if isinstance(f, str):
      source = discord.FFmpegOpusAudio(f, before_options=['stream_loop', '-1'])
      ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

      _,fname = os.path.split(f)
      await ctx.send('Now playing: {}'.format(fname))
    elif isinstance(f, list) and len(f) > 0:
      s = "Your request `{}` matches multiple files: {}".format(query, ['`' + x + '`' for x in f])
      await ctx.send(s)
    elif isinstance(f, list) and len(f) == 0:
      s = "Your request `{}` matches no file".format(query)
      await ctx.send(s)

  @commands.command()
  async def stop(self, ctx):
    """Stops and disconnects the bot from voice"""

    await ctx.voice_client.disconnect()

  @play.before_invoke
  async def ensure_voice(self, ctx):
    if ctx.voice_client is None:
      if ctx.author.voice:
        await ctx.author.voice.channel.connect()
      else:
        await ctx.send("You are not connected to a voice channel.")
        raise commands.CommandError("Author not connected to a voice channel.")
    elif ctx.voice_client.is_playing():
      ctx.voice_client.stop()

bot = commands.Bot(command_prefix=commands.when_mentioned,
                   description='Relatively simple music bot')

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')

bot.add_cog(Music(bot))

bot.run(token)
