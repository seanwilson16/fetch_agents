from pathlib import Path
from typing import List
import re

from bs4 import BeautifulSoup
from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# --- CONFIG ---
DOCS_PATH = Path(r"C:/Users/sj05w/animejs/animejs.com/documentation")  # HTTrack root
FAISS_INDEX_DIR = r"C:/Users/sj05w/fetch_projects/animejs_agent/animejs_docs_faiss_index"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120

def extract_clean_text(file_path: Path) -> List[Document]:
    """Extract docs: headings, paragraphs, lists, and code/pre. Remove nav/headers/footers/sidebars."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Remove site chrome
    for sel in ["nav", "header", "footer", "aside", "form", "button"]:
        for tag in soup.find_all(sel):
            tag.decompose()
    for tag in soup.find_all(attrs={"class": re.compile(r"(sidebar|menu|nav|toc)", re.I)}):
        tag.decompose()
    for tag in soup.find_all(attrs={"id": re.compile(r"(sidebar|menu|nav|toc)", re.I)}):
        tag.decompose()

    # Breadcrumb for metadata
    h1 = soup.find("h1")
    h2 = soup.find("h2")
    h3 = soup.find("h3")
    crumb = " / ".join([t.get_text(strip=True) for t in [h1, h2, h3] if t])

    # Collect docs content
    parts: List[str] = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li", "code", "pre"]):
        txt = tag.get_text(" ", strip=True)
        if txt:
            parts.append(txt)

    if not parts:
        return []

    # Collapse whitespace
    cleaned = "\n".join(parts)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    rel = str(file_path.relative_to(DOCS_PATH)) if file_path.is_relative_to(DOCS_PATH) else str(file_path)
    meta = {"source": rel, "breadcrumb": crumb}
    return [Document(page_content=cleaned, metadata=meta)]

# --- Load & parse all HTML files ---
all_docs: List[Document] = []
for file in DOCS_PATH.rglob("*.html"):
    all_docs.extend(extract_clean_text(file))

print(f"✅ Loaded {len(all_docs)} cleaned HTML documents")

# --- Split into chunks ---
splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
chunks = splitter.split_documents(all_docs)
print(f"✅ Split into {len(chunks)} chunks")

# --- Deduplicate ---
seen = set()
deduped: List[Document] = []
for d in chunks:
    key = hash(d.page_content.strip())
    if key not in seen:
        seen.add(key)
        deduped.append(d)
print(f"✅ Deduplicated to {len(deduped)} chunks")

# --- Embed & index ---
embedding = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(deduped, embedding)
Path(FAISS_INDEX_DIR).mkdir(parents=True, exist_ok=True)
vectorstore.save_local(FAISS_INDEX_DIR)

print(f"✅ FAISS index saved to folder: {FAISS_INDEX_DIR}")
print("   (index.faiss and index.pkl should be inside this folder)")
