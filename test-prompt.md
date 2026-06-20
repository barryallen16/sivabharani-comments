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
Input: விடைபெற்று கொள்வது சிவபரணி நிரஞ்சன் விக்னேஷ் பாக்கலாங்க பாய் பாய்

JSON Output:

