from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
FILE_PATH = PROJECT_DIR / "proxies" / "output" / "success_proxies.txt"

with open(FILE_PATH, "r", encoding="utf-8") as in_file:
    unique_success_proxies = {line.strip() for line in in_file if line.strip()}

print(f"Found {len(unique_success_proxies)} Successfully working proxies.")
print("writing only the unique proxies to success_proxies.txt")
with open(FILE_PATH, "w", encoding="utf-8") as out_file:
    for proxy in unique_success_proxies:
        out_file.write(proxy + "\n")