import sqlite3
import matplotlib.pyplot as plt
from ingestion import raw
from process import extract_transforme
from process import geolocation

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


def top_ips(conn, n=10):
    return conn.execute(
        "SELECT ip, COUNT(*) FROM logs WHERE ip IS NOT NULL "
        "GROUP BY ip ORDER BY 2 DESC LIMIT ?", (n,)
    ).fetchall()


def show_countries(top):
    print("Pays des IP :")
    for ip, count in top:
        info = geolocation.get_location(ip)
        if info:
            print(f"  {ip} ({count}) : {info.get('country', '?')} - {info.get('city', '?')}")
        else:
            print(f"  {ip} ({count}) : localisation indisponible")


def show_chart(top):
    ips = [ip for ip, _ in top]
    counts = [c for _, c in top]
    plt.figure(figsize=(10, 5))
    plt.barh(ips[::-1], counts[::-1])
    plt.xlabel("Nombre d'événements")
    plt.title("Top 10 des IP les plus actives")
    plt.tight_layout()
    plt.show()


def main():
    rows = raw.toRows('./data')
    entries = []
    for row in rows:
        entry = extract_transforme.extract_from_row(row)
        if entry:
            entries.append(entry)

    conn = sqlite3.connect(DB_PATH)
    create_table(conn)
    conn.execute("DELETE FROM logs")
    save_rows(conn, entries)
    print(f"{len(entries)} lignes enregistrées dans {DB_PATH}")

    top = top_ips(conn)
    print("Top IP :")
    for ip, count in top:
        print(f"  {ip} : {count}")
    conn.close()

    show_countries(top)
    show_chart(top)


if __name__ == "__main__":
    main()