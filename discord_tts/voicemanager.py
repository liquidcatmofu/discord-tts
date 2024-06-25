import asyncio
import io
from queue import Empty, Queue
import sqlite3
import threading
import time
import discord
from vv_wrapper import call, database


class VoiceManager:
    def __init__(self, bot: discord.Bot):
        self.bot: discord.Bot = bot
        self.read_channel: discord.TextChannel | None = None
        self.speak_channel: discord.VoiceChannel | None = None
        self.voice_client: discord.VoiceClient | None = None

        self.speak_message_q: Queue[discord.Message | dict[str: str | int]] = Queue()
        self.speak_source_q: Queue[discord.AudioSource] = Queue()
        self.converter_loop: bool = True
        self.converter_thread: threading.Thread | None = None

        self.replacers: dict[int: database.Replacer] = {}
        self.user_replacers: dict[int: database.Replacer] = {}

        self.user_settings: dict[int: database.BaseSetting] = {}
        self.guild_settings: dict[int: database.BaseSetting] = {}

    @staticmethod
    def _set_replacer(data: list[tuple[int, str, str, bool]]) -> tuple[dict[str, str], dict[str, str]]:
        regex_replacements = {}
        simple_replacements = {}
        for d in data:
            print("data:", d)
            before = d[1]
            after = d[2]
            use_regex = d[3]
            if use_regex:
                regex_replacements[before] = after
            else:
                simple_replacements[before] = after
        return regex_replacements, simple_replacements

    def set_replacer(self, guild_id: int) -> None:
        # for guild_id in guild_ids:
        try:
            print("try")
            data = database.Dictionary.fetch_dictionaries(guild_id, "guild")
        except sqlite3.OperationalError:
            database.Dictionary.create_table(guild_id)
            data = database.Dictionary.fetch_dictionaries(guild_id)
        print(data)
        regex, simple = self._set_replacer(data)
        if self.replacers.get(guild_id) is None:
            self.replacers[guild_id] = database.Replacer(regex, simple)
        else:
            self.replacers[guild_id].update_replacements(regex, simple)

    def set_replacers(self, guild_ids: list[int]) -> None:
        for guild_id in guild_ids:
            self.set_replacer(guild_id)

    async def stop(self):
        await self.disconnect()
        self.qclear()
        self.voice_client = None
        self.read_channel = None
        self.speak_channel = None

    def qclear(self):
        self.speak_message_q = Queue()
        self.speak_source_q = Queue()

    async def disconnect(self):
        if self.voice_client is not None:
            self.stop_converter()
            await self.voice_client.disconnect()
            self.voice_client = None
            self.start_converter()

    async def connect(self, channel: discord.VoiceChannel) -> discord.Client:
        if self.voice_client is None:
            self.voice_client = await channel.connect()
        else:
            await self.voice_client.move_to(channel)
        self.start_converter()
        return self.voice_client

    def _user_replacer(self, user_id: int) -> database.Replacer:
        try:
            u = database.Dictionary.fetch_dictionaries(user_id, "user")
        except sqlite3.OperationalError:
            database.Dictionary.create_table(user_id, "user")
            u = database.Dictionary.fetch_dictionaries(user_id, "user")
        regex, simple = self._set_replacer(u)
        return database.Replacer(regex, simple)

    def _converter(self):
        while self.converter_loop:
            userdict: database.Replacer | None = None
            user_settings: database.UserSetting | None = None
            server_settings: database.ServerSetting | None = None
            message_type: discord.MessageType | None = None
            reply: str = ""
            try:
                message = self.speak_message_q.get()
                if isinstance(message, discord.Message):
                    text = message.clean_content
                    guild = message.guild.id
                    user = message.author.id
                    message_type = message.type
                elif isinstance(message, dict):
                    text = message.get("text")
                    guild = message.get("guild")
                    user = message.get("user")
                else:
                    raise TypeError(f"message is not discord.Message or dict, but {type(message).__name__}")
            except Empty:
                continue

            if message_type == discord.MessageType.reply:
                if server_settings.read_replyuser:
                    reply += f"{self.bot.get_message(message.reference.message_id).author.display_name}へ"
                reply += f"リプライ、"

            print(text, guild, user)
            if user is not None:
                userdict = self.user_replacers.get(user)
                user_settings = self.user_settings.get(user)
                if userdict is None:
                    userdict = self.user_replacers[user] = self._user_replacer(user)
                if user_settings is None:
                    user_settings = self.user_settings[user] = database.SettingLoader.smart_fetch("users", user)
                    if user_settings is None:
                        database.SettingLoader.add_setting("users", user)
                        user_settings = self.user_settings[user] = database.SettingLoader.smart_fetch("users", user)
                reply = userdict.replace(reply)
                text = userdict.replace(text)

            if guild is not None:
                server_settings = self.guild_settings.get(guild)
                if server_settings is None:
                    server_settings = self.guild_settings[guild] = database.SettingLoader.smart_fetch("guilds", guild)
                    if server_settings is None:
                        database.SettingLoader.add_setting("guilds", guild)
                        server_settings = self.guild_settings[guild] = database.SettingLoader.smart_fetch("guilds",
                                                                                                          guild)
                print(self.replacers)
                text = self.replacers.get(guild, database.Replacer({}, {})).replace(text)

            text = reply + text
            print(server_settings, "\n", user_settings)

            if user is not None:
                wav = call.VoiceVox.synth_from_settings(text, user_settings)
            elif guild is not None:
                wav = call.VoiceVox.synth_from_settings(text, server_settings)
            else:
                wav = call.VoiceVox.synthesize(text)
            source = discord.FFmpegOpusAudio(io.BytesIO(wav), pipe=True)
            self.speak_source_q.put(source)

            time.sleep(0.3)


    def start_converter(self):
        self.converter_loop = True
        self.converter_thread = threading.Thread(target=self._converter)
        self.converter_thread.start()

    def stop_converter(self, join: bool = False) -> None:
        self.converter_loop = False
        if join:
            self.converter_thread.join()

    def speak(self, text: str, guild: int = None, user: int = None):
        self.speak_message_q.put({"text": text, "guild": guild, "user": user})

    def play(self, source: discord.AudioSource | None = None):
        if self.voice_client is None:
            raise discord.ClientException('voice client is not connected')
        if source is None:
            source = self.speak_source_q.get()
        self.voice_client.play(source)
