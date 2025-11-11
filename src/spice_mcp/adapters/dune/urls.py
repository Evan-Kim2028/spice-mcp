from __future__ import annotations

import os
import re
from collections.abc import Mapping
from typing import Any


def _base_url() -> str:
    base = os.getenv('DUNE_API_URL', 'https://api.dune.com/api/v1').rstrip('/')
    return base


url_templates = {
    'execution_status': _base_url() + '/execution/{execution_id}/status',
    'execution_results': _base_url() + '/execution/{execution_id}/results/csv',
    'query_execution': _base_url() + '/query/{query_id}/execute',
    'query_results': _base_url() + '/query/{query_id}/results/csv',
    'query_results_json': _base_url() + '/query/{query_id}/results',
    'query_create': _base_url() + '/query/',
    'query': _base_url() + '/query/{query_id}',
    'query_fork': _base_url() + '/query/{query_id}/fork',
    'query_archive': _base_url() + '/query/{query_id}/archive',
    'query_unarchive': _base_url() + '/query/{query_id}/unarchive',
}


def get_query_execute_url(query: int | str) -> str:
    if isinstance(query, str):
        return query
    elif isinstance(query, int):
        return url_templates['query_execution'].format(query_id=query)
    else:
        raise Exception('unknown query format: ' + str(type(query)))


def get_query_results_url(
    query: int | str, parameters: dict[str, Any], csv: bool = True
) -> str:
    query_id = get_query_id(query)
    if csv:
        template = url_templates['query_results']
    else:
        template = url_templates['query_results_json']
    url = template.format(query_id=query_id)

    parameters = dict(parameters.items())
    if 'query_parameters' in parameters:
        parameters['params'] = parameters.pop('query_parameters')
    for key, value in list(parameters.items()):
        if isinstance(value, dict):
            del parameters[key]
            for subkey, subvalue in value.items():
                parameters[key + '.' + subkey] = subvalue

    return add_args_to_url(url, parameters=parameters)


def get_execution_status_url(execution_id: str) -> str:
    return url_templates['execution_status'].format(execution_id=execution_id)


def get_execution_results_url(
    execution_id: str, parameters: Mapping[str, Any]
) -> str:
    url = url_templates['execution_results'].format(execution_id=execution_id)
    return add_args_to_url(url, parameters=parameters)


def add_args_to_url(url: str, parameters: Mapping[str, Any]) -> str:
    """Append query params to a base URL.

    - Flattens nested dicts like {"a": {"b": 1}} -> "a.b=1"
    - Joins lists via commas
    - Skips None values
    """
    # Flatten nested dicts once (shallow nesting like key: {sub: val})
    flat: dict[str, Any] = {}
    for key, value in parameters.items():
        if value is None:
            continue
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                flat[f"{key}.{subkey}"] = subvalue
        else:
            flat[key] = value

    # Build query string
    parts: list[str] = []
    for key, value in flat.items():
        if value is None:
            continue
        if isinstance(value, list):
            value = ','.join(str(item) for item in value)
        parts.append(f"{key}={value}")

    sep = '&' if '?' in url else '?'
    return url + (sep if parts else '') + '&'.join(parts)


def get_api_key() -> str:
    """get dune api key"""
    return os.environ['DUNE_API_KEY']


def get_query_id(query: str | int) -> int:
    """get id of a query"""
    if isinstance(query, int):
        return query
    elif isinstance(query, str):
        m = re.search(r"/api/v1/query/(\d+)", query)
        if m:
            query = m.group(1)
        else:
            m2 = re.search(r"dune\.com/queries/(\d+)", query)
            if m2:
                query = m2.group(1)

    try:
        return int(query)
    except ValueError:
        raise Exception('invalid query id: ' + str(query))


def get_headers(*, api_key: str | None = None) -> Mapping[str, str]:
    if api_key is None:
        api_key = get_api_key()
    return {'X-Dune-API-Key': api_key}
