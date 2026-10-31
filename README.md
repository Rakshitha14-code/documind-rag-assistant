# 📚 DocuMind — A Personal Document Workspace

> **"Your documents. Your knowledge. One workspace."**

DocuMind is an AI-powered document intelligence and productivity platform built specifically for students and researchers. It enables users to organize multi-page PDF documents (lecture notes, textbooks, research papers), perform natural language Q&A with verifiable page citations, compare documents side-by-side, save key insights to a research notebook, and export structured study reports to PDF and Microsoft Word (DOCX).

---

## 🎨 Design System & Philosophy

DocuMind features a visual design inspired by professional creative tools (such as Adobe products):
- **Primary Deep Red**: `#B42332` (Accents, primary action buttons, active states)
- **Main Creamy Background**: `#FFF9F0` (Warm, non-fatiguing reading atmosphere)
- **Soft Blush**: `#F7E8E5` (Card highlights and category badges)
- **White Panels**: `#FFFFFF` (Elevated content containers with subtle shadows)
- **Primary Text**: `#252525` (High-contrast typography using Google Fonts `Outfit` and `Inter`)
- **Secondary Text**: `#706B68` (Metadata, captions, and secondary details)
- **Borders**: `#E9DED7` (Refined divider lines)
- **Success & Badges**: `#287D55` (Verified and indexed status pills)

---

## 🛠️ Technology Stack

- **Frontend & App Framework**: [Streamlit](https://streamlit.io/)
- **Application Database**: SQLite3 (Users, document metadata, chat history, saved notes, collections, preferences)
- **Vector Storage**: [ChromaDB](https://www.trychroma.com/) (Persistent local cosine-similarity vector store)
- **Local Neural Embeddings**: [Hugging Face Sentence-Transformers](https://www.sbert.net/) (`all-MiniLM-L6-v2`, 100% offline & local)
- **PDF Extraction**: [PyPDF](https://pypdf.readthedocs.io/)
- **Document & Report Generation**: [ReportLab](https://www.reportlab.com/) (PDF exports) and [python-docx](https://python-docx.readthedocs.io/) (DOCX exports)
- **Authentication & Security**: [bcrypt](https://github.com/pyca/bcrypt/) password hashing with per-user tenant isolation
- **Configurable LLM Backend**: Google Gemini (`gemini-1.5-flash`), OpenAI (`gpt-4o-mini`), or Groq (`llama-3.1-8b-instant`) with automatic fallback to local evidence inspection when keys are unconfigured.

---

## 🚀 Key Features

### 1. Split-Screen Authentication
- Deep red branded hero area featuring CSS document illustrations and product pillars.
- Creamy-white authentication card with tabbed Sign In and Account Registration.
- Parameterized SQLite queries, email uniqueness checks, and bcrypt salted password hashing.

### 2. Comprehensive Dashboard
- Real metrics: total documents, indexed ready documents, knowledge chunks, questions asked.
- Interactive getting-started guide with actionable empty states.
- Recent documents list with status indicators and quick-navigation shortcuts.

### 3. Multi-PDF Document Manager
- Batch upload of multiple PDF documents with drag-and-drop.
- Robust validation: PDF magic bytes (`%PDF-`), size verification (50MB cap), and encryption detection.
- Detection of scanned PDFs lacking extractable text layers.
- Duplicate prevention: avoids redundant re-indexing of identical files.
- Document collections (e.g., Biology, Machine Learning, Economics).
- Safe document deletion with automatic pruning of ChromaDB vectors.

### 4. Grounded Multi-PDF Chat & Page Citations
- Semantic search across user's selected documents or entire library.
- Multi-turn conversation sessions with create, rename, and delete capabilities.
- Strict anti-hallucination prompt: answers strictly based on retrieved excerpts.
- Verifiable citations: expandable source drawers displaying exact PDF filenames, page numbers, match percentages, and verbatim excerpts.
- One-click "Save Answer to Notes" directly from chat.

### 5. Document Comparison
- Multi-select two or more documents to contrast on a specific topic.
- Structured analysis: Executive Summary, Key Similarities, Divergent Claims, Missing Information, and a markdown comparison table.
- Direct inspection of underlying evidence excerpts per document.

### 6. Saved Notes & Notebook
- Rich markdown notebook for capturing insights, equations, and answers.
- Direct linking of notes to source documents and page numbers.
- Live search by title, content, or tags.
- Full editing and deletion support.

### 7. Publication-Ready Exports
- Generate structured study summaries and executive research briefs.
- Export as styled PDF with DocuMind headers and tables via ReportLab.
- Export as editable Word (.docx) documents via python-docx.

### 8. Settings & Preferences
- Fine-tune top-K retrieved chunks (2 to 10), generation temperature, and answer style (Balanced, Concise, Detailed).
- Configure LLM provider (Gemini, OpenAI, Groq) and API keys.
- Update profile details or change account password.
- View real-time active storage backend status (Local Persistent Engine or Supabase Managed Cloud).
- Download full portable JSON workspace snapshots (`documind_workspace_backup.json`) for disaster recovery.
- Create on-demand transactional database backups (`documind_backup_*.db`).

---

## 📂 Project Architecture

```
multi-pdf-rag/
├── app.py                      # Main Streamlit application and navigation router
├── rag_pipeline.py             # Root RAG forwarder
├── requirements.txt            # Production dependencies
├── .env.example                # Sample environment configuration template
├── .gitignore                  # Git exclusions for databases, chroma, and secrets
├── pytest.ini                  # Pytest configuration
├── README.md                   # Comprehensive project documentation
│
├── migrations/                 # Cloud SQL migrations
│   └── 001_supabase_schema.sql # PostgreSQL schema, RLS policies, and private bucket definition
│
├── src/                        # Core backend modules
│   ├── database.py             # SQLite models, parameterized queries, and bcrypt hashing
│   ├── auth.py                 # Session state handling, cryptographic tokens, and auth guards
│   ├── supabase_client.py      # Resilient Supabase client & connection validator
│   ├── storage_provider.py     # Unified storage abstraction (Supabase S3 & Local filesystem)
│   ├── styles.py               # Adobe-inspired design system CSS injection
│   ├── document_processor.py   # PDF validation, text extraction, and recursive chunking
│   ├── embeddings.py           # Hugging Face sentence-transformers local model wrapper
│   ├── vector_store.py         # ChromaDB persistent client and tenant isolation
│   ├── rag_pipeline.py         # Grounded retrieval, prompt assembly, and LLM generation
│   ├── comparison.py           # Multi-document comparative synthesis engine
│   ├── report_generator.py     # PDF & DOCX export generator
│   ├── backup.py               # Workspace JSON export, SQLite backup, and disaster recovery plan
│   ├── migrations.py           # Non-destructive SQLite WAL migration runner
│   │
│   └── views/                  # Streamlit UI page views
│       ├── login_view.py       # Centered login & signup SaaS card
│       ├── dashboard_view.py   # Real metrics, quick upload/chat, and recent documents overview
│       ├── documents_view.py   # Multi-PDF upload, indexing, collections, and cascading delete
│       ├── chat_view.py        # Multi-document chat with verifiable page citations
│       ├── compare_view.py     # Cross-document comparison workspace
│       ├── notes_view.py       # Saved notes & research notebook with direct source links
│       ├── exports_view.py     # Publication-ready study report generator (PDF & DOCX)
│       └── settings_view.py    # Preferences, profile, security, and storage/backup management
│
├── tests/                      # Automated test suite (37 tests)
│   ├── test_auth.py            # Authentication, registration, and hashing tests
│   ├── test_documents.py       # Extraction, chunking, and ChromaDB vector tests
│   ├── test_rag.py             # Grounding, prompts, and missing-key fallback tests
│   ├── test_authorization.py   # Multi-tenant isolation and security tests
│   ├── test_production_storage.py # Production storage lifecycle, persistence, and restart tests
│   └── test_settings_and_backup.py # Workspace exports, DB snapshots, and recovery tests
│
├── data/                       # Local persistent storage (gitignored)
│   ├── documind.db             # WAL-enabled SQLite database
│   ├── backups/                # On-demand transactional database snapshots
│   └── uploads/                # User-isolated PDF document storage (`user_{id}/`)
│
└── chroma_db/                  # Local persistent Chroma vector store (gitignored)
```

---

## 💻 Local Setup & Installation

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Windows, macOS, or Linux

### 2. Environment Setup
Clone the repository and activate your virtual environment:

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Configure your preferred LLM provider in `.env`:
```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
```
*(You can obtain a free Gemini API key from [Google AI Studio](https://aistudio.google.com/)).*

> **Zero-Configuration Fallback**: If no API key is set, DocuMind operates cleanly in offline inspection mode: it extracts, chunks, vectorizes, performs semantic retrieval, displays exact citations and relevance scores, and allows full notes/exports without crashing.

### 5. Launch the Application
Run locally with Streamlit:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## ☁️ Supabase Cloud Storage & PostgreSQL Setup (Optional)

DocuMind runs out of the box with the local persistent engine (`data/documind.db` + ChromaDB + `data/uploads`). When deploying to cloud environments (Streamlit Community Cloud, Render, Fly.io, etc.), configure managed Supabase storage and database:

1. **Create a Supabase Project**:
   - Go to [database.new](https://database.new) and create a free project.
2. **Execute Database Migration**:
   - Open the **SQL Editor** in the Supabase Dashboard.
   - Open [migrations/001_supabase_schema.sql](migrations/001_supabase_schema.sql) and click **Run**.
   - This creates all tables (`profiles`, `collections`, `documents`, `chat_sessions`, `chat_messages`, `saved_notes`, `user_preferences`), performance indexes, auto-updating triggers, and strict Row Level Security (RLS) policies.
3. **Verify Storage Bucket**:
   - Navigate to **Storage** in the Supabase Dashboard.
   - Ensure the private bucket `documind-documents` exists (automatically created by the SQL migration).
4. **Set Environment Variables**:
   In your hosting provider's environment variables (or `.env`):
   ```ini
   SUPABASE_URL=https://<your-project-ref>.supabase.co
   SUPABASE_KEY=ey...  # Anon / Public Key
   SUPABASE_SERVICE_ROLE_KEY=ey...  # Service Role Key (Keep confidential)
   SUPABASE_STORAGE_BUCKET=documind-documents
   DOCUMIND_STORAGE_MODE=auto
   ```

---

## 🧪 Running the Automated Test Suite

DocuMind includes 37 automated tests covering the entire application lifecycle:

```bash
python -m pytest -v
```

To run individual test suites:
```bash
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_documents.py -v
python -m pytest tests/test_rag.py -v
python -m pytest tests/test_authorization.py -v
python -m pytest tests/test_production_storage.py -v
python -m pytest tests/test_settings_and_backup.py -v
```

---

## 🔒 Security & Tenant Isolation

- **Password Hashing**: Plaintext passwords are never stored; salted bcrypt hashes are generated with standard work factor.
- **SQL Injection Prevention**: All SQL queries strictly use parameterized bindings (`?` or `%s`).
- **Cryptographic Session Tokens**: HMAC-SHA256 tokens enable persistent session restoration without exposing raw credentials.
- **Multi-Tenant Physical Isolation**:
  - Vector embeddings are isolated into per-user Chroma collections: `user_{user_id}_knowledge`.
  - PDF files are strictly isolated into dedicated directories: `user_{user_id}/`.
  - Path traversal and cross-tenant folder accesses are rejected with `PermissionError`.
- **Source Grounding**: All retrieved citations reference actual chunk page metadata; ungrounded facts or unretrieved sources are rejected.

---

## 📄 License
MIT License. Built for student productivity, research excellence, and enterprise document intelligence.

