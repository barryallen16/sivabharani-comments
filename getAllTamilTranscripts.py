from youtube_transcript_api import YouTubeTranscriptApi
import json
from tqdm import tqdm
import time

start = time.perf_counter()

with open("./transcripts_report.json", "r", encoding="utf-8") as in_file:
    json_data = json.load(in_file)
    video_ids = json_data["ta"]["video_ids"]

processed_video_ids = set()
with open("./tamil_transcripts.jsonl", "r", encoding="utf-8") as jsonl_file:
    for line in jsonl_file:
        data = json.loads(line)
        video_id = list(data.keys())
        processed_video_ids.add(video_id)
print(f"Found {len(processed_video_ids)} already processed video ids")

unprocessed_video_ids = [vid for vid in video_ids if vid not in processed_video_ids]

print(
    f"Loaded {len(unprocessed_video_ids)} video ids to be processed from {len(video_ids)}."
)

ytt_api = YouTubeTranscriptApi()
for video_id in tqdm(video_ids, desc="Processing transcripts", unit="video"):
    transcript_list = ytt_api.list(video_id)
    transcript = transcript_list.find_generated_transcript(["ta"])
    raw_transcript_data = transcript.fetch()
    serializable_data = {
        video_id: [
            {"text": chunk.text, "start": chunk.start, "duration": chunk.duration}
            for chunk in raw_transcript_data
        ]
    }
    with open("tamil_transcripts.jsonl", "a", encoding="utf-8") as f:
        json.dump(serializable_data, f, ensure_ascii=False)
        f.write("\n")
    time.sleep(1.2)

end = time.perf_counter()
elapsed_time = end - start

hours = elapsed_time // 3600
minutes = (elapsed_time % 3600) // 60
seconds = elapsed_time % 60

print(f"finished in {hours}h {minutes}m {seconds:.2f}s")
