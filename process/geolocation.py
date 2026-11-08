
import requests
from requests import Response
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


def get_location(ip):
    try:
        response: Response = requests.get(
            "https://ipinfo.io/" + ip + "/json/",
            timeout=5
        )

        if response.status_code == 200:
            return response.json()

        logger.error(
            "Erreur HTTP %s lors de la géolocalisation de l'IP : %s",
            response.status_code,
            ip
        )
        return None

    except Exception:
        logger.exception(
            "Erreur lors de la géolocalisation de l'IP : %r", ip
        )
        raise


if __name__ == "__main__":
    print(get_location('109.199.110.135'))
