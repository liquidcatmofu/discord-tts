import asyncio
import io
import os
import queue
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
bot = discord.Bot(debug_guilds=test_guild, intents=intents)

vm = voicemanager.VoiceManager(bot)
database.Dictionary.set_db_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictionary.db"))

group_dictionary = SlashCommandGroup("dictionary", "辞書操作コマンド", guild_ids=test_guild)


@bot.event
async def on_ready():
    print(f"logged in as {bot.user}")
    print(f"guilds: {bot.guilds}")
    database.SettingLoader.create_table()
    for guild in bot.guilds:
        database.Dictionary.create_table(guild.id)
        vm.set_replacer(guild.id)
    # await bot.change_presence()


@bot.event
async def on_message(message: discord.Message):
    print(message.guild, message.channel, message.content)
    pprint(repr(message))
    if vm.read_channel is None:
        return

    if vm.read_channel.id != message.channel.id:
        return

    if message.author.bot:
        return
    vm.speak_message_q.put(message)


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
    a = call.VoiceVox.getspeakers()
    res = ""
    for i in a:
        res += f'### { i["name"]}\n'
        for j in i["styles"]:
            res += f'- {j["name"]} {j["id"]}\n'

    await ctx.respond(res)


@group_dictionary.command(name="add", description="辞書を追加する")
async def add(ctx: ApplicationContext, before: str, after: str, use_regex: bool = False):
    replacer = vm.replacers.get(ctx.guild.id)
    if replacer is None:
        database.Dictionary.create_table(ctx.guild.id)
    database.Dictionary.add_dictionary(ctx.guild.id, before, after, use_regex)
    vm.set_replacer(ctx.guild.id)
    embed = Embed(title="辞書追加",
                  description=f"### 単語\n# ```{before}```\n### 読み\n# ```{after}```\n### 正規表現: {'使用する' if use_regex else '使用しない'}")
    await ctx.respond(embed=embed)


@group_dictionary.command(name="delete", description="辞書を削除する")
async def delete(ctx: ApplicationContext, before: str):
    replacer = vm.replacers.get(ctx.guild.id)
    if replacer is None:
        database.Dictionary.create_table(ctx.guild.id)
        await ctx.respond("辞書が存在しません")
        return
    database.Dictionary.delete_dictionary(ctx.guild.id, before)
    vm.set_replacer(ctx.guild.id)
    embed = Embed(title="辞書削除", description=f"### 単語\n# ```{before}```")
    await ctx.respond(embed=embed)


@group_dictionary.command(name="list", description="辞書を表示する")
async def dictionary_list(ctx: ApplicationContext):
    replacer = vm.replacers.get(ctx.guild.id)
    if replacer is None:
        database.Dictionary.create_table(ctx.guild.id)
        await ctx.respond("辞書が存在しません")
        return
    data = database.Dictionary.fetch_dictionaries(ctx.guild.id)
    await ctx.respond(f"{len(data)}件の辞書が登録されています\n")
    res = ""
    for d in data:
        res += f"単語\n## ```{d[1]}```\n読み\n## ```{d[2]}```\n正規表現: {'使用する' if d[3] else '使用しない'}\n\n"
    await ctx.channel.send(res)


@group_dictionary.command(name="update", description="辞書を更新する")
async def update(ctx: ApplicationContext, old_before: str, new_before: str, after: str, use_regex: bool = False):
    replacer = vm.replacers.get(ctx.guild.id)
    if replacer is None:
        database.Dictionary.create_table(ctx.guild.id)
        await ctx.respond("辞書が存在しません")
        return
    database.Dictionary.update_dictionary(ctx.guild.id, old_before, new_before, after, use_regex)
    vm.set_replacer(ctx.guild.id)
    embed = Embed(title="辞書更新",
                  description=f"### 変更前単語\n```{old_before}```\n### 単語\n# ```{new_before}```\n### 読み\n# ```{after}```\n### 正規表現: {'使用する' if use_regex else '使用しない'}")
    await ctx.respond(embed=embed)


bot.add_application_command(group_dictionary)


def run(token: str):
    bot.run(token)


if __name__ == '__main__':
    run(token)
