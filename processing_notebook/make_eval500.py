"""Make stratified eval_500 for Step-1 benchmark (ponytail: stdlib only, seed 42)."""

import json
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC = PROJECT_ROOT / "intermediate-results" / "already_processed_transcripts.jsonl"
DST = SCRIPT_DIR / "eval_500.jsonl"
SEED = 42
N_HITS = 25
N_EMPTY = 475


def has_names(extract) -> bool:
    if not isinstance(extract, dict):
        return False
    return bool(extract.get("tamil")) or bool(extract.get("english"))


def main() -> None:
    random.seed(SEED)
    hits, empties = [], []
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            (hits if has_names(d.get("extract")) else empties).append(d)
    print(f"pool: hits={len(hits)} empties={len(empties)}")
    # spread across videos: shuffle then take (avoids one-video dominance)
    random.shuffle(hits)
    random.shuffle(empties)
    eval_rows = hits[:N_HITS] + empties[:N_EMPTY]
    random.shuffle(eval_rows)
    assert len(eval_rows) == N_HITS + N_EMPTY, len(eval_rows)
    assert sum(1 for r in eval_rows if has_names(r.get("extract"))) == N_HITS
    with open(DST, "w", encoding="utf-8") as out:
        for r in eval_rows:
            json.dump(
                {
                    "video_id": r["video_id"],
                    "text": r["text"],
                    "start": r.get("start"),
                    "duration": r.get("duration"),
                    "ref_extract": r.get("extract", {"tamil": [], "english": []}),
                },
                out,
                ensure_ascii=False,
            )
            out.write("\n")
    vids = len({r["video_id"] for r in eval_rows})
    print(f"wrote {DST} rows={len(eval_rows)} videos={vids} seed={SEED}")


if __name__ == "__main__":
    main()
