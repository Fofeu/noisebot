import asyncio
from aioconsole import ainput
from aioconsole import aprint

import discord

from discord.ext import commands

import os
import glob
import fnmatch
import json

conf = None
with open('./conf.json') as f:
  conf = json.load(f)

base_path = os.path.abspath(os.path.expanduser(conf['path']))
token = conf['token']

def either(c):
  return'[%s%s]' % (c.lower(), c.upper()) if c.isalpha() else c

def name_to_glob(name):
  return '*' + ''.join(map(either, name)) + '*'

async def repl(bot):
  cont = True
  state = "GetCommand"
  cmd = None
  guild = None
  channel = None
  song_candidates = []
  song = None
  connected_channel = None
  voice_client = None
  source = None
  while cont:
    if state == "GetCommand":
      cmd = await ainput("State your command: ")
      if cmd == "exit":
        cont = False
        await bot.close()
      elif cmd == "join":
        state = "JoinGuildInput"
      elif cmd == "disconnect":
        state = "Disconnect"
      elif cmd == "play":
        state = "PlayInit"
      elif cmd == "pause":
        state = "Pause"
      elif cmd == "resume":
        state = "Resume"
      elif cmd == "stop":
        state = "Stop"
      elif cmd == "volume":
        state = "Volume"
      else:
        await aprint("Unknown command")
    elif state == "JoinGuildInput":
      guild = await ainput("Guild: ")
      state = "JoinGuildMatch"
    elif state == "JoinGuildMatch":
      guilds = [g for g in bot.guilds if g.name == guild]
      if len(guilds) == 0:
        state = "GetCommand"
      elif len(guilds) == 1:
        guild = guilds[0]
        state = "JoinChannelInput"
      else:
        await aprint("Multiple guild match {}".format(guilds))
        state = "GetCommand"
    elif state == "JoinChannelInput":
      channel = await ainput("Channel: ")
      state = "JoinChannelMatch"
    elif state == "JoinChannelMatch":
      vcs = [vc for vc in guild.voice_channels if vc.name == channel]
      if len(vcs) == 0:
        await aprint("No match")
        state = "GetCommand"
      elif len(guilds) == 1:
        channel = vcs[0]
        state = "JoinConnect"
      else:
        await aprint("Multiple channels match {}".format(vcs))
        state = "GetCommand"
    elif state == "JoinConnect":
      try:
        if voice_client is not None:
          await voice_client.disconnect()
        voice_client = await channel.connect()
        connected_channel = channel
      except asyncio.TimeoutError:
        await aprint("Timeout")
      except discord.ClientException:
        await aprint("Client Exception: Probably already connected")
      except discord.OpusNotLoaded:
        await aprint("Opus library is not loaded")
      state = "GetCommand"
    elif state == "Disconnect":
      if voice_client is not None:
        await voice_client.disconnect()
      state = "GetCommand"
    elif state == "PlayInit":
      song_candidates = []
      state = "PlaySongGet"
    elif state == "PlaySongGet":
      if song_candidates == []:
        await aprint("No selected song")
      else:
        await aprint("Current song candidates:{}")
        for s in song_candidates:
          await aprint("  {}".format(s))
      await aprint("")
      await aprint("Select option: ")
      await aprint("  1: Select candidate")
      await aprint("  2: Search candidate")
      await aprint("  3: Clear candidates")
      await aprint("  4: Cancel")
      op = await ainput("[1/2/3/4]: ")
      if op == "1":
        state = "PlaySongSelect"
      elif op == "2":
        state = "PlaySongSearch"
      elif op == "3":
        state = "PlayInit"
      elif op == "4":
        state = "GetCommand"
      else:
        await aprint("Unknown option")
    elif state == "PlaySongSelect":
      if song_candidates == []:
        await aprint("No Selectable song")
        state = "PlaySongGet"
      else:
        for (i,s) in enumerate(song_candidates):
          await aprint("[{}] {}".format(i,s))
        choice = await ainput("Select song: ")
        try:
          choice = int(choice)
          if 0 <= choice < len(song_candidates):
            song = song_candidates[choice]
            state = "PlayConstructSource"
          else:
            await aprint("Unknown choice")
            state = "PlaySongGet"
        except:
          await aprint("Unknown choice")
          state = "PlaySongGet"
    elif state == "PlaySongSearch":
      search = await ainput("Enter your search query: ")
      path_search = base_path + '/' + name_to_glob(search)
      l = glob.glob(path_search)
      song_candidates.extend(l)
      state = "PlaySongGet"
    elif state == "PlayConstructSource":

      source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(song,
                               before_options='-fflags +genpts -stream_loop -1'
                               )
      )
      voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

      await aprint('Now playing: {}'.format(song))
      state = "GetCommand"
    elif state == "Pause":
      if voice_client is not None:
        voice_client.pause()
      state = "GetCommand"
    elif state == "Resume":
      if voice_client is not None:
        voice_client.resume()
      state = "GetCommand"
    elif state == "Stop":
      if voice_client is not None:
        voice_client.stop()
      state = "GetCommand"
    elif state == "Volume":
      try:
        if source is not None:
          volume = await ainput("Volume (in percent): ")
          if volume[0] == '+':
            volume = float(volume[1:])
            source.volume += volume/100
          elif volume[0] == '-':
            volume = float(volume[1:])
            source.volume -= volume/100
          else:
            volume = float(volume)
            source.volume = volume/100
      finally:
        state = "GetCommand"
    else:
      await aprint("Unknown state: {}".format(state))
      state = "GetCommand"


intents = discord.Intents.default()

bot = commands.Bot(command_prefix=commands.when_mentioned,
                   description='Relatively simple music bot',
                   intents=intents)
background_task = None

@bot.event
async def on_ready():
  global background_task

  await aprint('Logged in as {0} ({0.id})'.format(bot.user))
  await aprint('------')

  background_task = asyncio.create_task(repl(bot))


bot.run(token)
