#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===================================================
# Description : Après annotation, ce script corrige la structure des événements
#               dans les fichiers JSON.
#
# Entrées :
#   - Un répertoire contenant des fichiers JSON annotés (entités + événements).
# Sorties :
#   - Un fichier JSON corrigé contenant la structure correcte des événements.
# ===================================================

import json
import os
from collections import Counter

def fix_events_structure(events):
    corrected_events = []
    stats = Counter({
        "groupes_valides": 0,
        "central_vides": 0,
        "associated_vides": 0,
        "associated_orphelins": 0,
        "total_central": 0,
        "total_associated": 0,
    })

    current_group = []
    for entry in events:
        if not isinstance(entry, list) or len(entry) != 1:
            continue
        element = entry[0]
        attribute = element.get("attribute")
        occurrences = element.get("occurrences", [])

        if attribute == "evt:central_element":
            if current_group:
                corrected_events.append(current_group)
                stats["groupes_valides"] += 1
            stats["total_central"] += 1
            if not occurrences:
                stats["central_vides"] += 1
            current_group = [element]
        elif attribute == "evt:associated_element":
            stats["total_associated"] += 1
            if not occurrences:
                stats["associated_vides"] += 1
            if current_group:
                current_group.append(element)
            else:
                stats["associated_orphelins"] += 1
        else:
            continue

    if current_group:
        corrected_events.append(current_group)
        stats["groupes_valides"] += 1

    return corrected_events, stats

def log_stats(filepath, stats, is_global=False):
    log_path = os.path.join(os.path.dirname(__file__), "fix_json_events.log")
    with open(log_path, "a", encoding="utf-8") as logf:
        if is_global:
            logf.write(f"Statistiques pour {filepath} :\n")
        else:
            logf.write(f"Statistiques pour {filepath} :\n")
        for k, v in stats.items():
            logf.write(f"  {k}: {v}\n")
        logf.write("\n")

def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Si data est une liste (cas d'un fichier contenant plusieurs documents)
    if isinstance(data, list):
        stats_global = Counter()
        for doc in data:
            if "events" in doc:
                corrected, stats = fix_events_structure(doc["events"])
                doc["events"] = corrected
                stats_global.update(stats)
        with open(filepath.replace(".json", "_corrige.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log_stats(filepath, stats_global, is_global=True)
    # Si data est un dictionnaire unique
    elif isinstance(data, dict):
        if "events" in data:
            corrected, stats = fix_events_structure(data["events"])
            data["events"] = corrected
            with open(filepath.replace(".json", "_corrige.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            log_stats(filepath, stats)
        else:
            log_stats(filepath, {"error": "Aucun champ 'events'"})
    else:
        log_stats(filepath, {"error": "Format JSON inattendu"})

def main():
    merged_dir = os.path.join(os.path.dirname(__file__), "..", "data", "annotations", "merged")
    for root, _, files in os.walk(merged_dir):
        for file in files:
            if file.endswith(".json"):
                filepath = os.path.join(root, file)
                process_file(filepath)

if __name__ == "__main__":
    main()
