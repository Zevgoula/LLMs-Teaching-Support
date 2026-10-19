"""Central configuration for the UniTutor application.

Everything that used to be hard-coded or spread across modules lives here:
filesystem paths, the Gemini model/prompt, and the course catalogue.

Importing this module never touches the network and never requires an API key,
so it is safe to import from tests.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Filesystem paths ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
#: Uploaded PDFs and microphone recordings written at runtime.
USER_FILES_DIR = DATA_DIR / "user_files"
#: Lecture PDFs that ship with the project (read-only content).
COURSE_MATERIAL_DIR = DATA_DIR / "course_material"
#: Optional SQLite database (see :mod:`db`).
DATABASE_PATH = BASE_DIR / "database.db"

# Keep the runtime directory around even on a fresh clone.
USER_FILES_DIR.mkdir(parents=True, exist_ok=True)

# ── Environment ────────────────────────────────────────────────────
load_dotenv(BASE_DIR / ".env")

#: Name of the Gemini model used for tutoring sessions.
MODEL_NAME = "gemini-2.5-flash"

#: Used by Flask to sign session cookies. Override in production.
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")

#: Number of times a transient 503 from Gemini is retried.
MAX_RETRIES = 3
#: Seconds to wait between retries.
RETRY_DELAY = 5


def get_api_key() -> str:
    """Return the Gemini API key.

    The key is looked up in ``GEMINI_API_KEY`` first, then in the legacy
    ``myenv/api_key/api_key.txt`` file so existing setups keep working.
    """
    key = os.getenv("GEMINI_API_KEY")
    if key and key.strip():
        return key.strip()

    legacy_path = BASE_DIR / "myenv" / "api_key" / "api_key.txt"
    if legacy_path.exists():
        return legacy_path.read_text(encoding="utf-8").strip()

    raise RuntimeError(
        "No Gemini API key found. Create a .env file with GEMINI_API_KEY=... "
        "(see .env.example)."
    )


# ── Prompt ─────────────────────────────────────────────────────────
SYSTEM_INSTRUCTION = """You are an expert university tutor.
                                        First, try to answer the student's questions using the information found in the uploaded document.
                                        If the student asks a relevant question (like math, science, engineering, software development, electrical engineering, physics ect.) that is 
                                        NOT covered in the document, you are allowed to use your general knowledge to explain it to them. However, if you use outside knowledge, you MUST briefly
                                        mention that this information is not in the PDF (e.g., 'Αυτό δεν αναφέρεται στο έγγραφο, αλλά...'). If the student asks a question that is completely unrelated 
                                        to the document, politely inform them that you can only answer questions related to the uploaded PDF and ask them to rephrase their question in a way that relates to the document. 
                                        Do not make up information or provide false answers. If you are unsure about an answer, admit it and suggest that the student consults additional resources or 
                                        seeks help from a human tutor. Always be polite, encouraging, and supportive in your responses."""

#: Message that primes the session once the document has been attached.
SESSION_GREETING = "Γεια! Είμαι έτοιμος να ξεκινήσω το διάβασμα."


# ── Course catalogue ───────────────────────────────────────────────
#: ``file`` values are relative to :data:`COURSE_MATERIAL_DIR`.
# this is to be changed when db is used
COURSES = {
    "digital_logic": {
        "name": "Digital Logic",
        "description": "Boolean algebra, logic gates, and circuits.",
        "pdfs": [
            {
                "title": "Digital Logic Notes",
                "file": "digital_logic/Digital_logic.pdf",

            },
            {
                "title": "Digital Logic Notes 2",
                "file": "digital_logic/Digital_logic_2.pdf",
            },
            {
                "title": "Digital Logic Notes 3",
                "file": "digital_logic/Digital_logic_3.pdf",
            },
        ],
    },
    "telecommunications": {
        "name": "Telecommunications",
        "description": "Communication systems and analogue amplitude modulation.",
        "pdfs": [
            {
                "title": "Συστήματα Επικοινωνιών – Αναλογικές Διαμορφώσεις Πλάτους",
                "file": (
                    "telecommunications/Ενότητα 2η_Συστηματα Επικοινωνιών_"
                    "Αναλογικές Διαμορφώσεις Πλάτους_Μέρος Α_2025.pdf"
                ),
            },
            {
                "title": "Συστήματα Επικοινωνιών – Ψηφιακές Διαμορφώσεις Πλάτους",
                "file": (
                    "telecommunications/Ενότητα 2η_Συστηματα Επικοινωνιών_"
                    "Αναλογικές Διαμορφώσεις Πλάτους_Μέρος Α_2025.pdf"
                ),
            }
        ],
    },
}


# ── Course catalogue ───────────────────────────────────────────────
#: ``file`` values are relative to :data:`COURSE_MATERIAL_DIR`.
# this is to be changed when db is used
RECORDINGS = {
    "Python": {
        "name": "Python Programming",
        "description": "Introduction to Python programming.",
        "pdfs": [
            {
                "title": "Python Lecture 1",
                "file": "python/Python_Basics.pdf",
            },
            {
                "title": "Python Lecture 2",
                "file": "python/Python_Intermediate.pdf",
            }
        ],
    },

        "Java": {
                "name": "Java Programming",
                "description": "Introduction to Java programming.",
                "pdfs": [
                    {
                        "title": "Java Lecture 1",
                        "file": "java/Java_Basics.pdf",
                    },
                    {
                        "title": "Java Lecture 2",
                        "file": "java/Java_Intermediate.pdf",
                    }
                ],
            }
}

def resolve_course_pdf(relative_path: str) -> Path:
    """Resolve a course PDF path and make sure it stays inside the material dir.

    Raises ``ValueError`` if the path escapes :data:`COURSE_MATERIAL_DIR`, which
    also protects against directory-traversal input coming from the browser.
    """
    material_root = COURSE_MATERIAL_DIR.resolve()
    candidate = (material_root / relative_path).resolve()
    if not candidate.is_relative_to(material_root):
        raise ValueError("Invalid course file path.")
    return candidate
