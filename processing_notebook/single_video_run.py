"""Run the v5 commenter prompt over every window of ONE video, print the hits.

Usage (Kaggle GPU, fresh kernel):
    1. paste this file's body into a cell, or upload it and %run it
    2. set VIDEO_ID below, run top to bottom
    3. eyeball the printed non-empty preds; full output -> single_video_<id>.jsonl

ponytail: no sharding, no resume, no upload. One video, one model, stdout.
"""

import json
import subprocess
import sys

VIDEO_ID = "bHp-SDnsnS8"  # <-- change me
HALF_WINDOW = 2

# --- installs (skip if you already have unsloth) ---
subprocess.run([sys.executable, "-m", "uv", "pip", "install", "--system",
                "sentencepiece", "protobuf", "huggingface_hub", "hf_transfer"],
               check=False)
import re  # noqa: E402
import torch  # noqa: E402

_tm = re.match(r"[\d]{1,}\.[\d]{1,}", str(torch.__version__))
_tv = _tm.group(0) if _tm else "2.8"
xformers = "xformers==" + {"2.10": "0.0.34", "2.9": "0.0.33.post1",
                           "2.8": "0.0.32.post2"}.get(_tv, "0.0.34")
subprocess.run([sys.executable, "-m", "uv", "pip", "install", "--system", "--no-deps",
                "unsloth_zoo", "bitsandbytes", "accelerate", xformers,
                "peft", "trl", "triton", "unsloth"], check=False)
subprocess.run([sys.executable, "-m", "uv", "pip", "install", "--system",
                "--no-deps", "--upgrade", "torchao"], check=False)
subprocess.run([sys.executable, "-m", "uv", "pip", "install", "--system",
                "--upgrade", "--no-deps", "transformers==5.5.0",
                "tokenizers>=0.22.0,<=0.23.0"], check=False)
torch._dynamo.config.recompile_limit = 64

SYS = (
'Identify the commenter whose comment is read aloud in this Tamil transcript window. Reply JSON only: {"commenter_tamil": [...], "commenter_english": [...], "mentioned": [...]}. Empty lists if none.\n'
'A commenter name appears in ONE of these cue patterns (name FIRST, cue follows):\n'
'1. name + ப்ரோ. 2. bare name, no cue. 3. name + என்ன சொல்லிருக்காரு. 4. name + என்ன சொல்லிருக்காங்க. 5. name + வந்திருக்காது. 6. name + அப்படிங்கற/அப்படிங்கிற நண்பர் வந்து. 7. name + என்ன சொல்லிருக்கான். 8. name + என்ன கேட்டுருந்தாரு. 9. compound English username in Tamil script.\n'
'Rules: the cue word is நண்பர் (with ண). நம்பர் (with ம) means phone number - never extract it. Keep the WHOLE handle verbatim even if compound: brand+name, place+name, English words, initials, digits. Never truncate.\n'
'commenter_english is the most likely original handle spelling, lowercase, no spaces. mentioned holds names AFTER the cue or addressees (players, crew, co-host, சிவா) - never put them in commenter.\n'
'Transliterate handles into English spelling; never translate the meaning into English words.\n'
'Never output product terms, greetings, verbs, or common words alone (iphone, processor, ப்ரோ, hello, guys). Only extract spans verbatim in the Input. Never copy names from these examples. If no name precedes a cue, return empty lists.\n'
'Example: Input: வந்து பாத்தீங்கன்னா சிவகாசி விஜய் / அப்படிங்கற நண்பர் வந்து Samsung S25 எட் Output: {"commenter_tamil": ["சிவகாசி விஜய்"], "commenter_english": ["sivakasivijay"], "mentioned": []}\n'
'Example: Input: கவின் என்ன சொல்லிருக்காருன்னா iPhone 16 / Pro வாங்கலாம்னு இருக்கேன் ப்ரோ Output: {"commenter_tamil": ["கவின்"], "commenter_english": ["kavin"], "mentioned": []}\n'
'Example: Input: பாத்தீங்கன்னா டார்க் ஹன்டர் அப்படிங்கற / நண்பர் வந்து ஹாய் சிவான் கௌதம் ப்ரோ Output: {"commenter_tamil": ["டார்க் ஹன்டர்"], "commenter_english": ["darkhunter"], "mentioned": ["சிவான் கௌதம்"]}\n'
'Example: Input: சொல்லுங்க. உங்க போன் நம்பர் சொல்லுங்க Output: {"commenter_tamil": [], "commenter_english": [], "mentioned": []}\n'
'Example: Input: நரசிம்மா அப்படின்னு சொல்லி நம்ம குரூப்ல / ஒரு நண்பருடா குரூப் / ஆமா அவரு சொல்லிருக்காரு Output: {"commenter_tamil": ["நரசிம்மா"], "commenter_english": ["narasimha"], "mentioned": []}\n'
'Example: Input: விடைபெற்று கொள்வது சிவபரணி நிரஞ்சன் விக்னேஷ் பாக்கலாங்க பாய் பாய் Output: {"commenter_tamil": [], "commenter_english": [], "mentioned": []}\n'
'Input: {TEXT}\nOutput:')


def txt(c):
    return c.get("text", c.get(" text", ""))


def main():
    print(f"gpus={torch.cuda.device_count()}", flush=True)
    from unsloth import FastModel
    model, tokenizer = FastModel.from_pretrained(
        model_name="unsloth/gemma-3-4b-it", dtype=None,
        max_seq_length=1024, load_in_4bit=True, full_finetuning=False)
    try:
        dev = model.language_model.embed_tokens.weight.device
    except Exception:
        dev = "cuda:0"

    chunks = None
    with open("tamil_transcripts.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                if VIDEO_ID in d:
                    chunks = d[VIDEO_ID]
    assert chunks, f"{VIDEO_ID} not in tamil_transcripts.jsonl"
    print(f"chunks={len(chunks)}", flush=True)

    def llm_extract(text):
        msgs = [{"role": "user", "content": [{"type": "text",
                "text": SYS.replace("{TEXT}", text)}]}]
        inputs = tokenizer.apply_chat_template(
            msgs, add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors="pt").to(dev)
        out = model.generate(**inputs, max_new_tokens=128, do_sample=False)
        gen = tokenizer.decode(out[0][inputs.input_ids.shape[1]:],
                               skip_special_tokens=True)
        try:
            p = json.loads(gen.replace("json", "").replace("```", "").strip())
            return {"commenter_tamil": p.get("commenter_tamil", []),
                    "commenter_english": p.get("commenter_english", []),
                    "mentioned": p.get("mentioned", [])}
        except Exception:
            return {"commenter_tamil": [], "commenter_english": [],
                    "mentioned": []}

    out = open(f"single_video_{VIDEO_ID}.jsonl", "w", encoding="utf-8")
    hits = 0
    for i, c in enumerate(chunks):
        lo, hi = max(0, i - HALF_WINDOW), min(len(chunks), i + HALF_WINDOW + 1)
        wtext = " / ".join(txt(chunks[k]) for k in range(lo, hi))
        p = llm_extract(wtext)
        json.dump({"start": c.get("start"), "pred": p,
                   "window": wtext}, out, ensure_ascii=False)
        out.write("\n")
        if p["commenter_tamil"]:
            hits += 1
            print(f"{c.get('start'):8.1f}s C={p['commenter_tamil']} "
                  f"E={p['commenter_english']} M={p['mentioned']}", flush=True)
            print(f"         {wtext}", flush=True)
        elif (i + 1) % 50 == 0:
            print(f"...{i + 1}/{len(chunks)} hits={hits}", flush=True)
    out.close()
    print(f"DONE windows={len(chunks)} hits={hits}", flush=True)


if __name__ == "__main__":
    main()
