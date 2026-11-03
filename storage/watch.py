
import os
import time
import threading

import mysql.connector
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ingestion import raw
from process import extract_transforme
from storage.main import DB_CONFIG, create_table, save_rows


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

lock = threading.Lock()


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

        except Exception as e:
            print("Erreur pendant l'importation :", e)

        finally:
            if conn and conn.is_connected():
                conn.close()


class LogHandler(FileSystemEventHandler):

    def process_event(self, event):
        if event.is_directory:
            return

        filename = os.path.basename(event.src_path)

        if not filename.startswith("auth.log"):
            return

        print(f"\nModification détectée : {filename}")

        # Attendre que l'écriture du fichier soit terminée
        time.sleep(1)

        import_logs()

    def on_created(self, event):
        self.process_event(event)

    def on_modified(self, event):
        self.process_event(event)

    def on_moved(self, event):
        self.process_event(event)


def main():
    print("Importation initiale des logs...")
    import_logs()

    observer = Observer()
    observer.schedule(LogHandler(), DATA_DIR, recursive=False)
    observer.start()

    print("\nSurveillance automatique activée.")
    print("Dossier surveillé :", DATA_DIR)
    print("Appuyez sur CTRL + C pour arrêter.")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()
        print("\nSurveillance arrêtée.")

    observer.join()


if __name__ == "__main__":
    main()
