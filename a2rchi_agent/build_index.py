import os
import shutil
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def build_faiss_index(output_dir: str = "a2rchi_index"):
    DATA_FOLDERS = {
        "textbook": "data/textbook",
    }

    docs = []
    print("🔍 Scanning data folders...")

    for doc_type, folder in DATA_FOLDERS.items():
        path = Path(folder)
        if not path.exists():
            print(f"⚠️ Skipping {folder} (not found)")
            continue

        for file in os.listdir(path):
            fpath = path / file
            if file.endswith(".pdf"):
                loader = PyPDFLoader(str(fpath))
            elif file.endswith(".txt"):
                loader = TextLoader(str(fpath))
            else:
                print(f"⛔ Skipping unsupported file: {fpath}")
                continue

            print(f"📄 Loading {fpath}")
            try:
                loaded = loader.load()
                for doc in loaded:
                    doc.metadata["type"] = doc_type
                    doc.metadata["source"] = file
                docs.extend(loaded)
            except Exception as e:
                print(f"❌ Error loading {fpath}: {e}")

    print(f"✅ Loaded {len(docs)} documents.")

    if not docs:
        print("❌ No documents to index. Aborting.")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    print(f"🧩 Split into {len(chunks)} chunks.")

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
        print(f"🧹 Cleared old index at {output_dir}")

    vectorstore = FAISS.from_documents(chunks, OpenAIEmbeddings())
    vectorstore.save_local(output_dir)
    print(f"✅ FAISS index saved to '{output_dir}' with {len(chunks)} chunks.")

if __name__ == "__main__":
    build_faiss_index()
