#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===================================================
# Description : Ce script segmente les textes en plusieurs segments
#               de taille maximale définie par MAX_CHARS.
#               Chaque segment est enregistré dans un fichier JSON séparé.
# ===================================================

import os
import json
import re

INPUT_DIR = "data/split_texts"
OUTPUT_DIR = "data/segmented_paragraphs"
MAX_CHARS = 500

os.makedirs(OUTPUT_DIR, exist_ok=True)

def segment_text(text, max_chars, tolerance=0.1):
    segments = []
    start = 0
    text_length = len(text)
    max_allowed = int(max_chars * (1 + tolerance))

    while start < text_length:
        hard_limit = min(start + max_allowed, text_length)
        slice_ = text[start:hard_limit]

        # Cherche les coupures dans les bornes max_chars jusqu’à max_allowed
        candidate_points = []

        # 1. Sauts de ligne
        for match in re.finditer(r'[\n\r]', slice_):
            if match.start() <= max_chars:
                candidate_points.append((match.start() + 1, 'newline'))

        # 2. Espace + point
        for match in re.finditer(r' \.', slice_):
            if match.start() + 1 <= max_allowed:
                candidate_points.append((match.start() + 1, 'space_dot'))

        # 3. Ponctuation forte
        for match in re.finditer(r'[.!?…»]', slice_):
            if match.start() + 1 <= max_allowed:
                candidate_points.append((match.start() + 1, 'punctuation'))

        # On trie pour garder le point de coupure le plus tardif et prioritaire
        if candidate_points:
            split_point = max(pt for pt, _ in candidate_points)
        else:
            # En dernier recours, couper brutalement à MAX_CHARS
            split_point = min(max_chars, text_length - start)

        segment = text[start:start + split_point]

        # Éviter les segments vides (mais on garde les retours à la ligne utiles)
        if segment.strip() or not segments:
            segments.append(segment)
        else:
            # Segment vide → attacher au précédent si possible
            if segments and len(segments[-1]) + len(segment) <= max_allowed:
                segments[-1] += segment
            else:
                segments.append(segment)

        start += split_point

    return segments

# Traitement des fichiers
for file in os.listdir(INPUT_DIR):
    if not file.endswith(".json"):
        continue

    file_path = os.path.join(INPUT_DIR, file)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = json.load(f)[0]
        text = content["text"]

    segments = segment_text(text, MAX_CHARS)

    for idx, segment in enumerate(segments):
        out_file = os.path.join(OUTPUT_DIR, f"{file[:-5]}_seg{idx:04}.json")
        with open(out_file, "w", encoding='utf-8') as out_f:
            json.dump([{"text": segment}], out_f, ensure_ascii=False, indent=2)
