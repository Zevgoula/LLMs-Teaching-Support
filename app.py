"""UniTutor — HTTP layer.

All routing and request/response handling lives here; document ingestion and
model calls are delegated to :mod:`services.llm`, and every path/model/prompt
setting comes from :mod:`config`.
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import config
from services import llm

from db import init_db

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Initialize database tables on app start
with app.app_context():
    init_db()

#: Widest sensible cap for an upload (Gemini's inline limit is 50 MB).
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

#: The demo supports a single active tutoring session, kept in memory.
_chat_session = None


def get_chat_session():
    """Return the currently active Gemini chat session (or ``None``)."""
    return _chat_session


def set_chat_session(chat_session) -> None:
    """Replace the active Gemini chat session."""
    global _chat_session
    _chat_session = chat_session


def _is_pdf(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[-1].lower() == "pdf"


def _start_session_with(pdf_path) -> None:
    """Create a fresh tutoring session grounded on ``pdf_path``."""
    set_chat_session(llm.create_tutor_session(pdf_path))

# ── Pages ──────────────────────────────────────────────────────────


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/courses")
def courses():
    return render_template("courses.html", courses=config.COURSES)

@app.route("/recorder")
def recorder():
    return render_template("recorder.html")


# ── PDF loading ────────────────────────────────────────────────────


@app.route("/load_course_pdf", methods=["POST"])
def load_course_pdf():
    """Open a lecture PDF that ships with the project."""
    payload = request.get_json(silent=True) or {}
    relative_file = (payload.get("file") or "").strip()

    if not relative_file:
        return jsonify({"error": "No course file specified."}), 400

    try:
        pdf_path = config.resolve_course_pdf(relative_file)
    except ValueError:
        return jsonify({"error": "Invalid course file path."}), 400

    if not pdf_path.is_file():
        return jsonify({"error": "PDF file not found."}), 404

    try:
        _start_session_with(pdf_path)
        return jsonify(
            {"status": "success", "message": "Course PDF loaded and AI is ready!"}
        )
    except Exception as exc:  # noqa: BLE001 - message is shown to the user
        return jsonify({"error": str(exc)}), 500

@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle a student-uploaded PDF."""
    if "pdf_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["pdf_file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400
    if not _is_pdf(file.filename):
        return jsonify({"error": "Only PDF files are supported."}), 400

    save_path = config.USER_FILES_DIR / "temp_upload.pdf"
    file.save(save_path)

    try:
        _start_session_with(save_path)
        return jsonify(
            {"status": "success", "message": "PDF Uploaded and AI is ready!"}
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    """Send a question to the active tutoring session."""
    chat_session = get_chat_session()
    if not chat_session:
        return jsonify({"error": "Please upload a PDF first!"}), 400

    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Empty message."}), 400

    for attempt in range(config.MAX_RETRIES):
        try:
            return jsonify({"reply": llm.ask(chat_session, user_message)})
        except Exception as exc:  # noqa: BLE001
            if llm.is_context_exhausted(exc):
                return jsonify(
                    {
                        "error": (
                            "Context window exceeded. Please upload a new PDF "
                            "to start a fresh session."
                        )
                    }
                ), 429
            if llm.is_transient(exc) and attempt < config.MAX_RETRIES - 1:
                time.sleep(config.RETRY_DELAY)
                continue
            if llm.is_transient(exc):
                return jsonify(
                    {
                        "error": (
                            "Gemini is overloaded right now. "
                            "Please try again in a moment."
                        )
                    }
                ), 503
            return jsonify({"error": str(exc)}), 500


# ── Audio recorder ─────────────────────────────────────────────────


@app.route("/save_recording", methods=["POST"])
def save_recording():
    """Persist a microphone recording (WAV) sent from the browser."""
    if "audio_file" not in request.files:
        return jsonify({"status": "error", "message": "No audio file received"}), 400

    audio_file = request.files["audio_file"]
    #timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #filename = f"recording_{timestamp}.wav"
    filename = f"recording.wav"
    save_path = config.USER_FILES_DIR / "audio" / filename
    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        audio_file.save(save_path)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"status": "error", "message": str(exc)}), 500

    return jsonify({"status": "success", "filename": filename}), 200


@app.route("/run_docu_video_pipeline", methods=["POST"])
def run_docu_video_pipeline():
    """Kick off the WAV -> MP4 -> YouTube pipeline for a saved recording.

    (ffmpeg conversion + YouTube upload) runs in a background
    subprocess so the HTTP request can return immediately; stdout/stderr are
    captured to a log file next to the audio so failures can be inspected.
    """
    payload = request.get_json(silent=True) or {}
    # Never trust a client-supplied path: keep only the bare file name so the
    # value can't escape the audio directory (e.g. "..\\..\\secret").
    filename = Path((payload.get("filename") or "recording.wav")).name

    audio_path = config.USER_FILES_DIR / "audio" / filename
    if not audio_path.is_file():
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Recording not found: {filename}",
                }
            ),
            404,
        )

    script_path = Path(__file__).resolve().parent / "scripts" / "docu_video_pipeline.py"
    if not script_path.is_file():
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Pipeline script is missing (scripts/docu_video_pipeline.py).",
                }
            ),
            500,
        )

    log_path = config.USER_FILES_DIR / "audio" / "pipeline.log"
    try:
        # Run in the project root so relative paths (cover.png, token.json,
        # client.json) inside the pipeline resolve the same way as when it is
        # launched by hand. Launch detached so it outlives the request.
        log_file = open(log_path, "a", encoding="utf-8")
        subprocess.Popen(
            [sys.executable, str(script_path), str(audio_path)],
            cwd=str(Path(__file__).resolve().parent),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )
    except Exception as exc:  # noqa: BLE001 - message is shown to the user
        return jsonify({"status": "error", "message": str(exc)}), 500

    return (
        jsonify(
            {
                "status": "success",
                "message": f"Pipeline started for {filename}. See {log_path.name} for progress.",
            }
        ),
        200,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)