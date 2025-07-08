# 🧩 Modular RAG System Implementation Plan

## 📋 **Phase 1: Foundation (Start Here)**

### 1.1 Company Tag Parser Core
**File**: `company_parser.py` (50 lines)
- **Job**: Parse `Company_Names:` lines from files
- **Input**: File content string
- **Output**: Dictionary of company mappings
- **Test**: Parse one file, print results

### 1.2 Company Mapping Storage
**File**: `company_storage.py` (30 lines)
- **Job**: Save/load company mappings to JSON
- **Input**: Company dictionary
- **Output**: Persistent JSON file
- **Test**: Save mappings, restart, load successfully

### 1.3 Alias Resolver
**File**: `alias_resolver.py` (25 lines)
- **Job**: Convert any alias to primary company name
- **Input**: "ESPN" → Output: "Disney"
- **Test**: Test all known aliases

---

## 📋 **Phase 2: Document Processing**

### 2.1 Content Chunker
**File**: `content_chunker.py` (40 lines)
- **Job**: Split documents into chunks (min 50 chars)
- **Input**: Raw document text
- **Output**: List of text chunks
- **Test**: Chunk sample document, verify no loss

### 2.2 Metadata Enricher
**File**: `metadata_enricher.py` (35 lines)
- **Job**: Add company metadata to chunks
- **Input**: Chunk + company info
- **Output**: Chunk with metadata
- **Test**: Enrich sample chunk, verify metadata

### 2.3 File Processor
**File**: `file_processor.py` (45 lines)
- **Job**: Process single file end-to-end
- **Input**: File path
- **Output**: Processed chunks with metadata
- **Test**: Process one file, verify output

---

## 📋 **Phase 3: Database Integration**

### 3.1 ChromaDB Manager
**File**: `chroma_manager.py` (60 lines)
- **Job**: Handle ChromaDB operations
- **Input**: Chunks with metadata
- **Output**: Stored in ChromaDB
- **Test**: Store/retrieve sample chunks

### 3.2 Batch Ingestion
**File**: `batch_ingestion.py` (40 lines)
- **Job**: Process multiple files in batches
- **Input**: Directory path
- **Output**: Batch processing stats
- **Test**: Process small directory

### 3.3 Company Filter
**File**: `company_filter.py` (30 lines)
- **Job**: Filter search results by company
- **Input**: Search query + company name
- **Output**: Filtered results
- **Test**: Search with/without company filter

---

## 📋 **Phase 4: Search Enhancement**

### 4.1 Semantic Search
**File**: `semantic_search.py` (35 lines)
- **Job**: ChromaDB semantic search with company filter
- **Input**: Query + company
- **Output**: Semantic results
- **Test**: Search for "pricing" in specific company

### 4.2 Keyword Search
**File**: `keyword_search.py` (40 lines)
- **Job**: Whoosh keyword search with company filter
- **Input**: Query + company
- **Output**: Keyword results
- **Test**: Keyword search with company filter

### 4.3 Result Combiner
**File**: `result_combiner.py` (35 lines)
- **Job**: Combine semantic + keyword results
- **Input**: Two result sets
- **Output**: Ranked combined results
- **Test**: Combine sample results, verify ranking

---

## 📋 **Phase 5: Integration & Testing**

### 5.1 Search Interface
**File**: `search_interface.py` (50 lines)
- **Job**: Main search API
- **Input**: User query + options
- **Output**: Final search results
- **Test**: End-to-end search scenarios

### 5.2 System Coordinator
**File**: `system_coordinator.py` (30 lines)
- **Job**: Orchestrate all components
- **Input**: High-level commands
- **Output**: System operations
- **Test**: Full system integration

### 5.3 Validation Suite
**File**: `validation_suite.py` (60 lines)
- **Job**: Test all success metrics
- **Input**: Test queries
- **Output**: Pass/fail results
- **Test**: Verify no cross-contamination

---

## 🎯 **Implementation Strategy**

### **Option A: Sequential (Recommended)**
1. Build Phase 1 completely
2. Test Phase 1 thoroughly
3. Move to Phase 2, etc.

### **Option B: Parallel**
1. Different people work on different phases
2. Define clear interfaces between phases
3. Integrate at the end

### **Option C: Vertical Slice**
1. Pick one company (e.g., Tenable)
2. Build minimal version for just that company
3. Expand to other companies

---

## 🔧 **Quick Start: Phase 1 Only**

```bash
# Step 1: Just parse company tags
python company_parser.py internal_data/tenable.txt

# Step 2: Save mappings
python company_storage.py

# Step 3: Test alias resolution
python alias_resolver.py "tenable.com"
```

**Expected Output:**
```
✅ Found: Tenable -> [Tenable, Tenable.com, Tenable_com]
✅ Saved: company_mappings.json
✅ Resolved: "tenable.com" -> "Tenable"
```

---

## 📊 **Benefits of This Approach**

### ✅ **Smaller Context Windows**
- Each file: 25-60 lines
- Clear, focused purpose
- Easy to understand and debug

### ✅ **Parallel Development**
- Multiple people can work simultaneously
- Clear interfaces between components
- Easier code reviews

### ✅ **Incremental Testing**
- Test each component independently
- Catch issues early
- Build confidence progressively

### ✅ **Easier Maintenance**
- Modify one component without affecting others
- Clear separation of concerns
- Easier to add new features

---

## 🎯 **Next Steps**

1. **Choose your approach**: Sequential, Parallel, or Vertical Slice?
2. **Start with Phase 1.1**: Company Tag Parser Core
3. **Get that working perfectly**
4. **Move to Phase 1.2**: Company Mapping Storage
5. **Continue systematically**

Each phase builds on the previous one, but with clear boundaries and testable outcomes. This way, you're never overwhelmed by context, but each piece contributes to the whole solution.

Would you like me to start with just **Phase 1.1** - the 50-line Company Tag Parser Core?