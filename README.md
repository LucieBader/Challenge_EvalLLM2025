# Reconnaissance d'entités nommées et annotation d'événements à l'aide de LLM <!-- omit from toc -->

Ce projet propose un pipeline complet pour l'annotation automatique d'entités et d'événements dans des documents journalistiques en français pour le domaine de la santé. Le pipeline s'appuie sur des modèles de langage (LLM) et des prompts spécifiques pour détecter et annoter les informations d'intérêt sanitaire.  
Cette approche est réalisée dans le cadre du challenge d'extraction d'informations [EvalLLM2025](https://evalllm2025.sciencesconf.org/resource/page/id/5).

## Table des matières <!-- omit from toc -->

- [Prérequis](#prérequis)
  - [Installation des dépendances système](#installation-des-dépendances-système)
  - [Installation d'Ollama et des modèles](#installation-dollama-et-des-modèles)
- [Description du pipeline](#description-du-pipeline)
- [Organisation du projet](#organisation-du-projet)
- [Détail des scripts](#détail-des-scripts)
  - [Bibliothèques utilisées](#bibliothèques-utilisées)
- [Utilisation](#utilisation)
- [Résultats](#résultats)
- [Personnalisation](#personnalisation)

## Prérequis

- **Python 3.10+**
- **bash** 
- **jq** 
- **curl** 
- **Serveur Ollama et modèle installé** (cf. [Installation d'Ollama et des modèles](#installation-dollama-et-des-modèles))

### Installation des dépendances système

Sous Ubuntu/Debian :
```
sudo apt-get install jq curl
```

### Installation d'Ollama et des modèles

Sous Linux : 
```
curl -fsSL https://ollama.com/install.sh | sh
```

Choisissez ensuite un modèle depuis [la liste des modèles](https://ollama.com/search) et installez-le.  
Par exemple, pour installer Llama3.3 :
```
ollama pull llama3.3
```

Lorsqu'un modèle a plusieurs tailles disponibles, ne pas oublier de le préciser dans la commande. Par exemple, pour Gemma3 :
```python
ollama pull gemma3:1b
ollama pull gemma3 # Version de base (4b)
ollama pull gemma3:12b
ollama pull gemma3:27b
```

Pour vérifier la liste des modèles installés localement : 
```
ollama list
```

## Description du pipeline

Ce pipeline prend en entrée un fichier JSON placé dans le répertoire `data/input_files/`, contenant au minimum une clé `"text"`.

1. **Prétraitement et segmentation**

Les textes sont d’abord extraits puis segmentés en portions de moins de 500 caractères. Cette limitation permet d’optimiser les performances du modèle : bien que celui-ci puisse théoriquement traiter des textes plus longs, sa précision diminue au-delà d’un certain seuil de complexité.

2. **Annotation des entités**

Chaque segment est ensuite soumis à plusieurs phases d’annotation d’entités. Pour améliorer la qualité de l’annotation, les labels d’entités ont été regroupés en catégories, chacune associée à un prompt spécifique. Par exemple, les labels "RADIOISOTOPE", "TOXIC_C_AGENT", "EXPLOSIVE" et "BIO_TOXIN" sont traités via le prompt `prompts/specific_prompts/nrbce_toxines.txt`.  
Cette catégorisation permet d’orienter plus efficacement le modèle, en l’aidant à se concentrer sur des entités proches ou potentiellement ambiguës, qui risqueraient d’être mal interprétées dans un prompt global unique.  
Les résultats de l'annotation en entités sont sauvegardés dans le dossier `data/annotations/entities/annotated_paragraphs_<MODEL>/`

3. **Post-traitement des entités**

Une fois l’annotation des entités terminée, les segments sont fusionnés pour reconstituer les textes d’origine. Les éventuelles erreurs de format JSON sont corrigées, et chaque entité est enrichie avec un identifiant unique ainsi que ses positions (offsets) dans le texte.

4. **Annotation des événements**

Les textes annotés sont à nouveau segmentés pour une seconde phase d’annotation, cette fois dédiée aux événements. Contrairement à l’étape précédente, un unique prompt est utilisé pour l’ensemble des catégories d’événements.  
Les segments annotés sont fusionnés pour chaque document, et les résultats sont enregistrés dans le répertoire `data/annotations/events/annotated_paragraphs_<MODEL>/`.   

5. **Fusion finale et post-traitement des événements**

Les annotations des entités et des événements sont combinées dans un fichier unique. Enfin, la structure JSON des événements est corrigée pour respecter le format attendu de sortie.  
Le dossier final `data/annotations/merged/final_annotations_<MODEL>/` contient le fichier final annoté ainsi que le fichier corrigé.

## Organisation du projet

```
NER_LLM/
├── data/
│   ├── input_files/                # Fichiers d'entrée (JSON)
│   ├── split_texts/                # Paragraphes extraits individuellement
│   ├── segmented_paragraphs/       # Paragraphes segmentés (sous-parties de <500 caractères)
│   └── annotations/
│       ├── entities/
│       │   ├── annotated_paragraphs_<MODEL>/   # Annotations des entités par segment
│       │   └── final_annotations_<MODEL>/      # Annotations fusionnées par paragraphe
│       ├── events/
│       │   ├── annotated_paragraphs_<MODEL>/   # Annotations des événements par segment
│       │   └── segmented_texts/                # Paragraphes annotés en entités segmentés
│       └── merged/
│           └── final_annotations_<MODEL>/      # Annotations finales (entités + événements)   
├── prompts/
│   ├── general_prompt_entities.txt # Consignes générales d'annotation des entités
│   ├── prompt_events.txt           # Consignes pour l'annotation d'événements
│   └── specific_prompts/           # Prompts spécialisés par catégorie d'entité
├── scripts/
│   ├── add_positions_id.py             # Ajout des positions et des identifiants uniques
│   ├── annotate_entities.sh            # Annotation automatique des entités via LLM
│   ├── annotate_events.sh              # Annotation automatique des événements via LLM
│   ├── fix_json_events.py              # Correction de la structure des événements dans les fichiers JSON
│   ├── merge_entities.py               # Fusion des annotations d'entités pour chaque segment
│   ├── merge_entities_events.py        # Fusion des annotations d'événements pour chaque segment
│   ├── parse_llm_output.py             # Nettoyage et extraction de la sortie du LLM
│   ├── segment_paragraphs.py           # Segmentation en sous-paragraphes (<500 caractères)
│   ├── split_annotated_texts.py        # Segmentation des textes annotés pour l'annotation d'événements
│   └── split_texts.py                  # Extraction des paragraphes dans les fichiers d'entrée
├── pipeline.sh                     # Orchestration complète du pipeline
└── README.md
```

## Détail des scripts

- `scripts/add_positions_id.py` : Parcourt les annotations pour calculer les offsets (début/fin) de chaque entité et leur attribuer un identifiant unique.
- `scripts/annotate_entities.sh` : Transmet chaque segment au LLM avec un prompt général et chacun des prompts spécifiques (5 prompts spécifiques donc 5 requêtes pour traiter un segment) pour l'annotation des entités, en sauvegardant chaque résultat en JSON distinct.
- `scripts/annotate_events.sh` : Envoie les segments retraités au LLM avec un prompt spécialisé pour détecter et annoter les événements.
- `scripts/fix_json_events.py` : Corrige la structure des événements dans les fichiers JSON finaux pour garantir la conformité au format attendu.
- `scripts/merge_entities.py` : Fusionne les segments annotés pour reconstituer le texte complet et regrouper l'ensemble des entités; il corrige également les erreurs éventuelles de format JSON.
- `scripts/merge_entities_events.py` : Regroupe les annotations d'événements issues des différents segments afin d'obtenir un fichier final cohérent, en intégrant des corrections pour les éventuels problèmes de format. Fusionne textes, entités et événements pour chaque paragraphe.
- `scripts/parse_llm_output.py` : Nettoie et extrait la sortie brute du LLM pour obtenir un tableau JSON d'entités ou d'événements, même en cas de formatage imparfait ou de texte parasite.
- `scripts/segment_paragraphs.py` : Segmente chaque texte en sous-parties d'au maximum 500 caractères en tenant compte des délimiteurs (nouvelles lignes, ponctuation forte). Ceci permet d'envoyer des segments plus courts à traiter pour le LLM et ainsi augmenter théoriquement les performances.
- `scripts/split_annotated_texts.py` : Redécoupe les textes annotés et enrichis pour préparer l'annotation des événements, en conservant la cohérence des entités dans chaque segment.
- `scripts/split_texts.py` : Extrait les paragraphes des fichiers d'entrée JSON en lisant la clé "text". Ce découpage prépare les textes pour une segmentation plus fine.

### Bibliothèques utilisées

- **os** : gestion des chemins, fichiers et dossiers
- **json** : lecture et écriture du format JSON
- **collections** (**defaultdict**) : fusion et regroupement des données
- **re** : traitement des expressions régulières pour la segmentation des textes
- **uuid** : génération d'identifiants uniques pour les entités
- **jq** : manipulation et extraction des données JSON 
- **curl** : requêtes HTTP lors de l'interrogation de l'API Ollama

## Utilisation

1. **Préparer les fichiers d'entrée**  
   Placez vos fichiers **JSON** dans `data/input_files/`. Chaque fichier doit contenir au moins une clé `"text"` .
   ```
   [
   {
         "text": "Un premier texte..."
   },
   {
         "text": "Un autre texte..."
   },
   ...
   ]
   ```

2. **Définir le modèle à utiliser**  
   Modifiez la variable `MODEL` dans le fichier `pipeline.sh` selon le LLM souhaité (après l'avoir installé).

3. **Lancer le serveur Ollama**  
   Dans un terminal, démarrez le serveur :
   ```bash
   ollama serve
   ```

4. **Exécuter le pipeline**  
   Dans un autre terminal, lancez la commande :
   ```bash
   bash pipeline.sh
   ```
   Le pipeline exécutera alors toutes les étapes.  
   Les résultats intermédiaires et finaux se trouvent dans :
   - Pour les entités : `data/annotations/entities/final_annotations_<MODEL>/`
   - Pour les événements : `data/annotations/events/annotated_paragraphs_<MODEL>/`
   - Résultats finaux : `data/annotations/merged/` (le fichier final contenant toutes les annotations est nommé `final_annotated_file.json`)

## Résultats

À la fin du pipeline, vous obtiendrez un fichier final regroupant chaque texte et les annotations effectuées par le LLM, selon le format JSON suivant :

```json
[
   {
    "text": "Texte du paragraphe...",
    "entities": [
      {
         "text": "forme dans le texte", 
         "start": [
            integer
         ],
         "end": [
            integer
         ],
         "id": "identifiant unique",
         "label": "label de l'entité"},
      ... # Autres entités
    ],
    "events": [
      [
        {
          "attribute": "evt:central_element",
          "occurrences": [
            "<id_entité_1>", "<id_entité_2>"
          ]
        },
        {
          "attribute": "evt:associated_element",
          "occurrences": [
            "<id_entité_3>"
          ]
        }
      ],
      ... # Autres événements
    ]
  }
]
```
## Personnalisation

- **Modèle** :  
  Vous pouvez utiliser tous les modèles disponibles via Ollama en modifiant la variable `MODEL` dans `pipeline.sh`. 

- **Prompts** :  
  Vous pouvez modifier les prompts situés dans le dossier `prompts/`. Le prompt principal pour les entités est dans `general_prompt_entities.txt` et celui pour les événements dans `prompt_events.txt`. Les prompts spécifiques aux catégories d’entités se trouvent dans `prompts/specific_prompts/`.  
  Dans `annotate_entities.sh`, vous pouvez modifier la variable `SPECIFIC_PROMPTS` qui contient les noms des fichiers de prompts. Soit pour adapter le script à des noms de fichiers différents, soit pour lancer le processus d'annotation uniquement sur certains prompts et pas d'autres.

- **Limite de caractères pour la segmentation** :  
  Modifiez la variable `MAX_CHARS` dans `scripts/segment_paragraphs.py` si nécessaire pour ajuster la taille des segments. Une tolérance de 10% est appliquée, pour éviter des coupures indésirables (au milieu d'une phrase ou d'un mot).



