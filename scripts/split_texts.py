#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ===================================================
# Description : Ce script parcourt les fichiers d'entrée 
#               dans un dossier, extrait chaque texte, et crée un 
#               fichier JSON séparé pour chaque texte.
# ===================================================

import os
import json

input_dir = "data/input_files"
output_dir = "data/split_texts"
os.makedirs(output_dir, exist_ok=True)

for input_file in os.listdir(input_dir):
    if input_file.endswith(".json"):
        input_path = os.path.join(input_dir, input_file)
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for i, obj in enumerate(data):
            for key, value in obj.items():
                if key.startswith("text"):
                    paragraph = value
                    if paragraph:
                        output_path = os.path.join(output_dir, f"{os.path.splitext(input_file)[0]}_text_{i:04}.json")
                        with open(output_path, 'w', encoding='utf-8') as out_f:
                            json.dump([{"text": paragraph}], out_f, ensure_ascii=False, indent=2)
