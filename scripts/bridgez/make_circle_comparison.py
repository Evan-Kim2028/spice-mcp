import csv
from pathlib import Path


BASE = Path("notes/bridgez")
CIRCLE_DIR = BASE / "circle"


def read_single_row_metrics(path: Path):
    with path.open() as f:
        reader = csv.DictReader(f)
        row = next(reader)
        return {
            "tx_count": float(row.get("tx_count", 0) or 0),
            "total_usd": float(row.get("total_usd", 0) or 0),
            "avg_usd": float(row.get("avg_usd", 0) or 0),
        }


def read_circle_totals(path: Path):
    rows = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                {
                    "schema": r["schema"],
                    "usd_out_30d": float(r["usd_out_30d"]) if r["usd_out_30d"] else 0.0,
                    "usd_out_ytd": float(r["usd_out_ytd"]) if r["usd_out_ytd"] else 0.0,
                }
            )
    return rows


def write_text(path: Path, content: str):
    path.write_text(content)


def update_readme(readme_path: Path, section: str):
    # Append or replace a Circle vs LayerZero section
    marker_start = "\n## Circle vs LayerZero (Summary)\n"
    content = readme_path.read_text() if readme_path.exists() else ""
    if "## Circle vs LayerZero (Summary)" in content:
        # replace from marker to end or next header
        parts = content.split("## Circle vs LayerZero (Summary)")
        head = parts[0]
        tail = "## Circle vs LayerZero (Summary)" + parts[1]
        # cut tail at the next header if present
        tail_lines = tail.split("\n## ")
        new_tail = "## Circle vs LayerZero (Summary)\n" + section
        if len(tail_lines) > 1:
            # keep next headers
            new_content = head + new_tail + "\n## " + "\n## ".join(tail_lines[1:])
        else:
            new_content = head + new_tail
        readme_path.write_text(new_content)
    else:
        readme_path.write_text(content.rstrip() + marker_start + section)


def fmt_usd(x: float) -> str:
    return f"${x:,.2f}"


def main():
    # LayerZero metrics
    lz_30d = read_single_row_metrics(BASE / "metrics_last_30d.csv")
    lz_ytd = read_single_row_metrics(BASE / "metrics_ytd.csv")

    # Circle per-schema summary
    circle_rows = read_circle_totals(CIRCLE_DIR / "flows_outbound_summary.csv")
    c_30d_total = sum(r["usd_out_30d"] for r in circle_rows)
    c_ytd_total = sum(r["usd_out_ytd"] for r in circle_rows)

    # Build comparison text
    pct_30d = (c_30d_total / lz_30d["total_usd"] * 100.0) if lz_30d["total_usd"] else 0.0
    pct_ytd = (c_ytd_total / lz_ytd["total_usd"] * 100.0) if lz_ytd["total_usd"] else 0.0

    top_circle_30d = sorted(circle_rows, key=lambda r: r["usd_out_30d"], reverse=True)[:5]
    top_circle_ytd = sorted(circle_rows, key=lambda r: r["usd_out_ytd"], reverse=True)[:5]

    lines = []
    lines.append("Circle vs LayerZero (USD volumes)\n")
    lines.append(f"- LayerZero — 30d: {fmt_usd(lz_30d['total_usd'])}; YTD: {fmt_usd(lz_ytd['total_usd'])}")
    lines.append(f"- Circle (CCTP outbound) — 30d: {fmt_usd(c_30d_total)} ({pct_30d:.1f}% of LZ); YTD: {fmt_usd(c_ytd_total)} ({pct_ytd:.1f}% of LZ)\n")
    lines.append("Top Circle schemas (30d):")
    for r in top_circle_30d:
        lines.append(f"- {r['schema']}: {fmt_usd(r['usd_out_30d'])}")
    lines.append("")
    lines.append("Top Circle schemas (YTD):")
    for r in top_circle_ytd:
        lines.append(f"- {r['schema']}: {fmt_usd(r['usd_out_ytd'])}")
    lines.append("")
    lines.append("Note: circle_bnb and circle_zksync may be missing if their tables/columns differ; totals reflect included schemas only.")

    text = "\n".join(lines) + "\n"

    # Write dedicated comparison under circle
    write_text(CIRCLE_DIR / "COMPARISON.txt", text)

    # Update top-level README with a concise section
    section = (
        f"\n- LayerZero — 30d: {fmt_usd(lz_30d['total_usd'])}; YTD: {fmt_usd(lz_ytd['total_usd'])}\n"
        f"- Circle (CCTP outbound) — 30d: {fmt_usd(c_30d_total)} ({pct_30d:.1f}% of LZ); YTD: {fmt_usd(c_ytd_total)} ({pct_ytd:.1f}% of LZ)\n"
        "- Top Circle schemas (30d): "
        + ", ".join([f"{r['schema']} {fmt_usd(r['usd_out_30d'])}" for r in top_circle_30d])
        + "\n"
    )
    update_readme(BASE / "README.md", section)


if __name__ == "__main__":
    main()

