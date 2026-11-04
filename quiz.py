"""Generate a multiple-choice quiz (A-D) from one lecture's combined.txt.

Professor topics are required: each gets one question. Remaining slots are
filled by the model from the source. Each question returns the source tags
it used, which are resolved back to the exact slide and transcript text.
"""
import json
import random
import re
import sys
from pathlib import Path

from config import BASE_DIR
from services import llm

LECTURE_DIR = Path(BASE_DIR) / "tests" / "out" / "lecture_01"
COMBINED_PATH = LECTURE_DIR / "combined.txt"
OUTPUT_PATH = LECTURE_DIR / "quiz.json"

QUIZ_PROMPT = """You write multiple-choice quiz questions for a computer engineering student.

Source (tagged: [slide N] = slide content, [lecture line A-B] = what the professor said):
{source}

Write exactly {n} questions.
{topic_rules}

Rules:
- Use ONLY the source. Do not add outside facts. Skip course-admin text.
- Each question has exactly 4 options (A, B, C, D) with exactly one correct answer and plausible distractors.
- "sources" lists the tags the question relies on, copied exactly from the source, e.g. "slide 19" or "lecture line 1179-1230".
- Cite a small lecture line range that supports the question, ideally under 20 lines.
- Every question MUST cite at least one lecture line range AND/OR a slide tag.
- Do not put the answer letter inside the option text.

Respond with ONLY valid JSON (no markdown fences) in this exact shape:
[
  {{
    "topic": "the professor topic this covers, or null if free choice",
    "question": "...",
    "options": ["...", "...", "...", "..."],
    "answer_index": 0,
    "explanation": "one or two sentences based only on the source",
    "sources": ["slide 19"],
    "found_in_source": true
  }}
]
"""

TOPIC_RULES = """Each of these professor topics MUST get exactly one question, in this order:
{topics}
If a professor topic is not covered by the source, still output its question with "found_in_source": false and leave "options" empty, so the professor can see it was not found. Do not invent content for it."""


def load_source(path: Path) -> str:
    if not path.is_file():
        sys.exit(f"Source not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        sys.exit("Source is empty.")
    return text


def parse_json(raw: str) -> list[dict]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    quiz = json.loads(cleaned)
    for q in quiz:
        assert {"question", "options", "answer_index", "sources"} <= q.keys()
    return quiz


LECTURE_RE = re.compile(r"^\[lecture line (\d+)-(\d+)\]\n", re.M)
TAG_LINE_RE = re.compile(r"^lecture line (\d+)-(\d+)$")


def parse_transcript_lines(source: str) -> dict[int, str]:
    """Map each transcript line number to its text, from the [lecture line A-B] blocks."""
    lines = {}
    matches = list(LECTURE_RE.finditer(source))
    for i, m in enumerate(matches):
        start, end_marker = int(m.group(1)), int(m.group(2))
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        body = source[m.end():end].strip("\n").split("\n")
        # The block's lines map to numbers start..end_marker; the transcript
        # line count can differ from the text line count if a sentence wraps,
        # so number the block's lines in order from its start.
        for offset, text in enumerate(body):
            lines[start + offset] = text
    return lines

def parse_slide_blocks(source: str) -> dict[str, str]:
    """Map 'slide N' to only its own text, stopping at the next [ tag."""
    blocks = {}
    header = re.compile(r"^\[slide (\d+)[^\]]*\]\n", re.M)
    next_tag = re.compile(r"^\[", re.M)
    for m in header.finditer(source):
        rest = source[m.end():]
        stop = next_tag.search(rest)
        body = rest[:stop.start()] if stop else rest
        blocks[f"slide {m.group(1)}"] = body.strip()
    return blocks


def shuffle_options(q: dict) -> dict:
    if not q.get("found_in_source", True) or not q["options"]:
        return q
    correct = q["options"][q["answer_index"]]
    random.shuffle(q["options"])
    q["answer_index"] = q["options"].index(correct)
    return q


def transcript_range_text(tag: str, lines: dict[int, str]) -> str:
    m = TAG_LINE_RE.match(tag)
    if not m:
        return "(bad tag)"
    a, b = int(m.group(1)), int(m.group(2))
    found = [lines[n] for n in range(a, b + 1) if n in lines]
    return "\n".join(found) if found else "(tag not found in source)"


def attach_evidence(quiz: list[dict], source: str, slides: list[dict]) -> list[dict]:
    slide_blocks = parse_slide_blocks(source)
    transcript = parse_transcript_lines(source)
    by_num = {s["slide_number"]: s for s in slides}

    for q in quiz:
        q["evidence"] = {}
        q["slide_images"] = []
        q["transcript_range"] = None
        for tag in q["sources"]:
            key = tag.strip()
            m = re.match(r"slide (\d+)$", key)
            if m:
                num = int(m.group(1))
                q["evidence"][key] = slide_blocks.get(key, "(tag not found in source)")
                s = by_num.get(num)
                if s and s.get("page_render"):
                    q["slide_images"].append({"slide": num, "path": Path(s["page_render"]).as_posix()})
            elif TAG_LINE_RE.match(key):
                q["transcript_range"] = key
                q["evidence"][key] = transcript_range_text(key, transcript)
    return quiz


def generate_quiz(source: str, professor_topics: list[str], n: int) -> list[dict]:
    if len(professor_topics) > n:
        sys.exit(f"{len(professor_topics)} professor topics but only {n} questions requested.")

    topic_rules = TOPIC_RULES.format(
        topics="\n".join(f"{i+1}. {t}" for i, t in enumerate(professor_topics))
    ) if professor_topics else "Choose the topics yourself, covering the most important concepts."

    prompt = QUIZ_PROMPT.format(source=source, n=n, topic_rules=topic_rules)
    quiz = parse_json(llm.generate_text(prompt))

    if len(quiz) != n:
        print(f"Warning: asked for {n} questions, got {len(quiz)}")
    return [shuffle_options(q) for q in quiz]


if __name__ == "__main__":
    # Set these per run
    PROFESSOR_TOPICS = [
        "what is a tuple",
        "which of the following is not mutable",
    ]
    NUM_QUESTIONS = 5

    source = load_source(COMBINED_PATH)
    quiz = generate_quiz(source, PROFESSOR_TOPICS, NUM_QUESTIONS)
    slides = json.loads((LECTURE_DIR / "slides_merged.json").read_text(encoding="utf-8"))
    quiz = attach_evidence(quiz, source, slides)

    OUTPUT_PATH.write_text(json.dumps(quiz, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(quiz)} questions to {OUTPUT_PATH}")