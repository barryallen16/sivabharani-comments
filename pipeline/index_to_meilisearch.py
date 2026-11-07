"""
Meilisearch Indexer for Sivabharani Comments
Loads data/meili_documents.jsonl and indexes into Meilisearch via REST API.
"""

import os
import json
import argparse
import requests
from tqdm import tqdm


def setup_index(host, master_key, index_name="sivabharani_comments"):
    host = host.rstrip("/")
    headers = {
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json"
    }

    # Create index
    print(f"Connecting to Meilisearch at {host}...")
    r = requests.post(f"{host}/indexes", headers=headers, json={"uid": index_name, "primaryKey": "id"})
    if r.status_code in (200, 201, 202):
        print(f"[OK] Created index '{index_name}'.")
    elif r.status_code == 400 and "already_exists" in r.text:
        print(f"[OK] Index '{index_name}' already exists.")
    else:
        print(f"Notice: {r.status_code} - {r.text}")

    # Configure searchable attributes and settings
    settings = {
        "searchableAttributes": [
            "name_english",
            "name_tamil",
            "context_snippet",
            "video_id"
        ],
        "filterableAttributes": [
            "video_id",
            "timestamp_seconds"
        ],
        "sortableAttributes": [
            "timestamp_seconds"
        ],
        "rankingRules": [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness"
        ]
    }
    r = requests.patch(f"{host}/indexes/{index_name}/settings", headers=headers, json=settings)
    if r.status_code in (200, 201, 202):
        print(f"[OK] Index settings applied successfully.")
    else:
        print(f"Warning on settings: {r.status_code} - {r.text}")


def upload_documents(host, master_key, doc_file, index_name="sivabharani_comments", batch_size=1000):
    host = host.rstrip("/")
    headers = {
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json"
    }

    if not os.path.exists(doc_file):
        raise FileNotFoundError(f"Missing documents file: {doc_file}")

    print(f"Reading documents from {doc_file}...")
    batch = []
    total_docs = 0

    with open(doc_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            doc = json.loads(line)
            batch.append(doc)
            if len(batch) >= batch_size:
                r = requests.post(f"{host}/indexes/{index_name}/documents", headers=headers, json=batch)
                if r.status_code not in (200, 201, 202):
                    print(f"Error uploading batch: {r.status_code} - {r.text}")
                total_docs += len(batch)
                print(f"Uploaded {total_docs} documents so far...")
                batch = []

        if batch:
            r = requests.post(f"{host}/indexes/{index_name}/documents", headers=headers, json=batch)
            total_docs += len(batch)
            print(f"Uploaded final {len(batch)} documents.")

    print(f"\n[Finished] Total {total_docs} documents indexed in Meilisearch!")


def main():
    parser = argparse.ArgumentParser(description="Upload extracted comments to Meilisearch")
    parser.add_argument("--host", default="http://localhost:7700", help="Meilisearch URL")
    parser.add_argument("--key", default="sivabharani_master_key", help="Meilisearch API Master Key")
    parser.add_argument("--index", default="sivabharani_comments", help="Index name")
    parser.add_argument("--input", default="data/meili_documents.jsonl", help="Path to jsonl documents")
    args = parser.parse_args()

    setup_index(args.host, args.key, args.index)
    upload_documents(args.host, args.key, args.input, args.index)


if __name__ == "__main__":
    main()
