# Pan-and-Scan Research Notes

## Current Implementation

### Manual Tiling (Current Fallback)
- ✅ **Implemented and tested**
- Tested successfully: 2000x1500 image → 6 tiles (with proper overlap)
- Splits large images into 896x896 tiles with 10% overlap
- Processes each tile separately
- Combines results by sorting tiles (top-to-bottom, left-to-right)
- Each tile is preprocessed (aspect ratio preserved) before OCR

### Hugging Face AutoProcessor Pan-and-Scan
- ⚠️ **Planned but needs research**
- The `do_pan_and_scan=True` parameter is mentioned in Hugging Face documentation
- We're using `llama-cpp-python` for inference (GGUF models)
- Need to research if AutoProcessor can be used just for preprocessing/tiling

## Research Questions

1. **AutoProcessor API for Pan-and-Scan**:
   - Where exactly is `do_pan_and_scan=True` used?
   - Is it a parameter to `processor.apply_chat_template()`?
   - Or is it handled differently?
   - Can we use AutoProcessor just for image preprocessing, then pass tiles to llama-cpp-python?

2. **Tile Extraction**:
   - If AutoProcessor creates tiles internally, how do we extract them?
   - Does it return a list of processed images?
   - Or are tiles embedded in the tokenized output?

3. **Integration with llama-cpp-python**:
   - Can we use AutoProcessor for preprocessing only?
   - Then pass individual tiles to llama-cpp-python's `create_chat_completion()`?
   - This would be ideal: use HF's intelligent tiling, llama-cpp's efficient inference

## Next Steps

1. ✅ Test manual tiling first
2. Research AutoProcessor API documentation
3. Check Hugging Face source code if needed
4. Implement HF pan-and-scan integration if feasible
5. Compare results: manual tiling vs HF pan-and-scan

## References

- Hugging Face Gemma 3 Model Card
- Transformers library documentation: `AutoProcessor.apply_chat_template()`
- llama-cpp-python documentation: multimodal chat completion

