
import re
import os
import hashlib
import logging
import ipaddress
import json
import mysql.connector
from dotenv import load_dotenv
import requests
from collections import Counter

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from ingestion import raw
from process import extract_transforme
from process import geolocation


# ---------- Configuration ----------

load_dotenv()

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_DIR, "app_logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

if not logger.handlers:
    handler = logging.FileHandler(
        os.path.join(LOG_DIR, "storage.log"),
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False


# Configuration MySQL
try:
    DB_PORT = int(os.getenv("DB_PORT"))
except (TypeError, ValueError):
    logger.exception("Configuration MySQL invalide : DB_PORT")
    raise

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": DB_PORT,
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

FAILED_USER_RE = re.compile(
    r'^Failed password for (?:invalid user )?(\S+) from'
)

SUCCESS_USER_RE = re.compile(
    r'^Accepted (?:password|publickey|keyboard-interactive/pam) for (\S+) from'
)

BG, CARD, TEXT = "#0f172a", "#1e293b", "#e2e8f0"
BLUE, RED, GREEN, ORANGE, PURPLE = "#38bdf8", "#f87171", "#4ade80", "#fb923c", "#a78bfa"


# ---------- Base de données MySQL ----------

def create_table(conn):
    cursor = None

    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                month VARCHAR(20),
                day INT,
                time VARCHAR(20),
                message TEXT,
                ip VARCHAR(45),
                log_hash CHAR(64),
                UNIQUE KEY unique_log_hash (log_hash)
            )
        """)

        conn.commit()

    except Exception:
        logger.exception("Erreur lors de la création de la table MySQL")
        raise

    finally:
        if cursor is not None:
            cursor.close()


def save_rows(conn, entries):
    cursor = None

    try:
        cursor = conn.cursor()
        inserted = 0
        batch_size = 500

        for i in range(0, len(entries), batch_size):
            batch = []

            for e in entries[i:i + batch_size]:
                values = (
                    e["month"],
                    e["day"],
                    e["time"],
                    e["message"],
                    e["ip"]
                )

                content = "|".join(
                    str(value) if value is not None else ""
                    for value in values
                )

                log_hash = hashlib.sha256(
                    content.encode("utf-8")
                ).hexdigest()

                batch.append(values + (log_hash,))

            cursor.executemany(
                """
                INSERT IGNORE INTO logs
                (month, day, time, message, ip, log_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                batch
            )

            inserted += cursor.rowcount
            conn.commit()

        return inserted

    except Exception:
        logger.exception("Erreur lors de l'enregistrement des logs")
        raise

    finally:
        if cursor is not None:
            cursor.close()


def top_ips(conn, n=10):
    cursor = None

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT ip, COUNT(*)
            FROM logs
            WHERE ip IS NOT NULL
            GROUP BY ip
            ORDER BY 2 DESC
            LIMIT %s
            """,
            (n,)
        )

        return cursor.fetchall()

    except Exception:
        logger.exception("Erreur lors du calcul du top IP")
        raise

    finally:
        if cursor is not None:
            cursor.close()


def load_rows(conn):
    cursor = None

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT month, day, time, message, ip
            FROM logs
            ORDER BY id
            """
        )

        return cursor.fetchall()

    except Exception:
        logger.exception("Erreur lors de la lecture des logs")
        raise

    finally:
        if cursor is not None:
            cursor.close()


# ---------- Statistiques ----------

def classify(msg):
    if msg.startswith("Failed password for invalid user "):
        return "Failed password - Invalid user"

    if msg.startswith("Failed password"):
        return "Failed password"

    if msg.startswith("Invalid user "):
        return "Invalid user detected"

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
    try:
        s = {
            "types": Counter(),
            "hours": Counter(),
            "days": Counter(),
            "users": Counter(),
            "successful_users": Counter(),
            "ips": Counter(),
            "failed_ips": Counter(),
            "invalid_user_failures": 0,
        }

        for month, day, t, msg, ip in rows:
            kind = classify(msg)

            s["types"][kind] += 1
            s["hours"][int(t[:2])] += 1
            s["days"][f"{month} {day:02d}"] += 1

            if ip:
                s["ips"][ip] += 1

            if msg.startswith("Failed password"):

                if ip:
                    s["failed_ips"][ip] += 1

                m = FAILED_USER_RE.search(msg)

                if m:
                    s["users"][m.group(1)] += 1

                if msg.startswith("Failed password for invalid user "):
                    s["invalid_user_failures"] += 1

            if msg.startswith("Accepted"):
                m = SUCCESS_USER_RE.search(msg)

                if m:
                    s["successful_users"][m.group(1)] += 1

        return s

    except Exception:
        logger.exception("Erreur lors du calcul des statistiques")
        raise


# ---------- Géolocalisation des tentatives échouées ----------

def countries_stats(failed_ips):

    countries = Counter()

    cache_path = os.path.join(LOG_DIR, "country_cache.json")

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)

        if not isinstance(cache, dict):
            cache = {}

    except FileNotFoundError:
        cache = {}

    except (ValueError, OSError):
        logger.exception("Erreur lors de la lecture du cache géographique")
        cache = {}

    pending = []

    for ip, count in failed_ips.items():

        try:
            address = ipaddress.ip_address(ip)

            if not address.is_global:
                countries["IP privée / locale"] += count
                continue

        except ValueError:
            countries["Inconnu"] += count
            logger.error("Adresse IP invalide : %s", ip)
            continue

        if ip in cache:
            countries[cache[ip]] += count
        else:
            pending.append((ip, count))

    print("Nombre d'IP à géolocaliser :", len(pending))
    print("Nombre d'IP déjà en cache :", len(failed_ips) - len(pending))

    batch_size = 100
    processed = 0

    for i in range(0, len(pending), batch_size):

        batch = pending[i:i + batch_size]

        payload = [
            {"query": ip, "fields": "status,country"}
            for ip, count in batch
        ]

        try:
            response = requests.post(
                "http://ip-api.com/batch",
                json=payload,
                timeout=30
            )

            response.raise_for_status()

            results = response.json()

            if not isinstance(results, list) or len(results) != len(batch):
                raise ValueError("Réponse batch invalide")

            for (ip, count), info in zip(batch, results):

                if info.get("status") == "success" and info.get("country"):

                    country = info["country"]
                    cache[ip] = country
                    countries[country] += count

                else:
                    countries["Inconnu"] += count

                    logger.error(
                        "Géolocalisation indisponible pour l'IP %s",
                        ip
                    )

            processed += len(batch)

        except (requests.RequestException, ValueError, TypeError):
            logger.exception("Erreur pendant le batch numéro %s", i // batch_size + 1)

            for ip, count in batch:
                countries["Inconnu"] += count

            processed += len(batch)
            break

    # Les IP restantes sont comptabilisées comme inconnues
    for ip, count in pending[processed:]:
        countries["Inconnu"] += count

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    except OSError:
        logger.exception("Erreur lors de l'enregistrement du cache géographique")

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

    failed = (
        stats["types"]["Failed password"]
        + stats["types"]["Failed password - Invalid user"]
    )

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

    # 6. Pays des tentatives échouées
    barh(
        fig.add_subplot(gs[2, 2]),
        countries,
        "Tentatives échouées par pays",
        BLUE
    )

    plt.show()


# ---------- Programme principal ----------

def main():

    # Lecture et extraction des logs
    rows = raw.toRows('./data')

    entries = []

    for row in rows:
        entry = extract_transforme.extract_from_row(row)

        if entry:
            entries.append(entry)

    # Connexion à MySQL
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("Connexion à MySQL réussie !")

    except Exception:
        logger.exception("Erreur lors de la connexion à MySQL")
        raise

    try:
        create_table(conn)

        inserted = save_rows(conn, entries)

        print(f"{inserted} nouveaux logs enregistrés dans MySQL.")

        top = top_ips(conn)
        data = load_rows(conn)

    finally:
        conn.close()
        print("Connexion MySQL fermée.")

    # Calcul des statistiques
    stats = compute_stats(data)

    print("Types d'événements :", dict(stats["types"]))
    print("Connexions réussies par utilisateur :", dict(stats["successful_users"]))
    print("Tentatives échouées avec Invalid user :", stats["invalid_user_failures"])

    # Géolocalisation de toutes les IP échouées
    countries = countries_stats(stats["failed_ips"])

    print("Tentatives échouées par pays :", dict(countries))

    # Affichage du dashboard
    try:
        show_dashboard(data, stats, top, countries)

    except Exception:
        logger.exception("Erreur lors de l'affichage du dashboard")
        raise


if __name__ == "__main__":
    main()
