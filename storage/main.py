
import re
import sqlite3
import requests
from collections import Counter

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from ingestion import raw
from process import extract_transforme
from process import geolocation

DB_PATH = "logs.db"
USER_RE = re.compile(r'Failed password for (?:invalid user )?(\S+) from')

BG, CARD, TEXT = "#0f172a", "#1e293b", "#e2e8f0"
BLUE, RED, GREEN, ORANGE, PURPLE = "#38bdf8", "#f87171", "#4ade80", "#fb923c", "#a78bfa"


# ---------- Base de données ----------
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


def load_rows(conn):
    return conn.execute(
        "SELECT month, day, time, message, ip FROM logs ORDER BY id"
    ).fetchall()


# ---------- Statistiques ----------
def classify(msg):
    if "nvalid user" in msg:
        return "Invalid user"
    if msg.startswith("Failed password"):
        return "Failed password"
    if "authentication failure" in msg:
        return "Auth failure"
    if msg.startswith("Accepted"):
        return "Accepted login"
    if msg.startswith("Connection closed"):
        return "Connection closed"
    if "isconnect" in msg:
        return "Disconnect"
    return "Other"


def compute_stats(rows):
    s = {
        "types": Counter(),
        "hours": Counter(),
        "days": Counter(),
        "users": Counter(),
        "ips": Counter(),
    }

    for month, day, t, msg, ip in rows:
        kind = classify(msg)
        s["types"][kind] += 1
        s["hours"][int(t[:2])] += 1
        s["days"][f"{month} {day:02d}"] += 1

        if ip:
            s["ips"][ip] += 1

        if kind in ("Failed password", "Invalid user"):
            m = USER_RE.search(msg)
            if m:
                s["users"][m.group(1)] += 1

    return s



def countries_stats(top, limit=8):
    countries = Counter()

    print("Géolocalisation du top IP :")

    for ip, count in top[:limit]:

        if ip == "127.0.0.1":
            print(f"  {ip} ({count}) : adresse locale")
            continue

        try:
            response = requests.get(
                f"http://ip-api.com/json/{ip}?fields=status,country,city",
                timeout=5
            )

            info = response.json()

            if info.get("status") == "success":
                country = info.get("country", "Inconnu")
                city = info.get("city", "Inconnue")

                countries[country] += count
                print(f"  {ip} ({count}) : {country} - {city}")

            else:
                countries["Inconnu"] += count
                print(f"  {ip} ({count}) : localisation indisponible")

        except requests.RequestException:
            countries["Inconnu"] += count
            print(f"  {ip} ({count}) : erreur de connexion")

    return countries


# ---------- Dashboard ----------
def style(ax, title):
    ax.set_facecolor(CARD)
    ax.set_title(title, color=TEXT, fontsize=11, fontweight="bold", loc="left")
    ax.tick_params(colors=TEXT, labelsize=8)

    for sp in ax.spines.values():
        sp.set_visible(False)

    ax.grid(axis="x", alpha=0.15)


def barh(ax, counter, title, color, n=8):
    items = counter.most_common(n)
    labels = [k for k, _ in items][::-1]
    values = [v for _, v in items][::-1]

    style(ax, title)
    ax.barh(labels, values, color=color)


def show_dashboard(rows, stats, top, countries):
    total = len(rows)
    failed = stats["types"]["Failed password"]
    rate = failed / total * 100 if total else 0

    kpis = [
        ("Événements", total, BLUE),
        ("IP uniques", len(stats["ips"]), GREEN),
        ("Mots de passe échoués", failed, RED),
        ("Taux d'échec", f"{rate:.1f} %", ORANGE),
    ]

    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.suptitle(
        "Log Analyser - Dashboard SSH",
        color=TEXT,
        fontsize=18,
        fontweight="bold"
    )

    gs = GridSpec(
        3, 3,
        figure=fig,
        height_ratios=[0.5, 1, 1],
        hspace=0.55,
        wspace=0.35
    )

    # 4 indicateurs
    ax = fig.add_subplot(gs[0, :])
    ax.set_facecolor(BG)
    ax.axis("off")

    for i, (label, value, color) in enumerate(kpis):
        x = 0.02 + i * 0.25
        ax.text(
            x, 0.55, str(value),
            color=color,
            fontsize=26,
            fontweight="bold",
            transform=ax.transAxes
        )
        ax.text(
            x, 0.1, label,
            color=TEXT,
            fontsize=11,
            transform=ax.transAxes
        )

    # 1. Top IP
    ax = fig.add_subplot(gs[1, 0])
    style(ax, "Top 10 IP les plus actives")
    ax.barh(
        [ip for ip, _ in top][::-1],
        [c for _, c in top][::-1],
        color=BLUE
    )

    # 2. Types d'événements
    barh(
        fig.add_subplot(gs[1, 1]),
        stats["types"],
        "Types d'événements",
        PURPLE
    )

    # 3. Utilisateurs ciblés
    barh(
        fig.add_subplot(gs[1, 2]),
        stats["users"],
        "Comptes les plus ciblés",
        RED
    )

    # 4. Événements par heure
    ax = fig.add_subplot(gs[2, 0])
    style(ax, "Événements par heure")

    hours = list(range(24))
    ax.bar(
        hours,
        [stats["hours"].get(h, 0) for h in hours],
        color=GREEN
    )
    ax.set_xticks(range(0, 24, 3))

    # 5. Événements par jour
    ax = fig.add_subplot(gs[2, 1])
    style(ax, "Événements par jour")

    days = list(stats["days"].keys())
    values = list(stats["days"].values())

    ax.plot(
        range(len(days)),
        values,
        color=ORANGE,
        marker="o",
        markersize=3
    )

    step = max(1, len(days) // 6)
    ax.set_xticks(range(0, len(days), step))
    ax.set_xticklabels(days[::step], rotation=30)

    # 6. Pays
    barh(
        fig.add_subplot(gs[2, 2]),
        countries,
        "Pays des IP (top)",
        BLUE
    )

    plt.show()


# ---------- Programme principal ----------
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
    data = load_rows(conn)

    conn.close()

    stats = compute_stats(data)

    print("Types d'événements :", dict(stats["types"]))

    countries = countries_stats(top)

    show_dashboard(data, stats, top, countries)


if __name__ == "__main__":
    main()
