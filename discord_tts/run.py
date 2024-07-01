import asyncio
import io
import os
import queue
import sqlite3
import threading
from dotenv import load_dotenv
import discord
from discord import ApplicationContext, ChannelType, Embed
from discord.abc import GuildChannel
from discord.ext import commands, tasks
from discord.commands import slash_command, SlashCommandGroup, Option
from vv_wrapper import call, database
import voicemanager
from pprint import pprint
intents = discord.Intents(
    messages=True,
    guilds=True,
    members=True,
    voice_states=True,
    message_content=True,
)

load_dotenv(verbose=True)
token = os.getenv("TOKEN")
test_guild = [i for i in map(int, os.getenv("TEST_GUILD").split(","))]
bot = voicemanager.VoiceManagedBot(debug_guilds=test_guild, intents=intents)

vm = bot.voice_manager
database.DictionaryLoader.set_db_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictionary.db"))

group_dictionary = SlashCommandGroup("dictionary", "辞書操作コマンド", guild_ids=test_guild)


@bot.event
async def on_ready():
    print(f"logged in as {bot.user}")
    print(f"guilds: {bot.guilds}")
    database.SettingLoader.create_table()
    for guild in bot.guilds:
        database.DictionaryLoader.create_table(guild.id)
        vm.set_replacer(guild.id)
        vm.guild_settings.auto_load(guild.id,)

    # await bot.change_presence()


@bot.event
async def on_message(message: discord.Message):
    print(message.guild, message.channel, message.content, message.mentions)
    print(message.author.display_name, message.author.nick)
    # pprint(repr(message))
    if vm.read_channel is None:
        return

    if vm.read_channel.id != message.channel.id:
        return

    if message.author.bot:
        return
    if not vm.guild_settings.get(message.guild.id).read_nonparticipation:
        if not message.author.voice:
            return
        elif message.author.voice.channel != vm.voice_client.channel:
            return
    vm.speak_message_q.put(message)


@bot.event
async def on_guild_join(guild: discord.Guild):
    database.DictionaryLoader.create_table(guild.id)
    vm.set_replacer(guild.id)
    vm.guild_settings.auto_load(guild.id)


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.bot:
        return
    if vm.voice_client is None:
        print("speak_channel is None")
        return
    if not vm.guild_settings.get(vm.voice_client.guild.id).read_joinleave:
        print("read_joinleave is False")
        return
    replacer = vm.user_replacers.get(member.id)

    if after.channel is not None:
        if after.channel.id == vm.voice_client.channel.id:
            if before.channel == after.channel:
                return
            vm.speak(f"{replacer.replace(member.display_name)}さんが参加しました", guild=member.guild.id)
            print(f"{replacer.replace(member.display_name)}さんが参加しました")
            return
    elif before.channel is not None:
        if before.channel.id == vm.voice_client.channel.id:
            if after.channel == before.channel:
                return
            vm.speak(f"{replacer.replace(member.display_name)}さんが退出しました", guild=member.guild.id)
            print(f"{replacer.replace(member.display_name)}さんが退出しました")
            return


@tasks.loop(seconds=0.5)
async def say_clock():
    if not vm.voice_client.is_connected() or not vm.voice_client:
        await vm.stop()
        say_clock.stop()
        return

    if not vm.voice_client.is_playing():
        try:
            source = vm.speak_source_q.get_nowait()
            vm.voice_client.play(source)

        except queue.Empty:
            return


@bot.slash_command(description="応答速度を確認する")
async def ping(ctx: ApplicationContext):
    await ctx.respond(f"{round(bot.latency * 1000, 2)}ms")


@bot.slash_command(description="ボイスチャンネルに接続する")
async def join(
        ctx: ApplicationContext,
        vc: Option(GuildChannel, channel_types=[ChannelType.voice], required=False, description="接続するVC"),
        force: Option(bool, default=False, description="他で接続中でも強制的に接続させます")
):
    print(vc, ctx.author)
    print(ctx.author.voice)
    if vm.voice_client is not None and not force:
        await ctx.respond(f"既に{vm.voice_client.channel.name}に接続しています\n"
                          f"強制的に接続する場合は`force`オプションをTrueにしてください")
        return

    if vc is None:
        if not ctx.author.voice:
            await ctx.respond("VCに参加するか参加するチャンネルを指定してください")
            return
        else:
            channel = ctx.author.voice.channel
    else:
        channel = vc
    if len(channel.members):
        await ctx.respond(f"{channel.name}に接続しました")
        await vm.connect(channel)
        vm.read_channel = ctx.channel
        vm.qclear()
        vm.speak("接続しました", guild=ctx.guild.id)
        say_clock.start()
        vm.start_converter()

    else:
        await ctx.respond(f"VCに接続中のメンバーがいません")


@bot.slash_command(description="VCを切断する")
async def leave(ctx: ApplicationContext):
    if ctx.voice_client:
        await vm.disconnect()
        await ctx.respond(f"切断しました")
        say_clock.stop()
    else:
        await ctx.respond("接続されていません")


@bot.slash_command()
async def say(
        ctx: ApplicationContext,
        content: Option(str, default="こんにちは")
):
    if ctx.voice_client:
        data = call.VoiceVox.synthesize(content)
        print(data)
        i = io.BytesIO(data)
        await ctx.respond(f"「{content}」と言います")
        vm.voice_client.play(discord.FFmpegOpusAudio(i, pipe=True))
    else:
        await ctx.respond("接続してください")


@bot.slash_command()
async def speakers(ctx: ApplicationContext):
    a = call.VoiceVox.get_speakers_raw()
    res = ""
    for i in a:
        res += f'### { i["name"]}\n'
        for j in i["styles"]:
            res += f'- {j["name"]} {j["id"]}\n'

    await ctx.respond(res)


@group_dictionary.command(name="add", description="辞書を追加する")
async def add(ctx: ApplicationContext, before: str, after: str, use_regex: bool = False):
    replacer = vm.guild_replacers.get(ctx.guild.id)
    print("dictionary add", replacer)
    vm.guild_replacers.add(ctx.guild.id, before, after, use_regex)
    embed = Embed(title="辞書追加",
                  description=f"### 単語\n# ```{before}```\n### 読み\n# ```{after}```\n### 正規表現: {'使用する' if use_regex else '使用しない'}")
    await ctx.respond(embed=embed)


@group_dictionary.command(name="delete", description="辞書を削除する")
async def delete(ctx: ApplicationContext, before: str):
    try:
        vm.guild_replacers.delete(ctx.guild.id, before)
    except sqlite3.OperationalError:
        await ctx.respond("辞書が存在しません")
        return
    embed = Embed(title="辞書削除", description=f"### 単語\n# ```{before}```")
    await ctx.respond(embed=embed)


@group_dictionary.command(name="list", description="辞書を表示する")
async def dictionary_list(ctx: ApplicationContext):
    data = database.DictionaryLoader.fetch_dictionaries(ctx.guild.id)
    if not data:
        await ctx.respond("辞書が存在しません")
        return
    await ctx.respond(f"{len(data)}件の辞書が登録されています\n")
    res = ""
    for d in data:
        res += f"単語\n## ```{d[1]}```\n読み\n## ```{d[2]}```\n正規表現: {'使用する' if d[3] else '使用しない'}\n\n"
    await ctx.channel.send(res)


@group_dictionary.command(name="update", description="辞書を更新する")
async def update(ctx: ApplicationContext, old_before: str, new_before: str, after: str, use_regex: bool = False):
    replacer = vm.guild_replacers.get(ctx.guild.id)
    if not replacer:
        await ctx.respond("辞書が存在しません")
        return
    vm.guild_replacers.update(ctx.guild.id, old_before, new_before, after, use_regex)
    embed = Embed(title="辞書更新",
                  description=f"### 変更前単語\n```{old_before}```\n### 単語\n# ```{new_before}```\n### 読み\n# ```{after}```\n### 正規表現: {'使用する' if use_regex else '使用しない'}")
    await ctx.respond(embed=embed)


bot.add_application_command(group_dictionary)
bot.load_extension("cog")


def run(token: str):
    bot.run(token)


if __name__ == '__main__':
    run(token)
