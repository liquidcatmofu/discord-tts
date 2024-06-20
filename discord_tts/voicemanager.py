import asyncio
import io
from queue import Empty, Queue
import sqlite3
import threading
import time
import discord
from vv_wrapper import call, dictionary


class VoiceManager:
    def __init__(self, bot: discord.Bot):
        self.bot: discord.Bot = bot
        self.read_channel: discord.TextChannel | None = None
        self.speak_channel: discord.VoiceChannel | None = None
        self.voice_client: discord.VoiceClient | None = None

        self.speak_text_q: Queue[tuple[str, int, int]] = Queue()
        self.speak_source_q: Queue[discord.AudioSource] = Queue()
        self.converter_loop: bool = True
        self.converter_thread: threading.Thread | None = None

        self.replacers: dict[int: dictionary.EfficientReplacer] = {}

    def set_replacer(self, guild_id: int) -> None:
        # for guild_id in guild_ids:
        try:
            data = dictionary.Dictionary.fetch_dictionaries(guild_id)
        except sqlite3.OperationalError:
            dictionary.Dictionary.create_table(guild_id)
            data = dictionary.Dictionary.fetch_dictionaries(guild_id)

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
        if self.replacers.get(guild_id) is None:
            self.replacers[guild_id] = dictionary.EfficientReplacer(regex_replacements, simple_replacements)
        else:
            self.replacers[guild_id].update_replacements(regex_replacements, simple_replacements)

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
        self.speak_text_q = Queue()
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

    def _converter(self):
        while self.converter_loop:
            try:
                text, guild, user = self.speak_text_q.get()
            except Empty:
                pass
            else:
                print(text, guild, user)
                if guild is not None:
                    print(self.replacers)
                    text = self.replacers.get(guild, dictionary.EfficientReplacer({}, {})).replace(text)
                wav = call.VoiceVox.synthesize(text)
                source = discord.FFmpegOpusAudio(io.BytesIO(wav), pipe=True)
                self.speak_source_q.put(source)
            finally:
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
        self.speak_text_q.put((text, guild, user))

    def play(self, source: discord.AudioSource | None = None):
        if self.voice_client is None:
            raise discord.ClientException('voice client is not connected')
        if source is None:
            source = self.speak_source_q.get()
        self.voice_client.play(source)
