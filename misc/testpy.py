import json

processed_video_ids = set()
with open("./tamil_transcripts.jsonl", "r", encoding="utf-8") as jsonl_file:
    for line in jsonl_file:
        data = json.loads(line)
        video_id = list(data.keys())
        processed_video_ids.add(video_id)
