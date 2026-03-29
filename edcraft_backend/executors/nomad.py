"""Nomad executor: submits batch jobs to Nomad via its HTTP API."""

import base64
import importlib.resources as ir
import json
import logging

import httpx

from edcraft_backend.config import settings
from edcraft_backend.models.job import JobStatus

logger = logging.getLogger(__name__)


def _load_worker_source(filename: str) -> str:
    return ir.files("worker").joinpath(filename).read_text(encoding="utf-8")


class NomadExecutor:
    """Submits and queries Nomad batch jobs using the Nomad HTTP API."""

    @property
    def _base_url(self) -> str:
        cfg = settings.nomad
        return f"http://{cfg.host}:{cfg.port}/v1"

    @property
    def _headers(self) -> dict[str, str]:
        if settings.nomad.token:
            return {"X-Nomad-Token": settings.nomad.token}
        return {}

    async def submit_job(
        self,
        nomad_job_id: str,
        job_type: str,
        params: dict[str, object],
        callback_url: str,
    ) -> None:
        """Build and submit a Nomad batch job."""
        cfg = settings.nomad
        params_b64 = base64.b64encode(json.dumps(params, default=str).encode()).decode()
        entrypoint_src = _load_worker_source("entrypoint.py")
        handlers_src = _load_worker_source("handlers.py")

        job_spec = {
            "ID": nomad_job_id,
            "Name": nomad_job_id,
            "Type": "batch",
            "Datacenters": cfg.datacenters,
            "TaskGroups": [
                {
                    "Name": "worker",
                    "Count": 1,
                    "RestartPolicy": {"Attempts": 0, "Mode": "fail"},
                    "Tasks": [
                        {
                            "Name": "run",
                            "Driver": "docker",
                            "Config": {
                                "image": cfg.container_image,
                                "force_pull": False,
                                "command": "python",
                                "args": [f"{cfg.container_workdir}/entrypoint.py"],
                                "network_mode": "edcraft-network",
                                **(
                                    {
                                        "auth": {
                                            "username": cfg.registry_username,
                                            "password": cfg.registry_password,
                                        }
                                    }
                                    if cfg.registry_username and cfg.registry_password
                                    else {}
                                ),
                            },
                            "Templates": [
                                {
                                    "EmbeddedTmpl": entrypoint_src,
                                    "DestPath": f"{cfg.container_workdir}/entrypoint.py",
                                    "Perms": "0755",
                                    # Override template delimiters so Nomad doesn't
                                    # interpret Python's {{ }} or [[ ]] as template directives.
                                    "LeftDelim": "<%",
                                    "RightDelim": "%>",
                                },
                                {
                                    "EmbeddedTmpl": handlers_src,
                                    "DestPath": f"{cfg.container_workdir}/handlers.py",
                                    "Perms": "0644",
                                    "LeftDelim": "<%",
                                    "RightDelim": "%>",
                                },
                            ],
                            "Env": {
                                "EDCRAFT_JOB_TYPE": job_type,
                                "EDCRAFT_PARAMS_B64": params_b64,
                                "EDCRAFT_CALLBACK_URL": callback_url,
                            },
                            "Resources": {
                                "CPU": cfg.cpu_mhz,
                                "MemoryMB": cfg.memory_mb,
                            },
                        }
                    ],
                }
            ],
        }

        logger.info(
            "Submitting Nomad job",
            extra={"nomad_job_id": nomad_job_id, "job_type": job_type},
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/jobs",
                json={"Job": job_spec},
                headers=self._headers,
            )
            resp.raise_for_status()
        logger.info("Nomad job submitted", extra={"nomad_job_id": nomad_job_id})

    async def get_job_status(self, nomad_job_id: str) -> str:
        """Query Nomad for job status. Returns a JobStatus value."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self._base_url}/job/{nomad_job_id}/summary",
                headers=self._headers,
            )
            if resp.status_code == 404:
                return JobStatus.FAILED.value
            resp.raise_for_status()

        summary = resp.json()
        tg = summary.get("Summary", {}).get("worker", {})
        if tg.get("Failed", 0) > 0:
            logger.error("Nomad job failed", extra={"nomad_job_id": nomad_job_id})
            return JobStatus.FAILED.value
        if tg.get("Complete", 0) > 0:
            return JobStatus.COMPLETED.value
        return JobStatus.RUNNING.value
