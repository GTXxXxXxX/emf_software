import sqlite3


class DBHandler:
    def __init__(self, db_name):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.db_name = db_name

        self.cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {self.db_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            date TEXT NOT NULL,
            extraction_time FLOAT NOT NULL)         
        """)

    def insert_invoice(self, name, path, date, extraction_time):
        self.cursor.execute(f"INSERT INTO processed_invoices (name, path, date, extraction_time) VALUES (?,?,?,?)",
                            (name, path, date, round(extraction_time, 2)))
        self.connection.commit()

    def get_invoices(self):
        self.cursor.execute(f"SELECT * FROM processed_invoices")
        return self.cursor.fetchall()

    def clear_db(self):
        self.cursor.execute("DELETE FROM processed_invoices")
        self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='processed_invoices'")
        self.connection.commit()
        print("DB - Purged db.")

    def close_connection(self):
        self.connection.close()
