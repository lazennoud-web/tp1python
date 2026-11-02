# Log Analyser

## Présentation
Projet Python d’analyse de fichiers de logs SSH (auth.log).

## Fonctionnalités
- Lecture des fichiers normaux et compressés (.gz).
- Extraction avec expressions régulières.
- Identification des adresses IP.
- Stockage SQLite.
- Statistiques par événement, heure et jour.
- Identification des utilisateurs ciblés.
- Classement des IP les plus actives.
- Géolocalisation avec ipinfo.io.
- Dashboard Matplotlib : 4 indicateurs et 6 graphiques.

## Technologies
Python, SQLite, Matplotlib, Requests, Regex.

## Installation
uv sync

## Exécution
uv run python -m storage.main

## Auteur
Projet réalisé dans le cadre d’un travail pratique en informatique.

## Requêtes SQL

Base : `logs.db`, table `logs` (id, month, day, time, message, ip).

```sql
-- Nombre total de lignes
SELECT COUNT(*) FROM logs;

-- Top 10 des IP
SELECT ip, COUNT(*) FROM logs WHERE ip IS NOT NULL GROUP BY ip ORDER BY 2 DESC LIMIT 10;

-- IP avec le plus de mots de passe échoués
SELECT ip, COUNT(*) FROM logs WHERE message LIKE 'Failed password%' GROUP BY ip ORDER BY 2 DESC LIMIT 5;

-- Événements par heure
SELECT substr(time, 1, 2) AS heure, COUNT(*) FROM logs GROUP BY heure ORDER BY heure;

-- Jours les plus actifs
SELECT month, day, COUNT(*) FROM logs GROUP BY month, day ORDER BY 3 DESC LIMIT 5;

-- Connexion réussie
SELECT * FROM logs WHERE message LIKE 'Accepted%';
```
