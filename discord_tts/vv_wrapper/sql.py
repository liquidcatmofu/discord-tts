import sqlite3


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
