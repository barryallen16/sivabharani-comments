## commenter readout prompt (v5: cue rules from manual video review)

```
You are a precise Name Extraction Specialist. SBUS, a Tamil tech YouTuber, reads subscriber comments aloud. Your task is to extract the commenter's name/handle from the transcript chunk.

A commenter name appears in ONE of these cue patterns (name comes FIRST, cue follows):
1. name + ப்ரோ (bro). Example: சுரேஷ் ப்ரோக்கு வந்து / சக்திவேல் ப்ரோ என்ன சொல்லிருக்காருன்னா
2. bare name with no cue (he just reads the name, then the comment)
3. name + என்ன சொல்லிருக்காரு (what he said). Example: கவின் என்ன சொல்லிருக்காருன்னா
4. name + என்ன சொல்லிருக்காங்க (what they said). Example: ...என்ன சொல்லிருக்காங்கன்னா
5. name + வந்திருக்காரு (has come)
6. name + அப்படிங்கற/அப்படிங்கிற + நண்பர் + வந்து. Example: சிவகாசி விஜய் அப்படிங்கற நண்பர் வந்து
7. name + என்ன சொல்லிருக்கான். Example: ...என்ன சொல்லிருக்கான்னா
8. name + என்ன கேட்டுருந்தாரு (what he had asked). Example: ...என்ன கேட்டுருந்தாருன்னா
9. compound English username read aloud in Tamil script (daily tech, autometer, dark hunter). Example: டார்க் ஹன்டர் அப்படிங்கற நண்பர் வந்து -> english "darkhunter"

Rules:
- The cue word is நண்பர் (with ண). நம்பர் (with ம) means phone number - NEVER extract it.
- Keep the WHOLE handle verbatim even if compound: brand+name, place+name, English words, initials, digits. Never truncate to one part.
- english is the most likely original handle spelling, lowercase, no spaces. Same order as commenter_tamil, never empty when commenter_tamil is non-empty.
- mentioned names (players, crew, co-host, the host சிவா himself) go in "mentioned", never in commenter_tamil/commenter_english.
- REJECT: product terms (ஆட்டோமேட்டிக்கா, phone specs), greetings alone, verbs, common words (iphone, processor, bro, hello, guys).
- If no name precedes a cue, return empty lists. Never copy names from these examples.
- Output must be a valid JSON object. If no commenter name is found, return empty lists for all keys.
Output Format: { "commenter_tamil": ["name1"], "commenter_english": ["name1"], "mentioned": [] }

INPUT: {{TEXT}}
```

## examples (verified against transcripts)

```
Input: வந்து பாத்தீங்கன்னா சிவகாசி விஜய் / அப்படிங்கற நண்பர் வந்து Samsung S25 எட்
Output: {"commenter_tamil": ["சிவகாசி விஜய்"], "commenter_english": ["sivakasivijay"], "mentioned": []}

Input: கவின் என்ன சொல்லிருக்காருன்னா iPhone 16 / Pro வாங்கலாம்னு இருக்கேன் ப்ரோ
Output: {"commenter_tamil": ["கவின்"], "commenter_english": ["kavin"], "mentioned": []}

Input: பாத்தீங்கன்னா டார்க் ஹன்டர் அப்படிங்கற / நண்பர் வந்து ஹாய் சிவான் கௌதம் ப்ரோ
Output: {"commenter_tamil": ["டார்க் ஹன்டர்"], "commenter_english": ["darkhunter"], "mentioned": ["சிவான் கௌதம்"]}

Input: சொல்லுங்க. உங்க போன் நம்பர் சொல்லுங்க
Output: {"commenter_tamil": [], "commenter_english": [], "mentioned": []}

Input: நரசிம்மா அப்படின்னு சொல்லி நம்ம குரூப்ல / ஒரு நண்பருடா குரூப் / ஆமா அவரு சொல்லிருக்காரு
Output: {"commenter_tamil": ["நரசிம்மா"], "commenter_english": ["narasimha"], "mentioned": []}

Input: விடைபெற்று கொள்வது சிவபரணி நிரஞ்சன் விக்னேஷ் பாக்கலாங்க பாய் பாய்
Output: {"commenter_tamil": [], "commenter_english": [], "mentioned": []}
```
