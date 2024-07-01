import discord
from discord import ApplicationContext, ChannelType, Embed
from discord.abc import GuildChannel
from discord.ext import commands, tasks
from discord.commands import slash_command, SlashCommandGroup, Option
from vv_wrapper import call, database
import voicemanager

styles: dict[str, str] = {}


async def style_choices(ctx: discord.AutocompleteContext):
    return list(styles)


class UserCommands(commands.Cog):

    def __init__(self, bot: discord.Bot, vm: voicemanager.VoiceManager):
        self.bot = bot
        self.vm: voicemanager.VoiceManager = vm

    user_setting = SlashCommandGroup("user-setting", "ユーザー設定コマンド")
    user_dictionary = SlashCommandGroup("user-dictionary", "ユーザー辞書操作コマンド")

    # @classmethod
    # async def style_choices(cls, ctx: discord.AutocompleteContext):
    #     return list(cls.speakers.styles())

    @user_setting.command()
    async def change_speaker(
            self,
            ctx: ApplicationContext,
            speaker: Option(str, "話者を変更", autocomplete=style_choices)
    ):
        user_id = ctx.author.id
        print(user_id, ctx.author.display_name)
        speaker_id = self.vm.speakers.styles().get(speaker)
        if speaker_id is None:
            await ctx.send("無効な値です")
            return
        self.vm.user_settings.update(user_id, "speaker", speaker_id)
        await ctx.send(f"{ctx.user.display_name}の話者を{speaker}に変更しました")

    @user_setting.command()
    async def change_speed(
            self,
            ctx: ApplicationContext,
            speed: Option(float, "再生速度を変更", min_value=0.5, max_value=2.0)
    ):
        user_id = ctx.author.id
        if not (0.5 <= speed <= 2.0):
            await ctx.send("再生速度は0.5から2.0の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "speed", speed)
        await ctx.send(f"{ctx.user.display_name}の再生速度を{speed}に変更しました")

    @user_setting.command()
    async def change_pitch(
            self,
            ctx: ApplicationContext,
            pitch: Option(float, "音程を変更", min_value=-0.15, max_value=0.15)
    ):
        user_id = ctx.author.id
        if not (-0.15 <= pitch <= 0.15):
            await ctx.send("音程は-0.15から0.15の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "pitch", pitch)
        await ctx.send(f"{ctx.user.display_name}の音程を{pitch}に変更しました")

    @user_setting.command()
    async def change_intonation(
            self,
            ctx: ApplicationContext,
            intonation: Option(float, "抑揚を変更", min_value=0.0, max_value=2.0)
    ):
        user_id = ctx.author.id
        if not (0.0 <= intonation <= 2.0):
            await ctx.send("抑揚は0.0から2.0の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "intonation", intonation)
        await ctx.send(f"{ctx.user.display_name}の抑揚を{intonation}に変更しました")

    @user_setting.command()
    async def change_volume(
            self,
            ctx: ApplicationContext,
            volume: Option(float, "音量を変更", min_value=0.0, max_value=2.0)
    ):
        user_id = ctx.author.id
        if not (0.0 <= volume <= 2.0):
            await ctx.send("音量は0.0から2.0の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "volume", volume)
        await ctx.send(f"{ctx.user.display_name}の音量を{volume}に変更しました")

    @user_setting.command()
    async def show_setting(
            self,
            ctx: ApplicationContext
    ):
        user_id = ctx.author.id
        setting = self.vm.get_user_setting(user_id)
        speaker = "不明"
        for k, v in styles.items():
            if v == setting.speaker:
                speaker = k
                break
        embed = Embed(
            title=f"{ctx.user.display_name}の設定",
            description=f"話者: {speaker}\n"
                        f"再生速度: {setting.speed}\n"
                        f"音程: {setting.pitch}\n"
                        f"抑揚: {setting.intonation}\n"
                        f"音量: {setting.volume}"
        )
        await ctx.send(embed=embed)

    @user_dictionary.command()
    async def add(
            self,
            ctx: ApplicationContext,
            before: Option(str, "変換前の文字列"),
            after: Option(str, "変換後の文字列"),
            use_regex: Option(bool, "正規表現を使用するか")
    ):
        user_id = ctx.author.id
        self.vm.user_replacers.add(user_id, before, after, use_regex)
        embed = Embed(
            title="ユーザー辞書追加",
            description=f"変換前: {before}\n変換後: {after}\n正規表現: {'使用する' if use_regex else '使用しない'}"
        )
        await ctx.send(embed=embed)

    @user_dictionary.command()
    async def delete(
            self,
            ctx: ApplicationContext,
            before: Option(str, "変換前の文字列")
    ):
        user_id = ctx.author.id
        self.vm.user_replacers.delete(user_id, before)
        embed = Embed(
            title="ユーザー辞書削除",
            description=f"変換前: {before}"
        )
        await ctx.send(embed=embed)

    @user_dictionary.command()
    async def list(
            self,
            ctx: ApplicationContext
    ):
        user_id = ctx.author.id
        data = self.vm.user_replacers.get(user_id)
        if not data:
            await ctx.send("辞書が存在しません")
            return
        await ctx.send(f"{len(data)}件の辞書が登録されています")
        res = ""
        for k, v in data.regex_replacements_str.items():
            res += f"変換前: {k}\n変換後: {v}\n正規表現: 使用する\n\n"
        for k, v in data.simple_replacements.items():
            res += f"変換前: {k}\n変換後: {v}\n正規表現: 使用しない\n\n"
        await ctx.send(res)

    @user_dictionary.command()
    async def update(
            self,
            ctx: ApplicationContext,
            old_before: Option(str, "変換前の文字列"),
            new_before: Option(str, "変換前の文字列"),
            after: Option(str, "変換後の文字列"),
            use_regex: Option(bool, "正規表現を使用するか")
    ):
        user_id = ctx.author.id
        self.vm.user_replacers.update(user_id, old_before, new_before, after, use_regex)
        embed = Embed(
            title="ユーザー辞書更新",
            description=f"変換前: {old_before}\n変換後: {new_before}\n正規表現: {'使用する' if use_regex else '使用しない'}"
        )
        await ctx.send(embed=embed)


class GuildCommands(commands.Cog):

    def __init__(self, bot: discord.Bot, vm: voicemanager.VoiceManager):
        self.bot = bot
        self.vm: voicemanager.VoiceManager = vm

    guild_setting = SlashCommandGroup("server-setting", "サーバー設定コマンド")

    @guild_setting.command()
    async def change_speaker(
            self,
            ctx: ApplicationContext,
            speaker: Option(str, "サーバー標準話者を変更", autocomplete=style_choices)
    ):
        guild_id = ctx.guild.id
        speaker_id = styles.get(speaker)
        if speaker_id is None:
            await ctx.send("無効な値です")
            return
        self.vm.guild_settings.update(guild_id, "speaker", speaker_id)
        await ctx.send(f"サーバー標準の話者を{speaker}に変更しました")

    @guild_setting.command()
    async def change_speed(
            self,
            ctx: ApplicationContext,
            speed: Option(float, "サーバー標準再生速度を変更", min_value=0.5, max_value=2.0)
    ):
        guild_id = ctx.guild.id
        if not (0.5 <= speed <= 2.0):
            await ctx.send("再生速度は0.5から2.0の間で指定してください")
            return
        self.vm.guild_settings.update(guild_id, "speed", speed)
        await ctx.send(f"サーバー標準の再生速度を{speed}に変更しました")

    @guild_setting.command()
    async def change_pitch(
            self,
            ctx: ApplicationContext,
            pitch: Option(float, "サーバー標準音程を変更", min_value=-0.15, max_value=0.15)
    ):
        guild_id = ctx.guild.id
        if not (-0.15 <= pitch <= 0.15):
            await ctx.send("音程は-0.15から0.15の間で指定してください")
            return
        self.vm.guild_settings.update(guild_id, "pitch", pitch)
        await ctx.send(f"サーバー標準の音程を{pitch}に変更しました")

    @guild_setting.command()
    async def change_intonation(
            self,
            ctx: ApplicationContext,
            intonation: Option(float, "サーバー標準抑揚を変更", min_value=0.0, max_value=2.0)
    ):
        guild_id = ctx.guild.id
        if not (0.0 <= intonation <= 2.0):
            await ctx.send("抑揚は0.0から2.0の間で指定してください")
            return
        self.vm.guild_settings.update(guild_id, "intonation", intonation)
        await ctx.send(f"サーバー標準の抑揚を{intonation}に変更しました")

    @guild_setting.command()
    async def change_volume(
            self,
            ctx: ApplicationContext,
            volume: Option(float, "サーバー標準音量を変更", min_value=0.0, max_value=2.0)
    ):
        guild_id = ctx.guild.id
        if not (0.0 <= volume <= 2.0):
            await ctx.send("音量は0.0から2.0の間で指定してください")
            return
        self.vm.guild_settings.update(guild_id, "volume", volume)
        await ctx.send(f"サーバー標準の音量を{volume}に変更しました")

    @guild_setting.command()
    async def change_read_joinleave(
            self,
            ctx: ApplicationContext,
            read_joinleave: Option(bool, "ユーザーの参加/退出を読み上げるか")
    ):
        guild_id = ctx.guild.id
        self.vm.guild_settings.update(guild_id, "read_joinleave", read_joinleave)
        await ctx.send(f"ユーザーの参加/退出を読み上げる設定を{read_joinleave}に変更しました")

    @guild_setting.command()
    async def change_read_nonpaticipant(
            self,
            ctx: ApplicationContext,
            read_nonparticipant: Option(bool, "VCに参加していないユーザーを読み上げるか")
    ):
        guild_id = ctx.guild.id
        self.vm.guild_settings.update(guild_id, "read_nonparticipant", read_nonparticipant)
        await ctx.send(f"VCに参加していないユーザーを読み上げる設定を{read_nonparticipant}に変更しました")

    @guild_setting.command()
    async def change_read_replyuser(
            self,
            ctx: ApplicationContext,
            read_replyuser: Option(bool, "リプライされたユーザーを読み上げるか")
    ):
        guild_id = ctx.guild.id
        self.vm.guild_settings.update(guild_id, "read_replyuser", read_replyuser)
        await ctx.send(f"リプライされたユーザーを読み上げる設定を{read_replyuser}に変更しました")


def setup(bot: voicemanager.VoiceManagedBot):
    global styles
    styles = bot.voice_manager.speakers.styles()
    bot.add_cog(UserCommands(bot, bot.voice_manager))
    bot.add_cog(GuildCommands(bot, bot.voice_manager))
