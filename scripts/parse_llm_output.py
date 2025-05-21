#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===================================================
# Description : Ce script récupère la sortie brute d'un modèle de langage
#               et essaie d'en extraire un tableau JSON d'entités ou d'événements.
#               Utiliser --mode entities ou --mode events.
#               La sortie brute peut être un tableau JSON, une chaîne contenant
#               un tableau JSON, ou du texte avec des objets JSON imbriqués.
#               Le script gère les erreurs de formatage et les cas particuliers.
#               Il renvoie un tableau JSON d'entités ou d'événements (ou tableau vide).
# ===================================================

import sys
import json
import re
import argparse

def extract_entities(raw_response):
    if not raw_response or not raw_response.strip():
        return []

    # Première tentative : réponse directement sous forme de tableau JSON
    try:
        data = json.loads(raw_response)
        if isinstance(data, list):
            # Accepte aussi les champs "start", "id", "events" si présents
            return [
                e for e in data
                if isinstance(e, dict)
                and e.get("text")
                and e.get("label")
                # "start", "id", "events" sont optionnels
            ]
    except json.JSONDecodeError:
        pass

    # Deuxième tentative : la réponse est une chaîne contenant un tableau JSON
    # Exemple : '[{"text": "X", "label": "Y"}]' ou avec du texte avant/après
    json_like = re.search(r'\[\s*\{.*?\}\s*\]', raw_response, re.DOTALL)
    if json_like:
        try:
            data = json.loads(json_like.group())
            if isinstance(data, list):
                return [e for e in data if isinstance(e, dict) and e.get("text") and e.get("label")]
        except json.JSONDecodeError:
            pass

    # Si toutes les tentatives échouent, retourne un tableau vide
    return []

def validate_events_structure(events):
    # Normalise events : assure que c'est une liste et que chaque événement est une liste.
    if not isinstance(events, list):
        return []
    normalized = []
    for e in events:
        if isinstance(e, list):
            normalized.append(e)
        else:
            normalized.append([e])
    return normalized

def extract_events(raw_response):
    if not raw_response or not raw_response.strip():
        return []

    # 1. Réponse directement sous forme d'objet JSON avec 'events'
    try:
        data = json.loads(raw_response)
        # Cas 1 : {"events": [...]}
        if isinstance(data, dict) and "events" in data:
            events = data["events"]
            if isinstance(events, list):
                return validate_events_structure(events)
        # Cas 2 : [{"events": [...]}, ...]
        if isinstance(data, list):
            all_events = []
            for obj in data:
                if isinstance(obj, dict) and "events" in obj and isinstance(obj["events"], list):
                    all_events.extend(obj["events"])
            if all_events:
                return validate_events_structure(all_events)
        # Cas 3 : la sortie est déjà un tableau d'événements
        if isinstance(data, list):
            if all(isinstance(e, (dict, list)) for e in data):
                return validate_events_structure(data)
    except json.JSONDecodeError:
        pass

    # 2. Extraction par regex si la clé "events" est présente dans du texte
    match = re.search(r'"events"\s*:\s*(\[[\s\S]*?\])', raw_response)
    if match:
        try:
            events = json.loads(match.group(1))
            if isinstance(events, list):
                return validate_events_structure(events)
        except Exception:
            pass

    # 3. Extraction d'un tableau JSON isolé dans le texte
    json_like = re.search(r'\[\s*\{.*?\}\s*\]', raw_response, re.DOTALL)
    if json_like:
        try:
            data = json.loads(json_like.group())
            if isinstance(data, list):
                return validate_events_structure(data)
        except Exception:
            pass

    return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["entities", "events"], default="entities", help="Mode d'extraction")
    args = parser.parse_args()

    raw_input = sys.stdin.read()
    if args.mode == "entities":
        cleaned = extract_entities(raw_input)
    else:
        cleaned = extract_events(raw_input)
    print(json.dumps(cleaned, ensure_ascii=False))
