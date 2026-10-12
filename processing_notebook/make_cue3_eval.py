"""Build eval_cue3.jsonl: 15 cue-3 + 15 cue-4 windows for hand labeling.

Cue-3 = சொல்லிருக்காரு* (name + enna solli irukkaaru), 15 rows.
Cue-4 = சொல்லிருக்காங்க* (name + enna solli irukkaanga na), 15 rows.
Distinct videos per cue, excluding the 4 regression videos in
make_handle_eval.py for coverage. silver=null for human labeling.
ponytail: reuses make_handle_eval helpers, stdlib only, seed 42.
"""

import json
import random
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from make_handle_eval import HALF_WINDOW, load_raw, txt, window  # noqa: E402

DST = SCRIPT_DIR / "eval_cue3.jsonl"
SEED = 42
N_EACH = 15

CUE3 = "சொல்லிருக்காரு"
CUE4 = "சொல்லிருக்காங்க"
REGRESSION_VIDS = {"XId8oORl0iE", "h97k-dSt_98", "bHp-SDnsnS8", "DJsfWQc9xWg"}


def sample(raw, cue, n, taken_vids):
    pool = []
    for vid, chunks in raw.items():
        if vid in REGRESSION_VIDS or vid in taken_vids:
            continue
        for i, c in enumerate(chunks):
            if cue in txt(c):
                pool.append((vid, i))
                break
    assert len(pool) >= n, f"cue {cue}: only {len(pool)} videos"
    return random.sample(pool, n)


def main():
    random.seed(SEED)
    raw = load_raw()
    rows, taken = [], set()
    for cue in (CUE3, CUE4):
        for vid, i in sample(raw, cue, N_EACH, taken):
            taken.add(vid)
            rows.append({
                "video_id": vid, "center_start": raw[vid][i]["start"],
                "window": window(raw[vid], i),
                "cue": "cue3" if cue == CUE3 else "cue4",
                "silver": None,
            })
    random.shuffle(rows)
    with open(DST, "w", encoding="utf-8") as out:
        for r in rows:
            json.dump(r, out, ensure_ascii=False)
            out.write("\n")
    print(f"wrote {DST} rows={len(rows)} cue3={N_EACH} cue4={N_EACH}")


if __name__ == "__main__":
    main()
