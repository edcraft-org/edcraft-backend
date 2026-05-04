"""Nomad worker entrypoint.

Injected into the edcraft-engine container at runtime by the Nomad executor.

Reads job type and params from environment variables injected by Nomad,
executes the corresponding engine logic (pure compute, no DB access),
then POSTs the raw result to the callback URL for the backend to post-process.
"""

import asyncio
import base64
import json
import logging
import os
from typing import Any

import httpx
from edcraft_engine.question_generator.question_generator import QuestionGenerator
from edcraft_engine.static_analyser import StaticAnalyser
from input_gen import generate

from worker.handlers import JobHandlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entry / runner
# ---------------------------------------------------------------------------


def main() -> None:
    job_type = os.environ["EDCRAFT_JOB_TYPE"]
    callback_url = os.environ["EDCRAFT_CALLBACK_URL"]
    params = json.loads(base64.b64decode(os.environ["EDCRAFT_PARAMS_B64"]))

    logger.info("Starting worker for job type: %s", job_type)
    logger.info("Request: %s", params)
    asyncio.run(_run(job_type, params, callback_url))


async def _run(job_type: str, params: dict[str, Any], callback_url: str) -> None:
    result_json: str | None = None
    error: str | None = None

    try:
        handlers = JobHandlers(
            question_generator=QuestionGenerator(),
            static_analyser=StaticAnalyser(),
            generate_input=generate,
        )
        result = handlers.dispatch(job_type, params)
        result_json = json.dumps(result, default=str)
    except Exception as exc:
        logger.exception("Job %s failed", job_type)
        error = str(exc)

    await _post_callback(callback_url, result_json, error)


async def _post_callback(
    url: str,
    result_json: str | None,
    error: str | None,
) -> None:
    payload = {"result": result_json, "error": error}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("Callback delivered successfully")
    except Exception:
        logger.exception("Failed to deliver callback to %s", url)


if __name__ == "__main__":
    main()
