from dataclasses import dataclass
import os
import re
import sqlite3
from urllib.parse import urlparse

path = "../dictionary.db"


class SQLiteWrapper:
    def __init__(self, database):
        """データベースへの接続を初期化します。"""
        self.connection = sqlite3.connect(database)
        self.cursor = self.connection.cursor()

    def execute(self, query, params=None):
        """クエリを実行し、結果を返します。"""
        if params is None:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def commit(self):
        """変更をコミットします。"""
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        """データベースの接続を閉じます。"""
        self.connection.close()

    # def __del__(self):
    #     """データベースの接続を閉じます。"""
    #     if self.connection:
    #         self.connection.close()


class Replacer:
    def __init__(self, regex_replacements: dict[str: str], simple_replacements: dict[str: str]) -> None:
        self.regex_replacements: dict[re.Pattern: str] = {re.compile(k): v for k, v in regex_replacements.items()}
        self.simple_replacements: dict[str: str] = simple_replacements

    def replace(
            self,
            text: str,
            *,
            url_replacement: str | None = "URL省略"
    ) -> str:
        print(self.regex_replacements)
        # 正規表現を使用する置換を一括で実行
        for before, after in self.regex_replacements.items():
            text = before.sub(after, text)
            print("#regex", before, after, text)
        # 正規表現を使用しない置換を実行
        for before, after in self.simple_replacements.items():
            text = text.replace(before, after)
            print("#simple", before, after, text)
        # print(text)
        if url_replacement:
            text = self.replace_urls(text, url_replacement)

        return text

    def update_replacements(self, regex_replacements: dict[str: str], simple_replacements: dict[str: str]) -> None:
        self.regex_replacements: dict[re.Pattern: str] = {re.compile(k): v for k, v in regex_replacements.items()}
        self.simple_replacements: dict[str: str] = simple_replacements

    @staticmethod
    def replace_urls(text: str, replacement: str) -> str:
        # URLの正規表現パターン
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)

        for url in urls:
            parsed_url = urlparse(url)
            if parsed_url.scheme and parsed_url.netloc:
                text = text.replace(url, replacement)

        return text

    @staticmethod
    def replace_code_blocks(text: str, replacement: str) -> str:
        # コードブロックの正規表現パターン
        code_block_pattern = r'```.*?```'
        code_blocks = re.findall(code_block_pattern, text, re.DOTALL)

        for code_block in code_blocks:
            text = text.replace(code_block, replacement)

        return text

    def __bool__(self):
        return bool(self.regex_replacements or self.simple_replacements)


class Dictionary:
    """
    dictionary database wrapper
    """
    file_path: str | os.PathLike = path
    # replacer: EfficientReplacer | None = None

    @classmethod
    def set_db_path(cls, path: str | os.PathLike) -> None:
        cls.file_path = path

    @classmethod
    def create_table(cls, id: int, type: str = "guild") -> None:
        db = SQLiteWrapper(cls.file_path)
        try:
            db.execute(f"CREATE TABLE IF NOT EXISTS {type}{id} "
                       f"(id INTEGER PRIMARY KEY AUTOINCREMENT,before TEXT UNIQUE NOT NULL , after TEXT, re INTEGER)")
            db.commit()
        except sqlite3.OperationalError as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def add_dictionary(cls, id: int, before: str, after: str, use_re: bool = False, type: str = "guild") -> None:
        db = SQLiteWrapper(cls.file_path)
        try:
            db.execute(f"INSERT INTO {type}{id} (before, after, re) VALUES (?, ?, ?)",
                       (before, after, use_re))
            db.commit()
        except sqlite3.OperationalError as e:
            db.rollback()
            raise e
        except sqlite3.IntegrityError as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def delete_dictionary(cls, id: int, before: str, type: str = "guild") -> None:
        db = SQLiteWrapper(cls.file_path)
        try:
            db.execute(f"DELETE FROM {type}{id} WHERE before = ?",
                       (before,))
            db.commit()
        except sqlite3.OperationalError as e:
            db.rollback()
            raise e
        except sqlite3.IntegrityError as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def update_dictionary(cls, id: int,
                          old_before: str, new_before: str, after: str, use_re: bool = False,
                          type: str = "guild") -> None:
        db = SQLiteWrapper(cls.file_path)
        try:
            db.execute(f"UPDATE {type}{id} SET before = ?, after = ?, re = ? WHERE before = ?",
                       (new_before, after, use_re, old_before))
            db.commit()
        except sqlite3.OperationalError as e:
            db.rollback()
            raise e
        except sqlite3.IntegrityError as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def fetch_dictionaries(cls, id: int, type: str = "guild") -> list:
        """
        fetch all dictionaries from database
        :param id: discord id
        :param type: database type
        :return: dictionaries
        """
        db = SQLiteWrapper(cls.file_path)
        try:
            data = db.execute(f"SELECT * FROM {type}{id}")
        except sqlite3.OperationalError as e:
            raise e
        finally:
            db.close()
        return data

    @classmethod
    def fetch_dictionary(cls, id: int, before: str, type: str = "guild") -> list:
        """
        fetch dictionary from database with key
        :param type: database type
        :param id: discord id
        :param before: dictionary before (key)
        :return: dictionary
        """
        db = SQLiteWrapper(cls.file_path)
        try:
            data = db.execute(f"SELECT * FROM {type}{id} WHERE before = ?",
                              (before,))
        except sqlite3.OperationalError as e:
            raise e
        finally:
            db.close()
        return data


@dataclass
class BaseSetting:
    id: int
    speaker: int
    speed: float
    pitch: float
    intonation: float
    volume: float


@dataclass
class UserSetting(BaseSetting):
    use_dict_name: bool


@dataclass
class ServerSetting(BaseSetting):
    force_setting: bool
    force_speaker: bool
    read_joinleave: bool
    read_length: bool
    read_nonparticipation: bool
    read_replyuser: bool
    ignore_users: list[str]
    ignore_roles: list[str]


class SettingLoader:
    """
    setting database wrapper
    """
    file_path: str | os.PathLike = "./setting.db"

    @classmethod
    def set_db_path(cls, path: str | os.PathLike) -> None:
        cls.file_path = path

    @classmethod
    def create_table(cls) -> None:
        db = SQLiteWrapper(cls.file_path)
        try:
            db.execute(f"CREATE TABLE IF NOT EXISTS users "
                       f"(id INTEGER PRIMARY KEY , speaker INTEGER NOT NULL ,"
                       f" speed REAL , pitch REAL, intonation REAL, volume REAL , use_dict_name INTEGER)")
            db.execute(f"CREATE TABLE IF NOT EXISTS guilds "
                       f"(id INTEGER PRIMARY KEY , speaker INTEGER NOT NULL , speed REAL , pitch REAL, intonation REAL,"
                       f" volume REAL , force_setting INTEGER , force_speaker INTEGER , read_joinleave INTEGER ,"
                       f" read_length INTEGER , read_nonparticipation INTEGER , read_replyuser INTEGER ,"
                       f"  ignore_users TEXT , ignore_roles TEXT)")
            db.commit()
        except sqlite3.OperationalError as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def add_setting(cls, table: str, id: int, **kwargs) -> None:
        db = SQLiteWrapper(cls.file_path)
        if table == "users":
            datas = {"speaker": 3, "speed": 1.0, "pitch": 0.0, "intonation": 1.0, "volume": 1.0, "use_dict_name": 0}
        elif table == "guilds":
            datas = {"speaker": 3, "speed": 1.0, "pitch": 1.0, "intonation": 1.0, "volume": 1.0, "force_setting": 0,
                     "force_speaker": 0, "read_joinleave": 0, "read_length": 0, "read_nonparticipation": 0,
                     "read_replyuser": 0, "ignore_users": "", "ignore_roles": ""}
        else:
            raise ValueError(f"table name {table} is invalid")
        datas.update(kwargs)
        try:
            if table == "users":
                db.execute(
                    f"INSERT INTO {table} (id, speaker, speed, pitch, intonation, volume, use_dict_name) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (id, datas["speaker"], datas["speed"], datas["pitch"], datas["intonation"], datas["volume"],
                        datas["use_dict_name"]))
            elif table == "guilds":
                db.execute(
                    f"INSERT INTO {table} (id, speaker, speed, pitch, intonation, volume, force_setting, force_speaker,"
                    f" read_joinleave, read_length, read_nonparticipation, read_replyuser, ignore_users, ignore_roles) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (id, datas["speaker"], datas["speed"], datas["pitch"], datas["intonation"], datas["volume"],
                        datas["force_setting"], datas["force_speaker"], datas["read_joinleave"], datas["read_length"],
                        datas["read_nonparticipation"], datas["read_replyuser"], datas["ignore_users"],
                        datas["ignore_roles"]))
            db.commit()
        except sqlite3.OperationalError as e:
            db.rollback()
            raise e
        except sqlite3.IntegrityError as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def delete_setting(cls, table: str, id: int) -> None:
        db = SQLiteWrapper(cls.file_path)
        try:
            db.execute(f"DELETE FROM {table} WHERE id = ?",
                       (id,))
            db.commit()
        except sqlite3.OperationalError as e:
            db.rollback()
            raise e
        except sqlite3.IntegrityError as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def update_setting(cls, table: str, id: int, column: str, value: str) -> None:
        db = SQLiteWrapper(cls.file_path)
        try:
            db.execute(f"UPDATE {table} SET ? = ? WHERE id = ?",
                       (column, value, id))
            db.commit()
        except sqlite3.OperationalError as e:
            db.rollback()
            raise e
        except sqlite3.IntegrityError as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def fetch_settings(cls, table: str, id: int) -> list:
        """
        fetch all settings from database
        """
        db = SQLiteWrapper(cls.file_path)
        try:
            data = db.execute(f"SELECT * FROM {table} WHERE id = ?",
                              (id,))
        except sqlite3.OperationalError as e:
            raise e
        finally:
            db.close()
        return data

    @classmethod
    def smart_fetch(cls, table: str, id: int) -> ServerSetting | UserSetting | None:
        data = cls.fetch_settings(table, id)
        if not data:
            return None
        if table == "guilds":
            return ServerSetting(*data[0])
        elif table == "users":
            return UserSetting(*data[0])
        else:
            raise ValueError(f"table name {table} is invalid")
