"""Build eval_handles.jsonl: handle-focused eval with +/-2 chunk windows.

Regression rows carry silver labels from 4-video analysis (verify by
listening); random rows have silver=null for human labeling.
Label schema: commenter_* = handle BEFORE the cue; mentioned = names
inside the comment body (cricketers, crew, addressee); junk otherwise.
ponytail: stdlib only, seed 42.
"""

import json
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC = PROJECT_ROOT / "transcripts" / "output" / "tamil_transcripts.jsonl"
DST = SCRIPT_DIR / "eval_handles.jsonl"
SEED = 42
N_CUE = 30
N_PLAIN = 20
HALF_WINDOW = 2

# (video_id, center_start, commenter_tamil, commenter_english, mentioned, note)
REGRESSION = [
    ("XId8oORl0iE", 1057.0, ["சிவகாசி விஜய்"], ["sivakasivijay"], [], "compound handle in prev chunk"),
    ("XId8oORl0iE", 697.8, ["SK"], ["sk"], [], "initials handle in prev chunk"),
    ("XId8oORl0iE", 124.0, [], [], [], "garbled handle, needs human listen"),
    ("XId8oORl0iE", 774.2, [], [], [], "no handle, just 'oru nanbar'"),
    ("XId8oORl0iE", 943.0, [], [], [], "handle 2+ chunks earlier, tests window width"),
    ("XId8oORl0iE", 914.2, ["விக்கி"], ["vikki"], [], "same-chunk good case"),
    ("XId8oORl0iE", 290.5, ["கவின்"], ["kavin"], [], "same-chunk good case"),
    ("bHp-SDnsnS8", 390.0, ["NHR 6259"], ["nhr6259"], [], "digit handle read aloud"),
    ("bHp-SDnsnS8", 491.0, ["பொன்ராஜ்"], ["ponraj"], [], "same-chunk good case"),
    ("bHp-SDnsnS8", 699.4, ["வினோத்"], ["vinoth"], [], "same-chunk good case"),
    ("bHp-SDnsnS8", 819.0, ["சதீஷ் துரைசாமி"], ["sathishduraisamy"], ["சிவாபுரன் கௌதம்"], "addressee trap: SBUS himself in body"),
    ("bHp-SDnsnS8", 1399.0, ["டார்க் ஹன்டர்"], ["darkhunter"], [], "common-word compound"),
    ("DJsfWQc9xWg", 977.2, [], [], ["சாய் சுதர்சன்", "கில்"], "cricketers, not commenters"),
    ("DJsfWQc9xWg", 1926.2, [], [], ["அஸ்வத்"], "crew, not commenter"),
    ("DJsfWQc9xWg", 1202.5, [], [], ["மாதவ்"], "story person, not commenter"),
    ("DJsfWQc9xWg", 222.0, [], [], ["பரத்"], "co-host, not commenter"),
    ("h97k-dSt_98", 0.1, [], [], [], "scenery, no Q&A"),
]

CUE_WORDS = ("நண்பர்", "கமெண்ட்", "கமென்ட்", "ப்ரோ", "கேக்குற", "அப்படிங்கற", "அப்படிங்கிற")


def txt(c):
    return c.get("text", c.get(" text", ""))


def load_raw():
    raw = {}
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                raw.update(d)
    return raw


def find_idx(chunks, start):
    best, best_d = None, 1e9
    for i, c in enumerate(chunks):
        dd = abs(c["start"] - start)
        if dd < best_d:
            best, best_d = i, dd
    assert best_d < 0.05, f"start {start} not found"
    return best


def window(chunks, ci):
    lo, hi = max(0, ci - HALF_WINDOW), min(len(chunks), ci + HALF_WINDOW + 1)
    return [{"start": chunks[i]["start"], "text": txt(chunks[i])} for i in range(lo, hi)]


def main():
    random.seed(SEED)
    raw = load_raw()
    rows = []
    for vid, start, ct, ce, men, note in REGRESSION:
        chunks = raw[vid]
        ci = find_idx(chunks, start)
        rows.append({
            "video_id": vid, "center_start": start, "window": window(chunks, ci),
            "silver": {"commenter_tamil": ct, "commenter_english": ce,
                       "mentioned": men, "note": note},
        })
    reg_keys = {(vid, start) for vid, start, *_ in REGRESSION}
    cue_pool, plain_pool = [], []
    for vid, chunks in raw.items():
        for i, c in enumerate(chunks):
            if (vid, c["start"]) in reg_keys:
                continue
            (cue_pool if any(k in txt(c) for k in CUE_WORDS) else plain_pool).append((vid, i))
    for vid, i in random.sample(cue_pool, N_CUE) + random.sample(plain_pool, N_PLAIN):
        rows.append({"video_id": vid, "center_start": raw[vid][i]["start"],
                     "window": window(raw[vid], i), "silver": None})
    random.shuffle(rows)
    with open(DST, "w", encoding="utf-8") as out:
        for r in rows:
            json.dump(r, out, ensure_ascii=False)
            out.write("\n")
    n_silver = sum(1 for r in rows if r["silver"])
    print(f"wrote {DST} rows={len(rows)} regression={n_silver} unlabeled={len(rows) - n_silver}")


if __name__ == "__main__":
    main()
