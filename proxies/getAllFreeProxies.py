import requests
from bs4 import BeautifulSoup
import time
from pathlib import Path

start_time = time.perf_counter()

extracted_proxies = set()
print("Starting to extract free proxies..")


def github_repo_scrape(url) -> None:
    response = requests.get(url)
    proxies = response.text.split("\n")
    for proxy in proxies:
        proxy = proxy.strip()
        if proxy not in extracted_proxies and not proxy.startswith("error"):
            extracted_proxies.add(proxy.strip())


url = "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS.txt"
response = requests.get(url)
splitted_lines = response.text.split("\n")
for line in splitted_lines[12:]:
    line_splitted = line.split(" ")
    proxy = line_splitted[1]
    if proxy.strip() not in extracted_proxies:
        extracted_proxies.add(proxy.strip())

urls = [
    "https://raw.githubusercontent.com/mmpx12/proxy-list/refs/heads/master/http.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/refs/heads/master/https.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
]

for url in urls:
    github_repo_scrape(url)


def get_free_proxy_list():
    response = requests.get("https://free-proxy-list.net/en/")
    soup = BeautifulSoup(response.text, "html.parser")
    result = soup.find("textarea").text.strip()
    lines = result.split("\n")
    free_proxy_list = set(lines[3:])
    return free_proxy_list


FREE_PROXY_LIST = get_free_proxy_list()
for proxy in FREE_PROXY_LIST:
    if proxy.strip() not in extracted_proxies:
        extracted_proxies.add(proxy.strip())

SCRIPT_DIR = Path(__file__).resolve().parent
output_file_path = SCRIPT_DIR / "input" / "all_free_proxy_list.txt"
with open(output_file_path, "w", encoding="utf-8") as out_file:
    for proxy in extracted_proxies:
        out_file.write(proxy + "\n")

end_time = time.perf_counter()
total_time = end_time - start_time

print(f"Finished extracting {len(extracted_proxies)} proxies in {total_time:.2f}s")
