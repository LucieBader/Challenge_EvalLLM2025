#!/bin/bash
# ===================================================
# Description :
# ---------------------------------------------------
# Ce script automatise l'annotation d'événements sur des segments de texte à l'aide d'un modèle de langage (LLM) via une API (Ollama).
# Pour chaque segment JSON dans data/annotations/events/segmented_texts, il applique un prompt d'annotation d'événements.
#
# Entrées :
#   - data/annotations/events/segmented_texts : textes à annoter
#   - prompts/prompt_events.txt : consignes d'annotation d'événements
#
# Sorties :
#   - data/annotations/events/annotated_paragraphs_${MODEL}/annotated_*_text_*.json : annotations par texte
# ===================================================

MODEL="${MODEL}"
API_URL="http://localhost:11434/api/generate"
PROMPT_EVENTS_FILE="prompts/prompt_events.txt"
INPUT_DIR="data/annotations/events/segmented_texts"
OUTPUT_DIR="data/annotations/events/annotated_paragraphs_${MODEL}"
mkdir -p "$OUTPUT_DIR"

# Vérification des dépendances jq et curl
for cmd in jq curl; do
  command -v "$cmd" >/dev/null || {
    echo "Erreur : '$cmd' non trouvé. Veuillez l’installer." >&2
    exit 1
  }
done

# Vérifie la présence du fichier de prompt général
if [[ ! -f "$PROMPT_EVENTS_FILE" ]]; then
  echo "ERREUR : Fichier de prompt général introuvable : $PROMPT_EVENTS_FILE"
  exit 1
fi

prompt_events=$(cat "$PROMPT_EVENTS_FILE")

# Fonction pour extraire chaque objet (texte + entités) d'un fichier JSON
extract_objects_from_json_file() {
  local json_file="$1"
  jq -c '.[]' "$json_file"
}

# ===================================================
# Traitement des fichiers textes
# ===================================================

FILES=($(ls "$INPUT_DIR"/final_file_text_*_seg*.json | sort))

PARAGRAPH_IDS=($(for f in "${FILES[@]}"; do basename "$f" .json | grep -o 'text_[0-9]\+' ; done | sort | uniq))
TOTAL_PARAGRAPHS=${#PARAGRAPH_IDS[@]}
PARAGRAPHS_DONE=0

CURRENT_PARAGRAPH_ID=""

for json_file in "${FILES[@]}"; do
  TEXT_NAME=$(basename "$json_file" .json)
  PARAGRAPH_ID=$(echo "$TEXT_NAME" | grep -o 'text_[0-9]\+')
  OUTPUT_FILE="$OUTPUT_DIR/annotated_${TEXT_NAME}.json"

  echo "[" > "$OUTPUT_FILE"
  FIRST_ENTRY=true  

  if [[ "$CURRENT_PARAGRAPH_ID" != "$PARAGRAPH_ID" ]]; then
    if [[ -n "$CURRENT_PARAGRAPH_ID" ]]; then
      PARAGRAPHS_DONE=$((PARAGRAPHS_DONE + 1))
      PARAGRAPHS_LEFT=$((TOTAL_PARAGRAPHS - PARAGRAPHS_DONE))
      echo "→ Texte n°${CURRENT_PARAGRAPH_ID#text_} terminé. $PARAGRAPHS_LEFT restant(s)."
    fi
    CURRENT_PARAGRAPH_ID="$PARAGRAPH_ID"
  fi

  extract_objects_from_json_file "$json_file" | while read -r OBJ; do

    FULL_PROMPT="$prompt_events

Texte à annoter (format JSON) :
$OBJ

Ne modifie pas le texte, n'ajoute pas de commentaire. Si le texte ne contient aucun événement qui correspond aux définitions, passe au texte suivant. Ne modifie surtout pas l'annotation des entités (qui est déjà faite dans le fichier).
Retourne uniquement un tableau JSON sous ce format :
{
    \"events\": [
        [
            {
                \"attribute\": \"evt:central_element\",
                \"occurrences\": [
                    \"<identifiant_entité_1>\",
                    \"<identifiant_entité_2>\"
                ]
            },
            {
                \"attribute\": \"evt:associated_element\",
                \"occurrences\": [
                    \"<identifiant_entité_3>\"
                ]
            }
        ],
        ...
    ]
}
"
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

    RESPONSE=$(curl -s -X POST "$API_URL" -H "Content-Type: application/json" -d "$REQUEST_BODY")
    RAW_JSON=$(echo "$RESPONSE" | jq -r '.response // empty')

    if [[ -z "$RAW_JSON" ]]; then
      echo "ERREUR : Aucune réponse du LLM pour $TEXT_NAME"
      EVENTS="[]"
    else
      EVENTS=$(echo "$RAW_JSON" | python3 scripts/parse_llm_output.py --mode events)
    fi

    FINAL_OBJ=$(echo "$OBJ" | jq --argjson events "$EVENTS" '. + {events: $events}')

    if [ "$FIRST_ENTRY" = true ]; then
      echo "$FINAL_OBJ" >> "$OUTPUT_FILE"
      FIRST_ENTRY=false
    else
      echo "," >> "$OUTPUT_FILE"
      echo "$FINAL_OBJ" >> "$OUTPUT_FILE"
    fi
  done

  echo "]" >> "$OUTPUT_FILE"
done

if [[ -n "$CURRENT_PARAGRAPH_ID" ]]; then
  PARAGRAPHS_DONE=$((PARAGRAPHS_DONE + 1))
  PARAGRAPHS_LEFT=$((TOTAL_PARAGRAPHS - PARAGRAPHS_DONE))
  echo "→ Texte n°${CURRENT_PARAGRAPH_ID#text_} terminé. $PARAGRAPHS_LEFT restant(s)."
fi
