---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-02'
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - docs/planning-artifacts/prd.md
  - docs/planning-artifacts/architecture.md
  - nl_processing/extract_text_from_image/docs/product-brief-extract_text_from_image-2026-03-01.md
  - nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md
workflowType: 'architecture'
project_name: 'nl_processing'
user_name: 'Dima'
date: '2026-03-02'
scope: 'extract_text_from_image'
parentArchitecture: docs/planning-artifacts/architecture.md
---

# Architecture Decision Document — extract_text_from_image

> For shared architectural decisions (core package, code style, patterns, project structure), see the [shared architecture](../../../docs/planning-artifacts/architecture.md). This document covers only module-specific decisions.

---

## Module-Specific Architectural Decisions

### Decision: Vision API — Image as Base64 in Prompt Messages

This module is unique among the 4 pipeline modules because it uses OpenAI's **vision API** capabilities. The image must be encoded as base64 and embedded in the prompt message content (using LangChain's `HumanMessage` with image content parts).

**Implication:** The LangChain chain for this module differs structurally from text-only modules — it builds multi-modal messages with both text instructions and image data. This is internal to the module; callers see only `extract_from_path(path)` / `extract_from_cv2(image)`.

### Decision: Two Input Methods, Shared Internal Pipeline

The module provides two public methods:
- `extract_from_path(path: str) -> str` — reads image file, encodes to base64
- `extract_from_cv2(image: numpy.ndarray) -> str` — encodes cv2 array to base64

Both converge to the same internal chain execution after base64 encoding. The encoding logic is internal to the module.

### Decision: Image Format Validation

Before encoding, the module validates that the image format is supported by the OpenAI Vision API. Unsupported formats raise `UnsupportedImageFormatError` (from `core`) immediately — no API call is made.

### Decision: Synthetic Benchmark System (Internal)

The module includes internal benchmarking utilities (not part of public interface):

1. **Synthetic test image generator** — uses OpenCV to render known text onto images, producing deterministic test data
2. **Extraction quality evaluator** — compares extracted text against ground truth after normalization (strip whitespace, line breaks, markdown formatting)
3. **Model comparison runner** — runs the benchmark suite against different LLM models for cost/quality analysis

These utilities live within the module, not in `core` or `tests/`. They are development tools for prompt/model selection, not runtime code.

### Decision: Module-Specific Dependency

`opencv-python` (numpy) is required by this module only — for image input handling (cv2 array support, base64 encoding from file) and synthetic test image generation. No other module depends on opencv.

---

## Module Internal Structure

```
nl_processing/extract_text_from_image/
├── __init__.py              # empty
├── service.py               # ImageTextExtractor (public class)
├── prompts/
│   └── nl.json              # Dutch extraction prompt (ChatPromptTemplate format)
└── docs/
    ├── product-brief-extract_text_from_image-2026-03-01.md
    ├── prd_extract_text_from_image.md
    └── architecture_extract_text_from_image.md  # THIS DOCUMENT
```

Additional internal files may be added during implementation if `service.py` approaches the 200-line limit (e.g., extracting image encoding logic or benchmark utilities into separate internal modules).

---

## Test Strategy

- **Unit tests:** Mock LangChain chain invocation. Test image encoding logic (path → base64, cv2 → base64), format validation, error mapping.
- **Integration tests:** Real API calls with synthetic test images. Validate extraction accuracy (100% exact match after normalization) and performance (<10s per call).
- **E2e tests:** Full extraction scenarios with real-world-like images.

Synthetic test image generation is used in both unit tests (deterministic input) and integration tests (accuracy benchmark).
