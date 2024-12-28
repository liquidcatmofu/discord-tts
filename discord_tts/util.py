import discord
from aiohttp.log import client_logger
from discord.ext import tasks
from discord.ext.bridge import BridgeApplicationContext, BridgeExtContext

from voicemanager import VoiceManagedBot


class BridgeCtx(BridgeApplicationContext, BridgeExtContext):
    """
    Used instead of BridgeContext
    because BridgeContext causes annotation errors
    """
    pass


class JoinButton(discord.ui.View):

    def __init__(self, bot: VoiceManagedBot, clock: tasks.Loop):
        self.bot = bot
        self.vm = bot.voice_manager
        self.start_clock = clock
        super().__init__(timeout=None)

    @discord.ui.button(label="参加", style=discord.ButtonStyle.green, custom_id="join_button")
    async def join_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        client = self.vm.voice_clients.get(interaction.guild.id)
        if self.bot.voice_clients:
            if client not in self.bot.voice_clients:
                await interaction.response.send_message(
                    content="エラーが発生しました\n再度実行してください",
                    delete_after=10
                )
                for vc in self.bot.voice_clients:
                    if vc.guild == interaction.guild:
                        self.vm.voice_clients[interaction.guild.id] = vc
                        break
            else:
                await interaction.response.send_message(
                    f"既に<#{client.channel.id}>に接続しています",
                    delete_after=10
                )
                return
        if not interaction.user.voice:
            await interaction.response.send_message("VCに参加してください", delete_after=10)
            return
        vc = interaction.user.voice.channel
        await self.vm.connect(vc, interaction.guild.id)
        await interaction.response.send_message(f"<#{vc.id}>に接続しました", delete_after=10)
        self.vm.read_channels[interaction.guild.id] = interaction.channel
        self.vm.qclear()
        self.vm.speak("接続しました", guild=interaction.guild.id)
        self.start_clock.start()
        self.vm.start_converter()

    @discord.ui.button(label="切断", style=discord.ButtonStyle.red, custom_id="leave_button")
    async def leave_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        client = self.vm.voice_clients.get(interaction.guild.id)
        if self.bot.voice_clients:
            if client not in self.bot.voice_clients:
                await interaction.response.send_message(
                    content="エラーが発生しました\n再度実行してください",
                    delete_after=10
                )
                for vc in self.bot.voice_clients:
                    if vc.guild == interaction.guild:
                        self.vm.voice_clients[interaction.guild.id] = vc
                        break
        if not client:
            await interaction.response.send_message("接続されていません", delete_after=10)
            return
        await self.vm.disconnect(interaction.guild_id)
        await interaction.response.send_message("切断しました", delete_after=10)
        self.start_clock.stop()
