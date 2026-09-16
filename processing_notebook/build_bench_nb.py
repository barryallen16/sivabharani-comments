"""Build bench-eval500-ner-e4b.kaggle.ipynb (run once, then delete me)."""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "bench-eval500-ner-e4b.kaggle.ipynb"

SYS = (
    "Extract person names from Tamil text. Reply JSON only: "
    '{"tamil": [...], "english": [...]}. Empty lists if none.\n'
    "Example: Input: \u0bb5\u0ba3\u0b95\u0bcd\u0b95\u0bae\u0bcd, "
    "\u0ba8\u0bbe\u0ba9\u0bcd \u0b9a\u0bc2\u0bb0\u0bcd\u0baf\u0bbe. "
    'Output: {"tamil": ["\u0b9a\u0bc2\u0bb0\u0bcd\u0baf\u0bbe"], '
    '"english": ["Surya"]}\n'
    "Input: {TEXT}\nOutput:"
)


def cell(source, tags=None):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"tags": tags} if tags else {},
        "outputs": [],
        "source": source,
    }


cells = [
    cell(
        [
            "import os as _ka_os2\n",
            'WORKING_DIR = "/kaggle/working" if _ka_os2.path.exists("/kaggle/working") else _ka_os2.getcwd()\n',
            'SCRATCH_DIR = "/kaggle/tmp" if _ka_os2.path.exists("/kaggle/tmp") else _ka_os2.getcwd()\n',
        ],
        tags=["kaggle-automation-dirs"],
    ),
    cell(
        [
            "import sys as _ka_sys\n",
            "try:\n",
            "    _ka_sys.stdout.reconfigure(line_buffering=True)\n",
            "    _ka_sys.stderr.reconfigure(line_buffering=True)\n",
            "except Exception:\n",
            "    pass\n",
        ],
        tags=["kaggle-automation-buffering"],
    ),
]

cells.append(
    cell(
        [
            "%%capture\n",
            "import os, re\n",
            "import torch\n",
            '_tm = re.match(r"[\\d]{1,}\\.[\\d]{1,}", str(torch.__version__))\n',
            '_tv = _tm.group(0) if _tm else "2.8"\n',
            "xformers = 'xformers==' + {'2.10': '0.0.34', '2.9': '0.0.33.post1', '2.8': '0.0.32.post2'}.get(_tv, \"0.0.34\")\n",
            "!uv pip install --system sentencepiece protobuf datasets huggingface_hub hf_transfer\n",
            "!uv pip install --system --no-deps unsloth_zoo bitsandbytes accelerate {xformers} peft trl triton unsloth\n",
            "!uv pip install --system --no-deps --upgrade torchao\n",
            "!uv pip install --system --no-deps transformers tokenizers\n",
            "!uv pip install --system torchcodec\n",
            "import torch; torch._dynamo.config.recompile_limit = 64;\n",
        ]
    )
)

cells.append(
    cell(
        [
            "import os\n",
            "os.makedirs(SCRATCH_DIR, exist_ok=True)\n",
            "os.makedirs(WORKING_DIR, exist_ok=True)\n",
            "!wget -O {SCRATCH_DIR}/eval_500.jsonl https://github.com/barryallen16/sivabharani-comments/raw/refs/heads/main/processing_notebook/eval_500.jsonl\n",
            "!wc -l {SCRATCH_DIR}/eval_500.jsonl\n",
        ]
    )
)

LOAD_SRC = [
    "import torch\n",
    "print(f\"gpus={torch.cuda.device_count()}\", flush=True)\n",
    "assert torch.cuda.device_count() > 0, \"need T4 x2\"\n",
    "from transformers import pipeline\n",
    "ner = pipeline(\"token-classification\", model=\"ai4bharat/IndicNER\", aggregation_strategy=\"simple\", device=0)\n",
    "def ner_has_person(text):\n",
    "    try:\n",
    "        ents = ner(text)\n",
    "    except Exception:\n",
    "        return True\n",
    "    return any(\"PER\" in e.get(\"entity_group\", \"\") for e in ents)\n",
    "from unsloth import FastModel\n",
    "model, tokenizer = FastModel.from_pretrained(model_name=\"unsloth/gemma-4-E4B-it\", dtype=None, max_seq_length=1024, load_in_4bit=True, full_finetuning=False)\n",
    "print(\"models loaded\", flush=True)\n",
]

RUN_SRC = [
    "import json, time\n",
    "SYS = ('Extract person names from Tamil text. Reply JSON only: {\"tamil\": [...], \"english\": [...]}. Empty lists if none.\\n'\n",
    "'Example: Input: வணக்கம், நான் சூர்யா. Output: {\"tamil\": [\"சூர்யா\"], \"english\": [\"Surya\"]}\\n'\n",
    "'Input: {TEXT}\\nOutput:')\n",
    "def e4b_extract(text):\n",
    "    prompt = SYS.replace(\"{TEXT}\", text)\n",
    "    msgs = [{\"role\": \"user\", \"content\": [{\"type\": \"text\", \"text\": prompt}]}]\n",
    "    inputs = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors=\"pt\").to(\"cuda\")\n",
    "    out = model.generate(**inputs, max_new_tokens=64, do_sample=False)\n",
    "    gen = tokenizer.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)\n",
    "    cleaned = gen.replace(\"json\", \"\").replace(\"```\", \"\").strip()\n",
    "    try:\n",
    "        return json.loads(cleaned), False\n",
    "    except Exception:\n",
    "        return {\"tamil\": [], \"english\": []}, True\n",
    "def has_names(ex):\n",
    "    return bool(ex.get(\"tamil\")) or bool(ex.get(\"english\"))\n",
    "rows = [json.loads(l) for l in open(SCRATCH_DIR + \"/eval_500.jsonl\", encoding=\"utf-8\") if l.strip()]\n",
    "print(f\"eval rows={len(rows)}\", flush=True)\n",
    "t0 = time.perf_counter()\n",
    "ner_flags = [ner_has_person(r[\"text\"]) for r in rows]\n",
    "ner_secs = time.perf_counter() - t0\n",
    "print(f\"NER pass: {ner_secs:.1f}s\", flush=True)\n",
    "torch.cuda.reset_peak_memory_stats()\n",
]

RUN_SRC += [
    "preds = []\n",
    "t1 = time.perf_counter()\n",
    "e4b_calls = 0\n",
    "fails = 0\n",
    "for r, flag in zip(rows, ner_flags):\n",
    "    if flag:\n",
    "        ph, f = e4b_extract(r[\"text\"])\n",
    "        e4b_calls += 1\n",
    "        fails += f\n",
    "    else:\n",
    "        ph = {\"tamil\": [], \"english\": []}\n",
    "    pn = {\"tamil\": [\"?\"], \"english\": [\"?\"]} if flag else {\"tamil\": [], \"english\": []}\n",
    "    preds.append((pn, ph))\n",
    "hybrid_secs = time.perf_counter() - t1\n",
    "print(f\"hybrid LLM: {hybrid_secs:.1f}s calls={e4b_calls} fails={fails}\", flush=True)\n",
    "t2 = time.perf_counter()\n",
    "preds_all = []\n",
    "fails_all = 0\n",
    "for r in rows:\n",
    "    p, f = e4b_extract(r[\"text\"])\n",
    "    preds_all.append(p)\n",
    "    fails_all += f\n",
    "e4b_secs = time.perf_counter() - t2\n",
    "vram_gb = torch.cuda.max_memory_allocated() / 1e9\n",
    "print(f\"e4b-only: {e4b_secs:.1f}s fails={fails_all} vram={vram_gb:.1f}GB\", flush=True)\n",
]

MET_SRC = [
    "def score(pairs):\n",
    "    tp = fp = fn = tem = een = 0\n",
    "    for ref, p in pairs:\n",
    "        rh, ph = has_names(ref), has_names(p)\n",
    "        tp += rh and ph\n",
    "        fp += (not rh) and ph\n",
    "        fn += rh and (not ph)\n",
    "        if rh and ph:\n",
    "            tem += p.get(\"tamil\") == ref.get(\"tamil\")\n",
    "            een += p.get(\"english\") == ref.get(\"english\")\n",
    "    pr = tp / (tp + fp) if tp + fp else 0.0\n",
    "    rc = tp / (tp + fn) if tp + fn else 0.0\n",
    "    f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0\n",
    "    return {\"P\": round(pr, 3), \"R\": round(rc, 3), \"F1\": round(f1, 3), \"tamil_exact\": tem, \"eng_exact\": een}\n",
    "m = {\n",
    "    \"ner\": score([(r[\"ref_extract\"], pn) for r, (pn, ph) in zip(rows, preds)]),\n",
    "    \"hybrid\": score([(r[\"ref_extract\"], ph) for r, (pn, ph) in zip(rows, preds)]),\n",
    "    \"e4b_only\": score([(r[\"ref_extract\"], p) for r, p in zip(rows, preds_all)]),\n",
    "}\n",
    "m[\"time\"] = {\"ner_secs\": round(ner_secs, 1), \"hybrid_llm_secs\": round(hybrid_secs, 1), \"e4b_all_secs\": round(e4b_secs, 1), \"e4b_calls_hybrid\": e4b_calls, \"fails_hybrid\": fails, \"fails_e4b\": fails_all, \"vram_gb\": round(vram_gb, 2)}\n",
    "print(json.dumps(m, indent=1), flush=True)\n",
    "with open(WORKING_DIR + \"/eval_metrics.json\", \"w\", encoding=\"utf-8\") as f:\n",
    "    json.dump(m, f, ensure_ascii=False, indent=1)\n",
    "with open(WORKING_DIR + \"/eval_preds.jsonl\", \"w\", encoding=\"utf-8\") as f:\n",
    "    for r, (pn, ph), pa in zip(rows, preds, preds_all):\n",
    "        json.dump({\"video_id\": r[\"video_id\"], \"text\": r[\"text\"], \"ref\": r[\"ref_extract\"], \"ner\": pn, \"hybrid\": ph, \"e4b\": pa}, f, ensure_ascii=False)\n",
    "        f.write(\"\\n\")\n",
    "print(\"saved eval_metrics.json + eval_preds.jsonl\", flush=True)\n",
]

cells += [cell(LOAD_SRC), cell(RUN_SRC), cell(MET_SRC)]
nb = {
    "cells": cells,
    "metadata": {
        "kaggle": {"accelerator": "NvidiaTeslaT4", "isGpuEnabled": True, "isInternetEnabled": True, "language": "python"},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12.13"},
    },
    "nbformat": 4,
    "nbformat_minor": 4,
}
OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"wrote {OUT} cells={len(cells)}")
