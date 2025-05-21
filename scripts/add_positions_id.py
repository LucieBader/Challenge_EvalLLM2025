#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===================================================
# Description : Ce script ajoute des identifiants uniques et des positions (offsets)
#               à chaque entité annotée, même si elle est précédée ou coupée par des caractères invisibles.
# Entrées : 
#   - Un fichier JSON contenant les textes et leurs entités annotées.
# Sorties :
#   - Un fichier JSON contenant les textes et leurs entités annotées 
#     avec des identifiants uniques et des positions.
# ===================================================

import os
import json
import re
import uuid

MODEL = os.environ.get("MODEL")
if not MODEL:
    print("Erreur : la variable d'environnement MODEL n'est pas définie.")
    exit(1)

INPUT_FILE = f"data/annotations/entities/final_annotations_{MODEL}/final_annotations.json"
OUTPUT_FILE = f"data/annotations/entities/final_annotations_{MODEL}/final_file.json"

if not os.path.exists(INPUT_FILE):
    print(f"Erreur : le fichier d'entrée '{INPUT_FILE}' n'existe pas.")
    exit(1)

# Fonction pour générer un motif regex souple
def make_flexible_pattern(ent_text):
    # Découpe par espaces et insère \s+ entre les mots pour capturer les \n, \t, etc.
    tokens = re.split(r'\s+', ent_text.strip())
    pattern = r'\s*'.join(re.escape(token) for token in tokens)
    return pattern

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

total_input_entities = sum(len(item["entities"]) for item in data)

output = []
total_entities = 0

for item in data:
    text = item["text"]
    new_entities = []
    used_spans = {}  # (start, end) -> {"id": ..., "labels": set()}

    for ent in item["entities"]:
        ent_text = ent["text"]
        label = ent["label"]
        pattern = make_flexible_pattern(ent_text)
        matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
        found = False
        already_used = False

        for match in matches:
            start, end = match.start(), match.end()
            span = (start, end)

            if span not in used_spans:
                ent_id = str(uuid.uuid4())
                used_spans[span] = {"id": ent_id, "labels": set([label])}
                new_entities.append({
                    "text": text[start:end],
                    "start": [start],
                    "end": [end],
                    "id": ent_id,
                    "label": label
                })
                found = True
                break
            else:
                ent_id = used_spans[span]["id"]
                if label not in used_spans[span]["labels"]:
                    used_spans[span]["labels"].add(label)
                    new_entities.append({
                        "text": text[start:end],
                        "start": [start],
                        "end": [end],
                        "id": ent_id,
                        "label": label
                    })
                    found = True
                    break
                else:
                    already_used = True

        if not found:
            preview_len = 30
            first_occ = re.search(pattern, text, flags=re.IGNORECASE)
            if first_occ:
                start_ctx = max(0, first_occ.start() - preview_len)
                end_ctx = min(len(text), first_occ.end() + preview_len)
                preview = text[start_ctx:end_ctx].replace('\n', '\\n').replace('\r', '\\r')
            else:
                #print(f"Entité '{ent_text}' (label={label}) non trouvée dans le texte (tolérance espaces/sauts activée).")
                break

    total_entities += len(new_entities)
    new_entities.sort(key=lambda e: e["start"][0] if e["start"] else float('inf'))
    output.append({
        "text": text,
        "entities": new_entities
    })

#print(f"Nombre d'entités originales dans le fichier : {total_input_entities}")
#print(f"Nombre d'entités traitées (positions/id ajoutées) : {total_entities}")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
