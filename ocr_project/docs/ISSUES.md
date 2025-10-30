# OCR Project - Open Issues

This document tracks only **open** and **unresolved** issues that require decisions, clarification, or implementation. Resolved issues and decisions are documented in [DECISIONS.md](DECISIONS.md).

---

## 🎯 Decisions Needed Right Now

These are the issues that need your input **before** or **during** v0.1 implementation:

### 1. Testing Strategy - Use Case Review (Issue #5)
**Status**: AWAITING YOUR REVIEW  
**Action**: Review and refine the 10 proposed test use cases  
**Location**: See [DECISIONS.md](DECISIONS.md) Testing Strategy section  
**Priority**: Should be finalized before implementing v0.1 tests

---

### 2. Pan-and-Scan Implementation (Issue #15)

**Status**: ✅ **DECISION MADE** - Try native support with fallback  
**Priority**: HIGH - User expects many files larger than 896x896

**Implementation Strategy** (per user decision):
- **Try First**: Use `do_pan_and_scan=True` in AutoProcessor for images >896x896
- **If it works**: Great! Use native support
- **If it fails**: Implement fallback to manual tiling strategy
- **Error Handling**: Catch exceptions and gracefully fall back

**Implementation Notes**:
- Test during v0.1 implementation
- Log which method was used (native vs manual tiling)
- Manual tiling implementation details will be determined if needed

---

### 3. PDF Processing Strategy (Issue #6)
**Status**: POST v0.1 TESTING - Awaiting your testing  
**Action**: After v0.1 is complete, test PDF processing and report results  
**Priority**: Can be deferred until v0.1 is done

---

## All Open Issues Requiring Decisions

### Issue #1: Vault Merger Integration

**STATUS**: 📋 **DEFERRED to v0.5** - Design decisions needed

**Open Questions**:
- Define exact integration API signature
- Determine integration point in vault merger workflow (after merge? after deduplication?)
- Should OCR files be excluded from deduplication process?
- How should OCR files be handled in link mapping?

**Plan**: Address during v0.5 development per roadmap

---

### Issue #2: Hash-Based Duplicate Detection Implementation

**STATUS**: 📋 **SPECIFIED for v0.2** - Logic defined, implementation pending

**Specification** (per DECISIONS.md):
- Calculate SHA-256 hash (first 8 characters)
- Check hash in existing filenames
- Skip if found in OCR file, continue if found in non-OCR file
- Log both scenarios

**Open Implementation Questions**:
- How to efficiently search for hash in filenames (directory scanning strategy)?
- Hash collision handling strategy (extremely rare but possible)
- Content verification option (should it be implemented)?

**Priority**: v0.2 implementation

---

### Issue #5: Testing Strategy - Use Case Review

**STATUS**: 📋 **AWAITING USER REVIEW** - Use cases proposed, need refinement

**Current State**: 10 test use cases proposed (see DECISIONS.md Testing Strategy section)

**Action Required**: User to review, edit, and approve test use cases before implementation

**Next Step**: User will review and refine the proposed test use cases

---

### Issue #6: PDF Processing Strategy

**STATUS**: 📋 **POST v0.1 TESTING** - Decision pending after testing

**Current Plan**:
- User will test PDF processing using v0.1 prototype once completed
- Test if Gemma 3-12b-it accepts PDF input natively
- Decision on approach will be made based on test results

**Open Questions** (to be answered after testing):
- Does VLM handle PDFs natively or require conversion?
- If conversion needed, what library/approach?
- Multi-page PDF handling strategy?
- Should PDF support be in v0.1 or deferred?

**Action**: Test after v0.1 completion, then decide approach

---

## Open Issues Requiring Implementation

### Issue #7: Concurrent Processing Strategy

**Open Questions**:
- ThreadPoolExecutor vs ProcessPoolExecutor?
- How to share model instance across workers (singleton pattern)?
- GPU sharing strategy for multiple workers?
- Thread safety for CSV writes?
- Resource management approach?

---

### Issue #8: Configuration Validation

**Open Questions**:
- Use pydantic or custom validation?
- Validation rule specifics (ranges, types, required fields)?
- Error message format and clarity?
- Should `--validate-config` flag be implemented?

---

### Issue #9: Model Loading Optimization

**Open Questions**:
- When to load (eager vs lazy)?
- Model caching strategy (memory vs disk)?
- Model warm-up implementation?
- Quantization approach for memory efficiency?

---

### Issue #10: Image Preprocessing Pipeline Optimization

**Open Questions**:
- Exact preprocessing order (validation of proposed pipeline)?
- Caching strategy for preprocessed images?
- GPU-accelerated preprocessing worth it?
- Performance profiling approach?

---

### Issue #11: Result Caching Strategy

**Open Questions**:
- Cache format (JSON metadata, binary images)?
- Cache invalidation strategy (TTL vs manual)?
- Cache location (configurable or fixed)?
- Should caching be optional or always-on?

---

### Issue #12: Memory Management

**Open Questions**:
- Image size threshold for chunking?
- Progressive downscaling implementation details?
- Memory monitoring approach?
- OOM recovery strategy?

---

### Issue #14: Output Quality and Validation

**Open Questions**:
- Quality metrics to implement?
- Confidence score extraction (does model provide this)?
- Quality threshold configuration?
- Manual review workflow?

---

### Issue #15: Pan-and-Scan Implementation

**STATUS**: ✅ **STRATEGY DECIDED** - Try native support, fallback if needed

**Implementation Approach** (per user decision):
- **Primary**: Use `do_pan_and_scan=True` in AutoProcessor when processing images >896x896
- **Fallback**: If native support fails (exception/error), implement manual tiling
- **Testing**: Will be tested during v0.1 implementation

**If Native Support Works**:
- Use `do_pan_and_scan=True` parameter
- Document successful usage
- No manual implementation needed

**If Fallback Needed**:
- Implement manual tiling strategy
- Determine tile size and overlap percentage (likely 896x896 tiles with overlap)
- Text merging strategy to avoid duplicates
- Tile stitching approach
- Handle text split across tiles
- Log which method was used for each image

**Priority**: High - needed for v0.1 to handle user's large image files

---

### Issue #16: CSV Tracking Optimization

**Open Questions**:
- Should we switch to SQLite or optimize CSV?
- Indexing strategy for CSV?
- Performance vs simplicity trade-off?
- Migration path if switching to SQLite?

---

### Issue #17: Input Validation and Security

**Open Questions**:
- Maximum file size limits?
- Path traversal prevention approach?
- Image format validation strategy (MIME type vs file extension)?
- Security testing approach?

---

### Issue #18: Model Security

**Open Questions**:
- Model file checksum validation (which algorithms)?
- Trusted model source list?
- Security documentation requirements?
- Local model file security considerations?

---

### Issue #19: Setup Instructions

**Open Questions**:
- Installation approach documentation style?
- CUDA setup instructions depth?
- UV usage examples needed?
- First-run tutorial content?

---

### Issue #20: Usage Examples

**Open Questions**:
- Which examples are most important?
- API documentation style?
- Command-line vs API examples priority?
- Integration examples detail level?

---

### Issue #21: Configuration Documentation

**Open Questions**:
- Documentation format (inline comments vs separate doc)?
- Recommended values for each parameter?
- Trade-off explanations depth?
- Use case examples (which scenarios)?

---

### Issue #22: Separation of Concerns

**Open Questions**:
- Exact module boundaries (revisit during implementation)?
- How to enforce separation?
- Refactoring approach if boundaries violated?

---

### Issue #23: Dependency Injection

**Open Questions**:
- DI framework or manual injection?
- Injection points (which components)?
- Testing approach with DI?
- Factory pattern implementation?

---

### Issue #24: Result Format Extensibility

**Open Questions**:
- Plugin system complexity level?
- Format interface design?
- Supported formats priority (markdown, JSON, others)?
- Custom formatter API?

---

### Issue #25: Batch Processing Strategy

**Open Questions**:
- Adaptive batch sizing algorithm?
- Hardware detection for batch size recommendations?
- Progress reporting during batches?

---

### Issue #26: Progress Reporting

**Open Questions**:
- Progress bar granularity?
- ETA calculation approach?
- Notification system (if any)?
- Progress reporting for batch vs single file?

---

### Issue #27: Vault Merger Integration Design

**STATUS**: 📋 **DEFERRED to v0.5** - Design pending

**Open Questions**:
- API design details?
- Integration point in workflow?
- OCR file handling in link mapping?
- Error handling integration?

---

### Issue #28: Error Recovery Integration

**STATUS**: 📋 **DEFERRED to v0.5** - Design pending

**Open Questions**:
- Error handling integration approach?
- Error log format for vault merger?
- Failure mode preferences?

---

### Issue #29: Image Metadata Preservation

**Open Questions**:
- Which metadata to preserve?
- Frontmatter format preference?
- Metadata extraction library?
- Performance impact of metadata extraction?

---

### Issue #30: Language Detection

**Open Questions**:
- Language detection library selection?
- When to run detection (always vs optional)?
- Language-specific prompt customization?
- Multi-language document handling?

---

### Issue #31: Structured Text Extraction

**Open Questions**:
- Structure detection approach (model vs post-processing)?
- Which structures to support (lists, tables, headings)?
- Structure preservation format?
- Configuration approach?

---

## Issue Summary

### By Status
- **Deferred**: #1, #6, #27, #28 (awaiting later versions or testing)
- **Pending User Input**: #5 (test use cases review)
- **Implementation Pending**: #2, #7-31 (various stages of planning)

### By Priority
- **v0.1 Blockers**: None (all decisions made, ready for implementation)
- **v0.2 Required**: #2, #4 (duplicate detection, logging)
- **High Priority**: #5, #8, #17, #19, #20
- **Medium Priority**: #6, #7, #9, #10, #12, #14, #21, #22, #25, #26
- **Low Priority**: #11, #15, #16, #23, #24, #29, #30, #31

---

## Notes

- See [DECISIONS.md](DECISIONS.md) for all resolved issues and design decisions
- See [ROADMAP.md](ROADMAP.md) for version milestones and implementation plan
- Issues are removed from this document once resolved and moved to DECISIONS.md

