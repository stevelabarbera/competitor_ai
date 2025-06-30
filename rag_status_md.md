# RAG System Development Status

## 🎯 Project Overview
Building a competitive intelligence RAG system to analyze cybersecurity vendors using local data sources.

## 📁 Current Architecture

### Data Sources
- **`internal_documents/`** - PDFs with sales/marketing collateral and competitor info sheets
- **`output/`** - Web crawler results from competitor websites (first N pages deep)

### Tech Stack
- **Vector DB**: ChromaDB for semantic search
- **Keyword Search**: Whoosh index
- **LLM**: Ollama (model configured in `config_model.txt`)
- **UI**: Gradio interface
- **Chunking**: Custom chunker with configurable size/overlap

### Search Modes
1. **Semantic** - Vector similarity search via ChromaDB
2. **Keyword** - Traditional text search via Whoosh
3. **Hybrid** - Combines both semantic + keyword results
4. **Full** - Uses complete `full_context.txt` file (built by `build_full_context.py`)

## 🔧 Current Files Structure
```
├── search_engine.py      # Main search logic
├── ask.py               # CLI interface
├── ui.py                # Gradio web interface
├── ingest_internal_doc.py # Document ingestion pipeline
├── embedding_config.py   # ChromaDB collection config
├── chunker.py           # Text chunking utilities
├── build_full_context.py # Builds full_context.txt
├── chroma_db/           # ChromaDB storage
├── whoosh_index/        # Whoosh keyword index
├── internal_documents/  # Source PDFs/docs
└── output/              # Crawler results
```

## 🚨 Current Issue: Data Quality Problem

### The Problem
Getting metadata errors when debugging collection:
```
❌ Error: 'NoneType' object has no attribute 'get'
```

**Root Cause**: Some chunks in ChromaDB have `None` metadata instead of proper metadata objects.

### Impact
- Semantic search returns low-quality results
- Model not prioritizing local data effectively
- Debug tools crash on metadata inspection

## 🛠️ Immediate Fixes Identified

### 1. Debug Script Safety (READY TO IMPLEMENT)
```python
# Safe metadata extraction
sources = [meta.get('source', 'Unknown') if meta is not None else 'No Metadata' for meta in metadatas]
```

### 2. Ingestion Validation (READY TO IMPLEMENT)
- Add validation in `flush_batch()` function
- Check for None metadata before adding to ChromaDB
- Validate minimum content length (>10 chars)
- Ensure all required fields exist

### 3. Collection Health Check (READY TO IMPLEMENT)
- Added comprehensive validation function
- Checks for None metadata, empty docs, missing source fields
- Provides sample inspection capabilities

## 📈 Noise Sources Identified

### Primary Issues
1. **Low-relevance chunks** - Vector search returns legally similar but contextually irrelevant content
2. **Too much context** - Multiple chunks dilute the answer quality
3. **Mixed data quality** - Corporate boilerplate mixed with valuable competitor intel

### Contributing Factors
- Lack of metadata filtering at query time
- No semantic reranking after initial retrieval
- Generic corporate content polluting vector space
- Chunk quality inconsistencies

## 🎯 Next Steps Priority Order

### Phase 1: Data Quality (CURRENT FOCUS)
1. ✅ **Fix metadata validation** - Implement safe metadata handling
2. 🔄 **Clean re-ingestion** - Remove corrupted ChromaDB, re-ingest with validation
3. 🔄 **Add health checks** - Implement collection validation tools

### Phase 2: Search Quality Improvements
1. **Metadata filtering** - Filter semantic search by source
2. **Chunk quality validation** - Ensure minimum word count (50-100 words)
3. **Source prioritization** - Prefer `internal_documents` over `output`

### Phase 3: Advanced Features
1. **Semantic reranking** - Re-sort results by question relevance
2. **Hybrid mode optimization** - Better merging of semantic + keyword results
3. **Query preprocessing** - Clean and optimize user questions

## 🧪 Test Cases Available

### Known Good Test
- Mode: semantic
- Should prioritize internal competitor documents
- Expected: Relevant, sourced answers with [filename.txt] citations

### Known Bad Test (Current Issue)
- Debug script crashes on metadata inspection
- Error: `'NoneType' object has no attribute 'get'`
- Provides reproducible failure case

## 🔍 Recent Discoveries

### What Was Working Before
- Semantic search with metadata filtering (`source = cyberboing_test`)
- Clean chunk quality from focused datasets

### What Changed
1. **Full-context mode** addition shifted focus
2. **Hybrid mode** usage increased, mixing keyword junk with semantic results
3. **PDF/output re-ingestion** potentially introduced low-quality data
4. **Lost metadata filtering** - no longer isolating high-quality chunks

## 🚀 Success Metrics
- [ ] Debug tools run without crashes
- [ ] Semantic search returns relevant, local data
- [ ] Model provides accurate citations with [source] format
- [ ] Search feels "snappy, relevant, and exclusive to your data"
- [ ] Less than 5% irrelevant results in top 5 semantic matches

## ⚠️ Known Gotchas
- **ChromaDB batch operations** can fail silently
- **PDF processing** may create empty chunks
- **Metadata consistency** across different ingestion runs
- **Context window limits** with large document sets

---
*Status updated: Need to implement metadata validation fixes and clean re-ingestion*