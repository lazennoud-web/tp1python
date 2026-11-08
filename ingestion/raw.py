
import gzip
import logging
import os

# Configuration du fichier de journalisation du module ingestion
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_DIR, "app_logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

if not logger.handlers:
    handler = logging.FileHandler(
        os.path.join(LOG_DIR, "ingestion.log"),
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False


"""
Read data log from data directory as rows
"""


def toRows(path):
    rows = []

    try:
        files = os.listdir(path)
    except Exception:
        logger.exception("Erreur lors de l'accès au dossier : %s", path)
        raise

    for file in files:
        file_path = os.path.join(path, file)

        try:
            openner = (
                gzip.open(filename=file_path, mode='rt', encoding='utf-8')
                if file.endswith('.gz')
                else open(file_path)
            )

            with openner as f:
                rows.extend(f.readlines())

        except Exception:
            logger.exception("Erreur lors de la lecture du fichier : %s", file_path)
            raise

    return rows


if __name__ == "__main__":
    print(toRows('./data')[:10])
