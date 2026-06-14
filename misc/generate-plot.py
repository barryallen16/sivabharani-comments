import matplotlib.pyplot as plt
import json
from operator import itemgetter

with open(
    "../transcripts/output/transcripts_report.json", "r", encoding="utf-8"
) as in_file:
    for line in in_file:
        if line.strip():
            data: dict = json.loads(line)


if data:
    sorted_languages = sorted(
        data.keys(), key=lambda lang: data[lang]["count"], reverse=True
    )
    language_count = [data[lang]["count"] for lang in sorted_languages]
    bars = plt.bar(sorted_languages, language_count)
    plt.bar_label(bars, padding=3)
    plt.title("Transcript Language Distribution")
    plt.xlabel("Transcript Language")
    plt.ylabel("Transcript count in the corresponding language")
    plt.tight_layout()
    plt.show()
