import discord
from discord import ApplicationContext, Embed
from discord.ext import commands
from discord.ext.pages import Paginator, Page
from discord.commands import slash_command, SlashCommandGroup, Option
import voicemanager

styles: dict[str, str] = {}


async def style_choices(ctx: discord.AutocompleteContext):
    return list(styles)


def list_pagenation(regex: dict, simple: dict) -> Paginator:
    pages = []
    for k, v in regex.items():
        embed = Embed(title="辞書一覧")
        embed.add_field(name="変換前", value=k)
        embed.add_field(name="変換後", value=v)
        embed.add_field(name="正規表現", value="使用する")
        pages.append(Page(embeds=[embed]))
    for k, v in simple.items():
        embed = Embed(title="辞書一覧")
        embed.add_field(name="変換前", value=k)
        embed.add_field(name="変換後", value=v)
        embed.add_field(name="正規表現", value="使用しない")
        pages.append(Page(embeds=[embed]))
    return Paginator(pages=pages)


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
            await ctx.respond("無効な値です")
            return
        self.vm.user_settings.update(user_id, "speaker", speaker_id)
        await ctx.respond(f"{ctx.user.display_name}の話者を{speaker}に変更しました")

    @user_setting.command()
    async def change_speed(
            self,
            ctx: ApplicationContext,
            speed: Option(float, "再生速度を変更", min_value=0.5, max_value=2.0)
    ):
        user_id = ctx.author.id
        if not (0.5 <= speed <= 2.0):
            await ctx.respond("再生速度は0.5から2.0の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "speed", speed)
        await ctx.respond(f"{ctx.user.display_name}の再生速度を{speed}に変更しました")

    @user_setting.command()
    async def change_pitch(
            self,
            ctx: ApplicationContext,
            pitch: Option(float, "音程を変更", min_value=-0.15, max_value=0.15)
    ):
        user_id = ctx.author.id
        if not (-0.15 <= pitch <= 0.15):
            await ctx.respond("音程は-0.15から0.15の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "pitch", pitch)
        await ctx.respond(f"{ctx.user.display_name}の音程を{pitch}に変更しました")

    @user_setting.command()
    async def change_intonation(
            self,
            ctx: ApplicationContext,
            intonation: Option(float, "抑揚を変更", min_value=0.0, max_value=2.0)
    ):
        user_id = ctx.author.id
        if not (0.0 <= intonation <= 2.0):
            await ctx.respond("抑揚は0.0から2.0の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "intonation", intonation)
        await ctx.respond(f"{ctx.user.display_name}の抑揚を{intonation}に変更しました")

    @user_setting.command()
    async def change_volume(
            self,
            ctx: ApplicationContext,
            volume: Option(float, "音量を変更", min_value=0.0, max_value=2.0)
    ):
        user_id = ctx.author.id
        if not (0.0 <= volume <= 2.0):
            await ctx.respond("音量は0.0から2.0の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "volume", volume)
        await ctx.respond(f"{ctx.user.display_name}の音量を{volume}に変更しました")

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
        await ctx.respond(embed=embed)

    @user_dictionary.command()
    async def add(
            self,
            ctx: ApplicationContext,
            before: Option(str, "変換前の文字列"),
            after: Option(str, "変換後の文字列"),
            use_regex: Option(bool, "正規表現を使用するか", default=False)
    ):
        user_id = ctx.author.id
        if before in self.vm.user_replacers.get(user_id).keys():
            await ctx.respond("辞書が既に存在します")
            return
        self.vm.user_replacers.add(user_id, before, after, use_regex)
        embed = Embed(
            title="ユーザー辞書追加",
            description=f"変換前: {before}\n変換後: {after}\n正規表現: {'使用する' if use_regex else '使用しない'}"
        )
        await ctx.respond(embed=embed)

    @user_dictionary.command()
    async def delete(
            self,
            ctx: ApplicationContext,
            before: Option(str, "変換前の文字列")
    ):
        user_id = ctx.author.id
        if not self.vm.user_replacers.get(user_id, before):
            await ctx.respond("辞書が存在しません")
            return
        self.vm.user_replacers.delete(user_id, before)
        embed = Embed(
            title="ユーザー辞書削除",
            description=f"変換前: {before}"
        )
        await ctx.respond(embed=embed)

    @user_dictionary.command()
    async def list(
            self,
            ctx: ApplicationContext
    ):
        user_id = ctx.author.id
        self.vm.user_replacers.auto_load(user_id)
        data = self.vm.user_replacers.get(user_id)
        print(data)
        if not data:
            await ctx.respond("辞書が存在しません")
            return
        await ctx.respond(f"{len(data)}件の辞書が登録されています")
        pagenator = list_pagenation(data.regex_replacements_str, data.simple_replacements)
        await pagenator.respond(ctx.interaction)

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
        if not self.vm.user_replacers.get(user_id, old_before):
            await ctx.respond("辞書が存在しません")
            return
        self.vm.user_replacers.update(user_id, old_before, new_before, after, use_regex)
        embed = Embed(
            title="ユーザー辞書更新",
            description=f"変換前: {old_before}\n変換後: {new_before}\n正規表現: {'使用する' if use_regex else '使用しない'}"
        )
        await ctx.respond(embed=embed)


class GuildCommands(commands.Cog):

    def __init__(self, bot: discord.Bot, vm: voicemanager.VoiceManager):
        self.bot = bot
        self.vm: voicemanager.VoiceManager = vm

    guild_setting = SlashCommandGroup("server-setting", "サーバー設定コマンド")
    guild_dictionary = SlashCommandGroup("dictionary", "サーバー辞書操作コマンド")

    @guild_setting.command()
    async def change_speaker(
            self,
            ctx: ApplicationContext,
            speaker: Option(str, "サーバー標準話者を変更", autocomplete=style_choices)
    ):
        guild_id = ctx.guild.id
        speaker_id = styles.get(speaker)
        if speaker_id is None:
            await ctx.respond("無効な値です")
            return
        self.vm.guild_settings.update(guild_id, "speaker", speaker_id)
        await ctx.respond(f"サーバー標準の話者を{speaker}に変更しました")

    @guild_setting.command()
    async def change_speed(
            self,
            ctx: ApplicationContext,
            speed: Option(float, "サーバー標準再生速度を変更", min_value=0.5, max_value=2.0)
    ):
        guild_id = ctx.guild.id
        if not (0.5 <= speed <= 2.0):
            await ctx.respond("再生速度は0.5から2.0の間で指定してください")
            return
        self.vm.guild_settings.update(guild_id, "speed", speed)
        await ctx.respond(f"サーバー標準の再生速度を{speed}に変更しました")

    @guild_setting.command()
    async def change_pitch(
            self,
            ctx: ApplicationContext,
            pitch: Option(float, "サーバー標準音程を変更", min_value=-0.15, max_value=0.15)
    ):
        guild_id = ctx.guild.id
        if not (-0.15 <= pitch <= 0.15):
            await ctx.respond("音程は-0.15から0.15の間で指定してください")
            return
        self.vm.guild_settings.update(guild_id, "pitch", pitch)
        await ctx.respond(f"サーバー標準の音程を{pitch}に変更しました")

    @guild_setting.command()
    async def change_intonation(
            self,
            ctx: ApplicationContext,
            intonation: Option(float, "サーバー標準抑揚を変更", min_value=0.0, max_value=2.0)
    ):
        guild_id = ctx.guild.id
        if not (0.0 <= intonation <= 2.0):
            await ctx.respond("抑揚は0.0から2.0の間で指定してください")
            return
        self.vm.guild_settings.update(guild_id, "intonation", intonation)
        await ctx.respond(f"サーバー標準の抑揚を{intonation}に変更しました")

    @guild_setting.command()
    async def change_volume(
            self,
            ctx: ApplicationContext,
            volume: Option(float, "サーバー標準音量を変更", min_value=0.0, max_value=2.0)
    ):
        guild_id = ctx.guild.id
        if not (0.0 <= volume <= 2.0):
            await ctx.respond("音量は0.0から2.0の間で指定してください")
            return
        self.vm.guild_settings.update(guild_id, "volume", volume)
        await ctx.respond(f"サーバー標準の音量を{volume}に変更しました")

    @guild_setting.command()
    async def change_read_joinleave(
            self,
            ctx: ApplicationContext,
            read_joinleave: Option(bool, "ユーザーの参加/退出を読み上げるか")
    ):
        guild_id = ctx.guild.id
        self.vm.guild_settings.update(guild_id, "read_joinleave", read_joinleave)
        await ctx.respond(f"ユーザーの参加/退出を読み上げる設定を{read_joinleave}に変更しました")

    @guild_setting.command()
    async def change_read_nonpaticipant(
            self,
            ctx: ApplicationContext,
            read_nonparticipant: Option(bool, "VCに参加していないユーザーを読み上げるか")
    ):
        guild_id = ctx.guild.id
        self.vm.guild_settings.update(guild_id, "read_nonparticipant", read_nonparticipant)
        await ctx.respond(f"VCに参加していないユーザーを読み上げる設定を{read_nonparticipant}に変更しました")

    @guild_setting.command()
    async def change_read_replyuser(
            self,
            ctx: ApplicationContext,
            read_replyuser: Option(bool, "リプライされたユーザーを読み上げるか")
    ):
        guild_id = ctx.guild.id
        self.vm.guild_settings.update(guild_id, "read_replyuser", read_replyuser)
        await ctx.respond(f"リプライされたユーザーを読み上げる設定を{read_replyuser}に変更しました")

    @guild_setting.command()
    async def show_setting(
            self,
            ctx: ApplicationContext
    ):
        guild_id = ctx.guild.id
        setting = self.vm.guild_settings.get(guild_id)
        speaker = "不明"
        for k, v in styles.items():
            if v == setting.speaker:
                speaker = k
                break
        embed = Embed(
            title=f"{ctx.guild.name}の設定",
            description=f"話者: {speaker}\n"
                        f"再生速度: {setting.speed}\n"
                        f"音程: {setting.pitch}\n"
                        f"抑揚: {setting.intonation}\n"
                        f"音量: {setting.volume}\n"
                        f"参加/退出読み上げ: {bool(setting.read_joinleave)}\n"
                        f"VC未参加ユーザー読み上げ: {bool(setting.read_nonparticipation)}\n"
                        f"リプライユーザー読み上げ: {bool(setting.read_replyuser)}"
        )
        await ctx.respond(embed=embed)

    # async def dictionary_autocomplete(self, ctx: discord.AutocompleteContext):
    #     return list(self.vm.guild_replacers.get(ctx.guild.id).keys())

    @guild_dictionary.command(name="add", description="辞書を追加する")
    async def add(
            self,
            ctx: ApplicationContext,
            before: Option(str, "変換前の文字列"),
            after: Option(str, "変換後の文字列"),
            use_regex: Option(bool, "正規表現を使用するか", default=False)
    ):
        if before in self.vm.guild_replacers.get(ctx.guild.id):
            await ctx.respond("辞書が既に存在します")
            return
        self.vm.guild_replacers.add(ctx.guild.id, before, after, use_regex)
        embed = Embed(title="辞書追加",
                      description=f"### 単語\n# ```{before}```\n### 読み\n# ```{after}```\n### 正規表現: {'使用する' if use_regex else '使用しない'}")
        await ctx.respond(embed=embed)

    @guild_dictionary.command(name="delete", description="辞書を削除する")
    async def delete(
            self,
            ctx: ApplicationContext,
            before: Option(str, "変換前の文字列")
    ):
        if not self.vm.guild_replacers.get(ctx.guild.id, before):
            await ctx.respond("辞書が存在しません")
            return
        self.vm.guild_replacers.delete(ctx.guild.id, before)
        embed = Embed(
            title="サーバー辞書削除",
            description=f"変換前: {before}"
        )
        await ctx.respond(embed=embed)

    @guild_dictionary.command(name="list", description="辞書を表示する")
    async def dictionary_list(
            self,
            ctx: ApplicationContext
    ):
        data = self.vm.guild_replacers.get(ctx.guild.id)
        if not data:
            await ctx.send("辞書が存在しません")
            return
        await ctx.send(f"{len(data)}件の辞書が登録されています")
        pagenator = list_pagenation(data.regex_replacements_str, data.simple_replacements)
        await pagenator.respond(ctx.interaction)

    @guild_dictionary.command(name="update", description="辞書を更新する")
    async def update(
            self,
            ctx: ApplicationContext,
            old_before: Option(str, "変換前の文字列"),
            new_before: Option(str, "変換前の文字列"),
            after: Option(str, "変換後の文字列"),
            use_regex: Option(bool, "正規表現を使用するか")
    ):
        if not self.vm.guild_replacers.get(ctx.guild.id, old_before):
            await ctx.respond("辞書が存在しません")
            return
        self.vm.guild_replacers.update(ctx.guild.id, old_before, new_before, after, use_regex)
        embed = Embed(title="辞書更新",
                      description=f"### 変更前単語\n```{old_before}```\n### 単語\n# ```{new_before}```\n### 読み\n# ```{after}```\n### 正規表現: {'使用する' if use_regex else '使用しない'}")
        await ctx.respond(embed=embed)


def setup(bot: voicemanager.VoiceManagedBot):
    global styles
    styles = bot.voice_manager.speakers.styles()
    bot.add_cog(UserCommands(bot, bot.voice_manager))
    bot.add_cog(GuildCommands(bot, bot.voice_manager))
