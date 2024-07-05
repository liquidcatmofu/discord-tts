import io
import re
from queue import Empty, Queue
from subprocess import DEVNULL
import threading
import time
import discord
from vv_wrapper import call, database


class VoiceManagedBot(discord.Bot):
    """A subclass of discord.Bot that has a VoiceManager instance."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voice_manager: VoiceManager = VoiceManager(self)


class VoiceManager:
    """Manages voice connections and text-to-speech conversion."""
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

    @property
    def speakers(self) -> call.SpeakersHolder:
        """
        Get the available speakers from VoiceVox.
        :return: A SpeakersHolder object containing the available speakers.
        """
        return call.VoiceVox.get_speakers()


    def get_user_setting(self, user_id: int) -> database.UserSetting:
        """
        Get the user setting for a user.
        If the setting is not loaded, load it from the database.
        :param user_id: discord user id
        :return: UserSetting object
        """
        if self.user_settings.get(user_id) is None:
            self.user_settings[user_id] = database.SettingLoader.smart_fetch("users", user_id, True)
        return self.user_settings[user_id]

    def set_replacer(self, guild_id: int) -> None:
        """
        Set the replacers for a guild.
        load the replacers from the database.
        :param guild_id:
        :return: None
        """
        self.guild_replacers.auto_load(guild_id)

    def set_replacers(self, guild_ids: list[int]) -> None:
        """
        Set the replacers for multiple guilds.
        :param guild_ids:
        :return:
        """
        for guild_id in guild_ids:
            self.set_replacer(guild_id)

    async def stop(self):
        """
        Stop the voice manager.
        :return:
        """
        await self.disconnect()
        self.qclear()
        self.voice_client = None
        self.read_channel = None
        self.speak_channel = None

    def qclear(self):
        """
        Clear the speak_message_q and speak_source_q.
        cleanup the queues.
        :return:
        """
        self.speak_message_q = Queue()
        self.speak_source_q = Queue()

    async def disconnect(self):
        """
        Disconnect the voice client.
        :return:
        """
        if self.voice_client is not None:
            self.stop_converter()
            await self.voice_client.disconnect()
            self.voice_client = None
            self.start_converter()

    async def connect(self, channel: discord.VoiceChannel) -> discord.Client:
        """
        Connect to a voice channel.
        :param channel:
        :return:
        """
        if self.voice_client is None:
            self.voice_client = await channel.connect()
        else:
            await self.voice_client.move_to(channel)
        self.start_converter()
        return self.voice_client

    def _converter(self):
        """
        The main loop of the converter thread.
        get the text from the speak_message_q and convert it to audio.
        put the audio in the speak_source_q.
        apply the user and guild settings to the text.
        :return:
        """
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
                text = self.guild_replacers.get(guild).replace(text)
                if server_settings.read_length:
                    if len(text) > server_settings.read_length:
                        text = text[:server_settings.read_length] + "、以下省略"

            text = reply + text
            print(text)
            text = re.split("[。、\n]", text)

            for t in text:
                if user is not None:
                    wav = call.VoiceVox.synth_from_settings(t, user_settings)
                elif guild is not None:
                    wav = call.VoiceVox.synth_from_settings(t, server_settings)
                else:
                    wav = call.VoiceVox.synthesize(t)
                source = discord.FFmpegOpusAudio(io.BytesIO(wav), pipe=True, stderr=DEVNULL)
                self.speak_source_q.put(source)

            time.sleep(0.3)

    def start_converter(self):
        """
        Start the converter thread.
        :return:
        """
        self.converter_loop = True
        self.converter_thread = threading.Thread(target=self._converter)
        self.converter_thread.start()

    def stop_converter(self, join: bool = False) -> None:
        """
        Stop the converter thread.
        :param join: whether to wait for the thread to finish
        :return:
        """
        self.converter_loop = False
        if join:
            self.converter_thread.join()

    def speak(self, text: str, guild: int = None, user: int = None):
        """
        Speak the text.
        add the text to the speak_message_q.
        :param text: content of the message
        :param guild: discord guild id to apply the guild settings and replacers
        :param user: discord user id to apply the user settings and replacers
        :return:
        """
        self.speak_message_q.put({"text": text, "guild": guild, "user": user})
