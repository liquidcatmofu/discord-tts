import asyncio
import io
from queue import Empty, Queue
import sqlite3
import threading
import time
import discord
from vv_wrapper import call, database


class VoiceManagedBot(discord.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voice_manager: VoiceManager = VoiceManager(self)


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

        self.user_replacers: database.ReplacerHolder = database.ReplacerHolder("user", {})
        self.guild_replacers: database.ReplacerHolder = database.ReplacerHolder("guild", {})

        self.user_settings: database.SettingHolder = database.SettingHolder("users", {})
        self.guild_settings: database.SettingHolder = database.SettingHolder("guilds", {})

        # self.speakers: dict[str: dict[str: str]] = {}

    @property
    def speakers(self) -> call.SpeakersHolder:
        return call.VoiceVox.get_speakers()

    # @property
    # def user_settings(self) -> dict[int: database.BaseSetting]:
    #     if self.user_settings is None:
    #         self.user_settings = database.SettingLoader.smart_fetch("users", )
    #     return self.user_settings
    #
    # @user_settings.setter
    # def user_settings(self, value: dict[int: database.BaseSetting]):
    #     self.user_settings = value


    def get_user_setting(self, user_id: int) -> database.UserSetting:
        if self.user_settings.get(user_id) is None:
            self.user_settings[user_id] = database.SettingLoader.smart_fetch(user_id, "users", True)
        return self.user_settings[user_id]

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
        self.guild_replacers.auto_load(guild_id)
        # self.guild_replacers[guild_id] = database.DictionaryLoader.auto_read(guild_id, "guild")
        # try:
        #     print("try")
        #     data = database.DictionaryLoader.fetch_dictionaries(guild_id, "guild")
        # except sqlite3.OperationalError:
        #     database.DictionaryLoader.create_table(guild_id)
        #     data = database.DictionaryLoader.fetch_dictionaries(guild_id)
        # print(data)
        # regex, simple = self._set_replacer(data)
        # if self.guild_replacers.get(guild_id) is None:
        #     self.guild_replacers[guild_id] = database.Replacer(regex, simple)
        # else:
        #     self.guild_replacers[guild_id].update_replacements(regex, simple)

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

    # def _user_replacer(self, user_id: int) -> database.Replacer:
    #     try:
    #         u = database.DictionaryLoader.fetch_dictionaries(user_id, "user")
    #     except sqlite3.OperationalError:
    #         database.DictionaryLoader.create_table(user_id, "user")
    #         u = database.DictionaryLoader.fetch_dictionaries(user_id, "user")
    #     regex, simple = self._set_replacer(u)
    #     return database.Replacer(regex, simple)

    def _converter(self):
        while self.converter_loop:
            user_settings: database.UserSetting | None = None
            server_settings: database.GuildSetting | None = None
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

            if guild is not None:
                server_settings = self.guild_settings.get(guild)

            print(text, guild, user)
            if user is not None:
                userdict = self.user_replacers.get(user)
                if message_type == discord.MessageType.reply:
                    if server_settings.read_replyuser:
                        reply += f"{self.bot.get_message(message.reference.message_id).author.display_name}へ"
                    reply += f"リプライ、"

                user_settings = self.user_settings.get(user)
                reply = userdict.replace(reply)
                text = userdict.replace(text)

            if guild is not None:
                print(server_settings)
                print(self.guild_replacers)
                text = self.guild_replacers.get(guild).replace(text)



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
