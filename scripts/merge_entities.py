#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===================================================
# Description : Après annotation, ce script fusionne les segments 
#               pour reconstituer le paragraphe complet avec toutes ses entités.
#               En cas de fichier JSON mal formé, il conserve uniquement
#               le premier bloc valide et réécrit le fichier.
#
# Entrées :
#   - Un répertoire contenant des fichiers JSON annotés (segments annotés).
# Sorties :
#   - Un fichier JSON fusionné contenant le texte complet et toutes les entités.
# ===================================================

import os
import json
from collections import defaultdict

MODEL = os.environ.get("MODEL")
ANNOTATED_DIR = f"data/annotations/entities/annotated_paragraphs_{MODEL}"
FINAL_DIR = f"data/annotations/entities/final_annotations_{MODEL}"
MERGED_FILE = f"{FINAL_DIR}/final_annotations.json"

os.makedirs(FINAL_DIR, exist_ok=True)

merged_data = defaultdict(lambda: {"text": "", "entities": []})

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
    Extrait le premier objet JSON valide contenant "text" et "entities"
    """
    raw_objects = extract_json_objects(raw_text)

    for obj_text in raw_objects:
        try:
            obj = json.loads(obj_text)
            if isinstance(obj, dict) and "text" in obj and "entities" in obj:
                return [obj] 
        except json.JSONDecodeError:
            continue
    return None

files = [f for f in os.listdir(ANNOTATED_DIR) if f.endswith(".json")]
files = sorted(files, key=lambda f: (f.replace("annotated_paragraph_", "").split("_seg")[0],
                                       int(f.split("_seg")[-1].replace(".json", "")) if "_seg" in f else 0))
for file in files:
    parts = file.replace("annotated_paragraph_", "").replace(".json", "").split("_seg")
    para_id = parts[0]
    segment_index = int(parts[1]) if len(parts) > 1 else 0

    filepath = os.path.join(ANNOTATED_DIR, file)

    data = None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"JSON mal formé détecté. Tentative de réparation...")
        with open(filepath, 'r', encoding='utf-8') as f:
            raw = f.read()
        data = extract_first_valid_object(raw)
        if data:
            print(f"Réparation réussie pour : {filepath}. Fichier réécrit avec le premier bloc valide.")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            print(f"Échec de la réparation : {filepath}")
            continue

    # Vérification de la structure avant fusion
    if (
        isinstance(data, list) and len(data) > 0 and
        isinstance(data[0], dict) and "text" in data[0] and "entities" in data[0]
    ):
        seg_text = data[0]["text"]
        merged_data[para_id]["text"] += seg_text
        merged_data[para_id]["entities"].extend(data[0]["entities"])
    else:
        print(f"Structure invalide ignorée dans : {filepath}")

# Génération du fichier final fusionné
final_output = []
for key in sorted(merged_data.keys()):
    obj = merged_data[key]
    last_seg_text = obj["text"]
    final_output.append(obj)

with open(MERGED_FILE, "w", encoding='utf-8') as out_f:
    json.dump(final_output, out_f, ensure_ascii=False, indent=2)

