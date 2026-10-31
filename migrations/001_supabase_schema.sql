-- =============================================================================
-- DocuMind Production Database Schema for Supabase / PostgreSQL
-- Features:
--   - Strict User Isolation via Row Level Security (RLS)
--   - Cascading Foreign Keys
--   - Performant Indexes on user_id and foreign keys
--   - Auto-updating timestamps via Triggers
--   - Support for Private Supabase Storage bucket 'documind-documents'
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Optional pgvector extension for native PostgreSQL embeddings
-- Uncomment if pgvector is enabled in your Supabase project:
-- CREATE EXTENSION IF NOT EXISTS "vector";

-- -----------------------------------------------------------------------------
-- 1. PROFILES TABLE (Linked to Supabase auth.users)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    last_login TIMESTAMPTZ
);

-- -----------------------------------------------------------------------------
-- 2. COLLECTIONS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.collections (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 3. DOCUMENTS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.documents (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    collection_id BIGINT REFERENCES public.collections(id) ON DELETE SET NULL,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    page_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'processing' CHECK (status IN ('uploading', 'processing', 'indexed', 'failed')),
    error_message TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 4. CHAT SESSIONS & MESSAGES TABLES
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

CREATE TABLE IF NOT EXISTS public.chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources_json JSONB,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 5. SAVED NOTES TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.saved_notes (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    document_id BIGINT REFERENCES public.documents(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_citation TEXT,
    tags TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 6. USER PREFERENCES TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_preferences (
    user_id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    answer_style TEXT DEFAULT 'Balanced',
    top_k INTEGER DEFAULT 4,
    llm_provider TEXT DEFAULT 'gemini',
    api_key TEXT,
    temperature REAL DEFAULT 0.2,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 7. PERFORMANCE INDEXES
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_collections_user ON public.collections(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_user ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_collection ON public.documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.documents(status);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON public.chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON public.chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_saved_notes_user ON public.saved_notes(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_notes_doc ON public.saved_notes(document_id);

-- -----------------------------------------------------------------------------
-- 8. AUTOMATIC updated_at TRIGGER FUNCTION
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc', NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_profiles_updated_at ON public.profiles;
CREATE TRIGGER set_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS set_documents_updated_at ON public.documents;
CREATE TRIGGER set_documents_updated_at BEFORE UPDATE ON public.documents FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS set_chat_sessions_updated_at ON public.chat_sessions;
CREATE TRIGGER set_chat_sessions_updated_at BEFORE UPDATE ON public.chat_sessions FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS set_saved_notes_updated_at ON public.saved_notes;
CREATE TRIGGER set_saved_notes_updated_at BEFORE UPDATE ON public.saved_notes FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- -----------------------------------------------------------------------------
-- 9. ROW LEVEL SECURITY (RLS) POLICIES
-- Strict Isolation: Users can NEVER read, insert, update, or delete other users' data.
-- -----------------------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

-- Profiles: user owns profile
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Collections: user owns collections
CREATE POLICY "Users can manage own collections" ON public.collections FOR ALL USING (auth.uid() = user_id);

-- Documents: user owns documents
CREATE POLICY "Users can manage own documents" ON public.documents FOR ALL USING (auth.uid() = user_id);

-- Chat Sessions: user owns sessions
CREATE POLICY "Users can manage own chat sessions" ON public.chat_sessions FOR ALL USING (auth.uid() = user_id);

-- Chat Messages: user owns messages through chat session ownership
CREATE POLICY "Users can manage own chat messages" ON public.chat_messages FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM public.chat_sessions s
        WHERE s.id = chat_messages.session_id AND s.user_id = auth.uid()
    )
);

-- Saved Notes: user owns notes
CREATE POLICY "Users can manage own saved notes" ON public.saved_notes FOR ALL USING (auth.uid() = user_id);

-- User Preferences: user owns preferences
CREATE POLICY "Users can manage own preferences" ON public.user_preferences FOR ALL USING (auth.uid() = user_id);

-- -----------------------------------------------------------------------------
-- 10. PRIVATE SUPABASE STORAGE BUCKET CREATION & ACCESS POLICIES
-- -----------------------------------------------------------------------------
-- Create private bucket 'documind-documents' (50MB max size, PDF only)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'documind-documents',
    'documind-documents',
    false,
    52428800,
    ARRAY['application/pdf']
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = 52428800,
    allowed_mime_types = ARRAY['application/pdf'];

-- Storage RLS: Users can only upload, read, and delete files inside their own folder: user_{user_id}/*
CREATE POLICY "Allow users to upload documents to their folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'documind-documents' AND
    (storage.foldername(name))[1] = 'user_' || auth.uid()::text
);

CREATE POLICY "Allow users to view and download their documents"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'documind-documents' AND
    (storage.foldername(name))[1] = 'user_' || auth.uid()::text
);

CREATE POLICY "Allow users to delete their documents"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'documind-documents' AND
    (storage.foldername(name))[1] = 'user_' || auth.uid()::text
);
