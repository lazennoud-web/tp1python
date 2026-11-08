
import re
import logging
import os

# Configuration du fichier de journalisation
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_DIR, "app_logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

if not logger.handlers:
    handler = logging.FileHandler(
        os.path.join(LOG_DIR, "process.log"),
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False


# 4 groupes : mois, jour, heure (hh:mm:ss), message
PATTERN = re.compile(r'(\w{3})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})\s+\S+\s+\S+:\s(.*)')
IP_PATTERN = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')


def extract_from_row(row):
    try:
        match = PATTERN.search(row)

        if not match:
            return None

        month, day, time, message = match.groups()

        ip = IP_PATTERN.search(message)

        return {
            "month": month,
            "day": int(day),
            "time": time,
            "message": message.strip(),
            "ip": ip.group(1) if ip else None,
        }

    except Exception:
        logger.exception(
            "Erreur lors de l'extraction de la ligne : %r", row
        )
        raise


if __name__ == "__main__":
    from ingestion import raw
    print(extract_from_row(raw.toRows('./data')[0]))
