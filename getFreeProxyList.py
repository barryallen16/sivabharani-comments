import requests
from bs4 import BeautifulSoup


def get_free_proxy_list():
    response = requests.get("https://free-proxy-list.net/en/")
    soup = BeautifulSoup(response.text, "html.parser")
    result = soup.find("textarea").text.strip()
    lines = result.split("\n")
    free_proxy_list = set(lines[3:])
    return free_proxy_list


FREE_PROXY_LIST = get_free_proxy_list()
with open("./proxies/free-proxy-list.txt", "w", encoding="utf-8") as out_file:
    for proxy in FREE_PROXY_LIST:
        out_file.write(proxy + "\n")
