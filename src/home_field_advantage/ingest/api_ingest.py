from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import os


@dataclass
class APISource:
    league: str
    url: str
    format: str = "csv"
    token_env: str | None = None
    query: dict[str, str] | None = None


def _with_query(url: str, query: dict[str, str] | None) -> str:
    if not query:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(query)}"


def _headers(token_env: str | None) -> dict[str, str]:
    headers: dict[str, str] = {"User-Agent": "home-field-advantage/1.0"}
    if token_env:
        token = os.getenv(token_env)
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def _write_csv_bytes(raw_bytes: bytes, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(raw_bytes)


def _write_json_rows(raw_bytes: bytes, output_file: Path) -> None:
    payload = json.loads(raw_bytes.decode("utf-8"))
    rows: list[dict[str, Any]]
    if isinstance(payload, dict) and "games" in payload and isinstance(payload["games"], list):
        rows = payload["games"]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError("JSON API payload must be a list or object with 'games' list")

    if not rows:
        return

    fieldnames = sorted({key for row in rows for key in row.keys()})
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fetch_api_source(source: APISource, raw_dir: Path) -> Path:
    url = _with_query(source.url, source.query)
    request = Request(url=url, headers=_headers(source.token_env))
    output_file = raw_dir / f"{source.league.lower()}_games.csv"

    try:
        with urlopen(request, timeout=30) as response:
            body = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Failed to fetch {source.league} API source from {source.url}: {exc}") from exc

    if source.format.lower() == "json":
        _write_json_rows(body, output_file)
    else:
        _write_csv_bytes(body, output_file)
    return output_file


def sync_api_sources(sources: list[APISource], raw_dir: Path) -> list[Path]:
    output_files: list[Path] = []
    for source in sources:
        output_files.append(fetch_api_source(source, raw_dir))
    return output_files
