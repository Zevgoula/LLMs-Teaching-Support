"""
Split a lecture PDF into two kinds of slides:
  - slides with images: full-slide PNG (to send to Gemini), plus text
  - text-only slides: text only (no Gemini call needed)

Output:
  <out_dir>/slides.json          one record per slide
  <out_dir>/render/slide_NN.png  full-slide PNG, only for slides with images

Usage:
  python split_slides.py lecture.pdf out/lecture_01
"""
import json
import sys
from pathlib import Path
import fitz  # PyMuPDF


def split_pdf(pdf_path: Path, out_dir: Path, dpi: int = 150, min_image_px: int = 50):
    render_dir = out_dir / "render"
    render_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    slides = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()

        # Count only images large enough to matter (skips logos, bullets, etc.)
        real_images = [
            img for img in page.get_images(full=True)
            if img[2] >= min_image_px and img[3] >= min_image_px  # width, height
        ]
        has_image = len(real_images) > 0

        record = {
            "slide_number": i,
            "slide_text": text,
            "has_image": has_image,
            "page_render": None,
            "source": pdf_path.name,
        }

        if has_image:
            out = render_dir / f"slide_{i:02d}.png"
            page.get_pixmap(dpi=dpi).save(out)
            record["page_render"] = str(out.relative_to(out_dir))

        slides.append(record)
        print(f"Slide {i:02d}: {'image -> render' if has_image else 'text only'}")

    out_json = out_dir / "slides.json"
    out_json.write_text(json.dumps(slides, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSlides with images: {sum(s['has_image'] for s in slides)} / {len(slides)}")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python split_slides.py lecture.pdf out/lecture_01")
    split_pdf(Path(sys.argv[1]), Path(sys.argv[2]))