#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===================================================
# Description : Fusionne les segments annotés d'un fichier JSON en un seul objet JSON
#               en conservant les entités et événements de chaque segment.
# Entrées :
#   - Un répertoire contenant des fichiers JSON annotés (annotated_paragraphs).
# Sorties :
#   - Un fichier JSON fusionné contenant les textes, entités et événements.
# ===================================================

import os
import json
from collections import defaultdict

MODEL = os.environ.get("MODEL")

ANNOTATED_DIR = f"data/annotations/events/annotated_paragraphs_{MODEL}"
FINAL_DIR = f"data/annotations/merged/final_annotations_{MODEL}"
MERGED_FILE = f"{FINAL_DIR}/final_annotated_file.json"

os.makedirs(FINAL_DIR, exist_ok=True)

merged_data = defaultdict(lambda: {"text": "", "entities": [], "events": []})

def extract_json_objects(text):
    """
    Extrait tous les objets JSON imbriqués dans un texte,
    même si le JSON global est mal formé.
    """
    objects = []
    stack = []
    start_idx = None

    for i, char in enumerate(text):
        if char == '{':
            if not stack:
                start_idx = i
            stack.append(char)
        elif char == '}':
            if stack:
                stack.pop()
                if not stack and start_idx is not None:
                    obj_str = text[start_idx:i+1]
                    objects.append(obj_str)
                    start_idx = None
    return objects

def extract_first_valid_object(raw_text):
    """
    Extrait le premier objet JSON valide contenant "text", "entities" et "events"
    """
    raw_objects = extract_json_objects(raw_text)

    for obj_text in raw_objects:
        try:
            obj = json.loads(obj_text)
            if (
                isinstance(obj, dict)
                and "text" in obj
                and "entities" in obj
                and "events" in obj
            ):
                return [obj]
        except json.JSONDecodeError:
            continue
    return None

# Fusionne les segments par identifiant de paragraphe (text_{i:04})
files = [f for f in os.listdir(ANNOTATED_DIR) if f.endswith(".json") and f.startswith("annotated")]
files = sorted(files, key=lambda f: (f.rsplit("_seg", 1)[0], int(f.rsplit("_seg", 1)[1].replace(".json", ""))))
for file in files:
    # Extraction de l'identifiant du paragraphe et de l'index du segment
    base = file.rsplit("_seg", 1)
    para_id = base[0].replace(".json", "")
    segment_index = int(base[1].replace(".json", "")) if len(base) > 1 else 0
    parts = [para_id, segment_index]
    para_id = parts[0]  # ex: text_0000
    segment_index = int(parts[1]) if len(parts) > 1 else 0

    filepath = os.path.join(ANNOTATED_DIR, file)

    data = None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"Échec de la lecture JSON : {filepath}")
        continue

    # Vérification de la structure avant fusion
    if (
        isinstance(data, list) and len(data) > 0 and
        isinstance(data[0], dict) and
        "text" in data[0] and "entities" in data[0] and "events" in data[0]
    ):
        seg_text = data[0]["text"]
        merged_data[para_id]["text"] += seg_text
        merged_data[para_id]["entities"].extend(data[0]["entities"])
        merged_data[para_id]["events"].extend(data[0]["events"])
    else:
        print(f"Structure invalide ignorée dans : {filepath}")

# Génération du fichier final fusionné
final_output = []
for key in sorted(merged_data.keys()):
    obj = merged_data[key]
    final_output.append(obj)

with open(MERGED_FILE, "w", encoding='utf-8') as out_f:
    json.dump(final_output, out_f, ensure_ascii=False, indent=2)