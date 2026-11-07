"""
Sivabharani Comments - High-Throughput Distributed Extraction Pipeline
Uses multiple Groq API keys with qwen/qwen3.8-27b to extract subscriber names
from 1,400 video transcripts into Meilisearch-ready documents.
"""

import os
import re
import json
import time
import argparse
import threading
from queue import Queue
from pathlib import Path
import requests
from tqdm import tqdm

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "qwen/qwen3.8-27b"
TARGET_WINDOW_SECS = 65.0
OVERLAP_SECS = 10.0
# For qwen/qwen3.8-27b, Groq on-demand limits:
# 30 RPM, 7,000 ITPM (Input Tokens/Min), 8,000 TPM total, 1,000 RPD, 200,000 TPD.
# With ~850-950 input tokens/request, ~7.5s interval keeps throughput safely within 7,000 ITPM.
MIN_DELAY_PER_KEY = 7.5

def parse_groq_reset_time(val):
    """Parses Groq reset header strings into float seconds (e.g. '172ms', '7.66s', '2m59.56s', '7m12s')."""
    if not val:
        return 0.0
    val = str(val).strip()
    try:
        return float(val)
    except ValueError:
        pass
    total = 0.0
    h = re.search(r'([\d\.]+)h', val)
    if h:
        total += float(h.group(1)) * 3600
    m = re.search(r'([\d\.]+)m(?!s)', val)
    if m:
        total += float(m.group(1)) * 60
    ms = re.search(r'([\d\.]+)ms', val)
    if ms:
        total += float(ms.group(1)) / 1000.0
    else:
        s = re.search(r'([\d\.]+)s', val)
        if s:
            total += float(s.group(1))
    return total

SYSTEM_PROMPT = """You are an expert entity extraction engine for Tamil and Tanglish YouTube transcripts.
Your task is to identify and extract real commenter names, channel handles, and subscriber names mentioned by the speaker.

Rules:
1. Extract ONLY human names (e.g. 'கவின்' -> 'Kavin', 'அரவிந்த் குமார்' -> 'Arvind Kumar') and channel handles / usernames (e.g. 'டெய்லி டெக்' -> 'Daily Tech', 'என்ஜிகே' -> 'NGK', 'டார்க் ஹண்டர்' -> 'Dark Hunter').
2. Deduplication: NEVER repeat any name. Each unique person or handle must appear at most once.
3. Strip honorific suffixes attached to names:
   - 'சிவபரணிஅண்ணா' -> 'சிவபரணி' ('Sivabharani')
   - 'விஜய்சார்' -> 'விஜய்' ('Vijay')
   - 'ரஹ்மான்பாய்' -> 'ரஹ்மான்' ('Rahman')
4. STRICT EXCLUSIONS (Do NOT extract):
   - Tech/phone brands: OPPO, Vivo, Realme, Xiaomi, Apple, Samsung, Nothing, iQOO, OnePlus, Motorola, Sony, etc.
   - Hardware/specs: Snapdragon, SoC, Dimensity, AMOLED, etc.
   - Spoken fillers / greetings: சோ (so), ப்ரோ (bro), ஹாய் (hi), பாய் பாய் (bye bye), வணக்கம் (vanakkam), நண்பர் (nanbar), சார் (sir).
   - Transliterated English words: அபிஷியலா (officially), யூனிக்கா (uniquely), ராப்பிடா (rapidly).
5. Output format:
   Return ONLY a valid JSON object with keys 'tamil' and 'english':
   {"tamil": ["..."], "english": ["..."]}
   If no commenter or handle names are found, return:
   {"tamil": [], "english": []}"""


def load_api_keys(env_path=".env"):
    """Load all valid Groq API keys from .env without logging their contents."""
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Missing {env_path} file.")

    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()

    keys = []
    # Search for any gsk_ tokens in .env
    for match in re.findall(r"gsk_[A-Za-z0-9]+", content):
        if match not in keys:
            keys.append(match)

    if not keys:
        raise ValueError("No valid Groq API keys (gsk_...) found in .env!")

    print(f"[OK] Successfully loaded {len(keys)} unique Groq API keys.")
    return keys


def build_transcript_windows(transcripts_path, target_secs=65.0, overlap_secs=10.0):
    """
    Slices raw micro-chunks into continuous conversational windows.
    Preserves all chunk metadata for exact timestamp pinning.
    """
    windows = []
    if not os.path.exists(transcripts_path):
        raise FileNotFoundError(f"Missing transcripts file at: {transcripts_path}")

    with open(transcripts_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            for vid, chunks in data.items():
                if not chunks or not isinstance(chunks, list):
                    continue

                idx = 0
                n_chunks = len(chunks)
                while idx < n_chunks:
                    win_start = chunks[idx].get("start", 0.0)
                    win_chunks = []
                    curr_idx = idx

                    while curr_idx < n_chunks:
                        c = chunks[curr_idx]
                        win_chunks.append(c)
                        c_end = c.get("start", 0.0) + c.get("duration", 0.0)
                        if (c_end - win_start) >= target_secs:
                            break
                        curr_idx += 1

                    win_text = " ".join(c.get("text", "").strip() for c in win_chunks if c.get("text"))
                    if win_text:
                        window_id = f"{vid}_{int(win_start)}"
                        windows.append({
                            "window_id": window_id,
                            "video_id": vid,
                            "window_start": win_start,
                            "window_end": win_chunks[-1].get("start", 0.0) + win_chunks[-1].get("duration", 0.0),
                            "text": win_text,
                            "chunks": win_chunks
                        })

                    # Move forward by (target_secs - overlap_secs)
                    next_start_target = win_start + max(15.0, (target_secs - overlap_secs))
                    while idx < n_chunks and chunks[idx].get("start", 0.0) < next_start_target:
                        idx += 1
                    if idx == curr_idx and idx < n_chunks:
                        idx += 1

    return windows


def pin_name_timestamp(tamil_name, chunks, default_start):
    """
    Finds the exact micro-chunk inside the window where the name appears.
    Returns the exact chunk start timestamp.
    """
    clean_name = tamil_name.strip()
    if not clean_name:
        return default_start

    # Exact match in chunk
    for c in chunks:
        txt = c.get("text", "")
        if clean_name in txt:
            return c.get("start", default_start)

    # Word-level match if multi-word name
    parts = clean_name.split()
    if len(parts) > 1:
        for c in chunks:
            txt = c.get("text", "")
            if parts[0] in txt:
                return c.get("start", default_start)

    return default_start


def call_groq_api(api_key, text, max_retries=5):
    """
    Executes a single extraction call to Groq with rate-limit header inspection:
    - Inspects retry-after on HTTP 429
    - Inspects x-ratelimit-reset-tokens on TPM limits
    - Detects x-ratelimit-remaining-requests for RPD daily exhaustion
    Returns: (parsed_json_dict, is_daily_quota_exhausted)
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f'Transcript: "{text}"\nExtract names/handles:'}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": 600,
        "presence_penalty": 0.2
    }

    for attempt in range(max_retries):
        try:
            res = requests.post(GROQ_URL, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                # Proactive TPM pacing: if remaining tokens in current minute < 800, wait reset
                rem_tok_str = res.headers.get("x-ratelimit-remaining-tokens")
                reset_tok_str = res.headers.get("x-ratelimit-reset-tokens")
                if rem_tok_str is not None:
                    try:
                        rem_tok = int(rem_tok_str)
                        if rem_tok < 800:
                            wait_s = parse_groq_reset_time(reset_tok_str) + 0.1
                            time.sleep(min(wait_s, 10.0))
                    except ValueError:
                        pass

                # Check daily remaining requests
                rem_req_str = res.headers.get("x-ratelimit-remaining-requests")
                is_exhausted = False
                if rem_req_str is not None:
                    try:
                        if int(rem_req_str) <= 0:
                            is_exhausted = True
                    except ValueError:
                        pass

                raw = res.json()["choices"][0]["message"]["content"].strip()
                return json.loads(raw), is_exhausted

            elif res.status_code == 429:
                # Rate limit encountered - inspect exact headers and error body
                retry_after_hdr = res.headers.get("retry-after")
                rem_req_str = res.headers.get("x-ratelimit-remaining-requests")
                reset_tok_str = res.headers.get("x-ratelimit-reset-tokens")

                err_msg = ""
                err_code = ""
                try:
                    err_json = res.json().get("error", {})
                    err_msg = str(err_json.get("message", "")).lower()
                    err_code = str(err_json.get("code", "")).lower()
                except Exception:
                    pass

                # True Daily Quota Exhaustion (RPD / TPD):
                # 1. remaining-requests is explicitly 0, OR
                # 2. error message explicitly indicates daily exhaustion (RPD/TPD/day)
                is_daily_limit = False
                if rem_req_str is not None:
                    try:
                        if int(rem_req_str) <= 0:
                            is_daily_limit = True
                    except ValueError:
                        pass
                if "per day" in err_msg or "rpd" in err_msg or "tpd" in err_msg or "daily" in err_code:
                    is_daily_limit = True

                if is_daily_limit:
                    return None, True

                # Transient per-minute rate limit (TPM, ITPM, or RPM):
                # Sleep exactly the duration requested by Groq (retry-after or reset-tokens)
                wait_time = 7.0
                if retry_after_hdr:
                    try:
                        wait_time = float(retry_after_hdr) + 0.5
                    except ValueError:
                        wait_time = 7.0
                elif reset_tok_str:
                    wait_time = parse_groq_reset_time(reset_tok_str) + 0.5
                else:
                    wait_time = 3.0 * (attempt + 1)

                time.sleep(min(wait_time, 25.0))

            elif res.status_code in (500, 502, 503, 504):
                time.sleep(2.0 * (attempt + 1))
            elif res.status_code == 400:
                payload["temperature"] = 0.2
                time.sleep(1.0)
            else:
                return None, False
        except Exception:
            time.sleep(2.0 * (attempt + 1))

    return None, False


def worker_loop(key, work_queue, progress_bar, file_lock, out_f, done_f, stats):
    """Dedicated worker thread for one API key with adaptive rate-limit pacing."""
    while not stats.get("stop_requested", False):
        try:
            item = work_queue.get(timeout=2.0)
        except Exception:
            if stats.get("active_workers", 1) <= 0 or work_queue.empty():
                break
            continue

        if item is None:
            work_queue.task_done()
            break

        window_id = item["window_id"]
        vid = item["video_id"]
        win_start = item["window_start"]
        chunks = item["chunks"]
        text = item["text"]

        # Optimization: Skip pure music / sound tags to save tokens and avoid quota waste
        clean_text = re.sub(r'\[.*?\]', '', text).strip()
        if len(clean_text) < 15:
            with file_lock:
                done_f.write(window_id + "\n")
                done_f.flush()
                stats["done"] += 1
                progress_bar.update(1)
            work_queue.task_done()
            continue

        t0 = time.time()
        result, is_daily_exhausted = call_groq_api(key, text)
        elapsed = time.time() - t0

        if is_daily_exhausted:
            # Re-enqueue item so active keys can process it; gracefully retire this worker
            work_queue.put(item)
            work_queue.task_done()
            with file_lock:
                stats["active_workers"] -= 1
                progress_bar.write(f"[{time.strftime('%H:%M:%S')}] Key {key[:8]}... reached daily quota (RPD/TPD). Worker retired ({stats['active_workers']} active).")
                if stats["active_workers"] <= 0:
                    stats["stop_requested"] = True
            break

        if result is None:
            item["fail_count"] = item.get("fail_count", 0) + 1
            if item["fail_count"] >= 5:
                with file_lock:
                    done_f.write(window_id + "\n")
                    done_f.flush()
                    stats["done"] += 1
                    stats["pending"] -= 1
                    progress_bar.write(f"[{time.strftime('%H:%M:%S')}] Window {window_id} failed after 5 retries. Skipped.")
                    progress_bar.update(1)
                work_queue.task_done()
                continue
            work_queue.put(item)
            work_queue.task_done()
            time.sleep(1.0)
            continue

        # Maintain minimum safe delay per key to safeguard 8K TPM ceiling
        if elapsed < MIN_DELAY_PER_KEY:
            time.sleep(MIN_DELAY_PER_KEY - elapsed)

        if isinstance(result, dict):
            tamil_names = result.get("tamil", [])
            english_names = result.get("english", [])

            if isinstance(tamil_names, list) and isinstance(english_names, list):
                # Ensure valid paired extractions
                while len(english_names) < len(tamil_names):
                    english_names.append(tamil_names[len(english_names)])
                min_len = min(len(tamil_names), len(english_names))
                if min_len > 0:
                    for i in range(min_len):
                        t_name = str(tamil_names[i]).strip()
                        e_name = str(english_names[i]).strip()
                        if not t_name or not e_name:
                            continue

                        exact_ts = pin_name_timestamp(t_name, chunks, win_start)
                        mins = int(exact_ts // 60)
                        secs = int(exact_ts % 60)
                        formatted_time = f"{mins:02d}:{secs:02d}"

                        doc = {
                            "id": f"{vid}_{int(exact_ts)}_{i}",
                            "video_id": vid,
                            "video_url": f"https://youtu.be/{vid}?t={int(exact_ts)}",
                            "timestamp_seconds": round(exact_ts, 2),
                            "timestamp_formatted": formatted_time,
                            "name_tamil": t_name,
                            "name_english": e_name,
                            "context_snippet": text[:350]
                        }

                        with file_lock:
                            out_f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                            out_f.flush()
                            stats["hits"] += 1

        # Only mark as completed once successfully processed and saved
        with file_lock:
            done_f.write(window_id + "\n")
            done_f.flush()
            stats["done"] += 1
            stats["pending"] -= 1

            # Update progress bar safely inside lock
            progress_bar.set_postfix({
                "hits": stats["hits"],
                "done": f"{stats['done']}/{stats['total']}",
                "keys": stats["active_workers"]
            })
            progress_bar.update(1)

            # Print a clean milestone log line every 250 windows
            curr_done = stats["done"]
            if curr_done % 250 == 0:
                elapsed_sec = max(1, time.time() - stats["start_time"])
                speed = curr_done / elapsed_sec
                rem_sec = int((stats["total"] - curr_done) / speed) if speed > 0 else 0
                eta_str = f"{rem_sec // 3600}h {(rem_sec % 3600) // 60}m"
                pct = (curr_done / stats["total"]) * 100
                progress_bar.write(
                    f"[{time.strftime('%H:%M:%S')}] {pct:5.1f}% | Done: {curr_done:,}/{stats['total']:,} | Hits: {stats['hits']:,} | Speed: {speed:.1f} win/s | ETA: {eta_str}"
                )

        work_queue.task_done()


def main():
    parser = argparse.ArgumentParser(description="Distributed Groq extraction for Sivabharani comments")
    parser.add_argument("--test", type=int, default=0, help="Run only on N windows for testing")
    parser.add_argument("--transcripts", default="transcripts/output/tamil_transcripts.jsonl", help="Path to transcripts")
    parser.add_argument("--output", default="data/meili_documents.jsonl", help="Output path for Meilisearch docs")
    parser.add_argument("--done_file", default="data/processed_windows.txt", help="Tracker for completed windows")
    args = parser.parse_args()

    api_keys = load_api_keys()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Resume support: load previously completed windows
    processed_windows = set()
    if os.path.exists(args.done_file):
        with open(args.done_file, "r", encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    processed_windows.add(l.strip())
        print(f"[Resume] Found {len(processed_windows)} already processed windows.")

    print(f"[1/3] Building transcript conversational windows (~{TARGET_WINDOW_SECS}s with {OVERLAP_SECS}s overlap)...")
    all_windows = build_transcript_windows(args.transcripts, target_secs=TARGET_WINDOW_SECS, overlap_secs=OVERLAP_SECS)
    print(f"[1/3] Total windows generated: {len(all_windows)}")

    # Filter out already processed windows
    pending_windows = [w for w in all_windows if w["window_id"] not in processed_windows]
    print(f"[1/3] Windows remaining to process: {len(pending_windows)}")

    if args.test > 0:
        pending_windows = pending_windows[:args.test]
        print(f"[Test Mode] Limiting run to first {len(pending_windows)} windows.")

    if not pending_windows:
        print("[Done] All windows have already been processed!")
        return

    work_queue = Queue()
    for w in pending_windows:
        work_queue.put(w)

    file_lock = threading.Lock()
    out_f = open(args.output, "a", encoding="utf-8")
    done_f = open(args.done_file, "a", encoding="utf-8")

    stats = {
        "hits": 0,
        "done": len(processed_windows),
        "total": len(all_windows),
        "pending": len(pending_windows),
        "start_time": time.time(),
        "active_workers": len(api_keys),
        "stop_requested": False
    }
    progress_bar = tqdm(total=len(pending_windows), desc="Extracting comments", unit="win", ncols=100)

    # Launch 1 worker thread per API key
    threads = []
    for key in api_keys:
        t = threading.Thread(
            target=worker_loop,
            args=(key, work_queue, progress_bar, file_lock, out_f, done_f, stats),
            daemon=True
        )
        t.start()
        threads.append(t)

    # Wait for queue to empty or all workers to retire if daily quota is reached
    while not work_queue.empty() and stats["active_workers"] > 0:
        time.sleep(0.5)

    if stats["active_workers"] > 0:
        work_queue.join()

    # Gracefully terminate remaining worker threads
    stats["stop_requested"] = True
    for _ in range(len(api_keys) * 2):
        work_queue.put(None)
    for t in threads:
        t.join(timeout=2.0)

    progress_bar.close()
    out_f.close()
    done_f.close()

    if stats["active_workers"] <= 0 and not work_queue.empty():
        print(f"\n[Quota Alert] All {len(api_keys)} Groq API keys have reached their daily limit (RPD/TPD).")
        print(f"[Status] Checkpoint safely preserved: {stats['done']}/{stats['total']} windows processed.")
        print("[Next Step] Re-run this script once your Groq daily quota resets to continue smoothly.")
    else:
        print(f"\n[Finished] Total hits extracted: {stats['hits']}")
        print(f"[Output] Saved to: {args.output}")


if __name__ == "__main__":
    main()
