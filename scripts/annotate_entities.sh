#!/bin/bash
# ===================================================
# Description :
# ---------------------------------------------------
# Ce script automatise l'annotation d'entités nommées sur des segments de texte à l'aide d'un modèle de langage (LLM) via une API (Ollama).
# Pour chaque segment JSON dans data/segmented_paragraphs, il applique successivement plusieurs prompts spécialisés (un par catégorie d'entités).
# Il combine un prompt général et un prompt spécifique, envoie la requête au LLM, extrait les entités détectées, et agrège les résultats.
#
# Entrées :
#   - data/segmented_paragraphs/*_paragraph_*_seg*.json : segments à annoter
#   - prompts/general_prompt_entities.txt : consignes générales d'annotation
#   - prompts/specific_prompts/*.txt : consignes spécifiques par type d'entité
#
# Sorties :
#   - data/annotations/entities/annotated_paragraphs_${MODEL}/annotated_*_paragraph_*_seg*.json : annotations par segment
# ===================================================

MODEL="${MODEL}"
API_URL="http://localhost:11434/api/generate"
general_prompt_entities_FILE="prompts/general_prompt_entities.txt"
SPECIFIC_PROMPT_DIR="prompts/specific_prompts"
INPUT_DIR="data/segmented_paragraphs"
OUTPUT_DIR="data/annotations/entities/annotated_paragraphs_${MODEL}"
mkdir -p "$OUTPUT_DIR"

# Vérification des dépendances jq et curl
# jq : pour manipuler les données JSON
# curl : pour effectuer des requêtes HTTP
for cmd in jq curl; do
  command -v "$cmd" >/dev/null || {
    echo "Erreur : '$cmd' non trouvé. Veuillez l’installer." >&2
    exit 1
  }
done

# Vérifie la présence du fichier de prompt général
if [[ ! -f "$general_prompt_entities_FILE" ]]; then
  echo "ERREUR : Fichier de prompt général introuvable : $general_prompt_entities_FILE"
  exit 1
fi

# Vérifie la présence des fichiers de prompts spécifiques
SPECIFIC_PROMPTS=(
  "auteurs_sources.txt"
  "dates.txt"
  "lieux_organisations.txt"
  "maladies_pathogenes.txt"
  "nrbce_toxines.txt"
)

for prompt in "${SPECIFIC_PROMPTS[@]}"; do
  if [[ ! -f "$SPECIFIC_PROMPT_DIR/$prompt" ]]; then
    echo "ERREUR : Prompt spécifique manquant : $SPECIFIC_PROMPT_DIR/$prompt"
    exit 1
  fi
done

general_prompt_entities=$(cat "$general_prompt_entities_FILE")

# ===================================================
# Traitement des fichiers segmentés
# ===================================================

# Récupère et trie les fichiers JSON segmentés dans le répertoire d'entrée
FILES=($(ls "$INPUT_DIR"/*_text_*_seg*.json | sort))

# Calcul du nombre total de paragraphes distincts
PARAGRAPH_IDS=($(for f in "${FILES[@]}"; do basename "$f" .json | grep -o 'text_[0-9]\+' ; done | sort | uniq))
TOTAL_PARAGRAPHS=${#PARAGRAPH_IDS[@]}
PARAGRAPHS_DONE=0

CURRENT_PARAGRAPH_ID=""

# Boucle sur chaque fichier JSON segmenté
for json_file in "${FILES[@]}"; do
  SEGMENT_NAME=$(basename "$json_file" .json)
  # Extrait la partie avant _segX pour obtenir le nom du paragraphe d'origine
  PARAGRAPH_ID=$(echo "$SEGMENT_NAME" | sed -E 's/_seg[0-9]+$//')
  OUTPUT_FILE="$OUTPUT_DIR/annotated_${SEGMENT_NAME}.json"

  # Initialise le fichier de sortie avec un tableau JSON vide
  echo "[" > "$OUTPUT_FILE"
  FIRST_ENTRY=true  

  # Vérifie si on change de paragraphe
  if [[ "$CURRENT_PARAGRAPH_ID" != "$PARAGRAPH_ID" ]]; then
    if [[ -n "$CURRENT_PARAGRAPH_ID" ]]; then
      PARAGRAPHS_DONE=$((PARAGRAPHS_DONE + 1))
      PARAGRAPHS_LEFT=$((TOTAL_PARAGRAPHS - PARAGRAPHS_DONE))
      echo "→ ${CURRENT_PARAGRAPH_ID#paragraph_} terminé. $PARAGRAPHS_LEFT restant(s)."
    fi
    CURRENT_PARAGRAPH_ID="$PARAGRAPH_ID"
  fi

  # Charge le contenu JSON du fichier segmenté
  SEGMENT=$(jq -c '.' "$json_file")

  PARAGRAPH=$(jq '.[0].text // ""' "$json_file")

  # Vérifie si le texte est vide
  if [[ -z "$PARAGRAPH" ]]; then
    echo "ERREUR : Aucun texte trouvé dans $json_file"
    continue
  fi

  ALL_ENTITIES="[]"

  # Boucle sur chaque fichier de prompt spécifique
  for prompt_filename in "${SPECIFIC_PROMPTS[@]}"; do
    PROMPT_PATH="$SPECIFIC_PROMPT_DIR/$prompt_filename"
    SPECIFIC_PROMPT=$(cat "$PROMPT_PATH")

    # Détermine la catégorie d'entité à partir du nom du fichier
    ENTITY_CATEGORY=$(basename "$prompt_filename" .txt | sed 's/_/, /g')

    # Prépare le prompt complet en combinant le prompt général, le prompt spécifique et le texte
    FULL_PROMPT="$general_prompt_entities

Instruction spécifique :
$SPECIFIC_PROMPT

Texte à annoter :
$PARAGRAPH

Ne modifie pas le texte, n'ajoute pas de commentaire. Si le texte ne contient aucune entité qui correspond aux définitions, passe au texte suivant.
Retourne uniquement un tableau JSON listant les entités détectées, sous ce format :

[
  {
    \"text\": \"forme dans le texte\",
    \"label\": \"type d'entité\"
  },
  ...
]"

# ===================================================
# Envoi de la requête à l'API et traitement de la réponse du LLM
# ===================================================

    # Prépare le corps de la requête pour l'API
    REQUEST_BODY=$(jq -n \
      --arg model "$MODEL" \
      --arg prompt "$FULL_PROMPT" \
      --argjson num_ctx 8192 \
      '{
        model: $model,
        prompt: $prompt,
        options: {
          num_ctx: $num_ctx
        },
        stream: false
      }'
    )

    # Envoie une requête à l'API
    RESPONSE=$(curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d "$REQUEST_BODY")
    RAW_JSON=$(echo "$RESPONSE" | jq -r '.response // empty')
    #echo "DEBUG RAW_JSON: $RAW_JSON" >&2

    # Script Python pour extraire les entités de la sortie du LLM
    if [[ -z "$RAW_JSON" ]]; then
      echo "ERREUR : Aucune réponse du LLM pour $PARAGRAPH_ID."
      ENTITIES="[]"
    else
      ENTITIES=$(echo "$RAW_JSON" | python3 scripts/parse_llm_output.py --mode entities)
    fi

    # Ajoute les nouvelles entités détectées à la liste globale
    ALL_ENTITIES=$(jq -s 'add' <(echo "$ALL_ENTITIES") <(echo "$ENTITIES"))
  done

  # Crée un objet JSON final contenant le texte et les entités détectées
  FINAL_OBJ=$(jq -n \
    --argjson text "$PARAGRAPH" \
    --argjson entities "$ALL_ENTITIES" \
    '{text: $text, entities: $entities}')

  # Ajoute l'objet JSON au fichier de sortie
  if [ "$FIRST_ENTRY" = true ]; then
    printf "%s\n" "$FINAL_OBJ" >> "$OUTPUT_FILE"
    FIRST_ENTRY=false
  else
    printf ",\n%s\n" "$FINAL_OBJ" >> "$OUTPUT_FILE"
  fi

  # Termine le tableau JSON dans le fichier de sortie
  echo "]" >> "$OUTPUT_FILE"
done

if [[ -n "$CURRENT_PARAGRAPH_ID" ]]; then
  PARAGRAPHS_DONE=$((PARAGRAPHS_DONE + 1))
  PARAGRAPHS_LEFT=$((TOTAL_PARAGRAPHS - PARAGRAPHS_DONE))
  echo "→ Texte ${CURRENT_PARAGRAPH_ID#paragraph_} terminé. $PARAGRAPHS_LEFT restant(s)."
fi