"""Generate a quiz from the recorded lecture transcription (yt_transcription.txt)."""
import json
import re
import sys
from pathlib import Path

from config import BASE_DIR
from services import llm

TRANSCRIPT_PATH = Path(BASE_DIR)/"yt_transcript.txt"
OUTPUT_PATH = Path("quiz.json")
NUM_QUESTIONS = 5

QUIZ_PROMPT = """You are a university tutor. Based ONLY on the lecture transcript below,
write {n} multiple-choice questions in Greek that test understanding of the key concepts.

Rules:
- Each question tests exactly one idea and is phrased as a standalone question
  about the concept. Never mention "the speaker", "the lecture", "the transcript",
  or phrases like "σύμφωνα με τη διάλεξη / τον ομιλητή" anywhere, including
  in the explanations.
- Exactly 4 options. They must be similar in length and detail; the correct
  answer must not be longer or more specific than the others. Distractors must
  be plausible and from the same topic.
- "options" contains only the option text, with no letter prefixes.
- "explanation" is 1-2 clean sentences in your own words, not quotes from the transcript.

Respond with ONLY valid JSON (no markdown fences) in this exact shape:
[
  {{
    "question": "...",
    "options": ["...", "...", "...", "..."],
    "answer_index": 0,
    "explanation": "..."
  }}
]

Transcript:
\"\"\"
{transcript}
\"\"\"
"""

import random

def shuffle_options(quiz: list[dict]) -> list[dict]:
    for q in quiz:
        correct = q["options"][q["answer_index"]]
        random.shuffle(q["options"])
        q["answer_index"] = q["options"].index(correct)
    return quiz

def load_transcript(path: Path) -> str:
    if not path.is_file():
        sys.exit(f"Transcript not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        sys.exit("Transcript is empty.")
    return text


def parse_quiz(raw: str) -> list[dict]:
    """Strip accidental code fences and parse the model's JSON."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    quiz = json.loads(cleaned)
    for q in quiz:
        assert {"question", "options", "answer_index"} <= q.keys()
    return quiz


def generate_quiz(transcript: str, n: int = NUM_QUESTIONS) -> list[dict]:
    prompt = QUIZ_PROMPT.format(n=n, transcript=transcript)
    raw = llm.generate_text(prompt)

    return shuffle_options(parse_quiz(raw))


if __name__ == "__main__":
    transcript = load_transcript(TRANSCRIPT_PATH)
    quiz = generate_quiz(transcript)
    OUTPUT_PATH.write_text(json.dumps(quiz, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(quiz)} questions to {OUTPUT_PATH}")