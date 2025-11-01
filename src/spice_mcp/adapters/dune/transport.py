from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any

from ..http_client import HttpClient

_HTTP_CLIENT: HttpClient | None = None


@contextmanager
def use_http_client(client: HttpClient | None):
    global _HTTP_CLIENT
    previous = _HTTP_CLIENT
    if client is not None:
        _HTTP_CLIENT = client
    try:
        yield
    finally:
        _HTTP_CLIENT = previous


def current_http_client() -> HttpClient | None:
    return _HTTP_CLIENT


def request(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str],
    timeout: float,
    json: Any | None = None,
    data: Any | None = None,
) -> Any:
    client = _HTTP_CLIENT
    if client is not None:
        return client.request(
            method,
            url,
            headers=headers,
            timeout=timeout,
            json=json,
            data=data,
        )
    import requests

    return requests.request(
        method,
        url,
        headers=headers,
        timeout=timeout,
        json=json,
        data=data,
    )


def get(url: str, *, headers: Mapping[str, str], timeout: float):
    return request("GET", url, headers=headers, timeout=timeout)


def post(
    url: str,
    *,
    headers: Mapping[str, str],
    json: Any | None = None,
    timeout: float,
):
    return request("POST", url, headers=headers, json=json, timeout=timeout)
