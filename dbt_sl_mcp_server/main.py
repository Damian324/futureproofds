"""
MCP Server for dbt Semantic Layer (MetricFlow) integration.

This server exposes a small set of tools that let an AI agent query
metrics and dimensions defined in a local dbt Semantic Layer.
The agent does NOT have raw SQL access — all queries go through
MetricFlow to ensure consistent metric definitions (single source of truth).
"""

import csv
import json
import os
import subprocess
import tempfile
from typing import List, Dict, Optional

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

# Initialize the MCP server. The name shown here is what Cursor will display.
mcp = FastMCP("dbt-semantic-layer-server")

# Path to the dbt project directory. MetricFlow needs to know where
# the dbt_project.yml lives so it can read your semantic models.
# Set this in your .env file as DBT_PROJECT_DIR=/path/to/your/dbt/project
DBT_PROJECT_DIR = os.getenv("DBT_PROJECT_DIR")
if not DBT_PROJECT_DIR:
    raise RuntimeError(
        "DBT_PROJECT_DIR environment variable must be set, pointing "
        "to the directory containing your dbt_project.yml file."
    )

# Path to the directory containing profiles.yml.
# Required when dbt_cloud.yml is also present in ~/.dbt, which would
# otherwise cause MetricFlow to fail with "Could not find profile".
# Set this in your .env file as DBT_PROFILES_DIR=/Users/<you>/.dbt
DBT_PROFILES_DIR = os.getenv("DBT_PROFILES_DIR")
if not DBT_PROFILES_DIR:
    raise RuntimeError(
        "DBT_PROFILES_DIR environment variable must be set, pointing "
        "to the directory containing your profiles.yml file (usually ~/.dbt)."
    )


def _run_mf(args: List[str], capture_csv: bool = False) -> str:
    """
    Run a `mf` (MetricFlow) CLI command and return its output.

    args: list of command-line arguments AFTER `mf` (e.g. ["query", "--metrics", "..."])
    capture_csv: if True, request CSV output and return the file contents.

    Why we shell out: MetricFlow has a Python API but it's less stable
    than the CLI. The CLI is the supported interface and easier to debug.
    """
    if capture_csv:
        # Write CSV to a temporary file so we can parse it cleanly.
        with tempfile.NamedTemporaryFile(
            mode="r", suffix=".csv", delete=False
        ) as tmp:
            csv_path = tmp.name
        args = args + ["--csv", csv_path]

    result = subprocess.run(
        ["mf"] + args,
        cwd=DBT_PROJECT_DIR,
        env={**os.environ, "DBT_PROFILES_DIR": DBT_PROFILES_DIR},
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        # Surface the error back to the agent so it can adjust its approach.
        raise RuntimeError(
            f"MetricFlow command failed:\n"
            f"  args: {args}\n"
            f"  stderr: {result.stderr}\n"
            f"  stdout: {result.stdout}"
        )

    if capture_csv:
        with open(csv_path, "r") as f:
            content = f.read()
        os.remove(csv_path)
        return content

    return result.stdout


def _parse_csv_to_dicts(csv_text: str) -> List[Dict]:
    """Parse a CSV string into a list of row dictionaries."""
    if not csv_text.strip():
        return []
    reader = csv.DictReader(csv_text.splitlines())
    return [dict(row) for row in reader]


# =====================================================================
# TOOLS
# =====================================================================

@mcp.tool()
async def list_metrics() -> List[Dict]:
    """
    Return all metrics available in the dbt Semantic Layer.

    Each metric includes its name and (if available) its label and type.
    Use this as the first step when answering a question — discover
    what metrics exist before deciding which ones to query.
    """
    output = _run_mf(["list", "metrics"])

    # `mf list metrics` outputs lines in the format:
    #   • metric_name: dim1, dim2, ... and N more
    # We extract only the metric name (before the colon).
    metrics = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        clean = line.lstrip("•").strip()
        if clean and clean[0].isalpha():
            name = clean.split(":")[0].strip()
            metrics.append({"name": name})

    return metrics


@mcp.tool()
async def list_dimensions(metrics: Optional[List[str]] = None) -> List[Dict]:
    """
    Return dimensions available in the semantic layer.

    If `metrics` is provided, only returns dimensions that are valid
    for those specific metrics (dimensions you can group by when
    querying those metrics). If `metrics` is None, returns all dimensions
    across all semantic models.

    Always use this BEFORE calling query_metrics, so you know which
    `group_by` values are valid.
    """
    args = ["list", "dimensions"]
    if metrics:
        args += ["--metrics", ",".join(metrics)]

    output = _run_mf(args)

    dimensions = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        clean = line.lstrip("•").strip()
        if clean and clean[0].isalpha():
            dimensions.append({"name": clean})

    return dimensions


@mcp.tool()
async def get_metric_details(metric_name: str) -> Dict:
    """
    Return full details for a specific metric: its description, type,
    and the dimensions it can be grouped by.

    Use this when you need to understand a metric before querying it,
    or to confirm what dimensions are valid for grouping.
    """
    # Get dimensions valid for this metric
    dim_output = _run_mf(["list", "dimensions", "--metrics", metric_name])
    dimensions = [
        line.lstrip("•").strip()
        for line in dim_output.splitlines()
        if line.strip() and line.strip()[0].isalpha()
    ]

    return {
        "metric": metric_name,
        "available_dimensions": dimensions,
        "note": (
            "Use these dimension names in the `group_by` parameter of "
            "query_metrics. For time grouping, use 'metric_time' with a "
            "grain suffix like 'metric_time__day', 'metric_time__week', "
            "or 'metric_time__month'."
        ),
    }


@mcp.tool()
async def query_metrics(
    metrics: List[str],
    group_by: Optional[List[str]] = None,
    where: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    order_by: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[Dict]:
    """
    Query one or more metrics from the dbt Semantic Layer.

    Parameters:
      metrics: List of metric names to query (required).
        Example: ["key_saas_monthly_new_revenue_mt"]

      group_by: List of dimensions to group by (optional).
        For time grouping use 'metric_time__day', 'metric_time__week',
        or 'metric_time__month'.
        Example: ["metric_time__month", "keysaas_monthly_unique_key__product"]

      where: A SQL-style filter expression applied to the query (optional).
        Dimension names must use their full entity-prefixed form from list_dimensions.
        Example: "{{ Dimension('keysaas_monthly_unique_key__product') }} = 'core'"

      start_time: ISO date string to filter from (optional).
        Example: "2025-01-01"

      end_time: ISO date string to filter to (optional).
        Example: "2025-12-31"

      order_by: List of fields to order by (optional).
        Prefix with '-' for descending order.
        Example: ["-metric_time__month"]

      limit: Max number of rows to return (optional).

    Returns:
      List of dictionaries, one per result row.
    """
    args = ["query", "--metrics", ",".join(metrics)]

    if group_by:
        args += ["--group-by", ",".join(group_by)]
    if where:
        args += ["--where", where]
    if start_time:
        args += ["--start-time", start_time]
    if end_time:
        args += ["--end-time", end_time]
    if order_by:
        args += ["--order-by", ",".join(order_by)]
    if limit:
        args += ["--limit", str(limit)]

    csv_output = _run_mf(args, capture_csv=True)
    return _parse_csv_to_dicts(csv_output)


def main():
    # stdio transport is what Cursor uses to talk to MCP servers locally.
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
