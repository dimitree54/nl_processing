---
stepsCompleted: [step-01-init, step-02-discovery, step-02b-vision, step-02c-executive-summary, step-03-success, step-04-journeys, step-05-domain-skipped, step-06-innovation-skipped, step-07-project-type, step-08-scoping, step-09-functional, step-10-nonfunctional, step-11-polish, step-12-complete]
inputDocuments: [product-brief-extract_text_from_image-2026-03-01.md]
parentPrd: docs/planning-artifacts/prd.md
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: scientific
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - extract_text_from_image

**Author:** Dima
**Date:** 2026-03-01

> For shared requirements (structured output, configuration, language support, error handling, NFRs), see the [shared PRD](../../../docs/planning-artifacts/prd.md). This document covers only module-specific requirements.

## Executive Summary

`extract_text_from_image` is the first module in the `nl_processing` pipeline. It extracts text from images using LLM vision capabilities, returning clean markdown-formatted text with language-specific filtering. It accepts images as file paths or OpenCV arrays, builds and executes its own LangChain chain (no shared core "engine"), and enforces structured output via the `ExtractedText` model from `core` using tool calling. On initial release, only Dutch language extraction is supported. The module targets developers who need a zero-configuration, black-box text extraction tool.

### What Makes This Special

No ready-made solution combines LLM-based text extraction, language-specific filtering via native-language prompts, markdown formatting preservation, and structured output enforcement in a single module. Core value: one module, one interface, validated quality.

## Success Criteria

### Technical Success

- 100% exact match (after normalization) on the synthetic test suite — primary quality gate
- Each extraction call completes in < 10 seconds (wall clock time)
- Synthetic test images generated with OpenCV serve as both quality benchmarks and regression tests

### Measurable Outcomes

| Metric | Target | Measurement |
|---|---|---|
| Extraction accuracy | 100% exact match (normalized) | Synthetic benchmark suite |
| Extraction latency | < 10 seconds per call | Benchmark timing |
| Integration time | < 5 minutes | Docstring completeness |

## Scope

No MVP/version distinction. All features are required for the single release.

**Post-release extensions:**
- Additional language support (prompts and test suites for other languages)
- Input format expansion based on pipeline needs

**Risk mitigation:**
- **LLM quality:** Benchmarking suite validates extraction accuracy before any prompt or model change is accepted
- **Resource:** Single-developer module with limited scope — low risk

## User Journeys

### Journey 1: First Integration (Happy Path)

**Alex, backend developer**, is building a document processing pipeline. He needs to extract Dutch text from scanned images. He finds `extract_text_from_image` in the nl_processing project.

**Opening Scene:** Alex reads the module docstring. He sees: set `OPENAI_API_KEY`, import `ImageTextExtractor`, call `extract_from_path()`. Three lines of code.

**Rising Action:** He sets his API key, writes a quick test script with a sample image. He calls `extractor.extract_from_path("scan.png")` and gets back a clean markdown string — headings preserved, line breaks matching the original layout, only Dutch text extracted.

**Climax:** Alex drops the module into his pipeline, replacing a cobbled-together combination of OCR + post-processing + language filtering. It works on the first try.

**Resolution:** The module becomes an invisible part of Alex's pipeline. Images go in, correctly formatted Dutch text comes out.

### Journey 2: Error Handling

**Alex** processes a batch of images from various sources. Some contain only English text, some have unsupported formats, and API rate limits are occasionally hit.

**Opening Scene:** Alex's pipeline starts processing. Most images return clean Dutch text.

**Rising Action:** An English-only image raises `TargetLanguageNotFoundError`. A `.bmp` file raises `UnsupportedImageFormatError`. An API rate limit triggers `APIError`. Each is caught, logged, and handled.

**Climax:** Three `except` blocks cover every failure mode. The pipeline handles all errors gracefully.

**Resolution:** Alex's pipeline processes hundreds of images overnight. Successes produce clean text, failures are logged with clear error types, the pipeline never crashes unexpectedly.

### Journey Requirements Summary

| Capability | Revealed By |
|---|---|
| Zero-config instantiation | Journey 1 |
| `extract_from_path()` / `extract_from_cv2()` | Journey 1 |
| Clean markdown output with formatting preservation | Journey 1 |
| Language-specific extraction (Dutch only) | Journey 1 |
| `TargetLanguageNotFoundError` (from `core`) | Journey 2 |
| `UnsupportedImageFormatError` (from `core`) | Journey 2 |
| `APIError` (from `core`) | Journey 2 |

## Developer Tool Specific Requirements

### API Surface

**Public interface:**

```python
from nl_processing.extract_text_from_image.service import ImageTextExtractor

extractor = ImageTextExtractor()
text = extractor.extract_from_path("image.png")
text = extractor.extract_from_cv2(cv2_image)
```

**Exceptions** (all from `core`): `TargetLanguageNotFoundError`, `UnsupportedImageFormatError`, `APIError`

**Constructor (all parameters optional, sensible defaults):**
- `model` — LLM model name (default: `gpt-5-nano`). GPT-5 Mini is used as an evaluation baseline; the default is downgraded to the cheapest model that still passes the synthetic benchmark suite without quality loss.
- `language` — target language as `Language` enum from `core` (default: `Language.NL`)

### Implementation Considerations

- Dependencies: `opencv-python` (numpy) — module-specific; `core` handles LangChain/OpenAI
- Language-specific prompts stored as JSON in module directory, loaded by `core` utilities
- Uses LangChain directly for all LLM interaction; `core` provides shared models/exceptions and the prompt loading utility.

## Functional Requirements

### Text Extraction

- FR1: Developer can extract text from an image by providing a file path
- FR2: Developer can extract text from an image by providing an OpenCV numpy.ndarray
- FR3: Module extracts only text in the specified target language from the image
- FR4: Module ignores text in languages other than the target language
- FR5: Module returns extracted text as a markdown-formatted string
- FR6: Module preserves the original document's visual structure in markdown (headings, emphasis, line breaks)

### Error Handling (Module-Specific)

- FR7: Module raises `TargetLanguageNotFoundError` (from `core`) when no text in the target language is detected
- FR8: Module raises `UnsupportedImageFormatError` (from `core`) when the image format is not supported by the OpenAI API
- FR9: Module raises `TargetLanguageNotFoundError` when the image contains no text at all

### Benchmarking (Internal)

- FR10: Module includes a utility to generate synthetic test images with known text using OpenCV
- FR11: Module includes a utility to compare extracted text against ground truth after normalization
- FR12: Normalization strips whitespace, line breaks, and markdown formatting before comparison
- FR13: Module includes a utility to run the benchmark suite against a specified model for quality comparison

## Non-Functional Requirements (Module-Specific)

### Performance

- NFR1: Each extraction call completes in < 10 seconds wall clock time (QA gate)
- NFR2: Module does not perform unnecessary image processing or conversions that add latency

### Integration

- NFR3: Module supports all image formats accepted by the OpenAI Vision API

### Module-Specific Dependencies

- NFR4: `opencv-python` (numpy) for image handling and synthetic test generation
