# Document Q&A Bot (RAG)

A command-line bot that answers natural-language questions about a small collection of documents. It retrieves the most relevant passages from a local vector database and asks an LLM to answer **only** from those passages, always citing the source file and page. If the answer isn't in the documents, it says so instead of guessing.

> Built for the Bookxpert AI Intern technical assignment. Python 3.11+.

## Tech stack

| Purpose | Tool | Version |
|---|---|---|
| PDF loading | pypdf | 5.1.0 |
| DOCX loading (bonus) | python-docx | 1.1.2 |
| Chunking | langchain-text-splitters (RecursiveCharacterTextSplitter) | 0.3.2 |
| Embeddings | sentence-transformers, model `all-MiniLM-L6-v2` | 3.3.1 |
| Vector database | ChromaDB (persistent) | 0.5.23 |
| LLM | Google Gemini via `google-genai` (model set by `LLM_MODEL`, default `gemini-2.5-flash`) | latest |
| Config / secrets | python-dotenv | 1.0.1 |

<!-- TODO: run `pip freeze | grep -i -E "pypdf|docx|langchain|sentence|chromadb|genai|dotenv"` and make sure the versions above match what you actually installed. -->

## Architecture

The project is split into two separate steps, as required:

```
INDEXING (python ingest.py) - run once
  data/*.pdf|txt|docx
     -> load text page by page
     -> clean (strip page numbers, repeated headers/footers)
     -> chunk (800 chars, 150 overlap)
     -> batch-embed all chunks (all-MiniLM-L6-v2)
     -> store vectors + text + metadata in ChromaDB (chroma_db/ on disk)

QUERYING (python query.py) - run as often as you like, no re-indexing
  user question
     -> embed the question (same model)
     -> cosine-similarity search in ChromaDB -> top-k chunks
     -> similarity guard: weak match? -> "not found" (LLM never called)
     -> prompt = strict instructions + numbered chunks + question
     -> Gemini generates answer with [filename, page X] citations
     -> print answer + the exact source chunks used
```

**Files**

- `config.py` - all settings in one place (chunk size, top-k, model names, paths)
- `ingest.py` - indexing step
- `query.py` - querying step and interactive loop
- `data/` - the knowledge-base documents
- `chroma_db/` - the persisted vector store (created by `ingest.py`, git-ignored)

## Chunking strategy

I used **recursive character splitting: 800 characters per chunk with 150 characters of overlap**, splitting on paragraph breaks first, then lines, then sentences, then words.

- *Why recursive/paragraph-aware:* it keeps paragraphs and sentences intact where possible, so each chunk is a coherent idea. Blind fixed-size cuts often slice sentences in half.
- *Why 800 characters:* small enough that each chunk is focused (better retrieval precision), large enough to carry meaning on its own.
- *Why 150 overlap:* if an answer sits on a chunk boundary, the overlap means the context isn't lost.
- Chunking is done **per page**, so every chunk keeps an accurate page number. Metadata stored per chunk: source filename + page (PDF) or section (TXT/DOCX).

## Embedding model and vector database

- **Embedding model: `all-MiniLM-L6-v2`.** It runs locally (no API cost or rate limits), is small and fast on a laptop CPU, and gives good quality for English semantic search. Embeddings are normalized and computed in **batches** (`batch_size=64`), never one chunk at a time.
- **Vector DB: ChromaDB.** It persists to disk with almost no setup, stores metadata next to each vector (needed for citations), and supports cosine similarity out of the box. FAISS would be faster at large scale but needs extra code to store metadata, which wasn't worth it for a few documents.
- **LLM: Gemini.** Free tier and a simple API. It is called with temperature 0 and a system prompt that forbids outside knowledge.

## How the bot avoids hallucinating

1. The prompt tells the model to answer only from the supplied excerpts and to reply with a fixed "not found" sentence otherwise.
2. A similarity threshold (`MIN_SIMILARITY`, default 0.25) stops the pipeline before the LLM is even called when nothing relevant is retrieved.
3. Temperature is 0 so answers stay deterministic and close to the text.

## Setup

```bash
git clone <YOUR_REPO_URL>
cd <repo-folder>

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # Windows: copy .env.example .env
# open .env and paste your Gemini API key

python ingest.py                 # step 1: build the index (first run downloads the embedding model)
python query.py                  # step 2: start asking questions
```

Optional: `python query.py --k 6` (retrieve 6 chunks) or `python query.py --ask "your question"` (one-off).

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Free key from https://aistudio.google.com. Put it in `.env`. **Never commit `.env`** (it is in `.gitignore`). |
| `LLM_MODEL` | No | Gemini model name. Default `gemini-2.5-flash`. |
| `TOP_K` | No | Chunks retrieved per question. Default 4. |
| `MIN_SIMILARITY` | No | Below this score the bot answers "not found". Default 0.25. |

## Documents in the knowledge base

<!-- TODO: fill in after you choose your files, e.g.
1. `data/xyz.pdf` - what it is, ~N pages
2. ...
-->

## Example queries

<!-- TODO: after testing, list 5+ real questions and the answer theme you actually got. At least 2 documents. Example format:
1. "What is ...?" -> expected theme: ... (source: file.pdf, page 4)
2. ...
6. Out-of-scope: "Who won the 2018 World Cup?" -> bot replies it couldn't find this in the documents
-->

## Known limitations

<!-- TODO: keep the ones you actually observed while testing. Likely ones: -->
- Scanned/image-only PDFs have no extractable text (no OCR), so they can't be indexed.
- Tables and multi-column layouts can extract in a jumbled order, which hurts retrieval.
- Fixed similarity threshold: a good value for one set of documents may be too strict or too loose for another. Tune `MIN_SIMILARITY`.
- Only top-k chunks are seen by the LLM, so questions that need information spread across many pages (e.g. "summarize the whole document") work poorly.
- The embedding model is English-focused; other languages retrieve worse.
- No re-ranking and no conversation memory: each question is answered independently.
- Header/footer removal is heuristic (repeated lines) and can occasionally miss or over-remove text.
- Requires internet for the Gemini call (embeddings and the vector DB are fully local).
