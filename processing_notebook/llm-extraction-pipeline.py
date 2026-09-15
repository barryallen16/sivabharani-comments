# %%
%%capture
import os, re
if "COLAB_" not in "".join(os.environ.keys()):
    !pip install unsloth  # Do this in local & cloud setups
else:
    import torch; v = re.match(r'[\d]{1,}\.[\d]{1,}', str(torch.__version__)).group(0)
    xformers = 'xformers==' + {'2.10':'0.0.34','2.9':'0.0.33.post1','2.8':'0.0.32.post2'}.get(v, "0.0.34")
    !pip install sentencepiece protobuf "datasets==4.3.0" "huggingface_hub>=0.34.0" hf_transfer
    !pip install --no-deps unsloth_zoo bitsandbytes accelerate {xformers} peft trl triton unsloth
    !pip install --no-deps --upgrade "torchao>=0.16.0"
!pip install --no-deps transformers==5.5.0 "tokenizers>=0.22.0,<=0.23.0"
!pip install torchcodec
import torch; torch._dynamo.config.recompile_limit = 64;

# %%
%%capture
!pip install --no-deps --upgrade timm # For Gemma 4 vision/audio

# %%
!wget https://github.com/barryallen16/sivabharani-comments/raw/refs/heads/main/transcripts/output/tamil_transcripts.jsonl
!wget https://github.com/barryallen16/sivabharani-comments/raw/refs/heads/main/intermediate-results/already_processed_transcripts.jsonl

# %%
import hashlib
import json

ALREADY_PROCESSED_TRANSCRIPT_HASHES = set()
with open("/kaggle/working/already_processed_transcripts.jsonl", "r", encoding="utf-8") as in_file:
    for line in in_file:
        if line.strip():
            data = json.loads(line)
            video_id = data["video_id"]
            text = data["text"]
            transcript_hash = hashlib.sha256(f"{video_id} + {text}".encode()).hexdigest()
            if transcript_hash not in ALREADY_PROCESSED_TRANSCRIPT_HASHES:
                ALREADY_PROCESSED_TRANSCRIPT_HASHES.add(transcript_hash)

# %%
from unsloth import FastModel
import torch

gemma4_models = [
    # Gemma-4 instruct models:
    "unsloth/gemma-4-E2B-it",
    "unsloth/gemma-4-E4B-it",
    "unsloth/gemma-4-31B-it",
    "unsloth/gemma-4-26B-A4B-it",
    # Gemma-4 base models:
    "unsloth/gemma-4-E2B",
    "unsloth/gemma-4-E4B",
    "unsloth/gemma-4-31B",
    "unsloth/gemma-4-26B-A4B",
] 
model, tokenizer = FastModel.from_pretrained(
    model_name = "unsloth/gemma-4-31B-it",
    dtype = None, # None for auto detection
    max_seq_length = 2048, # Choose any for long context!
    load_in_4bit = True,  # 4 bit quantization to reduce memory
    full_finetuning = False, # [NEW!] We have full finetuning now!
    # token = "YOUR_HF_TOKEN", # HF Token for gated models
)

# %%
def gemma_do_inference(messages, max_new_tokens):
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt"
    ).to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=max_new_tokens, temperature=1.0,  top_p = 0.95, top_k = 64)
    prompt_length = inputs.input_ids.shape[1]
    generated_tokens = outputs[0][prompt_length:]
    final_result = tokenizer.decode(generated_tokens, skip_special_tokens=True)
    return final_result

# %%
def process_transcript_chunks(INPUT):
    
    # INPUT = "சரி ஓகே. என்ஜிகே அப்படிங்கிற நண்பர் வந்து ப்ரோ ஹாய் ப்ரோ நியூ அப்டேட்ல ஏர்பாட் சப்போர்ட் அண்ட் சம் அதர் பீச்சர்ஸ்ும் வந்திருக்கு. நான் F8"
    PROMPT="""
    ### System Instruction:
    You are a linguistic data extraction tool. Your goal is to identify human names in Tamil text and provide a JSON response containing the original Tamil names and their English transliterations.
    
    ### Constraints:
    - Only extract names of people.
    - Do not include words like "Bye Bye", "Hello", or "Location names".
    - Ensure the English list matches the order of the Tamil list.
    - If no names exist, return: {"tamil": [], "english": []}
    
    ### Examples:
    Input: வணக்கம், நான் சூர்யா.
    Output: {"tamil": ["சூர்யா"], "english": ["Surya"]}
    
    Input: இன்று ரவி மற்றும் கவி வந்தார்கள்.
    Output: {"tamil": ["ரவி", "கவி"], "english": ["Ravi", "Kavi"]}
    
    Input: நான் இப்போது செல்கிறேன். பாய் பாய்.
    Output: {"tamil": [], "english": []}
    
    ### Task:
    Extract names from the following input text:
    """
    PROMPT += f"""
    Input: {INPUT}
    JSON Output:
    """
    messages = [{
        "role" : "user",
        "content": [
            { "type": "text",  "text" : PROMPT }
        ]
    }]
    # You might have to wait 1 minute for Unsloth's auto compiler
    results = gemma_do_inference(messages, max_new_tokens = 256)
    cleaned_output = results.replace("json", "").replace("```", "").strip()
    return cleaned_output

# %%
from tqdm import tqdm
with open("/kaggle/working/tamil_transcripts.jsonl", "r", encoding="utf-8") as in_file:
    for line in tqdm(in_file, desc="Processing video transcrips", unit="video"):
        if line.strip():
            data = json.loads(line)
            for video_id, chunks in data.items():
                for chunk in chunks:    
                    input_text = chunk["text"]
                    transcript_hash = hashlib.sha256(f"{video_id} + {input_text}".encode()).hexdigest()
                    if transcript_hash in ALREADY_PROCESSED_TRANSCRIPT_HASHES:
                        continue
                    start = chunk["start"]
                    duration = chunk["duration"]
                    result = process_transcript_chunks(input_text)
                    if result:
                        try: 
                            parsed_extract = json.loads(result)
                            result_dict = {
                                "video_id": video_id,
                                "text": input_text,
                                "extract": parsed_extract,
                                "start": start,
                                "duration": duration
                            }
                            print(result_dict)
                            with open("/kaggle/working/already_processed_transcripts.jsonl", "a", encoding="utf-8") as out_file:
                                json.dump(result_dict, out_file, ensure_ascii=False)
                                out_file.write("\n")
                        except json.JSONDecodeError:
                            continue

# %%
from kaggle_secrets import UserSecretsClient
from huggingface_hub import HfApi, create_repo

LOCAL_FILE_NAME = "/kaggle/working/already_processed_transcripts.jsonl"
FILE_PATH_IN_REPO = "data/processed_transcripts.jsonl"
secret_label = "WRITE_HF_TOKEN"
REPO_ID = "barryallen16/sivabharani_comments"
try:
    
    HF_TOKEN = UserSecretsClient().get_secret(secret_label)
    
    api = HfApi(token = HF_TOKEN)
    create_repo(repo_id=REPO_ID, 
                repo_type="dataset",
               exist_ok=True,
               token=HF_TOKEN)
    api.upload_file(
        path_or_fileobj=LOCAL_FILE_NAME,
        path_in_repo=FILE_PATH_IN_REPO,
        repo_id=REPO_ID,
        repo_type="dataset",
        commit_message="Commit after initial processing."
    )
    print("pushed the jsonl file to hf repo.")
except Exception as e:
    print(f"error occured: {e}")


