from dataclasses import asdict
from io import StringIO
from json import dumps
from math import ceil

import discord
from discord import Embed, File
from discord.ext import commands, bridge
from discord.ext.bridge import BridgeContext, BridgeOption
from discord.ext.pages import Paginator, Page

# from discord.commands import slash_command, SlashCommandGroup, Option
import voicemanager
from util import BridgeCtx

styles: dict[str, str] = {}


async def style_choices(ctx: discord.AutocompleteContext):
    return list(styles)


def list_pagination(regex: dict, simple: dict) -> Paginator:
    pages = []
    embeds = []
    for k, v in regex.items():
        embed = Embed(title="辞書一覧")
        embed.add_field(name="単語", value=k)
        embed.add_field(name="読み", value=v)
        embed.add_field(name="正規表現", value="使用する")
        embeds.append(embed)
    for k, v in simple.items():
        embed = Embed(title="辞書一覧")
        embed.add_field(name="単語", value=k)
        embed.add_field(name="読み", value=v)
        embed.add_field(name="正規表現", value="使用しない")
        embeds.append(embed)
    for i in range(ceil(len(embeds) / 4)):
        pages.append(Page(embeds=embeds[i * 4: (i + 1) * 4]))
    return Paginator(pages=pages)


def mention_pagination(title: str, ids: list[int],
                       _type: str) -> Paginator:
    pages = []
    if not ids:
        return Paginator(pages=[Page(embeds=[Embed(title=title, description="登録されていません")])])
    if _type == "user":
        conv = lambda x: f"<@{x}>"
    elif _type == "role":
        conv = lambda x: f"<@&{x}>"
    else:
        raise TypeError(f"invalid type: {_type.__class__.__name__}")
    for i in range(ceil(len(ids) / 10)):
        embed = Embed(title=title)
        value = []
        for j, mention in enumerate(ids[i * 10: (i + 1) * 10], 1):
            value.append(f"{i}. {conv(mention)}")
        embed.add_field(name=f"{len(ids)}件中 {i * 10 + 1} ~ {min(i * 10 + 10, len(ids))} 件目を表示",
                        value="\n".join(value))
        pages.append(Page(embeds=[embed]))
    return Paginator(pages=pages)


class UserCommands(commands.Cog):

    def __init__(self, bot: discord.Bot | discord.AutoShardedBot, vm: voicemanager.VoiceManager):
        self.bot = bot
        self.vm: voicemanager.VoiceManager = vm

    @bridge.bridge_group(name="user-setting", description="ユーザー設定コマンド")
    async def user_setting(self, ctx: BridgeContext):
        pass

    @bridge.bridge_group(name="user-dictionary", description="ユーザー辞書操作コマンド")
    async def user_dictionary(self, ctx: BridgeContext):
        pass

    # user_setting = bridge.BridgeCommandGroup(bridge_command, name="user-setting", descriprion="ユーザー設定コマンド")
    # user_dictionary = bridge.BridgeCommandGroup(bridge_command, name="user-dictionary", description="ユーザー辞書操作コマンド")

    # @classmethod
    # async def style_choices(cls, ctx: discord.AutocompleteContext):
    #     return list(cls.speakers.styles())

    @user_setting.command(name="change-speaker", description="話者を変更")
    async def change_speaker(
            self,
            ctx: BridgeCtx,
            speaker: BridgeOption(str, "話者を変更", autocomplete=style_choices)
    ):
        user_id = ctx.author.id
        speaker_id = self.vm.speakers.styles().get(speaker)
        if speaker_id is None:
            await ctx.respond("無効な値です")
            return
        self.vm.user_settings.update(user_id, "speaker", speaker_id)
        await ctx.respond(f"<@{ctx.author.id}>さんの話者を{speaker}に変更しました")

    @user_setting.command(name="change-speed", description="再生速度を変更")
    async def change_speed(
            self,
            ctx: BridgeCtx,
            speed: BridgeOption(float, "再生速度を変更", min_value=0.5, max_value=2.0)
    ):
        user_id = ctx.author.id
        if not (0.5 <= speed <= 2.0):
            await ctx.respond("再生速度は0.5から2.0の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "speed", speed)
        await ctx.respond(f"<@{ctx.author.id}>さんの再生速度を{speed}に変更しました")

    @user_setting.command(name="change-pitch", description="音程を変更")
    async def change_pitch(
            self,
            ctx: BridgeCtx,
            pitch: BridgeOption(float, "音程を変更", min_value=-0.15, max_value=0.15)
    ):
        user_id = ctx.author.id
        if not (-0.15 <= pitch <= 0.15):
            await ctx.respond("音程は-0.15から0.15の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "pitch", pitch)
        await ctx.respond(f"<@{ctx.author.id}>さんの音程を{pitch}に変更しました")

    @user_setting.command(name="change-intonation", description="抑揚を変更")
    async def change_intonation(
            self,
            ctx: BridgeCtx,
            intonation: BridgeOption(float, "抑揚を変更", min_value=0.0, max_value=2.0)
    ):
        user_id = ctx.author.id
        if not (0.0 <= intonation <= 2.0):
            await ctx.respond("抑揚は0.0から2.0の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "intonation", intonation)
        await ctx.respond(f"<@{ctx.author.id}>さんの抑揚を{intonation}に変更しました")

    @user_setting.command(name="change-volume", description="音量を変更")
    async def change_volume(
            self,
            ctx: BridgeCtx,
            volume: BridgeOption(float, "音量を変更", min_value=0.0, max_value=2.0)
    ):
        user_id = ctx.author.id
        if not (0.0 <= volume <= 2.0):
            await ctx.respond("音量は0.0から2.0の間で指定してください")
            return
        self.vm.user_settings.update(user_id, "volume", volume)
        await ctx.respond(f"<@{ctx.author.id}>さんの音量を{volume}に変更しました")

    @user_setting.command(name="show-setting", description="ユーザー設定を表示")
    async def show_setting(
            self,
            ctx: BridgeCtx,
            json: BridgeOption(bool, "JSON形式で表示するか", default=True)
    ):
        user_id = ctx.author.id
        setting = self.vm.get_user_setting(user_id)
        speaker = "不明"
        for k, v in styles.items():
            if v == setting.speaker:
                speaker = k
                break

        if json:
            settings = asdict(setting)
            await ctx.respond(
                f"<@{ctx.author.id}>の設定"
                f"```json\n{dumps(settings, indent=2)}\n```"
            )

        else:
            embed = Embed(
                title=f"<@{ctx.author.id}>の設定",
                description=f"話者: {speaker}\n"
                            f"再生速度: {setting.speed}\n"
                            f"音程: {setting.pitch}\n"
                            f"抑揚: {setting.intonation}\n"
                            f"音量: {setting.volume}"
            )
            await ctx.respond(embed=embed)

    @user_dictionary.command(name="add", description="ユーザー辞書を追加する")
    async def add(
            self,
            ctx: BridgeCtx,
            before: BridgeOption(str, "変換前の文字列"),
            after: BridgeOption(str, "変換後の文字列"),
            use_regex: BridgeOption(bool, "正規表現を使用するか", default=False)
    ):
        user_id = ctx.author.id
        if before in self.vm.user_replacers.get(user_id).keys():
            await ctx.respond("辞書が既に存在します")
            return
        self.vm.user_replacers.add(user_id, before, after, use_regex)
        embed = Embed(title="ユーザー辞書追加")
        embed.add_field(name="単語", value=before)
        embed.add_field(name="読み", value=after)
        embed.add_field(name="正規表現", value="使用する" if use_regex else "使用しない")
        await ctx.respond(embed=embed)

    @user_dictionary.command(name="delete", description="ユーザー辞書を削除する")
    async def delete(
            self,
            ctx: BridgeCtx,
            before: BridgeOption(str, "変換前の文字列")
    ):
        user_id = ctx.author.id
        if not self.vm.user_replacers.get(user_id, before):
            await ctx.respond("辞書が存在しません")
            return
        self.vm.user_replacers.delete(user_id, before)
        embed = Embed(title="ユーザー辞書削除")
        embed.add_field(name="単語", value=before)
        await ctx.respond(embed=embed)

    @user_dictionary.command(name="list", description="ユーザー辞書を表示する")
    async def list(
            self,
            ctx: BridgeCtx,
            json: BridgeOption(bool, "JSON形式で表示するか", default=True)
    ):
        user_id = ctx.author.id
        self.vm.user_replacers.auto_load(user_id)
        data = self.vm.user_replacers.get(user_id)
        if not data:
            await ctx.respond("辞書が存在しません")
            return
        await ctx.respond(f"{len(data)}件の辞書が登録されています")
        if json:
            file = dumps(
                {
                    "regex": data.regex_replacements_str,
                    "simple": data.simple_replacements,
                },
                indent=2,
                ensure_ascii=False
            )
            file = StringIO(file)
            file.seek(0)
            await ctx.send(
                f"<@{ctx.author.id}>のユーザー辞書",
                file=File(file, filename=f"{ctx.author.id}_user_dictionary.json")
            )
        else:
            pagenator = list_pagination(data.regex_replacements_str, data.simple_replacements)
            await pagenator.respond(ctx)

    @user_dictionary.command(name="update", description="ユーザー辞書を更新する")
    async def update(
            self,
            ctx: BridgeCtx,
            old_before: BridgeOption(str, "変換前の文字列"),
            new_before: BridgeOption(str, "変換前の文字列"),
            after: BridgeOption(str, "変換後の文字列"),
            use_regex: BridgeOption(bool, "正規表現を使用するか")
    ):
        user_id = ctx.author.id
        if not self.vm.user_replacers.get(user_id, old_before):
            await ctx.respond("辞書が存在しません")
            return
        self.vm.user_replacers.update(user_id, old_before, new_before, after, use_regex)
        embed = Embed(title="ユーザー辞書更新")
        embed.add_field(name="単語", value=old_before)
        embed.add_field(name="新しい単語", value=new_before)
        embed.add_field(name="読み", value=after)
        embed.add_field(name="正規表現", value="使用する" if use_regex else "使用しない")
        await ctx.respond(embed=embed)


class GuildCommands(commands.Cog):

    def __init__(self, bot: discord.Bot | discord.AutoShardedBot, vm: voicemanager.VoiceManager):
        self.bot = bot
        self.vm: voicemanager.VoiceManager = vm

    @bridge.bridge_group(name="server-setting", description="サーバー設定コマンド")
    async def guild_setting(self, ctx: bridge.BridgeContext):
        pass

    @bridge.bridge_group(name="dictionary", description="サーバー辞書操作コマンド")
    async def guild_dictionary(self, ctx: bridge.BridgeContext):
        pass

    @guild_setting.command(name="change-speaker", description="サーバー標準の話者を変更")
    async def change_speaker(
            self,
            ctx: BridgeCtx,
            speaker: BridgeOption(str, "サーバー標準話者を変更", autocomplete=style_choices)
    ):
        speaker_id = styles.get(speaker)
        if speaker_id is None:
            await ctx.respond("無効な値です")
            return
        self.vm.guild_settings.update(ctx.guild.id, "speaker", speaker_id)
        await ctx.respond(f"サーバー標準の話者を{speaker}に変更しました")

    @guild_setting.command(name="change-speed", description="サーバー標準再生速度を変更")
    async def change_speed(
            self,
            ctx: BridgeCtx,
            speed: BridgeOption(float, "サーバー標準再生速度を変更", min_value=0.5, max_value=2.0)
    ):
        if not (0.5 <= speed <= 2.0):
            await ctx.respond("再生速度は0.5から2.0の間で指定してください")
            return
        self.vm.guild_settings.update(ctx.guild.id, "speed", speed)
        await ctx.respond(f"サーバー標準の再生速度を{speed}に変更しました")

    @guild_setting.command(name="change-pitch", description="サーバー標準音程を変更")
    async def change_pitch(
            self,
            ctx: BridgeCtx,
            pitch: BridgeOption(float, "サーバー標準音程を変更", min_value=-0.15, max_value=0.15)
    ):
        if not (-0.15 <= pitch <= 0.15):
            await ctx.respond("音程は-0.15から0.15の間で指定してください")
            return
        self.vm.guild_settings.update(ctx.guild.id, "pitch", pitch)
        await ctx.respond(f"サーバー標準の音程を{pitch}に変更しました")

    @guild_setting.command(name="change-intonation", description="サーバー標準抑揚を変更")
    async def change_intonation(
            self,
            ctx: BridgeCtx,
            intonation: BridgeOption(float, "サーバー標準抑揚を変更", min_value=0.0, max_value=2.0)
    ):
        if not (0.0 <= intonation <= 2.0):
            await ctx.respond("抑揚は0.0から2.0の間で指定してください")
            return
        self.vm.guild_settings.update(ctx.guild.id, "intonation", intonation)
        await ctx.respond(f"サーバー標準の抑揚を{intonation}に変更しました")

    @guild_setting.command(name="change-volume", description="サーバー標準音量を変更")
    async def change_volume(
            self,
            ctx: BridgeCtx,
            volume: BridgeOption(float, "サーバー標準音量を変更", min_value=0.0, max_value=2.0)
    ):
        if not (0.0 <= volume <= 2.0):
            await ctx.respond("音量は0.0から2.0の間で指定してください")
            return
        self.vm.guild_settings.update(ctx.guild.id, "volume", volume)
        await ctx.respond(f"サーバー標準の音量を{volume}に変更しました")

    @guild_setting.command(name="change-read-joinleave", description="参加/退出読み上げを変更")
    async def change_read_joinleave(
            self,
            ctx: BridgeCtx,
            read_joinleave: BridgeOption(bool, "ユーザーの参加/退出を読み上げるか")
    ):
        self.vm.guild_settings.update(ctx.guild.id, "read_joinleave", read_joinleave)
        await ctx.respond(f"ユーザーの参加/退出を読み上げる設定を{read_joinleave}に変更しました")

    @guild_setting.command(name="change-read-nonpaticipant", description="VCに参加していないユーザーの読み上げを変更")
    async def change_read_nonpaticipant(
            self,
            ctx: BridgeCtx,
            read_nonparticipant: BridgeOption(bool, "VCに参加していないユーザーを読み上げるか")
    ):
        self.vm.guild_settings.update(ctx.guild.id, "read_nonparticipation", read_nonparticipant)
        await ctx.respond(f"VCに参加していないユーザーを読み上げる設定を{read_nonparticipant}に変更しました")

    @guild_setting.command(name="change-read-replyuser", description="リプライユーザー読み上げを変更")
    async def change_read_replyuser(
            self,
            ctx: BridgeCtx,
            read_replyuser: BridgeOption(bool, "リプライされたユーザーを読み上げるか")
    ):
        self.vm.guild_settings.update(ctx.guild.id, "read_replyuser", read_replyuser)
        await ctx.respond(f"リプライされたユーザーを読み上げる設定を{read_replyuser}に変更しました")

    @guild_setting.command(name="change-read-nickname", description="ニックネーム読み上げを変更")
    async def read_nickname(
            self,
            ctx: BridgeCtx,
            read_nick: BridgeOption(bool, "ニックネームを読み上げるか")
    ):
        self.vm.guild_settings.update(ctx.guild.id, "read_nick", read_nick)
        await ctx.respond(f"ニックネームを読み上げる設定を{read_nick}に変更しました")

    @guild_setting.command(name="ignore-user-add", description="読み上げを無視するユーザーを追加")
    async def add_ignore_user(
            self,
            ctx: BridgeCtx,
            user: BridgeOption(discord.Member, "読み上げを無視するユーザー")
    ):
        ignores = self.vm.guild_settings.get(ctx.guild.id).ignore_users
        if user.id in ignores:
            await ctx.respond("既に追加されています")
            return
        ignores.append(user.id)
        self.vm.guild_settings.update(ctx.guild.id, "ignore_users", dumps(ignores))
        embed = Embed(title="読み上げ無視ユーザー追加")
        embed.add_field(name="ユーザー", value=f"<@{user.id}>")
        embed.add_field(name="現在の登録数", value=f"{len(ignores)}人")
        await ctx.respond(embed=embed)

    @guild_setting.command(name="ignore-user-remove", description="読み上げを無視するユーザーを削除")
    async def remove_ignore_user(
            self,
            ctx: BridgeCtx,
            user: BridgeOption(discord.Member, "読み上げの無視を解除するユーザー")
    ):
        ignores = self.vm.guild_settings.get(ctx.guild.id).ignore_users
        if user.id not in ignores:
            await ctx.respond("登録されていません")
            return
        ignores.remove(user.id)
        self.vm.guild_settings.update(ctx.guild.id, "ignore_users", dumps(ignores))
        embed = Embed(title="読み上げ無視ユーザー削除")
        embed.add_field(name="ユーザー", value=f"<@{user.id}>")
        embed.add_field(name="現在の登録数", value=f"{len(ignores)}人")
        await ctx.respond(embed=embed)

    @guild_setting.command(name="ignore-user-show", description="読み上げを無視するユーザーを表示")
    async def ignore_user_list(
            self,
            ctx: BridgeCtx,
            remove_notfound: BridgeOption(bool, "存在しないユーザーを削除するか", default=False)
    ):
        ignores = self.vm.guild_settings.get(ctx.guild.id).ignore_users
        await ctx.defer()
        if remove_notfound:
            notfound = False
            for i in ignores:
                user = ctx.guild.get_member(i)
                if not user:
                    ignores.remove(i)
                    notfound = True
            if notfound:
                self.vm.guild_settings.update(ctx.guild.id, "ignore_users", dumps(ignores))
                await ctx.channel.send(f"存在しないユーザーを削除しました")
        paginator = mention_pagination("除外されたユーザー", ignores, "user")
        await paginator.respond(ctx)

    @guild_setting.command(name="ignore-role-add", description="読み上げを無視するロールを追加")
    async def add_ignore_role(
            self,
            ctx: BridgeCtx,
            role: BridgeOption(discord.Role, "読み上げを無視するロール")
    ):
        ignores = self.vm.guild_settings.get(ctx.guild.id).ignore_roles
        if role.id in ignores:
            await ctx.respond("既に追加されています")
            return
        ignores.append(role.id)
        self.vm.guild_settings.update(ctx.guild.id, "ignore_roles", dumps(ignores))
        embed = Embed(title="読み上げ無視ロール追加")
        embed.add_field(name="ロール", value=f"<@&{role.id}>")
        embed.add_field(name="現在の登録数", value=f"{len(ignores)}個")
        await ctx.respond(embed=embed)

    @guild_setting.command(name="ignore-role-remove", description="読み上げを無視するロールを削除")
    async def remove_ignore_role(
            self,
            ctx: BridgeCtx,
            role: BridgeOption(discord.Role, "読み上げの無視を解除するロール")
    ):
        ignores = self.vm.guild_settings.get(ctx.guild.id).ignore_roles
        if role.id not in ignores:
            await ctx.respond("登録されていません")
            return
        ignores.remove(role.id)
        self.vm.guild_settings.update(ctx.guild.id, "ignore_roles", dumps(ignores))
        embed = Embed(title="読み上げ無視ロール削除")
        embed.add_field(name="ロール", value=f"<@&{role.id}>")
        embed.add_field(name="現在の登録数", value=f"{len(ignores)}個")
        await ctx.respond(embed=embed)

    @guild_setting.command(name="ignore-role-show", description="読み上げを無視するロールを表示")
    async def ignore_role_list(self, ctx: BridgeCtx):
        ignores = self.vm.guild_settings.get(ctx.guild.id).ignore_roles
        notfound = False
        for i in ignores:
            role = ctx.guild.get_role(i)
            if not role:
                ignores.remove(i)
                notfound = True
        if notfound:
            self.vm.guild_settings.update(ctx.guild.id, "ignore_roles", dumps(ignores))
            await ctx.channel.send("存在しないロールを削除しました")
        paginator = mention_pagination("除外されたロール", ignores, "role")
        await paginator.respond(ctx)

    @guild_setting.command(name="show-setting", description="サーバー設定を表示")
    async def show_setting(
            self,
            ctx: BridgeCtx,
            json: BridgeOption(bool, "JSON形式で表示するか", default=True)
    ):
        guild_id = ctx.guild.id
        setting = self.vm.guild_settings.get(guild_id)
        speaker = "不明"
        for k, v in styles.items():
            if v == setting.speaker:
                speaker = k
                break
        if json:
            settings = asdict(setting)
            await ctx.respond(
                f"{ctx.guild.name}の設定"
                f"```json\n{dumps(settings, indent=2)}\n```"
            )
        else:
            embed = Embed(
                title=f"{ctx.guild.name}の設定",
                description=f"話者: `{speaker}`\n"
                            f"再生速度: `{setting.speed}`\n"
                            f"音程: `{setting.pitch}`\n"
                            f"抑揚: `{setting.intonation}`\n"
                            f"音量: `{setting.volume}`\n"
                            f"参加/退出読み上げ: `{bool(setting.read_joinleave)}`\n"
                            f"VC未参加ユーザー読み上げ: `{bool(setting.read_nonparticipation)}`\n"
                            f"リプライユーザー読み上げ: `{bool(setting.read_replyuser)}`\n"
                            f"ニックネーム使用: `{bool(setting.read_nick)}`\n"
                            f"除外ユーザー: `{len(setting.ignore_users)}`人\n"
                            f"除外ロール: `{len(setting.ignore_roles)}`個"
            )
            await ctx.respond(embed=embed)

    # async def dictionary_autocomplete(self, ctx: discord.AutocompleteContext):
    #     return list(self.vm.guild_replacers.get(ctx.guild.id).keys())

    @guild_dictionary.command(name="add", description="辞書を追加する")
    async def add(
            self,
            ctx: BridgeCtx,
            before: BridgeOption(str, "変換前の文字列"),
            after: BridgeOption(str, "変換後の文字列"),
            use_regex: BridgeOption(bool, "正規表現を使用するか", default=False)
    ):
        if before in self.vm.guild_replacers.get(ctx.guild.id):
            await ctx.respond("辞書が既に存在します")
            return
        self.vm.guild_replacers.add(ctx.guild.id, before, after, use_regex)
        description = (f"### 単語\n```{before}```\n### 読み\n```{after}```\n"
                       f"### 正規表現: {'使用する' if use_regex else '使用しない'}")
        embed = Embed(title="辞書追加")
        embed.add_field(name="単語", value=before)
        embed.add_field(name="読み", value=after)
        embed.add_field(name="正規表現", value="使用する" if use_regex else "使用しない")
        await ctx.respond(embed=embed)

    @guild_dictionary.command(name="delete", description="辞書を削除する")
    async def delete(
            self,
            ctx: BridgeCtx,
            before: BridgeOption(str, "変換前の文字列")
    ):
        if not self.vm.guild_replacers.get(ctx.guild.id, before):
            await ctx.respond("辞書が存在しません")
            return
        self.vm.guild_replacers.delete(ctx.guild.id, before)
        embed = Embed(title="サーバー辞書削除")
        embed.add_field(name="単語", value=before)
        await ctx.respond(embed=embed)

    @guild_dictionary.command(name="list", description="辞書を表示する")
    async def dictionary_list(
            self,
            ctx: BridgeCtx,
            json: BridgeOption(bool, "JSON形式で表示するか", default=True)
    ):
        data = self.vm.guild_replacers.get(ctx.guild.id)
        if not data:
            await ctx.respond("辞書が存在しません")
            return
        await ctx.respond(f"{len(data)}件の辞書が登録されています")
        if json:
            file = dumps(
                {
                    "regex": data.regex_replacements_str,
                    "simple": data.simple_replacements,
                },
                indent=2,
                ensure_ascii=False
            )
            file = StringIO(file)
            file.seek(0)
            await ctx.send(
                f"<@{ctx.author.id}>のユーザー辞書",
                file=File(file, filename=f"{ctx.author.id}_guild_dictionary.json")
            )
        else:
            pagenator = list_pagination(data.regex_replacements_str, data.simple_replacements)
            await pagenator.respond(ctx)

    @guild_dictionary.command(name="update", description="辞書を更新する")
    async def update(
            self,
            ctx: BridgeCtx,
            old_before: BridgeOption(str, "変換前の文字列"),
            new_before: BridgeOption(str, "変換前の文字列"),
            after: BridgeOption(str, "変換後の文字列"),
            use_regex: BridgeOption(bool, "正規表現を使用するか")
    ):
        if not self.vm.guild_replacers.get(ctx.guild.id, old_before):
            await ctx.respond("辞書が存在しません")
            return
        self.vm.guild_replacers.update(ctx.guild.id, old_before, new_before, after, use_regex)
        description = (f"### 変更前単語\n```{old_before}```\n### 単語\n```{new_before}```\n### 読み\n```{after}```\n"
                       f"### 正規表現: {'使用する' if use_regex else '使用しない'}")
        embed = Embed(title="辞書更新", description=description)
        await ctx.respond(embed=embed)


def setup(bot: voicemanager.VoiceManagedBot):
    global styles
    styles = bot.voice_manager.speakers.styles()
    bot.add_cog(UserCommands(bot, bot.voice_manager))
    bot.add_cog(GuildCommands(bot, bot.voice_manager))
