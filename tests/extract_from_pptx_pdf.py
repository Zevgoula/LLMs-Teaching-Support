"""
Lecture pipeline in one script.

Menu:
  1) Extract: split a PDF into slide text and full-slide PNGs (for slides with images)
  2) Check:   confirm the Gemini output covers every slide with an image
  3) Combine: merge slides_text.json and slides_img.json into slides_merged.json

Usage:
  python lecture_pipeline.py
"""
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

DESC_FILE = "slides_img.json"  # Gemini output


def extract(pdf_path: Path, out_dir: Path, dpi: int = 150, min_image_px: int = 50):
    render_dir = out_dir / "render"            # images for the Gemini step
    all_dir = out_dir / "slides_img_all"       # every slide, for the UI
    render_dir.mkdir(parents=True, exist_ok=True)
    all_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    slides = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        real_images = [
            img for img in page.get_images(full=True)
            if img[2] >= min_image_px and img[3] >= min_image_px
        ]
        has_image = len(real_images) > 0

        # Full-slide PNG for every page, used by the UI
        all_out = all_dir / f"slide_{i:02d}.png"
        page.get_pixmap(dpi=dpi).save(all_out)

        # Full-slide PNG for image slides only, used by the Gemini step
        if has_image:
            page.get_pixmap(dpi=dpi).save(render_dir / f"slide_{i:02d}.png")

        slides.append({
            "slide_number": i,
            "slide_text": text,
            "has_image": has_image,
            "page_render": all_out.relative_to(out_dir).as_posix(),
            "source": pdf_path.name,
        })
        print(f"Slide {i:02d}: {'image' if has_image else 'text only'}")

    (out_dir / "slides_text.json").write_text(
        json.dumps(slides, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Rendered {len(slides)} slides to {all_dir}")
    print(f"Slides with images: {sum(s['has_image'] for s in slides)} / {len(slides)}")


def load_descriptions(out_dir: Path) -> dict:
    """Return {slide_number: description} from slides_img.json (Gemini output)."""
    path = out_dir / DESC_FILE
    if not path.exists():
        print(f"{DESC_FILE} not found in {path.parent.resolve()}")
        return {}

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    desc_by_slide = {}
    for d in data:
        m = re.search(r"(\d+)", str(d.get("img_number", "")))
        if not m:
            print(f"Skipping entry without slide number: {d.get('img_number')}")
            continue
        desc_by_slide.setdefault(int(m.group(1)), []).append(d.get("description", ""))
    print(f"Loaded descriptions for slides: {sorted(desc_by_slide)}")
    return desc_by_slide


def combine(out_dir: Path):
    slides_path = out_dir / "slides_text.json"
    if not slides_path.exists():
        print(f"File not found: {slides_path}")
        return
    slides = json.loads(slides_path.read_text(encoding="utf-8"))
    desc_by_slide = load_descriptions(out_dir)

    merged = []
    for s in slides:
        num = s["slide_number"]
        descs = desc_by_slide.get(num, []) if s["has_image"] else []
        merged.append({
            "slide_number": num,
            "source": s["source"],
            "slide_text": s["slide_text"],
            "has_image": s["has_image"],
            "page_render": s["page_render"],
            "image_descriptions": descs,
        })

    out = out_dir / "slides_merged.json"
    out.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    n_desc = sum(bool(m["image_descriptions"]) for m in merged)
    print(f"Merged {len(merged)} slides, {n_desc} with descriptions -> {out.resolve()}")

def main():
    print("1) Extract  2) Combine")
    choice = input("Choose a step: ").strip()
    path = Path(input("Path (PDF for step 1, output folder for step 2): ").strip())

    while True:
        if choice == "1":
            out_dir = Path(input("Output folder: ").strip())
            out_dir.mkdir(parents=True, exist_ok=True)
            extract(path, out_dir)
        elif choice == "2":
            combine(path)
            break
        else:
            sys.exit("Unknown choice.")
            break
            


if __name__ == "__main__":
    main()