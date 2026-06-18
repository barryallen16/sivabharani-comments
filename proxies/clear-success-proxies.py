import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FILE_DIR = SCRIPT_DIR / "output"
FILE_PATHS = ["success_proxies.txt", "new_success_proxies.txt"]

for FILE_PATH in FILE_PATHS:
    with open(SCRIPT_DIR / FILE_DIR / FILE_PATH, "w", encoding="utf-8") as in_file:
        pass
print(f"Cleared {len(FILE_PATHS)} proxy files.")