"""
Test Search Utility for Sivabharani Extracted Comments
Allows fast CLI testing across data/meili_documents.jsonl without requiring Meilisearch or Docker.
"""

import sys
import json
import argparse
from pathlib import Path
from collections import Counter

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def load_documents(doc_path: Path):
    if not doc_path.exists():
        print(f"Error: {doc_path} not found.")
        sys.exit(1)

    docs = []
    with open(doc_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                docs.append(json.loads(line))
    return docs


def print_stats(docs):
    total = len(docs)
    unique_videos = len(set(d.get("video_id") for d in docs if d.get("video_id")))
    name_counts = Counter()

    for d in docs:
        name = d.get("name_english") or d.get("name_tamil")
        if name:
            name_counts[name] += 1

    print("=" * 60)
    print("Sivabharani Comment Extraction - Current Stats")
    print("=" * 60)
    print(f"Total Extracted Comments : {total:,}")
    print(f"Unique Videos Covered    : {unique_videos:,}")
    print("\nTop 10 Most Frequent Commenter Mentions:")
    for rank, (name, count) in enumerate(name_counts.most_common(10), 1):
        print(f"  {rank:2d}. {name:<25} ({count} mentions)")

    print("\nRandom Sample Entry:")
    sample = docs[0] if docs else {}
    print(f"  Name      : {sample.get('name_english')} / {sample.get('name_tamil')}")
    print(f"  Video URL : {sample.get('video_url')} (at {sample.get('timestamp_formatted')})")
    print(f"  Snippet   : {sample.get('context_snippet', '')[:120]}...")
    print("=" * 60)
    print("\nUsage to search a specific name:")
    print('  uv run python pipeline/test_search.py "Kavin"')
    print('  uv run python pipeline/test_search.py "அரவிந்த்"')


def search_documents(docs, query, limit=10):
    q = query.strip().lower()
    matches = []

    for d in docs:
        en = (d.get("name_english") or "").lower()
        ta = d.get("name_tamil") or ""
        snip = (d.get("context_snippet") or "").lower()

        if q in en or q in ta.lower() or q in snip:
            matches.append(d)

    print("=" * 60)
    print(f'Search Results for "{query}" ({len(matches)} match{"es" if len(matches) != 1 else ""})')
    print("=" * 60)

    if not matches:
        print(f'No matches found for "{query}". Try a different spelling or Tamil script.')
        return

    for idx, hit in enumerate(matches[:limit], 1):
        name_en = hit.get("name_english") or "Unknown"
        name_ta = hit.get("name_tamil") or ""
        ts = hit.get("timestamp_formatted") or "00:00"
        url = hit.get("video_url") or ""
        snippet = hit.get("context_snippet") or ""

        print(f"[{idx}] {name_en} ({name_ta}) - Timestamp: {ts}")
        print(f"    Link  : {url}")
        print(f"    Quote : \"{snippet}\"\n")

    if len(matches) > limit:
        print(f"... and {len(matches) - limit} more matches (showing first {limit}).")


def main():
    parser = argparse.ArgumentParser(description="Test extracted comments from data/meili_documents.jsonl")
    parser.add_argument("query", nargs="?", default=None, help="Name or keyword to search (English or Tamil)")
    parser.add_argument("--limit", type=int, default=10, help="Max results to display")
    parser.add_argument("--input", default="data/meili_documents.jsonl", help="Path to jsonl file")
    args = parser.parse_args()

    doc_path = Path(args.input)
    if not doc_path.exists():
        # Fallback if run from inside pipeline/ or web/
        doc_path = Path(__file__).resolve().parent.parent / "data" / "meili_documents.jsonl"

    docs = load_documents(doc_path)

    if not args.query:
        print_stats(docs)
    else:
        search_documents(docs, args.query, limit=args.limit)


if __name__ == "__main__":
    main()
