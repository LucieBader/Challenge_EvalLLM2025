#!/bin/bash
# ===================================================
# Description :
# ---------------------------------------------------
# Ce script orchestre l'ensemble du pipeline d'annotation d'entités nommées :
#  1. Découpe les fichiers d'entrée en paragraphes individuels.
#  2. Segmente chaque paragraphe en sous-parties de moins de 500 caractères.
#  3. Annote chaque segment via un LLM (Ollama) avec des prompts spécifiques.
#  4. Fusionne les annotations pour reconstituer les paragraphes complets.
#  5. Ajoute des positions et des identifiants uniques aux entités.
#  6. Segmente les paragraphes annotés en entités.
#  7. Annote les événements en utilisant le LLM.
#  8. Fusionne les annotations d'événements.
#  9. Corrige la structure des événements dans le fichier final annoté.
#
# Usage :
#   bash pipeline.sh
# ===================================================
set -e

MODEL="llama3.3"  # Nom du modèle LLM à utiliser

START_TIME=$(date +%s)

# Création des dossiers nécessaires
mkdir -p data/split_texts
mkdir -p data/segmented_paragraphs
mkdir -p "data/annotations/entities/annotated_paragraphs_${MODEL}"
mkdir -p "data/annotations/entities/final_annotations_${MODEL}"
mkdir -p data/annotations/events
mkdir -p "data/annotations/events/annotated_paragraphs_${MODEL}"
mkdir -p data/annotations/merged

# Étape 1 : Découpage des fichiers d'entrée en paragraphes individuels
echo "Étape 1/8 : Extraction des paragraphes..."
python3 scripts/split_texts.py

# Étape 2 : Segmentation des paragraphes en sous-parties de <500 caractères
echo "Étape 2/8 : Segmentation des paragraphes..."
python3 scripts/segment_paragraphs.py

# Étape 3 : Annotation automatique des entités
echo "Étape 3/8 : Annotation des entités..."
MODEL="$MODEL" bash scripts/annotate_entities.sh

# Étape 4 : Fusion des annotations segmentées pour chaque paragraphe
echo "Étape 4/8 : Fusion des annotations d'entités..."
MODEL="$MODEL" python scripts/merge_entities.py

# Étape 5 : Ajout des positions et des identifiants uniques
echo "Étape 5/8 : Ajout des positions et identifiants uniques..."
MODEL="$MODEL" python scripts/add_positions_id.py

# Étape 6 : Segmentation des paragraphes annotés en entités (pour événements)
echo "Étape 6/8 : Segmentation des paragraphes annotés pour annotation des événements..."
MODEL="$MODEL" python scripts/split_annotated_texts.py

# Étape 7 : Annotation automatique des événéments
echo "Étape 7/8 : Annotation des événements..."
MODEL="$MODEL" bash scripts/annotate_events.sh

# Étape 8 : Fusion des annotations d'événements
echo "Étape 8/8 : Fusion des annotations d'événements..."
MODEL="$MODEL" python scripts/merge_entities_events.py

# Étape 9 : Correction de la structure des événements dans le fichier final annoté
echo "Correction de la structure des événements dans le fichier final annoté..."
python scripts/fix_events_structure.py

echo "Annotation effectuée avec succès. Résultats dans : data/annotations/merged/final_annotations_${MODEL}/final_annotated_file_corrige.json"

END_TIME=$(date +%s)
ELAPSED_TIME=$((END_TIME - START_TIME))
END_TIME=$(date +%s)
ELAPSED_TIME=$((END_TIME - START_TIME))
ELAPSED_HOURS=$((ELAPSED_TIME / 3600))
ELAPSED_MINUTES=$(((ELAPSED_TIME % 3600) / 60))
ELAPSED_SECONDS=$((ELAPSED_TIME % 60))

echo "Durée totale du pipeline : ${ELAPSED_HOURS}h ${ELAPSED_MINUTES}m ${ELAPSED_SECONDS}s."
echo "Durée totale du pipeline : ${ELAPSED_HOURS}h ${ELAPSED_MINUTES}m ${ELAPSED_SECONDS}s." >> pipeline_runtime.log
