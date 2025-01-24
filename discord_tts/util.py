import discord
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
        print("JoinButton init")
        self.bot = bot
        self.vm = bot.voice_manager
        self.say_clock = clock
        super().__init__(timeout=None)

    # @discord.ui.button(label="参加", style=discord.ButtonStyle.green, custom_id="join_button")
    # async def join_button(self, button: discord.ui.Button, interaction: discord.Interaction):
    #     client = self.bot.voice_clients_dict.get(interaction.guild.id)
    #     if self.bot.voice_clients:
    #         if client not in self.bot.voice_clients:
    #             await interaction.response.send_message(
    #                 content="エラーが発生しました\n再度実行してください",
    #                 delete_after=10
    #             )
    #             # for vc in self.bot.voice_clients:
    #             #     if vc.guild == interaction.guild:
    #             #         self.vm.voice_clients[interaction.guild.id] = vc
    #             #         break
    #         else:
    #             await interaction.response.send_message(
    #                 f"既に<#{client.channel.id}>に接続しています",
    #                 delete_after=10
    #             )
    #             return
    #     if not interaction.user.voice:
    #         await interaction.response.send_message("VCに参加してください", delete_after=10)
    #         return
    #     vc = interaction.user.voice.channel
    #     await self.vm.connect(vc, interaction.guild.id)
    #     await interaction.response.send_message(f"<#{vc.id}>に接続しました", delete_after=10)
    #     self.vm.read_channels[interaction.guild.id] = interaction.channel
    #     # self.vm.qclear()
    #     self.vm.speak("接続しました", guild=interaction.guild.id)
    #     if not self.say_clock.is_running():
    #         self.say_clock.start()
    #     if self.vm.converter_thread is None or not self.vm.converter_thread.is_alive():
    #         self.vm.start_converter()

    @discord.ui.button(label="切断", style=discord.ButtonStyle.red, custom_id="leave_button")
    async def leave_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        client = self.bot.voice_clients_dict.get(interaction.guild.id)
        if self.bot.voice_clients:
            if client not in self.bot.voice_clients:
                await interaction.response.send_message(
                    content="エラーが発生しました\n再度実行してください",
                    delete_after=10
                )
                # for vc in self.bot.voice_clients:
                #     # bot.voice_clients is a list of VoiceClient objects
                #     if vc.guild == interaction.guild:
                #         self.vm.voice_clients[interaction.guild.id] = vc
                #         break
        if not client:
            await interaction.response.send_message("接続されていません", delete_after=10)
            return
        await self.vm.disconnect(interaction.guild_id)
        await interaction.response.send_message("切断しました", delete_after=10)
        if not self.bot.voice_clients_dict:
            self.say_clock.stop()

    @discord.ui.select(
        placeholder="読み上げるチャンネルを選択",
        custom_id="read_channel_select",
        select_type=discord.ComponentType.channel_select,
        channel_types=[discord.ChannelType.text, discord.ChannelType.voice],
        row=0
    )
    async def read_channel_select(self, select: discord.ui.Select[discord.channel], interaction: discord.Interaction):
        client = self.bot.voice_clients_dict.get(interaction.guild.id)
        if self.bot.voice_clients:
            if client not in self.bot.voice_clients:
                await interaction.response.send_message(
                    content="エラーが発生しました\n再度実行してください",
                    delete_after=10
                )
                # for vc in self.bot.voice_clients:
                #     if vc.guild == interaction.guild:
                #         self.vm.voice_clients[interaction.guild.id] = vc
                #         break
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
        self.vm.read_channels[interaction.guild.id] = select.values[0]
        await select.values[0].send("接続しました")
        # self.vm.qclear()
        self.vm.speak("接続しました", guild=interaction.guild.id)
        if not self.say_clock.is_running():
            self.say_clock.start()
        if self.vm.converter_thread is None or not self.vm.converter_thread.is_alive():
            self.vm.start_converter()
