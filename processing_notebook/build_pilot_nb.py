"""Build pilot-handles-v2.kaggle.ipynb: prompt-v2 pilot on 17 regression windows.

Self-contained: regression rows embedded inline (8KB), no download needed.
Same model as bench (unsloth/gemma-3-4b-it) for comparability.
ponytail: mirrors build_bench_nb.py conventions (tags, uv installs, cleanup).
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUT = SCRIPT_DIR / "pilot-handles-v2.kaggle.ipynb"
SRC = SCRIPT_DIR / "eval_handles.jsonl"
TITLE = "Pilot handles v2"


def cell(source, tags=None):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"tags": tags} if tags else {},
        "outputs": [],
        "source": source,
    }


SYS_LINES = [
    "SYS = ('Identify the commenter whose comment is read aloud in this Tamil transcript window. Reply JSON only: {\"commenter_tamil\": [...], \"commenter_english\": [...], \"mentioned\": [...]}. Empty lists if none.\\n'\n",
    "'Rules: the commenter handle appears BEFORE cue words like \\u0b85\\u0baa\\u0bcd\\u0baa\\u0b9f\\u0bbf\\u0b99\\u0bcd\\u0b95\\u0bb1/\\u0b85\\u0baa\\u0bcd\\u0baa\\u0b9f\\u0bbf\\u0b99\\u0bcd\\u0b95\\u0bbf\\u0bb1 \\u0ba8\\u0ba3\\u0bcd\\u0baa\\u0bb0\\u0bcd \\u0bb5\\u0ba8\\u0bcd\\u0ba4\\u0bc1, \\u0b95\\u0bc7\\u0b95\\u0bcd\\u0b95\\u0bc1\\u0bb1\\u0bbe\\u0bb0\\u0bc1. Extract that span.\\n'\n",
    "'Keep the WHOLE handle verbatim even if compound: brand+name, place+name, English words, initials, digits. Never truncate to one part. Keep digits.\\n'\n",
    "'commenter_english is the most likely original handle spelling, lowercase, no spaces. mentioned holds names AFTER the cue (players, crew, the host) - never put them in commenter.\\n'\n",
    "'Never output tech words alone, greetings, verbs, or common words (iphone, processor, snapdragon, ram, bro, hello, guys).\\n'\n",
    "'Only extract spans verbatim in the Input. Never copy names from these examples.\\n'\n",
    "'Example: Input: \\u0bb5\\u0ba8\\u0bcd\\u0ba4\\u0bc1 \\u0baa\\u0bbe\\u0ba4\\u0bcd\\u0ba4\\u0bc0\\u0b99\\u0bcd\\u0b95\\u0ba9\\u0bcd\\u0ba9\\u0bbe \\u0b9a\\u0bbf\\u0bb5\\u0b95\\u0bbe\\u0b9a\\u0bbf \\u0bb5\\u0bbf\\u0b9c\\u0baf\\u0bcd / \\u0b85\\u0baa\\u0bcd\\u0baa\\u0b9f\\u0bbf\\u0b99\\u0bcd\\u0b95\\u0bb1 \\u0ba8\\u0ba3\\u0bcd\\u0baa\\u0bb0\\u0bcd \\u0bb5\\u0ba8\\u0bcd\\u0ba4\\u0bc1 Samsung S25 Output: {\"commenter_tamil\": [\"\\u0b9a\\u0bbf\\u0bb5\\u0b95\\u0bbe\\u0b9a\\u0bbf \\u0bb5\\u0bbf\\u0b9c\\u0baf\\u0bcd\"], \"commenter_english\": [\"sivakasivijay\"], \"mentioned\": []}\\n'\n",
    "'Example: Input: \\u0b85\\u0b9f\\u0bc1\\u0ba4\\u0bcd\\u0ba4\\u0bc1 \\u0baa\\u0bcd\\u0bb0\\u0bcb NHR 6259 \\u0b85\\u0baa\\u0bcd\\u0baa\\u0b9f\\u0bbf\\u0b99\\u0bcd\\u0b95\\u0bb1 \\u0ba8\\u0ba3\\u0bcd\\u0baa\\u0bb0\\u0bcd / \\u0bb5\\u0ba8\\u0bcd\\u0ba4\\u0bc1 \\u0b90\\u0bae\\u0bcd \\u0baf\\u0bc2\\u0b9a\\u0bbf\\u0b99\\u0bcd Xiaomi 15 Output: {\"commenter_tamil\": [\"NHR 6259\"], \"commenter_english\": [\"nhr6259\"], \"mentioned\": []}\\n'\n",
    "'Example: Input: \\u0b9a\\u0ba4\\u0bc0\\u0bb7\\u0bcd \\u0ba4\\u0bc1\\u0bb0\\u0bc8\\u0b9a\\u0bbe\\u0bae\\u0bbf \\u0b85\\u0baa\\u0bcd\\u0baa\\u0b9f\\u0bbf\\u0b99\\u0bcd\\u0b95\\u0bb1 / \\u0ba8\\u0ba3\\u0bcd\\u0baa\\u0bb0\\u0bcd \\u0bb5\\u0ba8\\u0bcd\\u0ba4\\u0bc1 \\u0b9f\\u0bbf\\u0baf\\u0bb0\\u0bcd \\u0b9a\\u0bbf\\u0bb5\\u0bbe\\u0baa\\u0bc1\\u0bb0\\u0ba9\\u0bcd \\u0b95\\u0bcc\\u0ba4\\u0bae\\u0bcd \\u0baa\\u0bcd\\u0bb0\\u0bcb Output: {\"commenter_tamil\": [\"\\u0b9a\\u0ba4\\u0bc0\\u0bb7\\u0bcd \\u0ba4\\u0bc1\\u0bb0\\u0bc8\\u0b9a\\u0bbe\\u0bae\\u0bbf\"], \"commenter_english\": [\"sathishduraisamy\"], \"mentioned\": [\"\\u0b9a\\u0bbf\\u0bb5\\u0bbe\\u0baa\\u0bc1\\u0bb0\\u0ba9\\u0bcd \\u0b95\\u0bcc\\u0ba4\\u0bae\\u0bcd\"]}\\n'\n",
    "'Example: Input: \\u0b87\\u0bb2\\u0bcd\\u0bb2 \\u0b9a\\u0bbe\\u0baf\\u0bcd \\u0b9a\\u0bc1\\u0ba4\\u0bb0\\u0bcd\\u0b9a\\u0ba9\\u0bc1\\u0bae\\u0bcd \\u0b95\\u0bbf\\u0bb2\\u0bcd\\u0bb2\\u0bc1\\u0bae\\u0bcd / \\u0b87\\u0bb1\\u0b99\\u0bcd\\u0b95\\u0bc1\\u0ba9\\u0bbe\\u0b99\\u0bcd\\u0b95\\u0ba9\\u0bbe\\u0bb2\\u0bc7 Output: {\"commenter_tamil\": [], \"commenter_english\": [], \"mentioned\": [\"\\u0b9a\\u0bbe\\u0baf\\u0bcd \\u0b9a\\u0bc1\\u0ba4\\u0bb0\\u0bcd\\u0b9a\\u0ba9\\u0bcd\", \"\\u0b95\\u0bbf\\u0bb2\\u0bcd\"]}\\n'\n",
    "'Example: Input: \\u0baa\\u0bcd\\u0bb0\\u0bcb iphone processor \\u0ba8\\u0bb2\\u0bcd\\u0bb2\\u0bbe \\u0b87\\u0bb0\\u0bc1\\u0b95\\u0bcd\\u0b95\\u0bc1. Output: {\"commenter_tamil\": [], \"commenter_english\": [], \"mentioned\": []}\\n'\n",
    "'Input: {TEXT}\\nOutput:')\n",
]

INSTALL_SRC = [
    "%%capture\n",
    "import os, re\n",
    "import torch\n",
    '_tm = re.match(r"[\\d]{1,}\\.[\\d]{1,}", str(torch.__version__))\n',
    '_tv = _tm.group(0) if _tm else "2.8"\n',
    "xformers = 'xformers==' + {'2.10': '0.0.34', '2.9': '0.0.33.post1', '2.8': '0.0.32.post2'}.get(_tv, \"0.0.34\")\n",
    "!uv pip install --system sentencepiece protobuf datasets huggingface_hub hf_transfer\n",
    "!uv pip install --system --no-deps unsloth_zoo bitsandbytes accelerate {xformers} peft trl triton unsloth\n",
    "!uv pip install --system --no-deps --upgrade torchao\n",
    "!uv pip install --system --upgrade --no-deps transformers==5.5.0 \"tokenizers>=0.22.0,<=0.23.0\"\n",
    "!uv pip install --system torchcodec\n",
    "import torch; torch._dynamo.config.recompile_limit = 64;\n",
]

LOAD_SRC = [
    "import torch\n",
    "print(f\"gpus={torch.cuda.device_count()}\", flush=True)\n",
    "assert torch.cuda.device_count() > 0, \"need T4 x2\"\n",
    "from unsloth import FastModel\n",
    "model, tokenizer = FastModel.from_pretrained(model_name=\"unsloth/gemma-3-4b-it\", dtype=None, max_seq_length=1024, load_in_4bit=True, full_finetuning=False)\n",
    "print(\"model loaded\", flush=True)\n",
]

SCORE_SRC = [
    "import json\n",
    "def norm_eng(s):\n",
    "    return \"\".join(ch for ch in s.lower() if ch.isalnum())\n",
    "def score_rows(rows, preds):\n",
    "    agg = {\"n\": 0, \"commenter_exact\": 0, \"english_match\": 0, \"exp_handles\": 0, \"leak\": 0, \"fp\": 0, \"clean_empty\": 0, \"empty_total\": 0}\n",
    "    details = []\n",
    "    for r, p in zip(rows, preds):\n",
    "        s = r[\"silver\"]\n",
    "        exp_c, exp_e, exp_m = s[\"commenter_tamil\"], s[\"commenter_english\"], s[\"mentioned\"]\n",
    "        got_c = p.get(\"commenter_tamil\", [])\n",
    "        got_e = p.get(\"commenter_english\", [])\n",
    "        has_exp = bool(exp_c)\n",
    "        exact = got_c == exp_c\n",
    "        eng = [norm_eng(x) for x in got_e] == [norm_eng(x) for x in exp_e]\n",
    "        leak = bool(set(got_c) & set(exp_m))\n",
    "        agg[\"n\"] += 1\n",
    "        agg[\"commenter_exact\"] += exact\n",
    "        if has_exp:\n",
    "            agg[\"exp_handles\"] += 1\n",
    "            agg[\"english_match\"] += eng\n",
    "        else:\n",
    "            agg[\"empty_total\"] += 1\n",
    "            agg[\"clean_empty\"] += not got_c\n",
    "            agg[\"fp\"] += bool(got_c) and not leak\n",
    "        agg[\"leak\"] += leak\n",
    "        details.append({\"video_id\": r[\"video_id\"], \"center\": r[\"center_start\"], \"exact\": exact, \"eng\": eng, \"leak\": leak, \"pred\": p, \"note\": s[\"note\"]})\n",
    "    return agg, details\n",
]


def main():
    with open(SRC, encoding="utf-8") as f:
        reg = [json.loads(l) for l in f if l.strip() and json.loads(l)["silver"]]
    assert len(reg) == 17, len(reg)

    data_src = (
        ["import json\n", f"REG = {json.dumps(reg, ensure_ascii=False)}\n", "print(f\"regression rows={len(REG)}\", flush=True)\n", "assert len(REG) == 17\n"]
        + SYS_LINES
        + [
            "def build_prompt(row):\n",
            "    window_text = \" / \".join(w[\"text\"] for w in row[\"window\"])\n",
            "    return SYS.replace(\"{TEXT}\", window_text)\n",
        ]
    )

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
        cell(
            [
                "import os as _ka_os\n",
                "def _gsv(name, default=None, cast=None):\n",
                "    v = globals().get(name)\n",
                "    if v is not None:\n",
                "        return v\n",
                "    e = _ka_os.environ.get(name)\n",
                "    if e is None or not str(e).strip():\n",
                "        return default\n",
                "    try:\n",
                "        return cast(e) if cast else e\n",
                "    except (TypeError, ValueError):\n",
                "        return default\n",
                "SHARD_ID = _gsv('SHARD_ID', 0, cast=int)\n",
                "TOTAL_SHARDS = _gsv('TOTAL_SHARDS', 1, cast=int)\n",
                "print(f\"shard={SHARD_ID}/{TOTAL_SHARDS}\", flush=True)\n",
            ],
            tags=["kaggle-automation-shard-fallback"],
        ),
        cell(INSTALL_SRC),
        cell(LOAD_SRC),
        cell(data_src),
        cell(SCORE_SRC),
        cell(
            [
                "import json, time\n",
                "OUTPUT_PATH = WORKING_DIR + f\"/pilot_handles_v2_shard{SHARD_ID}.jsonl\"\n",
                "def llm_extract(text):\n",
                "    prompt = SYS.replace(\"{TEXT}\", text)\n",
                "    msgs = [{\"role\": \"user\", \"content\": [{\"type\": \"text\", \"text\": prompt}]}]\n",
                "    try:\n",
                "        _dev = model.language_model.embed_tokens.weight.device\n",
                "    except Exception:\n",
                "        _dev = \"cuda:0\"\n",
                "    inputs = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors=\"pt\").to(_dev)\n",
                "    out = model.generate(**inputs, max_new_tokens=128, do_sample=False)\n",
                "    gen = tokenizer.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)\n",
                "    cleaned = gen.replace(\"json\", \"\").replace(\"```\", \"\").strip()\n",
                "    try:\n",
                "        p = json.loads(cleaned)\n",
                "        return {\"commenter_tamil\": p.get(\"commenter_tamil\", []), \"commenter_english\": p.get(\"commenter_english\", []), \"mentioned\": p.get(\"mentioned\", [])}, False\n",
                "    except Exception:\n",
                "        return {\"commenter_tamil\": [], \"commenter_english\": [], \"mentioned\": []}, True\n",
                "t0 = time.perf_counter()\n",
                "preds, fails = [], 0\n",
                "out = open(OUTPUT_PATH, \"w\", encoding=\"utf-8\")\n",
                "for ri, r in enumerate(REG):\n",
                "    wtext = \" / \".join(w[\"text\"] for w in r[\"window\"])\n",
                "    p, f = llm_extract(wtext)\n",
                "    fails += f\n",
                "    preds.append(p)\n",
                "    json.dump({\"video_id\": r[\"video_id\"], \"center_start\": r[\"center_start\"], \"pred\": p, \"silver\": r[\"silver\"]}, out, ensure_ascii=False)\n",
                "    out.write(\"\\n\")\n",
                "    print(f\"{ri + 1}/{len(REG)} fail={f} pred={json.dumps(p, ensure_ascii=False)}\", flush=True)\n",
                "out.close()\n",
                "agg, details = score_rows(REG, preds)\n",
                "agg[\"fails\"] = fails\n",
                "agg[\"secs\"] = round(time.perf_counter() - t0, 1)\n",
                "print(json.dumps(agg, indent=1, ensure_ascii=False), flush=True)\n",
                "with open(WORKING_DIR + \"/pilot_handles_v2_metrics.json\", \"w\", encoding=\"utf-8\") as mf:\n",
                "    json.dump({\"agg\": agg, \"details\": details}, mf, ensure_ascii=False, indent=1)\n",
                "print(f\"saved {OUTPUT_PATH}\", flush=True)\n",
            ]
        ),
        cell(
            [
                "import gc, shutil, os\n",
                "for _n in [\"model\", \"tokenizer\"]:\n",
                "    try:\n",
                "        del globals()[_n]\n",
                "    except KeyError:\n",
                "        pass\n",
                "gc.collect()\n",
                "try:\n",
                "    import torch\n",
                "    if torch.cuda.is_available():\n",
                "        torch.cuda.empty_cache()\n",
                "except Exception:\n",
                "    pass\n",
                "for _p in [os.path.expanduser(\"~/.cache/huggingface\"), os.path.expanduser(\"~/.cache/uv\"), \"/root/.cache/huggingface\"]:\n",
                "    try:\n",
                "        if os.path.isdir(_p):\n",
                "            shutil.rmtree(_p, ignore_errors=True)\n",
                "            print(f\"removed {_p}\", flush=True)\n",
                "    except Exception as _e:\n",
                "        print(f\"cleanup skip {_p}: {_e}\", flush=True)\n",
                "print(\"model files + caches removed; outputs kept\", flush=True)\n",
            ]
        ),
    ]
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


if __name__ == "__main__":
    main()
