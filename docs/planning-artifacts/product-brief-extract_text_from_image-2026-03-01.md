---
stepsCompleted: [1, 2]
inputDocuments: []
date: 2026-03-01
author: Dima
---

# Product Brief: nl_processing

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

`extract_text_from_image` is a Python module for extracting text from images using LLM vision capabilities (OpenAI API via LangChain). Unlike traditional OCR solutions, it leverages the language model's contextual understanding to produce higher-quality text extraction with markdown formatting that preserves the original document's visual structure. The module supports language-specific extraction -- filtering text by target language (Dutch on initial release) and ignoring text in other languages. It exposes a minimal public interface (a class with sensible defaults and multiple input methods for file paths and OpenCV images) while internally containing benchmarking tools for model selection and quality evaluation. The baseline model is GPT-5 Mini.

---

## Core Vision

### Problem Statement

Traditional OCR tools (Tesseract, etc.) extract text from images without contextual understanding, resulting in lower accuracy -- especially for mixed-language content, complex layouts, and documents where surrounding visual context could improve recognition. They also produce flat text output without formatting information, losing the structural intent of the original document.

### Problem Impact

- Inaccurate text extraction leads to downstream errors in text processing pipelines
- Loss of formatting (headings, emphasis, line breaks) degrades the usefulness of extracted text for further NLP processing
- Mixed-language documents are handled poorly -- OCR extracts everything without language discrimination, requiring additional post-processing to filter by target language
- No built-in mechanism to evaluate extraction quality or compare model performance, making it hard to optimize the pipeline

### Why Existing Solutions Fall Short

- **Classical OCR (Tesseract, etc.):** No contextual understanding, poor formatting preservation, no language filtering capability, inconsistent accuracy on varied image types (photos, screenshots, documents)
- **Cloud OCR APIs (Google Vision, etc.):** Better accuracy but still lack contextual reasoning, no native language-specific filtering, and return flat text without meaningful formatting
- **Direct LLM calls without structure:** LLMs tend to add conversational prefixes/suffixes ("Here is the extracted text:"), making raw output unreliable for programmatic use without structured output enforcement

### Proposed Solution

A Python module (`extract_text_from_image`) that:
- Accepts an image (file path or OpenCV `numpy.ndarray`) and target language as input
- Provides multiple input methods: `extract_from_path(path)` and `extract_from_cv2(image)`
- Uses LLM vision models (GPT-5 Mini baseline, via LangChain) with language-specific prompts to extract text
- Enforces structured output (via Pydantic/LangChain `with_structured_output()`) to ensure clean text without LLM "chatter"
- Returns markdown-formatted text preserving original layout (headings, emphasis, line breaks)
- Defines three error types:
  - `TargetLanguageNotFoundError` -- no text in the target language detected on the image
  - `UnsupportedImageFormatError` -- image format not supported by the OpenAI API
  - `APIError` -- upstream API errors (network, rate limits, auth) propagated with wrapping
- Provides a class-based interface (`ImageTextExtractor`) with sensible defaults -- usable with zero configuration
- Includes internal benchmarking utilities for model comparison using synthetic test images

### Key Differentiators

- **Context-aware extraction:** LLM understands the visual context of the entire image, improving accuracy over character-by-character OCR
- **Markdown formatting preservation:** Output reflects the original document's structure using markdown syntax
- **Language-specific prompting:** Prompts written in the target language guide the model to extract only that language, ignoring others
- **Structured output enforcement:** Uses LangChain structured output to guarantee clean, programmatic results
- **Deterministic evaluation:** Synthetic test images generated with OpenCV (known text rendered onto images) enable exact-match verification. Comparison normalizes both strings by stripping whitespace and markdown formatting, ensuring content accuracy regardless of formatting differences
- **Built-in benchmarking:** Internal tools for comparing models by quality and cost using the synthetic test suite
- **LangChain abstraction:** Easy model swapping without code changes (GPT-5 Mini baseline, configurable to any LangChain-compatible model)
