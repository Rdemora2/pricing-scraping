"""Spawns one Scrapy spider as an isolated OS subprocess.

Scrapy owns a Twisted reactor for the duration of a crawl. Running it
out-of-process keeps that reactor away from the asyncio event loop this
function itself runs on (Procrastinate's worker loop) and means a
spider crash cannot take the worker down with it.
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SpiderRunResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


async def run_spider(*, spider_name: str, source_id: UUID, run_id: UUID) -> SpiderRunResult:
    env = {**os.environ, "SCRAPY_SETTINGS_MODULE": "pricing_intel.collection.settings"}
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "scrapy",
        "crawl",
        spider_name,
        "-a",
        f"source_id={source_id}",
        "-a",
        f"run_id={run_id}",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return SpiderRunResult(
        exit_code=process.returncode if process.returncode is not None else -1,
        stdout=stdout.decode(errors="replace"),
        stderr=stderr.decode(errors="replace"),
    )
