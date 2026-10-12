"""Build pilot-handles-v5.kaggle.ipynb: v5 cue-rule prompt on 47 rows.

47 rows = 17 regression (eval_handles.jsonl, silver non-null) + 30
hand-labeled cue3/cue4 (eval_cue3.jsonl), embedded inline, no download.
Same model as v2-v4 (unsloth/gemma-3-4b-it) for comparability.
Scorer reports combined agg plus reg/cue3 splits.
SYS examples are asserted equal to prompt-templates.md at build time.
ponytail: mirrors build_pilot_nb.py conventions (tags, uv installs, cleanup).
"""

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUT = SCRIPT_DIR / "pilot-handles-v5.kaggle.ipynb"
REG_SRC = SCRIPT_DIR / "eval_handles.jsonl"
CUE_SRC = SCRIPT_DIR / "eval_cue3.jsonl"
TITLE = "Pilot handles v5"


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
    "'A commenter name appears in ONE of these cue patterns (name FIRST, cue follows):\\n'\n",
    "'1. name + ப்ரோ. 2. bare name, no cue. 3. name + என்ன சொல்லிருக்காரு. 4. name + என்ன சொல்லிருக்காங்க. 5. name + வந்திருக்காது. 6. name + அப்படிங்கிற/அப்படிங்கற நண்பர் வந்து. 7. name + என்ன சொல்லிருக்கான். 8. name + என்ன கேட்டுருந்தாரு. 9. compound English username in Tamil script.\\n'\n",
    "'Rules: the cue word is நண்பர் (with ண). நம்பர் (with ம) means phone number - never extract it. Keep the WHOLE handle verbatim even if compound: brand+name, place+name, English words, initials, digits. Never truncate.\\n'\n",
    "'commenter_english is the most likely original handle spelling, lowercase, no spaces. mentioned holds names AFTER the cue or addressees (players, crew, co-host, சிவா) - never put them in commenter.\\n'\n",
    "'Never output product terms, greetings, verbs, or common words alone (iphone, processor, ப்ரோ, hello, guys). Only extract spans verbatim in the Input. Never copy names from these examples. If no name precedes a cue, return empty lists.\\n'\n",
    "'Example: Input: வந்து பாத்தீங்கன்னா சிவகாசி விஜய் / அப்படிங்கற நண்பர் வந்து Samsung S25 எட் Output: {\"commenter_tamil\": [\"சிவகாசி விஜய்\"], \"commenter_english\": [\"sivakasivijay\"], \"mentioned\": []}\\n'\n",
    "'Example: Input: கவின் என்ன சொல்லிருக்காருன்னா iPhone 16 / Pro வாங்கலாம்னு இருக்கேன் ப்ரோ Output: {\"commenter_tamil\": [\"கவின்\"], \"commenter_english\": [\"kavin\"], \"mentioned\": []}\\n'\n",
    "'Example: Input: பாத்தீங்கன்னா டார்க் ஹன்டர் அப்படிங்கற / நண்பர் வந்து ஹாய் சிவான் கௌதம் ப்ரோ Output: {\"commenter_tamil\": [\"டார்க் ஹன்டர்\"], \"commenter_english\": [\"darkhunter\"], \"mentioned\": [\"சிவான் கௌதம்\"]}\\n'\n",
    "'Example: Input: சொல்லுங்க. உங்க போன் நம்பர் சொல்லுங்க Output: {\"commenter_tamil\": [], \"commenter_english\": [], \"mentioned\": []}\\n'\n",
    "'Example: Input: நரசிம்மா அப்படின்னு சொல்லி நம்ம குரூப்ல / ஒரு நண்பருடா குரூப் / ஆமா அவரு சொல்லிருக்காரு Output: {\"commenter_tamil\": [\"நரசிம்மா\"], \"commenter_english\": [\"narasimha\"], \"mentioned\": []}\\n'\n",
    "'Example: Input: விடைபெற்று கொள்வது சிவபரணி நிரஞ்சன் விக்னேஷ் பாக்கலாங்க பாய் பாய் Output: {\"commenter_tamil\": [], \"commenter_english\": [], \"mentioned\": []}\\n'\n",
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
    "        details.append({\"set\": r[\"set\"], \"video_id\": r[\"video_id\"], \"center\": r[\"center_start\"], \"exact\": exact, \"eng\": eng, \"leak\": leak, \"pred\": p, \"note\": s[\"note\"]})\n",
    "    return agg, details\n",
]


def main():
    ns = {}
    exec("".join(SYS_LINES), ns)
    tpl = (SCRIPT_DIR.parent / "prompt-templates.md").read_text(encoding="utf-8")
    tpl_ex = re.findall(r"Input: (.*?)\nOutput: (\{.*?\})", tpl)
    sys_ex = re.findall(r"Example: Input: (.*?) Output: (\{.*?\})", ns["SYS"])
    assert len(tpl_ex) == len(sys_ex) == 6, (len(tpl_ex), len(sys_ex))
    for (ti, to), (gi, go) in zip(tpl_ex, sys_ex):
        assert ti == gi and json.loads(to) == json.loads(go), (ti, gi)
    print("SYS examples match prompt-templates.md: True")
    with open(REG_SRC, encoding="utf-8") as f:
        reg = [json.loads(l) for l in f if l.strip() and json.loads(l)["silver"]]
    with open(CUE_SRC, encoding="utf-8") as f:
        cue = [json.loads(l) for l in f if l.strip() and json.loads(l)["silver"]]
    assert len(reg) == 17, len(reg)
    assert len(cue) == 30, len(cue)
    for r in reg:
        r["set"] = "reg"
    for r in cue:
        r["set"] = "cue3"
    rows = reg + cue

    data_src = (
        ["import json\n", f"ROWS = {json.dumps(rows, ensure_ascii=False)}\n", "print(f\"rows={len(ROWS)}\", flush=True)\n", "assert len(ROWS) == 47\n"]
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
                "OUTPUT_PATH = WORKING_DIR + f\"/pilot_handles_v5_shard{SHARD_ID}.jsonl\"\n",
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
                "for ri, r in enumerate(ROWS):\n",
                "    wtext = \" / \".join(w[\"text\"] for w in r[\"window\"])\n",
                "    p, f = llm_extract(wtext)\n",
                "    fails += f\n",
                "    preds.append(p)\n",
                "    json.dump({\"set\": r[\"set\"], \"video_id\": r[\"video_id\"], \"center_start\": r[\"center_start\"], \"pred\": p, \"silver\": r[\"silver\"]}, out, ensure_ascii=False)\n",
                "    out.write(\"\\n\")\n",
                "    print(f\"{ri + 1}/{len(ROWS)} fail={f} pred={json.dumps(p, ensure_ascii=False)}\", flush=True)\n",
                "out.close()\n",
                "agg, details = score_rows(ROWS, preds)\n",
                "reg_rows = [r for r, d in zip(ROWS, details) if r[\"set\"] == \"reg\"]\n",
                "cue_rows = [r for r, d in zip(ROWS, details) if r[\"set\"] == \"cue3\"]\n",
                "reg_agg, _ = score_rows(reg_rows, [preds[i] for i, r in enumerate(ROWS) if r[\"set\"] == \"reg\"])\n",
                "cue_agg, _ = score_rows(cue_rows, [preds[i] for i, r in enumerate(ROWS) if r[\"set\"] == \"cue3\"])\n",
                "agg[\"fails\"] = fails\n",
                "agg[\"secs\"] = round(time.perf_counter() - t0, 1)\n",
                "print(\"ALL:\", json.dumps(agg, ensure_ascii=False), flush=True)\n",
                "print(\"REG:\", json.dumps(reg_agg, ensure_ascii=False), flush=True)\n",
                "print(\"CUE3:\", json.dumps(cue_agg, ensure_ascii=False), flush=True)\n",
                "with open(WORKING_DIR + \"/pilot_handles_v5_metrics.json\", \"w\", encoding=\"utf-8\") as mf:\n",
                "    json.dump({\"agg\": agg, \"reg\": reg_agg, \"cue3\": cue_agg, \"details\": details}, mf, ensure_ascii=False, indent=1)\n",
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
