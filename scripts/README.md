# Dune Query Management Scripts

Utility scripts for managing Dune queries created via spice-mcp.

## dune_collect_query_ids.py

Collect query IDs from query history logs. Extracts query IDs from admin actions (create/update/fork) in the query history JSONL file.

### Usage

```bash
# Collect all query IDs from history
python scripts/dune_collect_query_ids.py

# Collect IDs in a specific range
python scripts/dune_collect_query_ids.py --start-id 1000 --end-id 2000

# Save to file
python scripts/dune_collect_query_ids.py --output query_ids.txt

# Use custom history file
python scripts/dune_collect_query_ids.py --history-path /path/to/queries.jsonl
```

### Output

- Default: Prints query IDs to stdout (one per line)
- With `--output`: Writes to specified file

## dune_bulk_archive.py

Bulk archive or unarchive Dune queries from a file of query IDs.

### Prerequisites

- `DUNE_API_KEY` environment variable set
- File containing query IDs (one per line)

### Usage

```bash
# Archive queries from file
python scripts/dune_bulk_archive.py archive query_ids.txt

# Unarchive queries
python scripts/dune_bulk_archive.py unarchive query_ids.txt

# Verify ownership before archiving (recommended)
python scripts/dune_bulk_archive.py archive query_ids.txt --verify-owner

# Use custom API key
python scripts/dune_bulk_archive.py archive query_ids.txt --api-key YOUR_KEY
```

### Example Workflow

```bash
# 1. Collect query IDs from history
python scripts/dune_collect_query_ids.py --output my_queries.txt

# 2. Review the file
cat my_queries.txt

# 3. Archive them (with ownership verification)
python scripts/dune_bulk_archive.py archive my_queries.txt --verify-owner

# 4. Later, unarchive if needed
python scripts/dune_bulk_archive.py unarchive my_queries.txt
```

### Notes

- Scripts include rate limiting (0.1s delay between requests)
- Progress is printed to stdout
- Errors are printed to stderr
- Summary shows success/failure counts

