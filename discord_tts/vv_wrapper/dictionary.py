import os
import re
import sqlite3
from vv_wrapper import sql

path = "../dictionary.db"


class EfficientReplacer:
    def __init__(self, regex_replacements: dict[str: str], simple_replacements: dict[str: str]) -> None:
        self.regex_replacements: dict[str: str] = regex_replacements
        self.simple_replacements: dict[str: str] = simple_replacements

    def replace(self, text: str) -> str:
        print(self.regex_replacements)
        # 正規表現を使用する置換を一括で実行
        for before, after in self.regex_replacements.items():
            text = re.sub(before, after, text)
            print("#regex", before, after, text)
        # 正規表現を使用しない置換を実行
        for before, after in self.simple_replacements.items():
            text = text.replace(before, after)
            print("#simple", before, after, text)
        # print(text)
        return text

    def update_replacements(self, regex_replacements: dict[str: str], simple_replacements: dict[str: str]) -> None:
        self.regex_replacements: dict[str: str] = regex_replacements
        self.simple_replacements: dict[str: str] = simple_replacements


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
    def create_table(cls, guild_id: int) -> None:
        db = sql.SQLiteWrapper(cls.file_path)
        try:
            db.execute(f"CREATE TABLE IF NOT EXISTS guild{guild_id} "
                       f"(id INTEGER PRIMARY KEY AUTOINCREMENT,before TEXT UNIQUE NOT NULL , after TEXT, re INTEGER)")
            db.commit()
        except sqlite3.OperationalError as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def add_dictionary(cls, guild_id: int, before: str, after: str, use_re: bool = False) -> None:
        db = sql.SQLiteWrapper(cls.file_path)
        try:
            db.execute(f"INSERT INTO guild{guild_id} (before, after, re) VALUES (?, ?, ?)",
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
    def delete_dictionary(cls, guild_id: int, before: str) -> None:
        db = sql.SQLiteWrapper(cls.file_path)
        try:
            db.execute(f"DELETE FROM guild{guild_id} WHERE before = ?",
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
    def update_dictionary(cls, guild_id: int,
                          old_before: str, new_before: str, after: str, use_re: bool = False) -> None:
        db = sql.SQLiteWrapper(cls.file_path)
        try:
            db.execute(f"UPDATE guild{guild_id} SET before = ?, after = ?, re = ? WHERE before = ?",
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
    def fetch_dictionaries(cls, guild_id: int) -> list:
        """
        fetch all dictionaries from database
        :param guild_id: discord guild id
        :return: dictionaries
        """
        db = sql.SQLiteWrapper(cls.file_path)
        try:
            data = db.execute(f"SELECT * FROM guild{guild_id}")
        except sqlite3.OperationalError as e:
            raise e
        finally:
            db.close()
        return data

    @classmethod
    def fetch_dictionary(cls, guild_id: int, before: str) -> list:
        """
        fetch dictionary from database with key
        :param guild_id: discord guild id
        :param before: dictionary before (key)
        :return: dictionary
        """
        db = sql.SQLiteWrapper(cls.file_path)
        try:
            data = db.execute(f"SELECT * FROM guild{guild_id} WHERE before = ?",
                              (before,))
        except sqlite3.OperationalError as e:
            raise e
        finally:
            db.close()
        return data
