from __future__ import annotations

import io
import os
import time
from typing import TYPE_CHECKING, overload

from ..http_client import HttpClient
from . import cache as _cache
from . import urls as _urls
from .transport import (
    current_http_client,
    use_http_client,
)
from .transport import (
    get as _transport_get,
)
from .transport import (
    post as _transport_post,
)
from .types import (
    ExecuteKwargs,
    Execution,
    OutputKwargs,
    Performance,
    PollKwargs,
    Query,
    RetrievalKwargs,
)
from .typing_utils import resolve_raw_sql_template_id

# Keep local helper implementations for compatibility with tests

ADAPTER_VERSION = "spice-mcp-adapter"

# Runtime-configurable HTTP timeouts (helps avoid host-level timeouts)
_GET_TIMEOUT: float = float(os.getenv("SPICE_DUNE_GET_TIMEOUT", os.getenv("SPICE_HTTP_TIMEOUT", "30")))
_POST_TIMEOUT: float = float(os.getenv("SPICE_DUNE_POST_TIMEOUT", os.getenv("SPICE_HTTP_TIMEOUT", "30")))

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any, Literal

    import polars as pl


# ---------------------------------------------------------------------------
# Internal helpers used by adapter code and tests

def _is_sql(query: int | str) -> bool:
    if isinstance(query, int):
        return False
    if isinstance(query, str):
        if query.startswith('https://') or query.startswith('api.dune.com') or query.startswith('dune.com/queries'):
            return False
        try:
            int(query)
            return False
        except ValueError:
            return True
    raise Exception('invalid format for query: ' + str(type(query)))


def _determine_input_type(
    query_or_execution: Query | Execution,
    parameters: Mapping[str, Any] | None = None,
) -> tuple[int | None, Execution | None, Mapping[str, Any] | None]:
    if isinstance(query_or_execution, str) and query_or_execution == '':
        raise Exception('empty query')
    if isinstance(query_or_execution, int | str):
        if _is_sql(query_or_execution):
            query_id = resolve_raw_sql_template_id()
            execution = None
            new_params = dict(parameters or {})
            new_params.update({'query': query_or_execution})
            parameters = new_params
        else:
            query_id = _urls.get_query_id(query_or_execution)
            execution = None
    elif isinstance(query_or_execution, dict) and 'execution_id' in query_or_execution:
        query_id = None
        execution = query_or_execution  # type: ignore[assignment]
    else:
        raise Exception('input must be a query id, query url, or execution id')
    return query_id, execution, parameters


def _http_get(url: str, *, headers: Mapping[str, str], timeout: float):
    import requests

    return requests.get(url, headers=headers, timeout=timeout)


@overload
def query(
    query_or_execution: Query | Execution,
    *,
    verbose: bool = True,
    refresh: bool = False,
    max_age: float | None = None,
    parameters: Mapping[str, Any] | None = None,
    api_key: str | None = None,
    performance: Performance = 'medium',
    poll: Literal[False],
    poll_interval: float = 1.0,
    timeout_seconds: float | None = None,
    limit: int | None = None,
    offset: int | None = None,
    sample_count: int | None = None,
    sort_by: str | None = None,
    columns: Sequence[str] | None = None,
    extras: Mapping[str, Any] | None = None,
    types: Sequence[type[pl.DataType]]
    | Mapping[str, type[pl.DataType]]
    | None = None,
    all_types: Sequence[type[pl.DataType]]
    | Mapping[str, type[pl.DataType]]
    | None = None,
    cache: bool = True,
    cache_dir: str | None = None,
    save_to_cache: bool = True,
    load_from_cache: bool = True,
    include_execution: bool = False,
) -> Execution: ...


@overload
def query(
    query_or_execution: Query | Execution,
    *,
    verbose: bool = True,
    refresh: bool = False,
    max_age: float | None = None,
    parameters: Mapping[str, Any] | None = None,
    api_key: str | None = None,
    performance: Performance = 'medium',
    poll: Literal[True] = True,
    poll_interval: float = 1.0,
    limit: int | None = None,
    offset: int | None = None,
    sample_count: int | None = None,
    sort_by: str | None = None,
    columns: Sequence[str] | None = None,
    extras: Mapping[str, Any] | None = None,
    types: Sequence[type[pl.DataType]]
    | Mapping[str, type[pl.DataType]]
    | None = None,
    all_types: Sequence[type[pl.DataType]]
    | Mapping[str, type[pl.DataType]]
    | None = None,
    cache: bool = True,
    cache_dir: str | None = None,
    save_to_cache: bool = True,
    load_from_cache: bool = True,
    include_execution: Literal[False] = False,
) -> pl.DataFrame: ...


@overload
def query(
    query_or_execution: Query | Execution,
    *,
    verbose: bool = True,
    refresh: bool = False,
    max_age: float | None = None,
    parameters: Mapping[str, Any] | None = None,
    api_key: str | None = None,
    performance: Performance = 'medium',
    poll: Literal[True] = True,
    poll_interval: float = 1.0,
    limit: int | None = None,
    offset: int | None = None,
    sample_count: int | None = None,
    sort_by: str | None = None,
    columns: Sequence[str] | None = None,
    extras: Mapping[str, Any] | None = None,
    types: Sequence[type[pl.DataType]]
    | Mapping[str, type[pl.DataType]]
    | None = None,
    all_types: Sequence[type[pl.DataType]]
    | Mapping[str, type[pl.DataType]]
    | None = None,
    cache: bool = True,
    cache_dir: str | None = None,
    save_to_cache: bool = True,
    load_from_cache: bool = True,
    include_execution: Literal[True],
) -> tuple[pl.DataFrame, Execution]: ...


def query(
    query_or_execution: Query | Execution,
    *,
    verbose: bool = True,
    refresh: bool = False,
    max_age: float | None = None,
    parameters: Mapping[str, Any] | None = None,
    api_key: str | None = None,
    performance: Performance = 'medium',
    poll: bool = True,
    poll_interval: float = 1.0,
    timeout_seconds: float | None = None,
    limit: int | None = None,
    offset: int | None = None,
    sample_count: int | None = None,
    sort_by: str | None = None,
    columns: Sequence[str] | None = None,
    extras: Mapping[str, Any] | None = None,
    types: Sequence[type[pl.DataType]]
    | Mapping[str, type[pl.DataType]]
    | None = None,
    all_types: Sequence[type[pl.DataType]]
    | Mapping[str, type[pl.DataType]]
    | None = None,
    cache: bool = True,
    cache_dir: str | None = None,
    save_to_cache: bool = True,
    load_from_cache: bool = True,
    include_execution: bool = False,
    http_client: HttpClient | None = None,
) -> pl.DataFrame | Execution | tuple[pl.DataFrame, Execution]:
    """get results of query as dataframe

    # Parameters
    - query: query or execution to retrieve results of
    - verbose: whether to print verbose info
    - refresh: trigger a new execution instead of using most recent execution
    - max_age: max age of last execution in seconds, or trigger a new execution
    - parameters: dict of query parameters
    - api_key: dune api key, otherwise use DUNE_API_KEY env var
    - performance: performance level
    - poll: wait for result as DataFrame, or just return Execution handle
    - poll_interval: polling interval in seconds
    - limit: number of rows to query in result
    - offset: row number to start returning results from
    - sample_count: number of random samples from query to return
    - sort_by: an ORDER BY clause to sort data by
    - columns: columns to retrieve, by default retrieve all columns
    - extras: extra parameters used for fetching execution result
        - examples: ignore_max_datapoints_per_request, allow_partial_results
    - types: column types to use in output polars dataframe
    - all_types: like types, but must strictly include all columns in data
    - cache: whether to use cache for saving or loading
    - cache_dir: directory to use for cached data (create tmp_dir if None)
    - save_to_cache: whether to save to cache, set false to load only
    - load_from_cache: whether to load from cache, set false to save only
    - include_execution: return Execution metadata alongside query result
    """

    with use_http_client(http_client):
        # Check if this is raw SQL and should use Execute SQL endpoint
        raw_sql_engine = os.getenv("SPICE_DUNE_RAW_SQL_ENGINE", "execution_sql")
        is_raw_sql = _is_sql(query_or_execution) if isinstance(query_or_execution, str) else False
        
        if is_raw_sql and raw_sql_engine == "execution_sql":
            # Use Execute SQL endpoint for raw SQL
            execution = _execute_raw_sql(
                query_or_execution,  # type: ignore[arg-type]
                parameters=parameters,
                timeout_seconds=timeout_seconds,
                api_key=api_key,
                verbose=verbose,
            )
            query_id = None
        else:
            # determine whether target is a query or an execution
            query_id, execution, parameters = _determine_input_type(
                query_or_execution,
                parameters,
            )

        # gather arguments
        execute_kwargs: ExecuteKwargs = {
            'query_id': query_id,
            'api_key': api_key,
            'parameters': parameters,
            'performance': performance,
        }
        poll_kwargs: PollKwargs = {
            'poll_interval': poll_interval,
            'api_key': api_key,
            'verbose': verbose,
            'timeout_seconds': timeout_seconds,
        }
        result_kwargs: RetrievalKwargs = {
            'limit': limit,
            'offset': offset,
            'sample_count': sample_count,
            'sort_by': sort_by,
            'columns': columns,
            'extras': extras,
            'types': types,
            'all_types': all_types,
            'verbose': verbose,
        }
        output_kwargs: OutputKwargs = {
            'execute_kwargs': execute_kwargs,
            'result_kwargs': result_kwargs,
            'cache': cache,
            'save_to_cache': save_to_cache,
            'cache_dir': cache_dir,
            'include_execution': include_execution,
        }

        # execute or retrieve query
        if query_id:
            # Check if this is a parameterized query (raw SQL via template or parameterized query)
            # For parameterized queries, results don't exist until execution, so skip GET attempt
            is_parameterized = (
                parameters is not None 
                and len(parameters) > 0 
                and ('query' in parameters or any(k != 'query' for k in parameters))
            )
            
            if cache and load_from_cache and not refresh:
                cache_result, cache_execution = _cache.load_from_cache(
                    execute_kwargs, result_kwargs, output_kwargs
                )
                if cache_result is not None:
                    return cache_result
                if execution is None and cache_execution is not None:
                    execution = cache_execution
            if max_age is not None and not refresh:
                age = get_query_latest_age(**execute_kwargs, verbose=verbose)  # type: ignore
                if age is None or age > max_age:
                    refresh = True
            # Skip GET results attempt for parameterized queries - they need execution first
            if not refresh and not is_parameterized:
                df = get_results(**execute_kwargs, **result_kwargs)
                if df is not None:
                    return process_result(df, execution, **output_kwargs)
            try:
                execution = execute_query(**execute_kwargs, verbose=verbose)
            except Exception as e:
                # Re-raise with more context about the failure
                if verbose:
                    print(f'execute_query failed for query_id={query_id}, parameters={parameters}')
                raise Exception(f'failed to execute query {query_id}: {e}') from e
        else:
            # query_id is None when using Execute SQL endpoint for raw SQL
            # execution should already be set from _execute_raw_sql() above
            if verbose and execution is None:
                print(f'query_id is None, execution={execution}, query_or_execution={query_or_execution}')

        # check execution status
        if execution is None:
            error_detail = f'query_id={query_id}, query_type={type(query_or_execution).__name__}'
            if isinstance(query_or_execution, str):
                error_detail += f', query_preview={query_or_execution[:100]}'
            raise Exception(f'could not determine execution ({error_detail})')
        if poll:
            poll_execution(execution, **poll_kwargs)
            df = get_results(execution, api_key, **result_kwargs)
            if df is not None:
                return process_result(df, execution, **output_kwargs)
            else:
                raise Exception('no successful execution for query')
        else:
            return execution


if TYPE_CHECKING:
    @overload
    def _process_result(
        df: pl.DataFrame,
        execution: Execution | None,
        execute_kwargs: ExecuteKwargs,
        result_kwargs: RetrievalKwargs,
        cache: bool,
        save_to_cache: bool,
        cache_dir: str | None,
        include_execution: Literal[False],
    ) -> pl.DataFrame: ...

    @overload
    def _process_result(
        df: pl.DataFrame,
        execution: Execution | None,
        execute_kwargs: ExecuteKwargs,
        result_kwargs: RetrievalKwargs,
        cache: bool,
        save_to_cache: bool,
        cache_dir: str | None,
        include_execution: Literal[True],
    ) -> tuple[pl.DataFrame, Execution]: ...

    @overload
    def _process_result(
        df: pl.DataFrame,
        execution: Execution | None,
        execute_kwargs: ExecuteKwargs,
        result_kwargs: RetrievalKwargs,
        cache: bool,
        save_to_cache: bool,
        cache_dir: str | None,
        include_execution: bool,
    ) -> pl.DataFrame | tuple[pl.DataFrame, Execution]: ...


def _process_result(
    df: pl.DataFrame,
    execution: Execution | None,
    execute_kwargs: ExecuteKwargs,
    result_kwargs: RetrievalKwargs,
    cache: bool,
    save_to_cache: bool,
    cache_dir: str | None,
    include_execution: bool,
) -> pl.DataFrame | tuple[pl.DataFrame, Execution]:
    if cache and save_to_cache and execute_kwargs['query_id'] is not None:
        if execution is None:
            execution = get_latest_execution(execute_kwargs)
            if execution is None:
                raise Exception('could not get execution')
        _cache.save_to_cache(
            df, execution, execute_kwargs, result_kwargs, cache_dir
        )

    if include_execution:
        if execution is None:
            execution = get_latest_execution(execute_kwargs)
            if execution is None:
                raise Exception('could not get execution')
        return df, execution
    else:
        return df


def _get_query_latest_age(
    query_id: int,
    *,
    verbose: bool = True,
    parameters: Mapping[str, Any] | None = None,
    performance: Performance = 'medium',
    api_key: str | None = None,
) -> float | None:
    import datetime
    import json

    # process inputs
    if api_key is None:
        api_key = _urls.get_api_key()
    headers = {'X-Dune-API-Key': api_key, 'User-Agent': get_user_agent()}
    data = {}
    if parameters is not None:
        data['query_parameters'] = parameters
    url = _urls.get_query_results_url(query_id, parameters=data, csv=False)

    # print summary
    if verbose:
        print('checking age of last execution, query_id = ' + str(query_id))

    response = _transport_get(url, headers=headers, timeout=15.0)

    # check if result is error
    result = response.json()
    try:
        if 'error' in result:
            if (
                result['error']
                == 'not found: No execution found for the latest version of the given query'
            ):
                if verbose:
                    print(
                        'no age for query, because no previous executions exist'
                    )
                return None
            raise Exception(result['error'])
    except json.JSONDecodeError:
        pass

    # process result
    if 'execution_started_at' in result:
        now = datetime.datetime.now(datetime.UTC).timestamp()
        started = _parse_timestamp(result['execution_started_at'])
        age = now - started

        if verbose:
            print('latest result age:', age)

        return age
    else:
        if verbose:
            print('no age for query, because no previous executions exist')
        return None


def _parse_timestamp(timestamp: str) -> int:
    import datetime

    # reduce number of decimals in
    if len(timestamp) > 27 and timestamp[-1] == 'Z':
        timestamp = timestamp[:26] + 'Z'

    timestamp_float = (
        datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        .replace(tzinfo=datetime.UTC)
        .timestamp()
    )
    return int(timestamp_float)


def _execute_raw_sql(
    query_sql: str,
    *,
    parameters: Mapping[str, Any] | None = None,
    timeout_seconds: float | None = None,
    api_key: str | None = None,
    verbose: bool = True,
) -> Execution:
    """Execute raw SQL via POST /execution/sql endpoint."""
    url = _urls.url_templates['execution_sql']
    if api_key is None:
        api_key = _urls.get_api_key()
    headers = {'X-Dune-API-Key': api_key, 'User-Agent': get_user_agent()}
    data: dict[str, Any] = {'query_sql': query_sql}
    if parameters is not None:
        data['parameters'] = parameters
    if timeout_seconds is not None:
        data['timeout_seconds'] = timeout_seconds

    if verbose:
        print(f'executing raw SQL via /execution/sql, query_preview={query_sql[:100]}...')

    response = _transport_post(url, headers=headers, json=data, timeout=_POST_TIMEOUT)
    
    try:
        result: Mapping[str, Any] = response.json()
    except Exception as e:
        if verbose:
            print(f'failed to parse response JSON: {e}')
            print(f'response status: {response.status_code}')
            print(f'response text: {response.text[:500]}')
        raise Exception(f'failed to parse response: {e}') from e

    if 'execution_id' not in result:
        error_msg = result.get('error', f'response missing execution_id: {result}')
        if verbose:
            print(f'execution failed: {error_msg}')
            print(f'response status: {response.status_code}')
            print(f'full response: {result}')
        raise Exception(error_msg)

    execution_id = result['execution_id']
    return {'execution_id': execution_id, 'timestamp': None}


def _execute(
    query_id: int | str,
    *,
    parameters: Mapping[str, Any] | None = None,
    performance: Performance = 'medium',
    api_key: str | None = None,
    verbose: bool = True,
) -> Execution:
    # process inputs
    url = _urls.get_query_execute_url(query_id)
    if api_key is None:
        api_key = _urls.get_api_key()
    headers = {'X-Dune-API-Key': api_key, 'User-Agent': get_user_agent()}
    data = {}
    if parameters is not None:
        data['query_parameters'] = parameters
    data['performance'] = performance

    # print summary
    if verbose:
        print('executing query, query_id = ' + str(query_id))

    # perform request
    response = _transport_post(url, headers=headers, json=data, timeout=_POST_TIMEOUT)
    
    # Parse response with better error handling
    try:
        result: Mapping[str, Any] = response.json()
    except Exception as e:
        if verbose:
            print(f'failed to parse response JSON: {e}')
            print(f'response status: {response.status_code}')
            print(f'response text: {response.text[:500]}')
        raise Exception(f'failed to parse response: {e}') from e

    # check for errors
    if 'execution_id' not in result:
        error_msg = result.get('error', f'response missing execution_id: {result}')
        if verbose:
            print(f'execution failed: {error_msg}')
            print(f'response status: {response.status_code}')
            print(f'full response: {result}')
        raise Exception(error_msg)

    # process result
    execution_id = result['execution_id']
    return {'execution_id': execution_id, 'timestamp': None}


def _get_results(
    execution: Execution | None = None,
    api_key: str | None = None,
    *,
    query_id: int | None = None,
    parameters: Mapping[str, Any] | None = None,
    performance: Performance = 'medium',
    limit: int | None = None,
    offset: int | None = None,
    sample_count: int | None = None,
    sort_by: str | None = None,
    columns: Sequence[str] | None = None,
    extras: Mapping[str, Any] | None = None,
    types: Sequence[type[pl.DataType]]
    | Mapping[str, type[pl.DataType]]
    | None = None,
    all_types: Sequence[type[pl.DataType]]
    | Mapping[str, type[pl.DataType]]
    | None = None,
    verbose: bool = True,
) -> pl.DataFrame | None:
    import random
    import time as _time

    import polars as pl

    # process inputs similar to upstream
    if api_key is None:
        api_key = _urls.get_api_key()
    headers = {'X-Dune-API-Key': api_key, 'User-Agent': get_user_agent()}
    params: dict[str, Any] = {
        'limit': limit,
        'offset': offset,
        'sample_count': sample_count,
        'sort_by': sort_by,
        'columns': columns,
    }
    if extras is not None:
        params.update(extras)
    if performance is not None:
        params['performance'] = performance
    if parameters is not None:
        params['query_parameters'] = parameters
    if query_id is not None:
        url = _urls.get_query_results_url(query_id, parameters=params)
    elif execution is not None:
        url = _urls.get_execution_results_url(execution['execution_id'], params)
    else:
        raise Exception('must specify query_id or execution')

    # print summary
    if verbose:
        if query_id is not None:
            print('getting results, query_id = ' + str(query_id))
        elif execution is not None:
            print('getting results, execution_id = ' + str(execution['execution_id']))

    # perform request
    # GET with simple retry/backoff for 429/502
    def _get_with_retries(u: str):
        client = current_http_client()
        if client is not None:
            return client.request("GET", u, headers=headers, timeout=_GET_TIMEOUT)

        attempts = 0
        backoff = 0.5
        while True:
            resp = _transport_get(u, headers=headers, timeout=_GET_TIMEOUT)
            if resp.status_code in (429, 502):
                attempts += 1
                if attempts >= 3:
                    return resp
                sleep_for = backoff * random.uniform(1.5, 2.5)
                _time.sleep(sleep_for)
                backoff = min(5.0, backoff * 2)
                continue
            return resp

    response = _get_with_retries(url)
    if response.status_code == 404:
        return None
    result = response.text

    # process result
    df = _process_raw_table(result, types=types, all_types=all_types)

    # support pagination when using limit
    response_headers = response.headers
    if limit is not None:
        n_rows = len(df)
        pages = []
        while 'x-dune-next-uri' in response_headers and n_rows < limit:
            if verbose:
                offset_hdr = response.headers.get('x-dune-next-offset', 'unknown')
                print('gathering additional page, offset = ' + str(offset_hdr))
            next_url = response_headers['x-dune-next-uri']
            response = _get_with_retries(next_url)
            result = response.text
            response_headers = response.headers
            page = _process_raw_table(result, types=types, all_types=all_types)
            n_rows += len(page)
            pages.append(page)
        df = pl.concat([df, *pages]).limit(limit)

    return df


def _process_raw_table(
    raw_csv: str,
    types: Sequence[type[pl.DataType] | None]
    | Mapping[str, type[pl.DataType] | None]
    | None,
    all_types: Sequence[type[pl.DataType]]
    | Mapping[str, type[pl.DataType]]
    | None = None,
) -> pl.DataFrame:
    import polars as pl

    # convert from map to sequence
    first_line = raw_csv.split('\n', maxsplit=1)[0]
    column_order = first_line.split(',')

    # parse data as csv
    df = pl.read_csv(
        io.StringIO(raw_csv),
        infer_schema_length=len(raw_csv),
        null_values='<nil>',
        truncate_ragged_lines=True,
        schema_overrides=[pl.String for column in column_order],
    )

    # check if using all_types
    if all_types is not None and types is not None:
        raise Exception('cannot specify both types and all_types')
    elif all_types is not None:
        types = all_types

    # cast types
    new_types = []
    for c, column in enumerate(df.columns):
        new_type = None
        if types is not None:
            if isinstance(types, list):
                if len(types) > c and types[c] is not None:
                    new_type = types[c]
            elif isinstance(types, dict):
                if column in types and types[column] is not None:
                    new_type = types[column]
            else:
                raise Exception('invalid format for types')

        if new_type is None:
            new_type = infer_type(df[column])

        if new_type == pl.Datetime or isinstance(new_type, pl.Datetime):
            time_format = '%Y-%m-%d %H:%M:%S%.3f %Z'
            df = df.with_columns(pl.col(column).str.to_datetime(time_format))
            new_type = None

        new_types.append(new_type)

    # check that all types were used
    if isinstance(types, dict):
        missing_columns = [
            name for name in types.keys() if name not in df.columns
        ]
        if len(missing_columns) > 0:
            raise Exception(
                'types specified for missing columns: ' + str(missing_columns)
            )
    if all_types is not None:
        missing_columns = [name for name in df.columns if name not in all_types]
        if len(missing_columns) > 0:
            raise Exception(
                'types not specified for columns: ' + str(missing_columns)
            )

    new_columns = []
    for column, type in zip(df.columns, new_types):
        if type is not None:
            if type == pl.Boolean:
                new_column = pl.col(column) == 'true'
            else:
                new_column = pl.col(column).cast(type)
            new_columns.append(new_column)
    df = df.with_columns(*new_columns)

    return df


def infer_type(s: pl.Series) -> pl.DataType:
    import re

    import polars as pl

    # Heuristic: detect common UTC timestamp format used by Dune exports
    try:
        non_null = [v for v in s.to_list() if v is not None and v != '<nil>']
        if non_null and all(
            isinstance(v, str)
            and re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} UTC$", v)
            for v in non_null
        ):
            return pl.Datetime
    except Exception:
        pass

    try:
        as_str = pl.DataFrame(s).write_csv(None)
        return pl.read_csv(io.StringIO(as_str))[s.name].dtype
    except Exception:
        return pl.String()



def _poll_execution(
    execution: Execution,
    *,
    api_key: str | None,
    poll_interval: float,
    verbose: bool,
    timeout_seconds: float | None,
) -> None:
    import random
    import time

    # process inputs
    url = _urls.get_execution_status_url(execution['execution_id'])
    execution_id = execution['execution_id']
    if api_key is None:
        api_key = _urls.get_api_key()
    headers = {'X-Dune-API-Key': api_key, 'User-Agent': get_user_agent()}

    # print summary
    t_start = time.time()

    # poll until completion
    sleep_amount = poll_interval
    while True:
        t_poll = time.time()

        # print summary
        if verbose:
            print(
                'waiting for results, execution_id = '
                + str(execution['execution_id'])
                + ', t = '
                + '%.02f' % (t_poll - t_start)
            )

        # poll
        response = _http_get(url, headers=headers, timeout=_GET_TIMEOUT)
        result = response.json()
        if (
            'is_execution_finished' not in result
            and response.status_code == 429
        ):
            sleep_amount = sleep_amount * random.uniform(1, 2)
            time.sleep(sleep_amount)
            continue
        if result['is_execution_finished']:
            if result['state'] == 'QUERY_STATE_FAILED':
                # Enrich error message with state and any error details if present
                err_detail = ''
                try:
                    if 'error' in result and result['error']:
                        err_detail = f", error={result['error']}"
                except Exception:
                    pass
                raise Exception(
                    f"QUERY FAILED execution_id={execution_id} state={result.get('state')}{err_detail}"
                )
            execution['timestamp'] = _parse_timestamp(
                result['execution_started_at']
            )
            break

        # timeout check
        if timeout_seconds is not None and (t_poll - t_start) > timeout_seconds:
            raise TimeoutError(
                f'query polling timed out after {timeout_seconds} seconds'
            )

        # wait until polling interval
        t_wait = time.time() - t_poll
        if t_wait < poll_interval:
            time.sleep(poll_interval - t_wait)

    # check for errors
    if result['state'] == 'QUERY_STATE_FAILED':
        err_detail = ''
        try:
            if 'error' in result and result['error']:
                err_detail = f", error={result['error']}"
        except Exception:
            pass
        raise Exception(
            f"QUERY FAILED execution_id={execution_id} state={result.get('state')}{err_detail}"
        )


def get_latest_execution(
    execute_kwargs: ExecuteKwargs,
    *,
    allow_unfinished: bool = False,
) -> Execution | None:
    import json
    import random


    query_id = execute_kwargs['query_id']
    api_key = execute_kwargs['api_key']
    parameters = execute_kwargs['parameters']
    if query_id is None:
        raise Exception('query_id required for get_latest_execution')

    # process inputs
    if api_key is None:
        api_key = _urls.get_api_key()
    headers = {'X-Dune-API-Key': api_key, 'User-Agent': get_user_agent()}
    data: dict[str, Any] = {}
    if parameters is not None:
        data['query_parameters'] = parameters
    data['limit'] = 0
    url = _urls.get_query_results_url(query_id, parameters=data, csv=False)

    sleep_amount = 1.0
    while True:
        # perform request
        response = _http_get(url, headers=headers, timeout=15.0)
        if response.status_code in (429, 502):
            sleep_amount = sleep_amount * random.uniform(1, 2)
            time.sleep(sleep_amount)
            continue

        # check if result is error
        result = response.json()
        try:
            if 'error' in result:
                if (
                    result['error']
                    == 'not found: No execution found for the latest version of the given query'
                ):
                    return None
                if response.status_code == 429:
                    sleep_amount = sleep_amount * random.uniform(1, 2)
                    time.sleep(sleep_amount)
                raise Exception(result['error'])
        except json.JSONDecodeError:
            pass

        break

    # process result
    if not result['is_execution_finished'] and not allow_unfinished:
        return None
    execution: Execution = {'execution_id': result['execution_id']}
    if 'execution_started_at' in result:
        execution['timestamp'] = int(
            _parse_timestamp(result['execution_started_at'])
        )
    return execution


def get_user_agent() -> str:
    # Identify as spice-mcp vendored spice client
    return 'spice-mcp/' + ADAPTER_VERSION

# ---------------------------------------------------------------------------
# Public aliases expected by adapter/tests (non-underscored names)

determine_input_type = _determine_input_type
get_query_latest_age = _get_query_latest_age
execute_query = _execute
get_results = _get_results
process_result = _process_result
poll_execution = _poll_execution
