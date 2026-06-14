import requests
from bs4 import BeautifulSoup
"""
scrapes free-proxy-list.net to get the free proxies and writes it to a txt file `./proxies/input/free-proxy-list.txt`
"""

def get_free_proxy_list():
    response = requests.get("https://free-proxy-list.net/en/")
    soup = BeautifulSoup(response.text, "html.parser")
    result = soup.find("textarea").text.strip()
    lines = result.split("\n")
    free_proxy_list = set(lines[3:])
    return free_proxy_list


FREE_PROXY_LIST = get_free_proxy_list()
with open("./input/free-proxy-list.txt", "w", encoding="utf-8") as out_file:
    for proxy in FREE_PROXY_LIST:
        out_file.write(proxy + "\n")

