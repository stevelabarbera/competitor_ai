# Keyword Index RAG - Quick Reference & Tasks

## Current State
- **Schema**: `company`, `path`, `content` (with stemming)
- **Sources**: `internal_data/` + `output/` directories
- **Search**: Basic keyword + quality filter (50+ words)
- **Missing**: Company filtering in search function

## File Issues
- `build_keyword_index.py` - incomplete/duplicate
- `build_woosh_index.py` - main implementation
- Need consolidation

## Priority Tasks

### Task 1: Core Fixes (1-2 hours)
**Assignee**: Backend dev
- Merge build scripts into single file
- Add company parameter to search function
- Complete error handling for index operations
- Test basic search + company filtering

### Task 2: Search Enhancement (2-3 hours)
**Assignee**: Search specialist
- Implement company-specific filtering in `search_keyword_enhanced()`
- Add query preprocessing improvements
- Optimize result scoring/ranking
- Add search result metadata

### Task 3: Index Management (3-4 hours)
**Assignee**: Infrastructure dev
- Create index update/refresh mechanism
- Add index health checks
- Implement proper logging
- Add configuration management

### Task 4: Integration & Testing (2-3 hours)
**Assignee**: QA/Integration dev
- End-to-end testing with RAG system
- Performance benchmarking
- Error case handling
- Documentation updates

## Quick Fixes Needed

### Missing Company Filter
```python
# Current search function lacks company filtering
def search_keyword_enhanced(question: str, company: str = None, n_results: int = 5):
    # Add: company filter logic here
```

### File Consolidation
- Choose: `build_woosh_index.py` as primary
- Delete: `build_keyword_index.py` 
- Ensure: Complete `collect_documents_from_directory()` function

### Error Handling
- Add: Index existence checks
- Add: Query parsing fallbacks
- Add: Empty result handling

## Success Criteria
- [ ] Company filtering works
- [ ] Single build script
- [ ] Error handling complete
- [ ] Integration tested with RAG

## Next Phase Ideas
- Query result caching
- Incremental index updates
- Hybrid vector+keyword search
- Performance monitoring