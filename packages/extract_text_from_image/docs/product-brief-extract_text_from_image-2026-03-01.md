---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments: []
date: 2026-03-01
author: Dima
parentBrief: docs/planning-artifacts/product-brief.md
---

# Product Brief: extract_text_from_image

> For shared project context (technology stack, target users, design principles), see the [shared product brief](../../../docs/planning-artifacts/product-brief.md).

## Executive Summary

`extract_text_from_image` is the first module in the `nl_processing` pipeline. It extracts text from images using LLM vision capabilities. Unlike traditional OCR solutions, it leverages the language model's contextual understanding to produce higher-quality text extraction with markdown formatting that preserves the original document's visual structure. The module supports language-specific extraction — filtering text by target language (Dutch on initial release) and ignoring text in other languages. It accepts images as file paths or OpenCV arrays and returns clean markdown-formatted text.

### What Makes This Module Special

- **Context-aware extraction:** LLM understands the visual context of the entire image, improving accuracy over character-by-character OCR
- **Markdown formatting preservation:** Output reflects the original document's structure using markdown syntax
- **Language-specific prompting:** Prompts written in the target language guide the model to extract only that language, ignoring others
- **Deterministic evaluation:** Synthetic test images generated with OpenCV (known text rendered onto images) enable exact-match verification after normalization
- **Built-in benchmarking:** Internal tools for comparing models by quality and cost using the synthetic test suite

---

## Core Vision

### Problem Statement

Traditional OCR tools (Tesseract, etc.) extract text from images without contextual understanding, resulting in lower accuracy — especially for mixed-language content, complex layouts, and documents where surrounding visual context could improve recognition. They also produce flat text output without formatting information.

### Problem Impact

- Inaccurate text extraction leads to downstream errors in text processing pipelines
- Loss of formatting (headings, emphasis, line breaks) degrades the usefulness of extracted text
- Mixed-language documents are handled poorly — OCR extracts everything without language discrimination
- No built-in mechanism to evaluate extraction quality or compare model performance

### Why Existing Solutions Fall Short

- **Classical OCR (Tesseract, etc.):** No contextual understanding, poor formatting preservation, no language filtering
- **Cloud OCR APIs (Google Vision, etc.):** Better accuracy but still lack contextual reasoning, no language-specific filtering, flat text output

### Proposed Solution

A Python module that:
- Accepts an image (file path or OpenCV `numpy.ndarray`) and target language as input
- Provides two input methods: `extract_from_path(path)` and `extract_from_cv2(image)`
- Uses LangChain directly with language-specific prompts to extract text (`core` provides shared models/exceptions and the prompt loading utility)
- Returns markdown-formatted text preserving original layout (headings, emphasis, line breaks)
- Defines module-specific error types: `TargetLanguageNotFoundError`, `UnsupportedImageFormatError` (defined in `core`)
- Provides a class-based interface (`ImageTextExtractor`) with sensible defaults
- Includes internal benchmarking utilities for model comparison using synthetic test images

---

## Success Metrics

### Acceptance Criteria

1. **Extraction Accuracy:** 100% exact match (after normalization) on the synthetic test suite. Normalization strips all whitespace, line breaks, and markdown formatting characters before comparison.
2. **Extraction Speed:** Each extraction call completes in < 10 seconds (wall clock time).

### Benchmark System

- Synthetic test images generated programmatically with OpenCV (known text rendered onto images)
- Benchmark compares extracted text against known ground truth after normalization
- Benchmark can be run against different LLM models to compare quality and identify the optimal model for cost/quality trade-off

---

## Scope

Note: This module has no MVP/versioning distinction. All features listed below are required for the complete module.

### Core Features

1. **`ImageTextExtractor` class** with sensible defaults (usable with zero configuration)
   - Constructor accepts optional configuration: model name, target language

2. **Two extraction methods:**
   - `extract_from_path(path)` — accepts a file path to an image
   - `extract_from_cv2(image)` — accepts an OpenCV `numpy.ndarray`
   - Both return a `str` with markdown-formatted extracted text

3. **Language-specific prompting:**
   - Prompts written in the target language (Dutch on initial release), stored as JSON in the module directory
   - Extracts only text in the target language, ignores text in other languages
   - Interface supports passing other languages via `Language` enum from `core`

4. **Three typed exceptions** (all defined in `core`):
   - `TargetLanguageNotFoundError` — no text in the target language found on the image
   - `UnsupportedImageFormatError` — image format not supported by OpenAI API
   - `APIError` — wraps upstream API errors

5. **Supported image formats:** those supported by the OpenAI Vision API

6. **Internal benchmarking utilities** (not part of public interface):
   - Synthetic test image generation with OpenCV
   - Extraction quality evaluation: exact match after normalization
   - Model comparison capability

### Module-Specific Dependencies

- `opencv-python` (numpy) — for image input handling and synthetic test image generation

### Out of Scope

- Video processing
- Batch/parallel processing of multiple images
- Result caching
- Support for PIL.Image or raw bytes as input
- OCR fallback or hybrid OCR+LLM approach
- Languages other than Dutch (interface supports them, but only Dutch prompts are implemented and tested)

### Future Vision

- Additional language support (prompts and test suites for other languages)
- Potential expansion of input format support based on downstream pipeline needs
