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
- Géolocalisation avec IP-API.
- Dashboard Matplotlib : 4 indicateurs et 6 graphiques.

## Technologies
Python, SQLite, Matplotlib, Requests, Regex.

## Installation
uv sync

## Exécution
uv run python -m storage.main

## Auteur
Projet réalisé dans le cadre d’un travail pratique en informatique.
