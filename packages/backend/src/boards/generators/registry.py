"""Generator registry and YAML loader for declarative specs."""

from __future__ import annotations

from typing import Dict, Any, List
import yaml
import httpx

from .base import BaseGenerator, GenerationOutput
from ..providers.registry import ProviderRegistry, provider_registry


class RestSpecGenerator(BaseGenerator):
    def __init__(self, name: str, artifact_type: str, spec: Dict[str, Any], providers: ProviderRegistry):
        self.name = name
        self.artifact_type = artifact_type
        self.spec = spec
        self.providers = providers

    async def run(self, inputs: Dict[str, Any]) -> GenerationOutput:
        provider_key = self.spec["provider"]
        provider = self.providers.get(provider_key)
        exec_spec = self.spec["execution"]

        async with httpx.AsyncClient(base_url=provider.get_base_url(), headers=provider.build_headers(), timeout=60) as client:
            submit = exec_spec["submit"]
            method = submit.get("method", "POST").upper()
            path = submit["path"]
            json_payload = _interpolate(submit.get("json"), inputs, {})
            resp = await client.request(method, path, json=json_payload)
            resp.raise_for_status()
            submit_data = resp.json()

            poll = exec_spec.get("poll")
            job_id = submit_data.get("id") or submit_data.get("prediction", {}).get("id") or submit_data.get("data", {}).get("id")

            result_data = submit_data
            if poll and job_id:
                path = _interpolate_string(poll["path"], inputs, {"job": {"id": job_id}})
                method = poll.get("method", "GET").upper()
                # naive polling; in real impl add backoff and terminal state mapping
                for _ in range(60):
                    r = await client.request(method, path)
                    r.raise_for_status()
                    result_data = r.json()
                    status = (result_data.get("status") or result_data.get("state") or "").lower()
                    if status in {"succeeded", "success", "completed", "failed", "error", "canceled"}:
                        break

            extract = exec_spec.get("extract", {})
            output_paths: List[str] = extract.get("output_paths", [])
            urls: List[str] = []
            for p in output_paths:
                value = _get_path(result_data, p)
                if isinstance(value, list):
                    urls.extend([v for v in value if isinstance(v, str)])
                elif isinstance(value, str):
                    urls.append(value)

        return GenerationOutput(storage_urls=urls, metadata={"provider_job": job_id, "raw": result_data})


def _get_path(data: Any, path: str) -> Any:
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _interpolate(obj: Any, inputs: Dict[str, Any], ctx: Dict[str, Any]) -> Any:
    if isinstance(obj, str):
        return _interpolate_string(obj, inputs, ctx)
    if isinstance(obj, list):
        return [_interpolate(v, inputs, ctx) for v in obj]
    if isinstance(obj, dict):
        return {k: _interpolate(v, inputs, ctx) for k, v in obj.items()}
    return obj


def _interpolate_string(s: str, inputs: Dict[str, Any], ctx: Dict[str, Any]) -> str:
    def repl(token: str) -> str:
        if token.startswith("input."):
            return str(_get_path(inputs, token[len("input."):]) or "")
        # support ${job.id}
        cur = ctx
        for part in token.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                cur = None
                break
        return str(cur or "")

    out = ""
    i = 0
    while i < len(s):
        if s[i : i + 2] == "${":
            j = s.find("}", i + 2)
            if j != -1:
                token = s[i + 2 : j]
                out += repl(token)
                i = j + 1
                continue
        out += s[i]
        i += 1
    return out


class GeneratorRegistry:
    def __init__(self, providers: ProviderRegistry):
        self._generators: Dict[str, BaseGenerator] = {}
        self.providers = providers

    def register(self, name: str, generator: BaseGenerator) -> None:
        self._generators[name] = generator

    def get(self, name: str) -> BaseGenerator:
        return self._generators[name]

    def load_from_yaml(self, yaml_path: str) -> None:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        gens = (data.get("generators") or [])
        for node in gens:
            name = node["name"]
            artifact_type = node["artifact_type"]
            execution = node.get("execution", {})
            if execution.get("type") == "rest":
                gen = RestSpecGenerator(name=name, artifact_type=artifact_type, spec=node, providers=self.providers)
            else:
                raise ValueError(f"Unsupported execution type: {execution.get('type')}")
            self.register(name, gen)


generator_registry = GeneratorRegistry(provider_registry)

