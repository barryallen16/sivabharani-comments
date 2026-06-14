import os
import time
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

# Proper Path setup
output_dir = Path("proxies")
output_dir.mkdir(parents=True, exist_ok=True)

proxy_file_path = "./proxies/results-http.txt"
# Clean load
with open(
    "./proxies/not_working_free_http_proxies.txt", "r", encoding="utf-8"
) as in_file:
    not_working_proxies = {line.strip() for line in in_file if line.strip()}

with open("./proxies/working_free_http_proxies.txt", "r", encoding="utf-8") as in_file:
    working_proxies = {line.strip() for line in in_file if line.strip()}

already_processed_proxies = not_working_proxies.union(working_proxies)

with open(proxy_file_path, "r", encoding="utf-8") as in_file:
    PROXY_LIST = [
        f"http://{line.strip()}"
        if not line.strip().startswith("http://")
        else line.strip()
        for line in in_file
        if line.strip()
    ]
print(f"Loaded {len(PROXY_LIST)} to be processed.")
CLEAN_PROXY_LIST = [
    proxy for proxy in PROXY_LIST if proxy not in already_processed_proxies
]
print(
    f" excluding {len(PROXY_LIST) - len(CLEAN_PROXY_LIST)} already processed proxies.",
    f"Found {len(CLEAN_PROXY_LIST)} unprocessed proxies.",
)

video_id = "qyEEVWy6FZ8"


# Define the individual worker function
def check_single_proxy(proxy_url):
    proxy_config = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
    ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
    try:
        if hasattr(ytt_api, "_http_client"):
            ytt_api._http_client.timeout = 3.0  # Keep it short!

        ytt_api.list(video_id)
        return proxy_url, True
    except Exception:
        return proxy_url, False


print(f"Testing {len(CLEAN_PROXY_LIST)} proxies concurrently...")

# Max workers sets how many threads run at the exact same time
MAX_THREADS = 60
start_time = time.perf_counter()

if len(CLEAN_PROXY_LIST) > 0:
    # ThreadPoolExecutor spins up threads and manages them automatically
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # Kick off all verification jobs at once
        futures = {
            executor.submit(check_single_proxy, proxy): proxy
            for proxy in CLEAN_PROXY_LIST
        }

        # tqdm updates dynamically as each independent thread finishes its job
        for future in tqdm(
            as_completed(futures),
            total=len(PROXY_LIST),
            desc="Checking proxies",
            unit="proxy",
        ):
            proxy, is_working = future.result()
            if is_working:
                with open(
                    output_dir / "working_free_http_proxies.txt", "a", encoding="utf-8"
                ) as out_file:
                    out_file.write(proxy + "\n")
                working_proxies.add(proxy)
            else:
                with open(
                    output_dir / "not_working_free_http_proxies.txt",
                    "a",
                    encoding="utf-8",
                ) as out_file:
                    out_file.write(proxy + "\n")

                not_working_proxies.add(proxy)


end_time = time.perf_counter()
print(f"\nFinished concurrently in {end_time - start_time:.2f} seconds!")
print(f"Working: {len(working_proxies)} | Dead: {len(not_working_proxies)}")
