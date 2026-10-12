"""Reconstruct shards/pilot_handles_v5_metrics.json from the pasted Kaggle run log.

Run rows 1-17 = eval_handles.jsonl regression order; 18-47 = eval_cue3.jsonl
file order (verified: row 18 pred matches cue3 row 0's window).
Asserts reconstructed agg == pasted ALL/REG/CUE3 lines exactly.
ponytail: throwaway reconstruction, kept for provenance.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREDS = [
{"commenter_tamil": ["சிவகாசி விஜய்"], "commenter_english": ["sivakasivijay"], "mentioned": []},
{"commenter_tamil": ["லுக்கா"], "commenter_english": ["lucas"], "mentioned": []},
{"commenter_tamil": ["டார்க் ஹன்டர்"], "commenter_english": ["darkhunter"], "mentioned": ["சிவான் கௌதம்"]},
{"commenter_tamil": ["வினோத்"], "commenter_english": ["vinoth"], "mentioned": []},
{"commenter_tamil": ["கண்டிப்பா நான் சந்திக்கிறேன்", "அடுத்து", "Infinix போன் நம்பி வாங்கலாமா", "அப்படின்னும்போது கீழ ஒரு நண்பர் வந்து", "Redmi விட Infinix ோட ஆஃப்டர் சேல்", "சப்போர்ட் நல்லா இருக்கு அப்படின்னு"], "commenter_english": ["definitely i will meet", "next", "infinix phone number to buy", "when below a friend came", "redmi vs infinix after sale", "support is good like that"], "mentioned": []},
{"commenter_tamil": ["SK"], "commenter_english": ["sk"], "mentioned": ["VI"]},
{"commenter_tamil": ["NHR 6259"], "commenter_english": ["nhr6259"], "mentioned": ["Xiaomi 15"]},
{"commenter_tamil": ["கண்ணாடியே", "பொன்ராஜ்"], "commenter_english": ["kannadiyae", "ponraj"], "mentioned": ["சிவா", "ஐம் யூசிங்", "ச3அப் இயர்ஸ்"]},
{"commenter_tamil": ["அஸ்வத் ப்ரோ"], "commenter_english": ["ashwat bro"], "mentioned": []},
{"commenter_tamil": ["அப்டேட்ஸ் எவ்வளோ செக்யூரிட்டி பேட்ச்", "தேங்க்யூ ப்ரோ", "நல்ல டேட்டா", "கவின் என்ன சொல்லிருக்காருன்னா iPhone 16", "iPhone 18 Pro லான்ச் ஒர்த்தா இருக்குமா"], "commenter_english": ["updates how many security patches", "thank you bro", "good data", "kavin what is saying about iphone 16", "iphone 18 pro launch will be soon"], "mentioned": ["கவின்"]},
{"commenter_tamil": ["விக்னேஷ்", "விக்கி"], "commenter_english": ["vineesh", "wiki"], "mentioned": ["டிசிஷன்"]},
{"commenter_tamil": ["மாதவ"], "commenter_english": ["madhav"], "mentioned": []},
{"commenter_tamil": ["சோஃர்ஸ்ட்", "கரூஸ் அண்டர்ஸ கண்ட்ரோல்", "யடாக்அபட் os", "someம் ஆப்ஸ்வ", "run afterட afterட yearயஸ் இif itட் isஸ்"], "commenter_english": ["software", "cruse anders control", "yadaabpt os", "some apps", "run after years if it is"], "mentioned": []},
{"commenter_tamil": ["சோ"], "commenter_english": ["so"], "mentioned": []},
{"commenter_tamil": ["ஜிடி", "சாய் சுதர்சன்", "கில்ல்", "மாப்பிள்ளை", "சாமி"], "commenter_english": ["gtd", "sai sudharsan", "gill", "mappilai", "sami"], "mentioned": []},
{"commenter_tamil": ["சதீஷ் துரைசாமி"], "commenter_english": ["sathish thuraisamy"], "mentioned": ["சிவாபுரன் கௌதம்"]},
{"commenter_tamil": ["பரத் ப்ரோ", "சிவா"], "commenter_english": ["prath", "shiva"], "mentioned": []},
{"commenter_tamil": ["சூஸ்", "நாட்6", "நாட்6", "40,000 வரைக்கும்"], "commenter_english": ["sues", "nat6", "nat6", "40000 onwards"], "mentioned": []},
{"commenter_tamil": ["சர்வீஸ் பொறுத்தவரைக்கும்"], "commenter_english": ["service regarding"], "mentioned": ["v கேர் பார் ரியல்"]},
{"commenter_tamil": ["50% பாஸ்டர்", "பிரிவியஸ் ஜெனரேஷன்", "2x பாஸ்டர்", "டிபிகல் டிவி", "ஒரு ஆவரேஜ் டிவி"], "commenter_english": ["50percentposter", "previousgeneration", "2xposter", "typicaltv", "oneaveragtv"], "mentioned": []},
{"commenter_tamil": ["அமௌண்ட் கம்மி ஆகல"], "commenter_english": ["amount didn't work"], "mentioned": []},
{"commenter_tamil": ["ஆனந்த் பிரபு"], "commenter_english": ["anandprabhu"], "mentioned": []},
{"commenter_tamil": ["LPDR 4X ரேம்", "UFS 3.1 ஸ்டோரேஜ்", "812 வேரியன்ட்", "256 GBயா"], "commenter_english": ["lprd 4x ram", "ufs 3.1 storage", "812 variant", "256 gb"], "mentioned": []},
{"commenter_tamil": ["கப்பிள்டா"], "commenter_english": ["kapildha"], "mentioned": []},
{"commenter_tamil": ["தீய", "கவிய", "அவர்", "சிவா", "Realme 14 Pro பிளஸ் 826", "GB"], "commenter_english": ["deep", "kavi", "he", "siva", "realme 14 pro plus 826", "gb"], "mentioned": ["அரசு"]},
{"commenter_tamil": ["இல்லையா?"], "commenter_english": ["no"], "mentioned": ["K13", "run ni game"]},
{"commenter_tamil": ["நண்பர்கள்"], "commenter_english": ["friends"], "mentioned": []},
{"commenter_tamil": ["செட்டப்போட டீசன்ட்டான"], "commenter_english": ["setthapoda desantana"], "mentioned": []},
{"commenter_tamil": ["தர்வாஸ்"], "commenter_english": ["darvas"], "mentioned": []},
{"commenter_tamil": ["அந்த ஆறு பேர்ல"], "commenter_english": ["the six people"], "mentioned": []},
{"commenter_tamil": ["நான்"], "commenter_english": ["i"], "mentioned": ["சோ பாக்ஸ்"]},
{"commenter_tamil": ["வித்தியாசம் பெருசா இல்ல"], "commenter_english": ["difference is not big"], "mentioned": ["புனிதமூர்த்தி"]},
{"commenter_tamil": ["லாஜிக்தான்", "ஜீரோ டிகரில"], "commenter_english": ["logic", "zero decimal"], "mentioned": ["அவனுங்க"]},
{"commenter_tamil": ["நரசிம்மா", "பாடிசார்", "ஹட்ஆர்", "1.187", "0.8245"], "commenter_english": ["narasimha", "badischar", "hotr", "1.187", "0.8245"], "mentioned": ["ஒplus 12"]},
{"commenter_tamil": ["சசி"], "commenter_english": ["sasi"], "mentioned": []},
{"commenter_tamil": ["2010நோokia 5800 எக்ஸ்பிரஸ்"], "commenter_english": ["2010nokia 5800 express"], "mentioned": []},
{"commenter_tamil": ["ரோஹித்"], "commenter_english": ["rohit"], "mentioned": []},
{"commenter_tamil": ["கான்வர்சேஷன் டைப் ஆப் வீடியோதான்", "பண்றீங்க அதனால எங்களுக்கு ரொம்ப வசதியா இருக்கு அப்படின்னு சொல்லிருக்காங்க"], "commenter_english": ["conversation type of video", "you are doing that", "it would be very convenient for us", "when someone needs something", "i always refer them to the channel"], "mentioned": []},
{"commenter_tamil": ["ப்ரோவும்", "அவர்"], "commenter_english": ["bro", "he"], "mentioned": ["ஆண்டவர்"]},
{"commenter_tamil": ["ப்ராசசர்"], "commenter_english": ["processor"], "mentioned": []},
{"commenter_tamil": ["ப்ரோ"], "commenter_english": ["pro"], "mentioned": []},
{"commenter_tamil": ["சர்வீஸ் விட்டு எடுத்த வண்டியில அவரு கார"], "commenter_english": ["the guy in the van"], "mentioned": []},
{"commenter_tamil": ["அவங்களோட கூறுதல்"], "commenter_english": ["them"], "mentioned": []},
{"commenter_tamil": ["ஜேபிஎஸ்சி பிஇடி"], "commenter_english": ["jpcs bpt"], "mentioned": ["bsnl"]},
{"commenter_tamil": ["ஸ்டெப் கோல்ஸ்"], "commenter_english": ["step goals"], "mentioned": []},
{"commenter_tamil": ["அவன்"], "commenter_english": ["he"], "mentioned": []},
{"commenter_tamil": ["சோ"], "commenter_english": ["so"], "mentioned": ["சம பிரைஸ்"]},
]

PASTED_ALL = {"n": 47, "commenter_exact": 9, "english_match": 8, "exp_handles": 15, "leak": 2, "fp": 31, "clean_empty": 0, "empty_total": 32, "fails": 0, "secs": 305.3}
PASTED_REG = {"n": 17, "commenter_exact": 6, "english_match": 5, "exp_handles": 9, "leak": 1, "fp": 7, "clean_empty": 0, "empty_total": 8}
PASTED_CUE = {"n": 30, "commenter_exact": 3, "english_match": 3, "exp_handles": 6, "leak": 1, "fp": 24, "clean_empty": 0, "empty_total": 24}


def norm_eng(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


def score_rows(rows, preds):
    agg = {"n": 0, "commenter_exact": 0, "english_match": 0, "exp_handles": 0, "leak": 0, "fp": 0, "clean_empty": 0, "empty_total": 0}
    details = []
    for r, p in zip(rows, preds):
        s = r["silver"]
        exp_c, exp_e, exp_m = s["commenter_tamil"], s["commenter_english"], s["mentioned"]
        got_c = p.get("commenter_tamil", [])
        got_e = p.get("commenter_english", [])
        has_exp = bool(exp_c)
        exact = got_c == exp_c
        eng = [norm_eng(x) for x in got_e] == [norm_eng(x) for x in exp_e]
        leak = bool(set(got_c) & set(exp_m))
        agg["n"] += 1
        agg["commenter_exact"] += exact
        if has_exp:
            agg["exp_handles"] += 1
            agg["english_match"] += eng
        else:
            agg["empty_total"] += 1
            agg["clean_empty"] += not got_c
            agg["fp"] += bool(got_c) and not leak
        agg["leak"] += leak
        details.append({"set": r["set"], "video_id": r["video_id"], "center": r["center_start"], "exact": exact, "eng": eng, "leak": leak, "pred": p, "note": s["note"]})
    return agg, details


def main():
    with open(ROOT / "processing_notebook" / "eval_handles.jsonl", encoding="utf-8") as f:
        reg = [json.loads(l) for l in f if l.strip() and json.loads(l)["silver"]]
    with open(ROOT / "processing_notebook" / "eval_cue3.jsonl", encoding="utf-8") as f:
        cue = [json.loads(l) for l in f if l.strip() and json.loads(l)["silver"]]
    assert len(reg) == 17 and len(cue) == 30 and len(PREDS) == 47
    for r in reg:
        r["set"] = "reg"
    for r in cue:
        r["set"] = "cue3"
    rows = reg + cue
    agg, details = score_rows(rows, PREDS)
    agg["fails"] = 0
    agg["secs"] = PASTED_ALL["secs"]
    reg_agg, _ = score_rows([r for r in rows if r["set"] == "reg"], [PREDS[i] for i, r in enumerate(rows) if r["set"] == "reg"])
    cue_agg, _ = score_rows([r for r in rows if r["set"] == "cue3"], [PREDS[i] for i, r in enumerate(rows) if r["set"] == "cue3"])
    assert agg == PASTED_ALL, (agg, PASTED_ALL)
    assert reg_agg == PASTED_REG, (reg_agg, PASTED_REG)
    assert cue_agg == PASTED_CUE, (cue_agg, PASTED_CUE)
    print("reconstruction matches pasted agg lines exactly: True")
    out = ROOT / "shards" / "pilot_handles_v5_metrics.json"
    out.write_text(json.dumps({"agg": agg, "reg": reg_agg, "cue3": cue_agg, "details": details}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
