import io
import re
import threading
import time
import warnings
from queue import Empty, Queue
from subprocess import DEVNULL
from typing import Optional, overload

import discord
from discord import VoiceProtocol, VoiceClient
from discord.ext import bridge

from vv_wrapper import call, database

UserID = int
ChannelID = int
GuildID = int


class VoiceManagedBot(bridge.AutoShardedBot):
    """A subclass of discord.Bot that has a VoiceManager instance."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voice_manager: VoiceManager = VoiceManager(self)
        self.start_time: float = time.time()

    @property
    def voice_clients(self) -> list[VoiceClient]:
        return self._connection.voice_clients

    def get_voice_client(self, guild_id: int) -> Optional[VoiceClient]:
        """
        Get the voice client for a guild.
        :param guild_id: discord guild id
        :return: discord.VoiceClient
        """
        return self._connection._voice_clients.get(guild_id)

    @property
    def voice_clients_dict(self) -> dict[GuildID, VoiceClient]:
        """
        Get the voice clients as a dictionary.
        :return: dict
        """
        return self._connection._voice_clients


class VoiceManager:
    """Manages voice connections and text-to-speech conversion."""
    def __init__(self, bot: VoiceManagedBot):
        self.bot: VoiceManagedBot = bot
        # self.read_channel: discord.TextChannel | None = None
        # self.speak_channel: discord.VoiceChannel | None = None
        # self.voice_client: discord.VoiceClient | None = None

        self.read_channels: dict[GuildID, discord.TextChannel] = {}
        # self.speak_channels: dict[GuildID, discord.VoiceChannel] = {}
        # self.voice_clients: dict[GuildID, discord.VoiceClient] = {}

        self.speak_message_q: Queue[discord.Message | dict[str: str | GuildID | UserID]] = Queue()
        self.speak_source_q: Queue[discord.AudioSource] = Queue()
        self.converter_loop: Optional[bool] = True
        self.converter_thread: Optional[threading.Thread] = None
        self.converter_interval: float = 0.1

        self.user_replacers: database.ReplacerHolder = database.ReplacerHolder("user", {})
        self.guild_replacers: database.ReplacerHolder = database.ReplacerHolder("guild", {})

        self.user_settings: database.SettingHolder = database.SettingHolder("users", {})
        self.guild_settings: database.SettingHolder = database.SettingHolder("guilds", {})

    @property
    def speak_channels(self) -> dict[GuildID, discord.VoiceChannel]:
        return {guild_id: vc.channel for guild_id, vc in self.bot.voice_clients_dict.items()}

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
        await self.disconnect(-1)
        self.qclear()
        # self.voice_clients.clear()
        self.read_channels.clear()
        self.speak_channels.clear()

    def qclear(self):
        """
        Clear the speak_message_q and speak_source_q.
        cleanup the queues.
        :return:
        """
        self.speak_message_q = Queue()
        self.speak_source_q = Queue()

    async def disconnect(self, guild_id: int):
        """
        Disconnect the voice client.
        :param guild_id: discord guild id, if -1, disconnect all voice clients.
        :return:
        """
        if self.bot.voice_clients_dict:

            if guild_id > 0:
                try:
                    await self.bot.voice_clients_dict[guild_id].disconnect()
                    self.read_channels.pop(guild_id)
                    # self.voice_clients.pop(guild_id)
                except KeyError:
                    warnings.warn(f"Voice client not found for guild {guild_id}", RuntimeWarning)
                    # self.bot.voice_clients_dict.pop(guild_id, None)
            else:
                self.stop_converter()
                self.qclear()
                for vc in self.bot.voice_clients_dict.values():
                    await vc.disconnect()
                # self.voice_clients.clear()
            # self.start_converter()
        else:
            warnings.warn(f"No voice client to disconnect at guild {guild_id}", RuntimeWarning)

    async def connect(self, channel: discord.VoiceChannel, guild_id: int) -> discord.VoiceClient:
        """
        Connect to a voice channel.
        :param channel: discord voice channel
        :param guild_id: discord guild id
        :return:
        """
        if self.bot.voice_clients_dict.get(guild_id) is None:
            await channel.connect()
        else:
            await self.bot.voice_clients_dict[guild_id].move_to(channel)
        if self.converter_thread is None or not self.converter_thread.is_alive():
            self.start_converter()
        return self.bot.voice_clients_dict[guild_id]

    def _converter(self):
        """
        The main loop of the converter thread.
        get the text from the speak_message_q and convert it to audio.
        put the audio in the speak_source_q.
        apply the user and guild settings to the text.
        :return:
        """
        while self.converter_loop:
            user_settings: Optional[database.UserSetting] = None
            server_settings: Optional[database.GuildSetting] = None
            message_type: Optional[discord.MessageType] = None
            ignore_users: list[UserID] = []
            ignore_roles: list[UserID] = []
            reply: str = ""
            try:
                message = self.speak_message_q.get()
                if isinstance(message, discord.Message):
                    text: str = message.clean_content
                    guild: int = message.guild.id
                    user: discord.user = message.author
                    message_type: discord.MessageType = message.type
                elif isinstance(message, dict):
                    text: str = message.get("text")
                    guild: int = message.get("guild")
                    user: discord.user = message.get("user")
                else:
                    raise TypeError(f"message is not discord.Message or dict, but {type(message).__name__}")
            except Empty:
                continue

            if guild is not None:
                server_settings = self.guild_settings.get(guild)
                ignore_users = server_settings.ignore_users
                ignore_roles = server_settings.ignore_roles

            if user is not None:
                if user.id in ignore_users:
                    continue
                if any(role.id in ignore_roles for role in user.roles):
                    continue
                userdict = self.user_replacers.get(user.id)
                if message_type == discord.MessageType.reply:
                    if server_settings.read_replyuser:
                        reply += f"{self.bot.get_message(message.reference.message_id).author.display_name}へ"
                    reply += f"リプライ、"

                user_settings = self.user_settings.get(user.id)
                reply = userdict.replace(reply)
                text = userdict.replace(text)

            if guild is not None:
                text = self.guild_replacers.get(guild).replace(text)
                if server_settings.read_length:
                    if len(text) > server_settings.read_length:
                        text = text[:server_settings.read_length] + "、以下省略"

            text = reply + text
            split = re.split("[。、\n]", text)

            for t in split:
                if user is not None:
                    wav = call.VoiceVox.synth_from_settings(t, user_settings)
                elif guild is not None:
                    wav = call.VoiceVox.synth_from_settings(t, server_settings)
                else:
                    wav = call.VoiceVox.synthesize(t)
                source = discord.FFmpegOpusAudio(io.BytesIO(wav), pipe=True, stderr=DEVNULL)
                self.speak_source_q.put(source)

            time.sleep(self.converter_interval)

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
        :return: None
        """
        self.converter_loop = False
        if join:
            self.converter_thread.join()

    def speak(self, text: str, guild: int = None, user: discord.user = None):
        """
        Speak the text.
        add the text to the speak_message_q.
        :param text: content of the message
        :param guild: discord guild id to apply the guild settings and replacers
        :param user: discord user id to apply the user settings and replacers
        :return: None
        """
        self.speak_message_q.put({"text": text, "guild": guild, "user": user})
