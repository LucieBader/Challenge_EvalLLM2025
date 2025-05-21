#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===================================================
# Description : Segmente les textes d'un fichier d'annotations complet (avec entités, positions et identifiants)
#               en morceaux de taille max (500), en conservant les entités de chaque segment.
# ===================================================

import os
import json
import re

MODEL = os.environ.get("MODEL")
if not MODEL:
    print("Erreur : la variable d'environnement MODEL n'est pas définie.")
    exit(1)
MAX_CHARS = 500

INPUT_FILE = f"data/annotations/entities/final_annotations_{MODEL}/final_file.json"
OUTPUT_DIR = "data/annotations/events/segmented_texts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def split_text_and_entities(text, entities, max_chars):
    # Segmentation en phrases à l'aide de re.finditer pour conserver les indices d'origine
    sentence_spans = []
    start = 0
    for match in re.finditer(r'(?<=[.!?])\s+', text):
        end = match.end()
        sentence_spans.append((start, end))
        start = end
    if start < len(text):
        sentence_spans.append((start, len(text)))
    if not sentence_spans:
        sentence_spans = [(0, len(text))]

    # Regroupement des phrases en segments ne dépassant pas max_chars
    segments = []
    seg_start, seg_end = sentence_spans[0]
    for span in sentence_spans[1:]:
        if span[1] - seg_start <= max_chars:
            seg_end = span[1]
        else:
            segments.append((seg_start, seg_end))
            seg_start, seg_end = span
    segments.append((seg_start, seg_end))

    # Constitution des segments avec ajustement des entités
    result = []
    for seg_start, seg_end in segments:
        segment_text = text[seg_start:seg_end]
        segment_entities = []
        for ent in entities:
            ent_start = ent["start"][0]
            ent_end = ent["end"][0]
            if ent_start >= seg_start and ent_end <= seg_end:
                ent_copy = ent.copy()
                ent_copy["start"] = [ent_start - seg_start]
                ent_copy["end"] = [ent_end - seg_start]
                segment_entities.append(ent_copy)
        result.append({"text": segment_text, "entities": segment_entities})
    return result

with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

error_log_path = os.path.join(OUTPUT_DIR, "segmentation_errors.log")
with open(error_log_path, "w", encoding="utf-8") as error_log:
    for i, obj in enumerate(data):
        text = obj["text"]
        entities = obj.get("entities", [])
        segments = split_text_and_entities(text, entities, MAX_CHARS)
        reconstructed = "".join(seg["text"] for seg in segments)
        if reconstructed != text:
            error_log.write(f"Erreur d'intégrité pour l'item {i}\n")
            error_log.write(f"Texte original :\n{text!r}\n")
            error_log.write(f"Texte reconstruit :\n{reconstructed!r}\n")
            error_log.write(f"Dernier segment :\n{segments[-1]['text']!r}\n")
            error_log.write("="*40 + "\n")
            print(f"[ERREUR] Le texte segmenté diffère du texte original pour l'item {i}. Voir {error_log_path}")
            continue  # Passe à l'item suivant sans écrire les segments
        for j, seg in enumerate(segments):
            output_path = os.path.join(
                OUTPUT_DIR,
                f"final_file_text_{i:04}_seg{j}.json"
            )
            with open(output_path, 'w', encoding='utf-8') as out_f:
                json.dump([seg], out_f, ensure_ascii=False, indent=2)
