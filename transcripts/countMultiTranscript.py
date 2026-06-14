import json

"""
in the original scraped transcripts list report, which showed what all transcript languages were available had only 
three languages in it , namely ko (Korean), ta (Tamil), en (English). The following code checks if any video_id has
multiple transcript language avaible from the above three. 

"""
with open("./output/transcripts_report.json", "r", encoding="utf-8") as in_file:
    for line in in_file:
        data = json.loads(line)
        korean_list = data["ko"]["video_ids"]
        tamil_list = data["ta"]["video_ids"]
        english_list = data["en"]["video_ids"]
        multitranscript_count = 0
        for vidx in korean_list:
            if vidx in tamil_list or vidx in english_list:
                multitranscript_count += 1
                print(f"multitranscript found video_id - {vidx}")
        for vidx in tamil_list:
            if vidx in korean_list or vidx in english_list:
                multitranscript_count += 1
                print(f"multitranscript found video_id - {vidx}")
        for vidx in english_list:
            if vidx in korean_list or vidx in tamil_list:
                multitranscript_count += 1
                print(f"multitranscript found video_id - {vidx}")

print(f"Total no of video ids with multiple transcript: {multitranscript_count}")
