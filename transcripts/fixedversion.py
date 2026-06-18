import json
import random
import time
from pathlib import Path
from tqdm import tqdm
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

start = time.perf_counter()

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = SCRIPT_DIR / "output"
PROXY_FILE_DIR = PROJECT_ROOT / "proxies" / "output"
PROXY_FILE_V1_PATH = PROXY_FILE_DIR / "success_proxies.txt"
PROXY_FILE_V2_PATH = PROXY_FILE_DIR / "working_free_http_proxies.txt"

LANGUAGE = "ko"
OUTPUT_FILENAME = "korean_transcripts.jsonl"
success_proxies_set = set()


def load_proxies(file_path):
    proxy_list = []
    try:
        with open(file_path, "r", encoding="utf-8") as proxies:
            for proxy_line in proxies:
                line = proxy_line.strip()
                if not line:
                    continue
                # FIX: Keep the proxy instead of dropping it if it has http://
                if not line.startswith("http://") and not line.startswith("https://"):
                    line = f"http://{line}"
                proxy_list.append(line)
    except FileNotFoundError:
        print(f"Warning: Proxy file not found at {file_path}")
    return set(proxy_list)


PROXY_LIST = load_proxies(PROXY_FILE_V1_PATH)
if len(PROXY_LIST) > 0:
    pass
else: 
    PROXY_LIST = load_proxies(PROXY_FILE_V2_PATH)
print(f"Loaded {len(PROXY_LIST)} HTTP proxies for rotation.")


with open(OUTPUT_DIR / "transcripts_report.json", "r", encoding="utf-8") as in_file:
    json_data = json.load(in_file)
    video_ids = json_data[LANGUAGE]["video_ids"]  # "ta" for tamil , LANGUAGE for korean

processed_video_ids = set()
# FIX: Wrap in try-except so a missing file doesn't break a fresh run
try:
    with open(OUTPUT_DIR / OUTPUT_FILENAME, "r", encoding="utf-8") as jsonl_file:
        for line in jsonl_file:
            if line.strip():
                data = json.loads(line)
                video_id = list(data.keys())[0]
                processed_video_ids.add(video_id)
except FileNotFoundError:
    pass

print(f"Found {len(processed_video_ids)} already processed video ids")

unprocessed_video_ids = [vid for vid in video_ids if vid not in processed_video_ids]
print(
    f"Loaded {len(unprocessed_video_ids)} video ids to be processed from {len(video_ids)}."
)

count = 0

# Guard against running the loop if your proxy extraction yielded nothing
if not PROXY_LIST and unprocessed_video_ids:
    print("\n[!] Error: No working proxies loaded. Aborting loop execution.")
    unprocessed_video_ids = []

for video_id in tqdm(
    unprocessed_video_ids, desc="Processing transcripts", unit="video"
):
    # FIX: Move the proxy extraction validation into a safe deterministic layout
    if not PROXY_LIST:
        tqdm.write(
            "\n[!] All proxies completely exhausted from the list. Halting execution."
        )
        break

    current_proxy = random.choice(PROXY_LIST)
    proxy_config = GenericProxyConfig(http_url=current_proxy, https_url=current_proxy)
    ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)

    # Force a 3.5 second network timeout so dead proxies fail fast
    if hasattr(ytt_api, "_http_client"):
        ytt_api._http_client.timeout = 3.5

    try:
        transcript_list = ytt_api.list(video_id)
        transcript = transcript_list.find_generated_transcript([LANGUAGE])
        raw_transcript_data = transcript.fetch()

        serializable_data = {
            video_id: [
                {
                    "text": chunk.text,
                    "start": chunk.start,
                    "duration": chunk.duration,
                }
                for chunk in raw_transcript_data
            ]
        }

        with open(OUTPUT_DIR / OUTPUT_FILENAME, "a", encoding="utf-8") as f:
            json.dump(serializable_data, f, ensure_ascii=False)
            f.write("\n")

        count += 1
        tqdm.write(f"Success with proxy - {current_proxy} | success_count - {count}")
        if current_proxy not in success_proxies_set:
            success_proxies_set.add(current_proxy)
            with open(
                PROXY_FILE_DIR / "new_success_proxies.txt", "a", encoding="utf-8"
            ) as f:
                f.write(current_proxy + "\n")
        time.sleep(5)

    except Exception as e:
        # Prune the bad proxy from the active rotation list if it encounters problems
        tqdm.write(
            f"Skipped video {video_id} using {current_proxy} | Error: {type(e).__name__}"
        )
        if (
            "Connection" in str(e)
            or "429" in str(e)
            or "Timeout" in str(e)
            or "ProxyError" in str(e)
        ):
            if current_proxy in PROXY_LIST:
                PROXY_LIST.remove(current_proxy)
                tqdm.write(
                    f"Removed dead proxy. Remaining pool size: {len(PROXY_LIST)}"
                )
        continue

end = time.perf_counter()
elapsed_time = end - start

hours = int(elapsed_time // 3600)
minutes = int((elapsed_time % 3600) // 60)
seconds = elapsed_time % 60

print(f"\nFinished processing in {hours}h {minutes}m {seconds:.2f}s")
