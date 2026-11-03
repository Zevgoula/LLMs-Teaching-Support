import re
import sys
from pathlib import Path
import os, contextlib
#import pymupdf      #opens pdfs, to count pages, might replace
import chromadb     
import ollama       
from tqdm import tqdm       #progress bar for emb
import json
import pymupdf4llm      #pdf to markdownn (->json)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent)) #to import config,
from config import COURSE_MATERIAL_DIR

PDF_NAME = "python_textbook.pdf"
EMBED_MODEL = "nomic-embed-text"    #model that turns text (pdf) to vectors
LLM_MODEL = "qwen2.5:7b"
CHUNK_WORDS = 250
OVERLAP_WORDS = 40      
TOP_K = 6       
CACHE = Path("chunks_cache.json")   #chunks are saved here


#code that removes a terminal message about an update 
@contextlib.contextmanager  #used in build_chunks()
def suppress_output():
    """Silence everything written to the console"""
    sys.stdout.flush()
    sys.stderr.flush()
    saved = [os.dup(1), os.dup(2)]
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved[0], 1)
        os.dup2(saved[1], 2)
        for fd in saved + [devnull]:
            os.close(fd)

def clean(text):
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)      # picture-text markers
    text = re.sub(r"</?mark>|<br>|\*\*", " ", text)           # html tags
    text = re.sub(r"(?:\b[A-Za-z] ){2,}[A-Za-z]\b",
                  lambda m: m.group().replace(" ", ""), text) # removed some spaces between letters in a word
    text = re.sub(r"-\n(\w)", r"\1", text) 
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_chunks(pdf_path, use_cache=True):
    """creates chunks of the pdf and adds them to chunks_cache.json"""
    """if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))   
    print("Extracting PDF (~20sec)") 

    n_pages = len(pymupdf.open(pdf_path))
    BATCH = 10  #num of pages to be proccessed each time
    chunks = []
    for b in tqdm(range(0, n_pages, BATCH), desc="Extracting pages"):
        page_ids = list(range(b, min(b + BATCH, n_pages))) #how many pages in current batch
        with suppress_output():
            results = pymupdf4llm.to_markdown(str(pdf_path), pages=page_ids, page_chunks=True)
        for page_idx, res in zip(page_ids, results):
            words = clean(res["text"]).split()
            step = CHUNK_WORDS - OVERLAP_WORDS #to not miss context between chunks
            for start in range(0, len(words), step):
                piece = " ".join(words[start:start + CHUNK_WORDS])
                if len(piece.split()) >= 10:
                    chunks.append({"text": piece, "page": page_idx + 1})

    CACHE.write_text(json.dumps(chunks), encoding="utf-8")
    return chunks"""

    """creates chunks of the pdf and adds them to chunks_cache.json"""
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))

    print("Extracting PDF (about 20 seconds)...")
    pages = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)

    chunks = []
    step = CHUNK_WORDS - OVERLAP_WORDS
    for page_idx, res in enumerate(tqdm(pages, desc="Chunking pages")):
        words = clean(res["text"]).split()
        for start in range(0, len(words), step):
            piece = " ".join(words[start:start + CHUNK_WORDS])
            if len(piece.split()) >= 10:
                chunks.append({"text": piece, "page": page_idx + 1})

    CACHE.write_text(json.dumps(chunks), encoding="utf-8")
    return chunks


def embed(texts, kind="document"):
    """raw text -(embed)->vectors/embeddings. Used both for user query and document"""
    texts = [f"search_{kind}: {t}" for t in texts] #changes based on type of search
    return ollama.embed(model=EMBED_MODEL, input=texts)["embeddings"]


def index(chunks):
    """database chroma_db, persistent"""
    client = chromadb.PersistentClient(path="chroma_db") #persistent: does not disappear after scipt closes
   #clear previous data
    try:
        client.delete_collection("book")

    except Exception:
        pass
    #cosine similarity (angle between vectors)
    col = client.create_collection("book", metadata={"hnsw:space": "cosine"})
    for i in tqdm(range(0, len(chunks), 32), desc="Embedding"): #chunk = 250 words ~ 178 chunks total
        batch = chunks[i:i + 32]
        col.add(
            ids=[f"c{i + j}" for j in range(len(batch))],   #id for each chunk
            documents=[c["text"] for c in batch],   #store the raw text in db
            embeddings=embed([c["text"] for c in batch]),   #store the math vectrors through embed
            metadatas=[{"page": c["page"]} for c in batch], #for print
        )
    return col


def ask(col, question):
    """user question -> vectors -> comparison through db -> top_k chunks are returned
        k chunks are passed through the llm +prompt
    """
    q_emb = embed([question], kind="query")
    res = col.query(query_embeddings=q_emb, n_results=TOP_K) 
    docs, metas = res["documents"][0], res["metadatas"][0]  #vectors to text and page numbers

    context = "\n\n".join(f"[Page {m['page']}] {d}" for d, m in zip(docs, metas))
    system = (
        "You answer questions using ONLY the context below. "
        "Cite the page like (p. 12) after each claim. "
        "Use the wording of the context. Do not add terms or facts that are not in it. "
        "If the context does not contain the answer, say exactly: "
        "'The material does not answer this.'"
    )
    reply = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        options={"num_ctx": 4096, "temperature": 0},    #temp = 0:no creativity /num_ctx:context
    )
    print("\n" + reply["message"]["content"])
    print("Retrieved pages:", sorted({m["page"] for m in metas}))
    tps = reply["eval_count"] / (reply["eval_duration"] / 1e9)
    print(f"[{tps:.1f} tokens/s]")


if __name__ == "__main__":
    chunks = build_chunks(Path(COURSE_MATERIAL_DIR) / PDF_NAME) 
    #for c in chunks:
    #    if c["page"] == 56:
    #        print(c["text"][:400])
    print(len(chunks), "chunks. Embedding (one-time thing, takes a few minutes)...")
    col = index(chunks)
    while True:
        q = input("\nQuestion (or 'quit'): ")
        if q.strip().lower() == "quit":
            break
        ask(col, q)