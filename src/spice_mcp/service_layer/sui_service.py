from __future__ import annotations

import time

from .query_service import QueryService


class SuiService:
    """Opinionated helpers for Sui package exploration."""

    def __init__(self, query_service: QueryService):
        self.query_service = query_service

    def events_preview(
        self, packages: list[str], *, hours: int = 72, limit: int = 50, performance: str = "large"
    ) -> dict[str, object]:
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - hours * 3600 * 1000

        norms = _normalize_packages(packages)
        if norms:
            preds = [f"lower(event_type) LIKE '{pkg}::%'" for pkg in norms]
            where = " OR ".join(preds)
            sql = (
                "SELECT timestamp_ms, package, module, event_type FROM sui.events "
                f"WHERE ({where}) AND timestamp_ms BETWEEN {start_ms} AND {now_ms} "
                "ORDER BY timestamp_ms DESC "
                f"LIMIT {limit}"
            )
        else:
            sql = (
                "SELECT timestamp_ms, package, module, event_type FROM sui.events "
                f"WHERE timestamp_ms BETWEEN {start_ms} AND {now_ms} "
                "ORDER BY timestamp_ms DESC LIMIT {limit}"
            ).format(limit=limit)

        result = self.query_service.execute(
            sql,
            performance=performance,
            timeout_seconds=60,
            limit=limit,
        )
        return {
            "rowcount": result["rowcount"],
            "columns": result["columns"],
            "data_preview": result["data_preview"],
        }

    def package_overview(
        self,
        packages: list[str],
        *,
        hours: int = 72,
        timeout_seconds: float | None = 30,
        performance: str = "large",
    ) -> dict[str, object]:
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - hours * 3600 * 1000
        norms = _normalize_packages(packages)
        in_clause = ",".join(f"'{pkg}'" for pkg in norms)

        out: dict[str, object] = {"ok": True}

        def _run(sql: str, limit: int) -> dict[str, object]:
            return self.query_service.execute(
                sql,
                performance=performance,
                timeout_seconds=timeout_seconds,
                limit=limit,
            )

        # Events
        try:
            sql_ev = (
                "SELECT timestamp_ms, package, module, event_type, event_json FROM sui.events "
                f"WHERE lower(package) IN ({in_clause}) AND timestamp_ms BETWEEN {start_ms} AND {now_ms} "
                "ORDER BY timestamp_ms DESC LIMIT 200"
            )
            ev = _run(sql_ev, 200)
            out["events_preview"] = ev.get("data_preview")
            out["events_count"] = ev.get("rowcount")
        except TimeoutError:
            out["events_timeout"] = True
        except Exception as exc:
            out["events_error"] = str(exc)

        # Transactions
        try:
            sql_tx = (
                "WITH txs AS (SELECT DISTINCT transaction_digest FROM sui.events "
                f"WHERE lower(package) IN ({in_clause}) AND timestamp_ms BETWEEN {start_ms} AND {now_ms}) "
                "SELECT t.* FROM sui.transactions t "
                "JOIN txs ON t.transaction_digest = txs.transaction_digest "
                "ORDER BY t.timestamp_ms DESC LIMIT 200"
            )
            tx = _run(sql_tx, 200)
            out["transactions_preview"] = tx.get("data_preview")
            out["transactions_count"] = tx.get("rowcount")
        except TimeoutError:
            out["transactions_timeout"] = True
        except Exception as exc:
            out["transactions_error"] = str(exc)

        # Objects
        try:
            sql_ob = (
                "WITH txs AS (SELECT DISTINCT transaction_digest FROM sui.events "
                f"WHERE lower(package) IN ({in_clause}) AND timestamp_ms BETWEEN {start_ms} AND {now_ms}) "
                "SELECT o.* FROM sui.objects o "
                "WHERE o.previous_transaction IN (SELECT transaction_digest FROM txs) "
                "ORDER BY o.timestamp_ms DESC LIMIT 200"
            )
            ob = _run(sql_ob, 200)
            out["objects_preview"] = ob.get("data_preview")
            out["objects_count"] = ob.get("rowcount")
        except TimeoutError:
            out["objects_timeout"] = True
        except Exception as exc:
            out["objects_error"] = str(exc)

        return out


def _normalize_packages(packages: list[str]) -> list[str]:
    norms: list[str] = []
    for p in packages:
        value = p.lower()
        if not value.startswith("0x"):
            value = "0x" + value
        norms.append(value)
    return norms
