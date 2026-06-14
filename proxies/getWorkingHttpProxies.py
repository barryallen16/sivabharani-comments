from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
import os
from tqdm import tqdm
from pathlib import Path

"""
filter the proxies that work for yt api in normal sequencial manner
"""
output_dir = "output"
with open("./input/results-http.txt", "r", encoding="utf-8") as in_file:
    PROXY_LIST = [f"http://{line.strip()}" for line in in_file if line.strip()]

video_id = "qyEEVWy6FZ8"
working_proxies = set()
not_working_proxies = set()

for current_proxy in tqdm(PROXY_LIST, desc="Checking proxies", unit="proxy"):
    proxy_config = GenericProxyConfig(http_url=current_proxy, https_url=current_proxy)
    ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
    try:
        if hasattr(ytt_api, "_http_client"):
            ytt_api._http_client.timeout = 3.0
        transcript_list = ytt_api.list(video_id)
        working_proxies.add(current_proxy)
    except Exception as e:
        not_working_proxies.add(current_proxy)

with open(
    Path.joinpath(output_dir, "working_http_proxies.txt"), "a", encoding="utf-8"
) as out_file:
    for proxy in working_proxies:
        out_file.write(proxy + "\n")
with open(
    Path.joinpath(output_dir, "not_working_http_proxies.txt"), "a", encoding="utf-8"
) as out_file:
    for proxy in not_working_proxies:
        out_file.write(proxy + "\n")
