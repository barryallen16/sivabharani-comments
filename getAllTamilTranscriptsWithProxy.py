from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
import json
import random
from tqdm import tqdm
import time

start = time.perf_counter()


def load_proxies(file_path):
    with open(file_path, "r", encoding="utf-8") as proxies:
        proxy_list = [
            f"http://{proxy_line.strip()}"
            for proxy_line in proxies
            if not proxy_line.strip().startswith("http://")
        ]
        return proxy_list


PROXY_LIST = load_proxies("./results-http.txt")

with open("./transcripts_report.json", "r", encoding="utf-8") as in_file:
    json_data = json.load(in_file)
    video_ids = json_data["ta"]["video_ids"]

processed_video_ids = set()
with open("./tamil_transcripts.jsonl", "r", encoding="utf-8") as jsonl_file:
    for line in jsonl_file:
        data = json.loads(line)
        video_id = list(data.keys())[0]
        processed_video_ids.add(video_id)

print(f"Found {len(processed_video_ids)} already processed video ids")

unprocessed_video_ids = [vid for vid in video_ids if vid not in processed_video_ids]

print(
    f"Loaded {len(unprocessed_video_ids)} video ids to be processed from {len(video_ids)}."
)

for video_id in tqdm(
    unprocessed_video_ids, desc="Processing transcripts", unit="video"
):
    current_proxy = None
    if PROXY_LIST:
        current_proxy = random.choice(PROXY_LIST)
        proxy_config = GenericProxyConfig(
            http_url=current_proxy, https_url=current_proxy
        )

        ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
        try:
            transcript_list = ytt_api.list(video_id)
            transcript = transcript_list.find_generated_transcript(["ta"])
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
            with open("tamil_transcripts.jsonl", "a", encoding="utf-8") as f:
                json.dump(serializable_data, f, ensure_ascii=False)
                f.write("\n")
            time.sleep(5)
        except Exception as e:
            tqdm.write(f"error occured with proxy - {current_proxy}")
            if "Connection" in str(e) or "429" in str(e):
                tqdm.write("Found dead proxy. removing from proxy list..")
                PROXY_LIST.remove(current_proxy)
            continue


end = time.perf_counter()
elapsed_time = end - start

hours = elapsed_time // 3600
minutes = (elapsed_time % 3600) // 60
seconds = elapsed_time % 60

print(f"finished in {hours}h {minutes}m {seconds:.2f}s")
