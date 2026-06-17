from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
from pathlib import Path
import json

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
TRANSCRIPT_REPORT_DIR = PROJECT_ROOT / "transcripts" / "output"
TRANSCRIPT_REPORT_FILEPATH = TRANSCRIPT_REPORT_DIR / "transcripts_report.json"
with open(TRANSCRIPT_REPORT_FILEPATH, "r", encoding="utf-8") as in_file:
    for line in in_file:
        if line.strip():
            data = json.loads(line)
            korean_vids = data["ko"]["video_ids"]
            count = data["ko"]["count"]
print(len(korean_vids), count)
proxy_list = [
    "http://81.168.119.85:443",
    "http://206.135.55.224:999",
    "http://185.11.134.227:8443",
]
current_proxy = "http://206.135.55.224:999"
proxy_config = GenericProxyConfig(http_url=current_proxy, https_url=current_proxy)
ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
transcript_list = ytt_api.list(korean_vids[0])
transcript = transcript_list.find_generated_transcript(["ko"])
translated = transcript.translate("ta")
translated_result = translated.fetch()
print(translated_result)
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
from pathlib import Path
import json

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
TRANSCRIPT_REPORT_DIR = PROJECT_ROOT / "transcripts" / "output"
TRANSCRIPT_REPORT_FILEPATH = TRANSCRIPT_REPORT_DIR / "transcripts_report.json"
with open(TRANSCRIPT_REPORT_FILEPATH, "r", encoding="utf-8") as in_file:
    for line in in_file:
        if line.strip():
            data = json.loads(line)
            korean_vids = data["ko"]["video_ids"]
            count = data["ko"]["count"]
print(len(korean_vids), count)
proxy_list = [
    "http://81.168.119.85:443",
    "http://206.135.55.224:999",
    "http://185.11.134.227:8443",
]
current_proxy = "http://206.135.55.224:999"
proxy_config = GenericProxyConfig(http_url=current_proxy, https_url=current_proxy)
ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
transcript_list = ytt_api.list(korean_vids[0])
transcript = transcript_list.find_generated_transcript(["ko"])
translated = transcript.translate("ta")
translated_result = translated.fetch()
print(translated_result)
