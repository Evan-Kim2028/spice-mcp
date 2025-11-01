"""
Spellbook Explorer - Parses dbt models from Spellbook GitHub repository.

This adapter clones or accesses the Spellbook GitHub repo and parses dbt models
to discover available tables, schemas, and column information.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ...core.models import SchemaMatch, TableColumn, TableDescription, TableSummary
from ...core.ports import CatalogExplorer


class SpellbookExplorer(CatalogExplorer):
    """
    Explorer that parses Spellbook dbt models from GitHub repository.
    
    Spellbook repo: https://github.com/duneanalytics/spellbook
    """

    SPELLBOOK_REPO_URL = "https://github.com/duneanalytics/spellbook.git"
    DEFAULT_BRANCH = "main"

    def __init__(
        self,
        repo_path: Path | str | None = None,
        repo_url: str | None = None,
        branch: str | None = None,
    ):
        """
        Initialize Spellbook explorer.
        
        Args:
            repo_path: Local path to spellbook repo (if None, will clone to temp dir)
            repo_url: GitHub repo URL (defaults to official spellbook repo)
            branch: Git branch to use (defaults to 'main')
        """
        self.repo_url = repo_url or self.SPELLBOOK_REPO_URL
        self.branch = branch or self.DEFAULT_BRANCH
        self._repo_path: Path | None = None
        self._models_cache: dict[str, list[dict[str, Any]]] | None = None
        
        if repo_path:
            self._repo_path = Path(repo_path)
        else:
            # Use cache directory if available, otherwise temp
            cache_base = os.getenv("SPICE_SPELLBOOK_CACHE", tempfile.gettempdir())
            self._repo_path = Path(cache_base) / "spellbook_repo"

    def _ensure_repo(self) -> Path:
        """Ensure spellbook repo is cloned locally."""
        if self._repo_path is None:
            raise RuntimeError("Repository path not set")
        
        repo_path = self._repo_path
        
        # Clone if doesn't exist
        if not repo_path.exists() or not (repo_path / ".git").exists():
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", self.branch, self.repo_url, str(repo_path)],
                check=True,
                capture_output=True,
            )
        else:
            # Update if exists
            try:
                subprocess.run(
                    ["git", "-C", str(repo_path), "pull", "origin", self.branch],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
            except Exception:
                pass  # Ignore update failures
        
        return repo_path

    def _load_models(self) -> dict[str, list[dict[str, Any]]]:
        """Load all dbt models from spellbook repo, organized by schema/subproject."""
        if self._models_cache is not None:
            return self._models_cache
        
        repo_path = self._ensure_repo()
        models: dict[str, list[dict[str, Any]]] = {}
        
        # Spellbook uses subprojects - look in dbt_subprojects/ and models/ directories
        subproject_dirs = [
            repo_path / "dbt_subprojects",
            repo_path / "models",
        ]
        
        for base_dir in subproject_dirs:
            if not base_dir.exists():
                continue
            
            # Walk through subproject directories
            for subproject_dir in base_dir.iterdir():
                if not subproject_dir.is_dir():
                    continue
                
                # Skip hidden directories
                if subproject_dir.name.startswith("."):
                    continue
                
                schema_name = subproject_dir.name
                if schema_name not in models:
                    models[schema_name] = []
                
                # Find SQL model files
                models_dir = subproject_dir / "models"
                if not models_dir.exists():
                    models_dir = subproject_dir
                
                for sql_file in models_dir.rglob("*.sql"):
                    # Skip files in target/ or node_modules/
                    if "target" in sql_file.parts or "node_modules" in sql_file.parts:
                        continue
                    
                    # Extract model name from file path
                    # models/schema/table.sql -> table
                    model_name = sql_file.stem
                    
                    # Try to find schema.yml for metadata
                    schema_yml = sql_file.parent / "schema.yml"
                    if not schema_yml.exists():
                        schema_yml = sql_file.parent.parent / "schema.yml"
                    
                    models[schema_name].append({
                        "name": model_name,
                        "file": sql_file,
                        "schema_yml": schema_yml if schema_yml.exists() else None,
                        "schema": schema_name,
                    })
        
        self._models_cache = models
        return models

    def find_schemas(self, keyword: str) -> Sequence[SchemaMatch]:
        """
        Find schemas (subprojects) matching keyword in Spellbook repo.
        
        This searches through dbt subproject names and model descriptions.
        """
        models = self._load_models()
        matches: list[SchemaMatch] = []
        keyword_lower = keyword.lower()
        
        for schema_name, model_list in models.items():
            # Match schema name
            if keyword_lower in schema_name.lower():
                matches.append(SchemaMatch(schema=schema_name))
                continue
            
            # Match model names/descriptions
            for model in model_list:
                if keyword_lower in model["name"].lower():
                    if not any(m.schema == schema_name for m in matches):
                        matches.append(SchemaMatch(schema=schema_name))
                    break
        
        return matches

    def list_tables(self, schema: str, limit: int | None = None) -> Sequence[TableSummary]:
        """
        List tables (dbt models) in a given schema/subproject.
        
        Returns model names from the spellbook repository.
        """
        models = self._load_models()
        schema_models = models.get(schema, [])
        
        summaries = [
            TableSummary(schema=schema, table=model["name"])
            for model in schema_models
        ]
        
        if limit is not None:
            summaries = summaries[:limit]
        
        return summaries

    def describe_table(self, schema: str, table: str) -> TableDescription:
        """
        Describe table columns by parsing dbt model SQL and schema.yml.
        
        Attempts to extract column information from:
        1. schema.yml file (if exists)
        2. SQL SELECT statement columns
        3. Fallback to basic inference
        """
        models = self._load_models()
        schema_models = models.get(schema, [])
        
        # Find matching model
        model_info = None
        for model in schema_models:
            if model["name"] == table:
                model_info = model
                break
        
        if model_info is None:
            raise ValueError(f"Table {schema}.{table} not found in Spellbook")
        
        columns: list[TableColumn] = []
        
        # Try to parse schema.yml first
        if model_info["schema_yml"]:
            columns = self._parse_schema_yml(model_info["schema_yml"], table)
        
        # Fallback: parse SQL file for column hints
        if not columns:
            columns = self._parse_sql_columns(model_info["file"])
        
        # If still no columns, create a basic placeholder
        if not columns:
            columns = [
                TableColumn(name="column_1", dune_type="VARCHAR", polars_dtype="Utf8")
            ]
        
        return TableDescription(
            fully_qualified_name=f"{schema}.{table}",
            columns=columns,
        )

    def _parse_schema_yml(self, schema_yml_path: Path, table_name: str) -> list[TableColumn]:
        """Parse dbt schema.yml to extract column definitions."""
        try:
            try:
                import yaml
            except ImportError:
                # PyYAML not available, skip schema.yml parsing
                return []
            
            with open(schema_yml_path, encoding="utf-8") as f:
                content = yaml.safe_load(f)
            
            if not isinstance(content, dict):
                return []
            
            # Find model in schema.yml
            models = content.get("models", [])
            for model in models:
                if model.get("name") == table_name:
                    cols = model.get("columns", [])
                    return [
                        TableColumn(
                            name=col.get("name", ""),
                            dune_type=col.get("data_type", "VARCHAR"),
                            polars_dtype=col.get("data_type"),
                            comment=col.get("description"),
                        )
                        for col in cols
                    ]
        except Exception:
            pass
        
        return []

    def _parse_sql_columns(self, sql_file: Path) -> list[TableColumn]:
        """Parse SQL file to extract column names from SELECT statements."""
        try:
            with open(sql_file, encoding="utf-8") as f:
                sql = f.read()
            
            # Look for SELECT ... FROM patterns
            # Match: SELECT col1, col2, col3 FROM ...
            select_match = re.search(
                r"SELECT\s+(.+?)\s+FROM",
                sql,
                re.IGNORECASE | re.DOTALL,
            )
            
            if select_match:
                cols_str = select_match.group(1)
                # Split by comma, but handle function calls and aliases
                cols = []
                for col in cols_str.split(","):
                    col = col.strip()
                    # Extract column name (handle aliases: col AS alias -> col)
                    if " AS " in col.upper():
                        col = col.split(" AS ", 1)[0].strip()
                    elif " " in col and not col.startswith("("):
                        # Might be alias without AS
                        parts = col.split()
                        col = parts[0].strip()
                    
                    # Clean up function calls: function(col) -> col
                    col = re.sub(r"^\w+\((.+)\)", r"\1", col)
                    col = col.strip().strip('"').strip("'")
                    
                    if col and col not in ["*", "DISTINCT"]:
                        cols.append(
                            TableColumn(
                                name=col,
                                dune_type="VARCHAR",  # Default, can't infer from SQL
                                polars_dtype="Utf8",
                            )
                        )
                
                return cols[:20]  # Limit to reasonable number
        except Exception:
            pass
        
        return []

