"""Build bulk-ner-gemma3.kaggle.ipynb (run once, then keep as source). Fresh-run Method A bulk."""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "bulk-ner-gemma3.kaggle.ipynb"

SYS_LINES = [
    "SYS = ('Extract person names from Tamil text. Reply JSON only: {\"tamil\": [...], \"english\": [...]}. Empty lists if none.\\n'\n",
    "'Rules: names must be Tamil-script person names only. Never output English words, brands, objects, greetings (bro, hello, hey, you, iphone, processor).\\n'\n",
    "'English must list the transliteration of each Tamil name in the same order - never empty when tamil is non-empty.\\n'\n",
    "'Only extract names that appear verbatim in the Input. Never copy names from these examples.\\n'\n",
    "'Example: Input: வணக்கம், நான் சூர்யா. Output: {\"tamil\": [\"சூர்யா\"], \"english\": [\"Surya\"]}\\n'\n",
    "'Example: Input: ப்ரோ iphone processor நல்லா இருக்கு. Output: {\"tamil\": [], \"english\": []}\\n'\n",
    "'Input: {TEXT}\\nOutput:')\n",
]


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
            "START_INDEX = _gsv('START_INDEX', None, cast=int)\n",
            "END_INDEX = _gsv('END_INDEX', None, cast=int)\n",
            "print(f\"shard={SHARD_ID}/{TOTAL_SHARDS} slice=[{START_INDEX}:{END_INDEX}]\", flush=True)\n",
        ],
        tags=["kaggle-automation-shard-fallback"],
    ),
    cell(
        [
            "%%capture\n",
            "import os, re\n",
            "import torch\n",
            '_tm = re.match(r"[\\d]{1,}\\.[\\d]{1,}", str(torch.__version__))\n',
            '_tv = _tm.group(0) if _tm else "2.8"\n',
            "xformers = 'xformers==' + {'2.10': '0.0.34', '2.9': '0.0.33.post1', '2.8': '0.0.32.post2'}.get(_tv, \"0.0.34\")\n",
            "!uv pip install --system sentencepiece protobuf datasets huggingface_hub hf_transfer\n",
            "!uv pip install --system --upgrade --no-deps unsloth_zoo bitsandbytes accelerate {xformers} peft trl triton unsloth\n",
            "!uv pip install --system --upgrade --no-deps torchao\n",
            "!uv pip install --system --upgrade --no-deps transformers==5.5.0 \"tokenizers>=0.22.0,<=0.23.0\"\n",
            "!uv pip install --system torchcodec\n",
            "import torch; torch._dynamo.config.recompile_limit = 64;\n",
        ]
    ),
]

cells.append(
    cell(
        [
            "import os, time, urllib.request\n",
            "os.makedirs(SCRATCH_DIR, exist_ok=True)\n",
            "os.makedirs(WORKING_DIR, exist_ok=True)\n",
            "_url = \"https://github.com/barryallen16/sivabharani-comments/raw/refs/heads/main/transcripts/output/tamil_transcripts.jsonl\"\n",
            "_dst = SCRATCH_DIR + \"/tamil_transcripts.jsonl\"\n",
            "for _t in range(5):\n",
            "    try:\n",
            "        urllib.request.urlretrieve(_url, _dst)\n",
            "        break\n",
            "    except Exception as _e:\n",
            "        print(f\"download try {_t + 1} failed: {_e}\", flush=True)\n",
            "        time.sleep(30)\n",
            "else:\n",
            "    raise RuntimeError(\"tamil_transcripts.jsonl download failed after retries\")\n",
            "print(f\"downloaded {_dst}\", flush=True)\n",
        ]
    )
)

LOAD_SRC = [
    "import torch\n",
    "print(f\"gpus={torch.cuda.device_count()}\", flush=True)\n",
    "assert torch.cuda.device_count() > 0, \"need T4 x2\"\n",
    "from unsloth import FastModel\n",
    "from transformers import pipeline\n",
    "ner = pipeline(\"token-classification\", model=\"ai4bharat/IndicNER\", aggregation_strategy=\"simple\", device=0, batch_size=128)\n",
    "def ner_flags_batch(texts):\n",
    "    try:\n",
    "        ents = ner(texts)\n",
    "    except Exception:\n",
    "        return [True] * len(texts)\n",
    "    if ents and isinstance(ents[0], dict):\n",
    "        ents = [ents]\n",
    "    return [any(\"PER\" in e.get(\"entity_group\", \"\") for e in el) for el in ents]\n",
    "model, tokenizer = FastModel.from_pretrained(model_name=\"unsloth/gemma-3-4b-it\", dtype=None, max_seq_length=1024, load_in_4bit=True, full_finetuning=False)\n",
    "print(\"models loaded\", flush=True)\n",
]

RUN_SRC = [
    "import json, time, hashlib\n",
    "INPUT_PATH = SCRATCH_DIR + \"/tamil_transcripts.jsonl\"\n",
    "OUTPUT_PATH = WORKING_DIR + f\"/bulk_shard{SHARD_ID}.jsonl\"\n",
    "SOFT_LIMIT = 11 * 3600\n",
    "t_start = time.perf_counter()\n",
    "def _txt(c):\n",
    "    return c.get(\"text\", c.get(\" text\", \"\"))\n",
    "done = set()\n",
    "try:\n",
    "    with open(OUTPUT_PATH, encoding=\"utf-8\") as _f:\n",
    "        for _line in _f:\n",
    "            if _line.strip():\n",
    "                _d = json.loads(_line)\n",
    "                done.add(hashlib.sha256(f\"{_d['video_id']} + {_d['text']}\".encode()).hexdigest())\n",
    "except FileNotFoundError:\n",
    "    pass\n",
    "print(f\"resumed {len(done)} rows from own shard file\", flush=True)\n",
    "videos = []\n",
    "with open(INPUT_PATH, encoding=\"utf-8\") as _f:\n",
    "    for _line in _f:\n",
    "        if _line.strip():\n",
    "            _d = json.loads(_line)\n",
    "            for _vid, _ch in _d.items():\n",
    "                videos.append((_vid, _ch))\n",
    "remaining = [(_vid, _ch) for _vid, _ch in videos if any(hashlib.sha256(f\"{_vid} + {_txt(_c)}\".encode()).hexdigest() not in done for _c in _ch)]\n",
    "if START_INDEX is not None and END_INDEX is not None:\n",
    "    work = remaining[START_INDEX:END_INDEX]\n",
    "else:\n",
    "    work = remaining[SHARD_ID::TOTAL_SHARDS]\n",
    "print(f\"videos total={len(videos)} remaining={len(remaining)} this shard={len(work)}\", flush=True)\n",
    "assert len(videos) > 0, \"input file empty, aborting\"\n",
] + SYS_LINES + [
    "def llm_extract(text):\n",
    "    prompt = SYS.replace(\"{TEXT}\", text)\n",
    "    msgs = [{\"role\": \"user\", \"content\": [{\"type\": \"text\", \"text\": prompt}]}]\n",
    "    try:\n",
    "        _dev = model.language_model.embed_tokens.weight.device\n",
    "    except Exception:\n",
    "        _dev = \"cuda:0\"\n",
    "    inputs = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors=\"pt\").to(_dev)\n",
    "    out = model.generate(**inputs, max_new_tokens=64, do_sample=False)\n",
    "    gen = tokenizer.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)\n",
    "    cleaned = gen.replace(\"json\", \"\").replace(\"```\", \"\").strip()\n",
    "    try:\n",
    "        return json.loads(cleaned), False\n",
    "    except Exception:\n",
    "        return {\"tamil\": [], \"english\": []}, True\n",
    "def has_names(ex):\n",
    "    return bool(ex.get(\"tamil\")) or bool(ex.get(\"english\"))\n",
]

RUN_SRC += [
    "out = open(OUTPUT_PATH, \"a\", encoding=\"utf-8\")\n",
    "n_done = n_llm = n_fail = 0\n",
    "for vi, (vid, chunks) in enumerate(work):\n",
    "    if time.perf_counter() - t_start > SOFT_LIMIT:\n",
    "        print(\"soft timeout, stopping loop for upload\", flush=True)\n",
    "        break\n",
    "    todo = [(c, hashlib.sha256(f\"{vid} + {_txt(c)}\".encode()).hexdigest()) for c in chunks]\n",
    "    todo = [(c, h) for c, h in todo if h not in done]\n",
    "    if not todo:\n",
    "        continue\n",
    "    flags = ner_flags_batch([_txt(c) for c, h in todo])\n",
    "    for (c, h), flag in zip(todo, flags):\n",
    "        t = _txt(c)\n",
    "        if flag:\n",
    "            pred, f = llm_extract(t)\n",
    "            n_llm += 1\n",
    "            n_fail += f\n",
    "            if n_llm % 50 == 0:\n",
    "                print(f\"llm={n_llm} fails={n_fail} rows={n_done} elapsed={time.perf_counter()-t_start:.0f}s\", flush=True)\n",
    "        else:\n",
    "            pred = {\"tamil\": [], \"english\": []}\n",
    "        json.dump({\"video_id\": vid, \"text\": t, \"extract\": pred, \"start\": c.get(\"start\"), \"duration\": c.get(\"duration\")}, out, ensure_ascii=False)\n",
    "        out.write(\"\\n\")\n",
    "        done.add(h)\n",
    "        n_done += 1\n",
    "    out.flush()\n",
    "    if vi % 100 == 0:\n",
    "        print(f\"videos {vi}/{len(work)} rows={n_done} llm={n_llm}\", flush=True)\n",
    "out.close()\n",
    "print(f\"SHARD DONE rows={n_done} llm={n_llm} fails={n_fail}\", flush=True)\n",
]

UP_SRC = [
    "from huggingface_hub import HfApi, create_repo\n",
    "import os\n",
    "LOCAL = WORKING_DIR + f\"/bulk_shard{SHARD_ID}.jsonl\"\n",
    "REMOTE = f\"data/bulk_shard{SHARD_ID}.jsonl\"\n",
    "REPO = \"barryallen16/sivabharani_comments\"\n",
    "tok = os.environ.get(\"HF_TOKEN\") or os.environ.get(\"WRITE_HF_TOKEN\") or os.environ.get(\"HUGGINGFACE_TOKEN\")\n",
    "if not tok:\n",
    "    try:\n",
    "        from kaggle_secrets import UserSecretsClient\n",
    "        tok = UserSecretsClient().get_secret(\"WRITE_HF_TOKEN\")\n",
    "    except Exception as _e:\n",
    "        print(f\"no HF token: {_e}\", flush=True)\n",
    "        tok = None\n",
    "if tok:\n",
    "    api = HfApi(token=tok)\n",
    "    create_repo(repo_id=REPO, repo_type=\"dataset\", exist_ok=True, token=tok)\n",
    "    api.upload_file(path_or_fileobj=LOCAL, path_in_repo=REMOTE, repo_id=REPO, repo_type=\"dataset\", commit_message=f\"Bulk shard {SHARD_ID}.\")\n",
    "    print(f\"pushed {LOCAL}\", flush=True)\n",
    "else:\n",
    "    print(\"skipped upload: no token\", flush=True)\n",
]

CLEAN_SRC = [
    "import gc, shutil, os\n",
    "for _n in [\"model\", \"tokenizer\", \"ner\"]:\n",
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

cells += [cell(LOAD_SRC), cell(RUN_SRC), cell(UP_SRC), cell(CLEAN_SRC)]
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
