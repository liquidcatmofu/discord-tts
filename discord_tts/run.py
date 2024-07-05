import io
import os
import queue
import sqlite3
from dotenv import load_dotenv
import discord
from discord import ApplicationContext, ChannelType, Embed
from discord.abc import GuildChannel
from discord.ext import tasks, pages
from discord.commands import SlashCommandGroup, Option
from vv_wrapper import call, database
import voicemanager

intents = discord.Intents(
    messages=True,
    guilds=True,
    members=True,
    voice_states=True,
    message_content=True,
)

if not load_dotenv(verbose=True):
    with open(".env", "w", encoding="utf-8") as f:
        f.write("TOKEN=\n")
        f.write("TEST_GUILD=\n")
token = os.getenv("TOKEN")
if not token:
    print("Failed to load token")
    raise FileNotFoundError("Failed to load token")
if os.getenv("TEST_GUILD"):
    print("Starting as Test Bot")
    test_guild = [i for i in map(int, os.getenv("TEST_GUILD").split(","))]
    bot = voicemanager.VoiceManagedBot(debug_guilds=test_guild, intents=intents)
else:
    print("Starting as Public Bot")
    bot = voicemanager.VoiceManagedBot(intents=intents)

vm = bot.voice_manager
database.DictionaryLoader.set_db_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictionary.db"))

# group_dictionary = SlashCommandGroup("dictionary", "辞書操作コマンド")


@bot.event
async def on_ready():
    """Event handler for bot ready."""
    print(f"logged in as {bot.user}")
    print(f"guilds: {[(g.name, g.id) for g in bot.guilds]}")
    database.SettingLoader.create_table()
    for guild in bot.guilds:
        database.DictionaryLoader.create_table(guild.id)
        vm.set_replacer(guild.id)
        vm.guild_settings.auto_load(guild.id, )

    # await bot.change_presence()


@bot.event
async def on_message(message: discord.Message):
    """Event handler for receiving message."""
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
    print(message.clean_content)
    vm.speak_message_q.put(message)


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Event handler for guild join."""
    database.DictionaryLoader.create_table(guild.id)
    vm.set_replacer(guild.id)
    vm.guild_settings.auto_load(guild.id)


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """Event handler for voice state update."""
    if member.id == bot.user.id:
        if after.channel is None:
            if vm.voice_client:
                await vm.disconnect()
                print("Disconnected")
                return
    if member.bot:
        return
    if vm.voice_client is None:
        return
    if not vm.guild_settings.get(vm.voice_client.guild.id).read_joinleave:
        return
    replacer = vm.user_replacers.get(member.id)

    if after.channel is not None:
        if after.channel.id == vm.voice_client.channel.id:
            if before.channel == after.channel:
                return
            vm.speak(f"{replacer.replace(member.display_name)}さんが参加しました", guild=member.guild.id)
            return
    elif before.channel is not None:
        if before.channel.id == vm.voice_client.channel.id:
            if after.channel == before.channel:
                return
            vm.speak(f"{replacer.replace(member.display_name)}さんが退出しました", guild=member.guild.id)
            return


@tasks.loop(seconds=0.1)
async def say_clock():
    """Check if the bot is speaking and play the next source if it is not playing."""
    if not vm.voice_client:
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
    """Check the response time of the bot."""
    await ctx.respond(f":ping_pong: {round(bot.latency * 1000, 2)}ms")


@bot.slash_command(description="ボイスチャンネルに接続する")
async def join(
        ctx: ApplicationContext,
        vc: Option(GuildChannel, channel_types=[ChannelType.voice], required=False, description="接続するVC"),
        force: Option(bool, default=False, description="他で接続中でも強制的に接続させます")
):
    """Connect to the voice channel."""
    if ctx.voice_client != vm.voice_client:
        vm.voice_client = ctx.voice_client
        await ctx.respond("エラーが発生しました\n再度コマンドを実行してください")
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
    """Disconnect from the voice channel."""
    if ctx.voice_client != vm.voice_client:
        vm.voice_client = ctx.voice_client
        await ctx.respond("エラーが発生しました\n再度コマンドを実行してください")
    if ctx.voice_client:
        await vm.disconnect()
        await ctx.respond(f"切断しました")
        say_clock.stop()
    else:
        await ctx.respond("接続されていません")


bot.load_extension("cog")


def run(token: str):
    bot.run(token)


if __name__ == '__main__':
    run(token)
