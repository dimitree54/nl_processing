"""Latency benchmark for NeonBackend add_word operations against real Neon PostgreSQL.

NFR1: p95 latency for add_word must be ≤ 200ms.
"""

import time
import uuid

import pytest

from nl_processing.database.backend.neon import NeonBackend

_NUM_OPERATIONS = 50
_P95_THRESHOLD_MS = 200


@pytest.mark.asyncio
async def test_add_word_p95_latency(neon_backend: NeonBackend) -> None:
    """Add 50 words and assert p95 latency ≤ 200ms per operation."""
    timings: list[float] = []

    for i in range(_NUM_OPERATIONS):
        word = f"latency_word_{i}_{uuid.uuid4().hex[:8]}"
        start = time.perf_counter()
        await neon_backend.add_word("nl", word, "noun")
        elapsed_ms = (time.perf_counter() - start) * 1000
        timings.append(elapsed_ms)

    timings.sort()
    p95_index = int(len(timings) * 0.95)
    p95_latency = timings[p95_index]

    assert p95_latency <= _P95_THRESHOLD_MS, (
        f"p95 latency {p95_latency:.1f}ms exceeds {_P95_THRESHOLD_MS}ms threshold. "
        f"Median: {timings[len(timings) // 2]:.1f}ms, "
        f"Max: {timings[-1]:.1f}ms"
    )
