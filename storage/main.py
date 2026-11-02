import sqlite3
from ingestion import raw
from process import extract_transforme

DB_PATH = "logs.db"


def create_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT,
            day INTEGER,
            time TEXT,
            message TEXT,
            ip TEXT
        )
    """)


def save_rows(conn, entries):
    conn.executemany(
        "INSERT INTO logs (month, day, time, message, ip) VALUES (?, ?, ?, ?, ?)",
        [(e["month"], e["day"], e["time"], e["message"], e["ip"]) for e in entries],
    )
    conn.commit()


def main():
    rows = raw.toRows('./data')
    entries = []
    for row in rows:
        entry = extract_transforme.extract_from_row(row)
        if entry:
            entries.append(entry)

    conn = sqlite3.connect(DB_PATH)
    create_table(conn)
    conn.execute("DELETE FROM logs")   # repart de zéro à chaque lancement
    save_rows(conn, entries)
    conn.close()
    print(f"{len(entries)} lignes enregistrées dans {DB_PATH}")


if __name__ == "__main__":
    main()