
import os
import time
import threading
import logging

import mysql.connector
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ingestion import raw
from process import extract_transforme
from storage.main import DB_CONFIG, create_table, save_rows


# ---------- Configuration ----------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

LOG_DIR = os.path.join(BASE_DIR, "app_logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

if not logger.handlers:
    handler = logging.FileHandler(
        os.path.join(LOG_DIR, "watch.log"),
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False


lock = threading.Lock()


# ---------- Importation automatique ----------

def import_logs():
    with lock:
        conn = None

        try:
            rows = raw.toRows(DATA_DIR)

            entries = []

            for row in rows:
                entry = extract_transforme.extract_from_row(row)

                if entry:
                    entries.append(entry)

            conn = mysql.connector.connect(**DB_CONFIG)

            create_table(conn)

            inserted = save_rows(conn, entries)

            print(f"{inserted} nouveaux logs enregistrés dans MySQL.")

        except Exception:
            logger.exception("Erreur pendant l'importation automatique des logs")
            print("Erreur pendant l'importation. Consultez app_logs/watch.log")

        finally:
            if conn is not None:
                try:
                    if conn.is_connected():
                        conn.close()

                except Exception:
                    logger.exception("Erreur lors de la fermeture de la connexion MySQL")


# ---------- Surveillance des fichiers ----------

class LogHandler(FileSystemEventHandler):

    def process_event(self, event):
        try:
            if event.is_directory:
                return

            filename = os.path.basename(event.src_path)

            if not filename.startswith("auth.log"):
                return

            print(f"\nModification détectée : {filename}")

            # Attendre que l'écriture du fichier soit terminée
            time.sleep(1)

            import_logs()

        except Exception:
            logger.exception("Erreur lors du traitement d'un événement de fichier")

    def on_created(self, event):
        self.process_event(event)

    def on_modified(self, event):
        self.process_event(event)

    def on_moved(self, event):
        self.process_event(event)


# ---------- Programme principal ----------

def main():
    observer = None

    try:
        print("Importation initiale des logs...")
        import_logs()

        observer = Observer()
        observer.schedule(LogHandler(), DATA_DIR, recursive=False)
        observer.start()

        print("\nSurveillance automatique activée.")
        print("Dossier surveillé :", DATA_DIR)
        print("Appuyez sur CTRL + C pour arrêter.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nSurveillance arrêtée.")

    except Exception:
        logger.exception("Erreur pendant le démarrage ou la surveillance des fichiers")
        raise

    finally:
        if observer is not None:
            try:
                observer.stop()
                observer.join()

            except Exception:
                logger.exception("Erreur lors de l'arrêt de la surveillance")


if __name__ == "__main__":
    main()
