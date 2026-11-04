"""gemini 2.5 flash combine the lecture transcription with the slide text (and image descriptions)"""

from pathlib import Path
from google import genai
import json
import re
import sys


BASE_DIR = Path(__file__).resolve().parents[2]
legacy_path = BASE_DIR / "myenv" / "api_key" / "api_key.txt"
if not legacy_path.exists():
    sys.exit(f"API key file not found: {legacy_path}")
API_KEY = legacy_path.read_text(encoding="utf-8").strip()


MODEL = "gemini-2.5-flash"

PROMPT = """You are aligning a lecture transcript to its slides.

Slides (JSON, in order):
{slides}

Transcript (numbered lines, in order):
{transcript}

For each slide, find the transcript line where the professor FIRST starts discussing that slide's content.
- The slide is introduced at that line, so the professor's speech about it comes after the slide.
- If a slide is never discussed, omit it.
- Off-topic lines (greetings, logistics, exam talk) are never a slide start.
- Slide starts must increase with slide number.

Return only valid JSON, with no text before or after it:
[{{"slide_number": 4, "starts_at_line": 60}}]
"""


def read_transcript(transcript_path: Path) -> list[str]:
    """Return caption lines with timing lines, tags and repeats removed."""
    content = transcript_path.read_text(encoding="utf-8")
    lines, last = [], None
    for raw in content.splitlines():
        if "-->" in raw or raw.startswith(("WEBVTT", "Kind:", "Language:")) or not raw.strip():
            continue
        text = re.sub(r"<[^>]+>", "", raw).strip()
        if text and text != last:
            lines.append(text)
            last = text
    return lines


def slide_body(s: dict) -> str:
    parts = []
    if s["slide_text"]:
        parts.append(s["slide_text"])
    parts += s.get("image_descriptions", [])
    return "\n".join(parts)


def parse_json_reply(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    return json.loads(text)


def get_starts(client, slides: list[dict], lines: list[str]) -> list[dict]:
    numbered = "\n".join(f"{i+1}: {t}" for i, t in enumerate(lines))
    slides_json = json.dumps(
        [{"slide_number": s["slide_number"], "slide_text": s["slide_text"],
          "image_descriptions": s.get("image_descriptions", [])} for s in slides],
        indent=2, ensure_ascii=False)

    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(slides=slides_json, transcript=numbered),
        config={"temperature": 0, "response_mime_type": "application/json"},
    )
    return parse_json_reply(response.text)


def validate(starts: list[dict], slides: list[dict], n_lines: int) -> list[dict]:
    """Keep only valid entries: known slide, line in range, starts increasing."""
    valid_nums = {s["slide_number"] for s in slides}
    seen, kept, last_line = set(), [], 0
    for x in sorted(starts, key=lambda x: int(x["starts_at_line"])):
        num, line = int(x["slide_number"]), int(x["starts_at_line"])
        if num not in valid_nums or num in seen:
            print(f"Dropped slide {num}: unknown or duplicate")
            continue
        if not (1 <= line <= n_lines) or line <= last_line:
            print(f"Dropped slide {num}: line {line} out of order or out of range")
            continue
        seen.add(num)
        kept.append({"slide_number": num, "starts_at_line": line})
        last_line = line
    return kept


def build_document(lines: list[str], slides: list[dict], starts: list[dict]) -> str:
    by_num = {s["slide_number"]: s for s in slides}
    order = [(x["starts_at_line"], x["slide_number"]) for x in starts]
    out = []

    first = order[0][0] if order else len(lines) + 1
    if first > 1:
        out.append(f"[off-topic lecture line 1-{first-1}]\n" + "\n".join(lines[:first-1]))

    ends = [s for s, _ in order[1:]] + [len(lines) + 1]
    for (start, num), end in zip(order, ends):
        out.append(f"[slide {num}]\n{slide_body(by_num[num])}")
        out.append(f"[lecture line {start}-{end-1}]\n" + "\n".join(lines[start-1:end-1]))

    placed = {num for _, num in order}
    for s in slides:
        if s["slide_number"] not in placed:
            out.append(f"[slide {s['slide_number']} (not discussed)]\n{slide_body(s)}")
    return "\n\n".join(out)


def main():
    out_dir = Path("C:/Users/nekta/Desktop/code/LLMs-for-Teaching-Support/tests/out/lecture_01")
    transcript_path = Path("C:/Users/nekta/Desktop/code/LLMs-for-Teaching-Support/yt_transcript.txt")

    slides = json.loads((out_dir / "slides_merged.json").read_text(encoding="utf-8"))
    lines = read_transcript(transcript_path)
    print(f"{len(lines)} transcript lines, {len(slides)} slides")

    client = genai.Client(api_key=API_KEY)
    raw = get_starts(client, slides, lines)
    starts = validate(raw, slides, len(lines))
    print(f"Kept {len(starts)} of {len(raw)} slide starts")

    doc = build_document(lines, slides, starts)
    out_file = out_dir / "combined.txt"
    out_file.write_text(doc, encoding="utf-8")
    (out_dir / "starts.json").write_text(json.dumps(starts, indent=2), encoding="utf-8")
    print(f"Saved -> {out_file.resolve()}")


if __name__ == "__main__":
    main()