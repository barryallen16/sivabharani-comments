from youtube_transcript_api import YouTubeTranscriptApi
import json

"""
This code iterates through all the 2755 video_ids and extracts its corresponding transcript
list (list that shows the available language transcripts) and write a json file containing the 
transcript language count and its corresponding video_ids to   `./output/transcripts_report.json`
"""
video_ids = []
with open("./input/video_ids.txt", "r") as in_file:
    for line in in_file:
        video_ids.append(line.strip())

api_instance = YouTubeTranscriptApi()

generated_languages = {}
for video_id in video_ids:
    try:
        transcript_list = api_instance.list(video_id)
        for lang in list(transcript_list._generated_transcripts.keys()):
            if lang not in generated_languages.keys():
                generated_languages[lang] = {"count": 1, "video_ids": [video_id]}
            elif lang in generated_languages.keys():
                generated_languages[lang]["count"] += 1
                generated_languages[lang]["video_ids"].append(video_id)
    except:
        continue

print(generated_languages)
with open("./output/transcripts_report.json", "w", encoding="utf-8") as out_file:
    out_file.write(json.dumps(generated_languages))
