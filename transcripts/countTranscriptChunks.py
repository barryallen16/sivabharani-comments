import json
from pathlib import Path

"""
As i have chunks of transcripts, with start, end and text fields. 
i need to send process them individually one by one. To lessen the hallucinations that happen.
This scripts finds out how many total chunks of transcripts are there in the 1400 tamil transcripts.
And it was found to be `1185665 transcript chunks to be processed`.
"""
SCRIPT_DIR = Path(__file__).resolve().parent
FILE_PATH = SCRIPT_DIR / "output" / "tamil_transcripts.jsonl"
total_transcript_chunks = 0
with open(FILE_PATH, "r", encoding="utf-8") as in_file:
    for line in in_file:
        if line.strip():
            data = json.loads(line)
            for video_id, transcript_list in data.items():
                total_transcript_chunks += len(transcript_list)
print(f"Found {total_transcript_chunks} transcript chunks to be processed")
