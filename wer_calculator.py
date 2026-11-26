import re
import unicodedata
import jiwer
from scipy.stats import binomtest

FILLERS = {"ε", "εε", "α", "αα", "μμ", "μμμ", "χμ", "ναι", "οκ"}

# Όροι του μαθήματος (γράψτε τους όπως τους θέλετε· κανονικοποιούνται αυτόματα)
"""TERMS_RAW = [
    # Ελληνικοί όροι
    "συνάρτηση", "συναρτήσεις", "όρισμα", "ορίσματα", "παράμετρος", "παραμέτρους",
    "μέθοδος", "μεθόδους", "αντικείμενο", "αντικείμενα", "πίνακας", "πίνακες",
    "συμβολοσειρά", "ακέραιος", "επικεφαλίδα", "σώμα", "εντολή", "εντολές",
    "μεταβλητή", "μεταβλητές", "κώδικα", "γεγονός", "πλήκτρο", "τετράγωνο", "τετράγωνα",

    # Αγγλικοί όροι και αναγνωριστικά κώδικα
    "JavaScript", "functional", "programming", "callable", "objects", "underscore",
    "function", "return", "random", "Math", "floor", "break", "parseInt",
    "onclick", "button", "script", "style", "HTML", "string",
    "pointer", "arrays", "squares", "calculate", "literal", "notation",
]"""    #Για την διάλεξη "Συναρτήσεις JavaScript" - Mathesis - Nikolaos Avouris

TERMS_RAW = [
    # Ελληνικοί όροι (μονολεκτικοί, όπως εμφανίζονται στο κείμενο)
    "κβαντική", "διαπλοκή", "καταχωρητή", "τανιστικό", "γινόμενο",
    "πύλη", "πύλες", "παρατήρηση", "παρατηρούμε", "πιθανότητα",
    "κατάσταση", "καταστάσεις", "συντελεστές", "κύκλωμα", "κυκλώματα",
    "συντονίζονται", "τοπικότητα", "παράδοξο", "αντιδιαισθητικά",
    "ταχύτητα", "φωτός", "κανάλι", "πληροφορία", "κωδικοποιητής",
    "αποκωδικοποιητής", "τηλεμεταφορά", "φάσης", "ακαριαίος",
    "αντίρρηση", "συμμετρικό",

    # Αγγλικοί όροι και ονόματα
    "qubit", "qubits", "Hadamard", "CNOT", "Bell", "GHZ",
    "EPR", "Einstein", "Podolsky", "Rosen",
]

def normalize(text):
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("ς", "σ")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


TERMS = {normalize(t) for t in TERMS_RAW}


def remove_fillers(text):
    return " ".join(w for w in text.split() if w not in FILLERS)


def prepare(path):
    text = open(path, encoding="utf-8").read()
    return remove_fillers(normalize(text))


def evaluate(ref, hyp):
    out = jiwer.process_words(ref, hyp)

    ref_words = ref.split()
    correct = [False] * len(ref_words)
    for chunk in out.alignments[0]:
        if chunk.type == "equal":
            for i in range(chunk.ref_start_idx, chunk.ref_end_idx):
                correct[i] = True

    term_hits = {}
    for term in TERMS:
        positions = [i for i, w in enumerate(ref_words) if w == term]
        if positions:
            term_hits[term] = sum(correct[i] for i in positions) / len(positions)

    term_total = [i for i, w in enumerate(ref_words) if w in TERMS]
    term_acc = sum(correct[i] for i in term_total) / len(term_total) if term_total else 0.0

    return {
        "wer": out.wer,
        "term_accuracy": term_acc,
        "term_count": len(term_total),
        "term_breakdown": term_hits,
        "correct": correct,
    }


def mcnemar_terms(res_a, res_b, ref_words):
    idx = [i for i, w in enumerate(ref_words) if w in TERMS]
    a, b = res_a["correct"], res_b["correct"]
    only_a = sum(a[i] and not b[i] for i in idx)   # μόνο το Α σωστό
    only_b = sum(b[i] and not a[i] for i in idx)   # μόνο το Β σωστό
    n = only_a + only_b
    p = binomtest(min(only_a, only_b), n, 0.5).pvalue if n else 1.0
    return only_a, only_b, p


ref = prepare("whisper-results/reference.txt")

results = {}
for m in ["tiny", "base", "small", "medium", "youtube"]:
    hyp = prepare(f"whisper-results/{m}.txt")

    if not hyp.strip():
        print(f"{m}: ΠΑΡΑΛΕΙΦΘΗΚΕ (κενό αρχείο μετά την επεξεργασία)")
        continue

    r = evaluate(ref, hyp)
    results[m] = r
    print(f"\n{m}")
    print(f"  WER:               {r['wer'] * 100:.2f}%")
    print(f"  Ακρίβεια όρων:     {r['term_accuracy'] * 100:.1f}%  (n={r['term_count']})")
    for term, acc in sorted(r["term_breakdown"].items()):
        print(f"    {term:<15} {acc * 100:.0f}%")

if "youtube" in results and "medium" in results:
    a, b, p = mcnemar_terms(results["youtube"], results["medium"], ref.split())
    print(f"\nMcNemar (YouTube vs medium)")
    print(f"  Μόνο YouTube σωστό: {a}, μόνο medium σωστό: {b}, p = {p:.4f}")