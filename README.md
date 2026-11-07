# Sivabharani Comment Search Engine

Searchable index of subscriber comment replies across 1,400+ Sivabharani YouTube video transcripts.

Sivabharani answers viewer comments and product buying questions throughout his videos.
With more than 1,400 uploaded videos on the channel, finding where a specific question was answered manually takes hours.
This project transcribes the channel, extracts subscriber names mentioned by the host using an LLM pipeline, pins the exact micro-chunk timestamp, and indexes the records into Meilisearch for instant search.

![SBUS Banner](misc/sbus.png)

## Pipeline Architecture

```
[1,400+ Video Transcripts (1,185,665 micro-chunks)]
                      │
                      ▼
[65s Conversational Windows with 10s Overlap (36,818 windows)]
                      │
                      ▼
[Distributed Groq LLM Extraction Pipeline (27 API Keys)]
              (qwen/qwen3.8-27b)
                      │
                      ▼
[Micro-Chunk Exact Timestamp Pinning]
                      │
                      ▼
[data/meili_documents.jsonl (15,155 unique commenter docs)]
                      │
                      ▼
[Meilisearch Production Index] ──► [Instant Search Web Client]
```

## Dataset & Hugging Face

The full extracted dataset and window tracking files are published on Hugging Face:
[barryallen16/sivabharani_comments](https://huggingface.co/datasets/barryallen16/sivabharani_comments)

- Total videos covered: 1,400+
- Raw transcript micro-chunks: 1,185,665
- Conversational windows analyzed: 36,818
- Extracted commenter documents: 15,155 unique entries
- Search engine: Meilisearch (`sivabharani_comments` index on `https://adhi.isroot.in`)
- Web interface: Static frontend hosted on GitHub Pages querying live Meilisearch directly

## How to Run

### 1. Requirements

Install dependencies using `uv`:

```bash
uv sync
```

Or install using standard `pip`:

```bash
pip install -r requirements.txt
```

### 2. Extract Comment Mentions

The distributed extraction script reads all Groq API keys from `.env` and processes conversational windows concurrently:

```bash
uv run python pipeline/run_extraction.py
```

- Windows already processed are tracked in `data/processed_windows.txt`.
- If interrupted, re-running the script resumes from the exact point it stopped.
- Output documents are appended to `data/meili_documents.jsonl`.

To run a test batch on the first 50 windows only:

```bash
uv run python pipeline/run_extraction.py --test 50
```

### 3. Index into Meilisearch

Configure and upload the extracted documents into Meilisearch:

```bash
uv run python pipeline/index_to_meilisearch.py --host https://adhi.isroot.in --key YOUR_MEILISEARCH_KEY --index sivabharani_comments
```

Index settings applied by the script:
- Searchable attributes: `name_english`, `name_tamil`, `context_snippet`, `video_id`
- Filterable attributes: `video_id`, `timestamp_seconds`
- Sortable attributes: `timestamp_seconds`

### 4. Search from the CLI

Test search results directly in your terminal without starting a browser:

```bash
# Search in English
uv run python pipeline/test_search.py "Kavin"

# Search in Tamil
uv run python pipeline/test_search.py "கவின்"
```

### 5. Launch the Web Interface

Open `web/index.html` directly in any web browser, or serve it with Python:

```bash
cd web
python -m http.server 3000
```

Open `http://localhost:3000` in your browser.

## Document Schema

Each indexed record contains the commenter identity, video URL, exact timestamp, and transcript context:

```json
{
  "id": "XId8oORl0iE_290_0",
  "video_id": "XId8oORl0iE",
  "video_url": "https://youtu.be/XId8oORl0iE?t=290",
  "timestamp_seconds": 290.48,
  "timestamp_formatted": "04:50",
  "name_tamil": "கவின்",
  "name_english": "Kavin",
  "context_snippet": "அடுத்து கவின் என்ன சொல்லிருக்காருன்னா iPhone 16 Pro வாங்கலாம்னு இருக்கேன் ப்ரோ..."
}
```

## REST API Search Query Example

```bash
curl -X POST "https://adhi.isroot.in/indexes/sivabharani_comments/search" \
  -H "Authorization: Bearer 5e81db2e26ebe8b85982c0d883abbbc23aed0f3b4fd54ffd0e9eaa872fe6229e" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "Kavin",
    "limit": 10
  }'
```
