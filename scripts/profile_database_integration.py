from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES_DIR = ROOT / "packages"

TARGETS = [
    ROOT / "packages/database/tests/integration/database/test_delete.py",
    ROOT / "packages/database/tests/integration/database/test_detailed_integration.py",
    ROOT / "packages/database/tests/integration/database/test_exercise_scores.py",
    ROOT / "packages/database/tests/integration/database/test_neon_backend.py",
    ROOT / "packages/database/tests/integration/database/test_personal_vocab.py",
    ROOT / "packages/database/tests/integration/database/test_table_creation.py",
    ROOT / "packages/database/tests/integration/database/test_tiered_store.py",
    ROOT / "packages/database_cache/tests/integration/database_cache/test_delete.py",
    ROOT / "packages/database_cache/tests/integration/database_cache/test_detailed_lifecycle.py",
    ROOT / "packages/database_cache/tests/integration/database_cache/test_detailed_schema_integration.py",
    ROOT / "packages/database_cache/tests/integration/database_cache/test_flush_retry.py",
    ROOT / "packages/database_cache/tests/integration/database_cache/test_persistence.py",
    ROOT / "packages/database_cache/tests/integration/database_cache/test_refresh_rebuild.py",
]

PYTHONPATHS = {
    "database": "src:../core/src:../translate_word/src",
    "database_cache": "src:../core/src:../database/src:../translate_word/src:../extract_word_details/src",
}

COUNTER_PATCH = textwrap.dedent(
    """
    from __future__ import annotations

    import atexit
    import json
    import os
    from functools import wraps

    COUNTS = {
        "asyncpg_connect": 0,
        "asyncpg_execute": 0,
        "asyncpg_executemany": 0,
        "asyncpg_fetch": 0,
        "asyncpg_fetchrow": 0,
        "asyncpg_fetchval": 0,
        "httpx_async_send": 0,
        "httpx_send": 0,
    }

    def _write_counts() -> None:
        path = os.environ.get("QUERY_COUNTER_OUT")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(COUNTS, handle)

    atexit.register(_write_counts)

    try:
        import asyncpg
    except Exception:
        asyncpg = None

    if asyncpg is not None:
        _orig_connect = asyncpg.connect

        @wraps(_orig_connect)
        async def _counted_connect(*args, **kwargs):
            COUNTS["asyncpg_connect"] += 1
            return await _orig_connect(*args, **kwargs)

        asyncpg.connect = _counted_connect

        def _patch_async_method(name: str) -> None:
            original = getattr(asyncpg.Connection, name)

            @wraps(original)
            async def wrapped(self, *args, **kwargs):
                COUNTS[f"asyncpg_{name}"] += 1
                return await original(self, *args, **kwargs)

            setattr(asyncpg.Connection, name, wrapped)

        for _name in ("execute", "executemany", "fetch", "fetchrow", "fetchval"):
            _patch_async_method(_name)

    try:
        import httpx
    except Exception:
        httpx = None

    if httpx is not None:
        _orig_async_send = httpx.AsyncClient.send
        _orig_send = httpx.Client.send

        @wraps(_orig_async_send)
        async def _counted_async_send(self, *args, **kwargs):
            COUNTS["httpx_async_send"] += 1
            return await _orig_async_send(self, *args, **kwargs)

        @wraps(_orig_send)
        def _counted_send(self, *args, **kwargs):
            COUNTS["httpx_send"] += 1
            return _orig_send(self, *args, **kwargs)

        httpx.AsyncClient.send = _counted_async_send
        httpx.Client.send = _counted_send
    """
).strip()


def _package_python(package: str) -> Path:
    package_python = PACKAGES_DIR / package / ".venv" / "bin" / "python"
    if package_python.exists():
        return package_python
    return ROOT / ".venv" / "bin" / "python"


def _run_target(target: Path, patch_dir: Path) -> tuple[float, dict[str, int]]:
    package = target.relative_to(PACKAGES_DIR).parts[0]
    fd, out_path_str = tempfile.mkstemp(prefix="query-count-", suffix=".json")
    os.close(fd)
    out_path = Path(out_path_str)
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{patch_dir}:{PYTHONPATHS[package]}"
    env["QUERY_COUNTER_OUT"] = str(out_path)
    command = [
        "doppler",
        "run",
        "--",
        "uv",
        "run",
        "--python",
        str(_package_python(package)),
        "python",
        "-m",
        "pytest",
        "-o",
        "addopts=",
        str(target),
        "-q",
    ]
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=PACKAGES_DIR / package,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr)
        raise SystemExit(completed.returncode)
    return elapsed, json.loads(out_path.read_text())


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="db-profile-") as temp_dir:
        patch_dir = Path(temp_dir)
        (patch_dir / "sitecustomize.py").write_text(COUNTER_PATCH, encoding="utf-8")
        rows = []
        for target in TARGETS:
            elapsed, counts = _run_target(target, patch_dir)
            queries = (
                counts["asyncpg_execute"]
                + counts["asyncpg_executemany"]
                + counts["asyncpg_fetch"]
                + counts["asyncpg_fetchrow"]
                + counts["asyncpg_fetchval"]
            )
            http_calls = counts["httpx_async_send"] + counts["httpx_send"]
            rows.append((elapsed, queries, counts["asyncpg_connect"], http_calls, target))

    print("| Time (s) | Neon SQL round-trips | Neon connects | HTTP calls | File |")
    print("|---:|---:|---:|---:|---|")
    for elapsed, queries, connects, http_calls, target in sorted(rows, reverse=True):
        print(f"| {elapsed:.3f} | {queries} | {connects} | {http_calls} | {target} |")


if __name__ == "__main__":
    main()
