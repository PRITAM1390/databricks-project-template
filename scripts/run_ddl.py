"""Run DDL files against one bundle target through a SQL warehouse.

Usage: python scripts/run_ddl.py -t <target> <file1.sql> [<file2.sql> ...]
Files must live in src/ddl/<layer>/ and contain ONE SQL statement using :catalog and :schema.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem, StatementState

LAYER_ORDER = ["bronze", "silver", "gold"]


def bundle_summary(target: str) -> dict:
    """Ask the bundle for resolved names (catalogs, schemas, warehouse, host) of this target."""
    out = subprocess.run(
        ["databricks", "bundle", "summary", "-t", target, "-o", "json"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(out.stdout)


def layer_of(path: Path) -> str:
    """src/ddl/<layer>/file.sql -> <layer>"""
    parts = path.parts
    if len(parts) < 4 or parts[0] != "src" or parts[1] != "ddl" or parts[2] not in LAYER_ORDER:
        sys.exit(f"Not a DDL file under src/ddl/<bronze|silver|gold>/: {path}")
    return parts[2]


def run_statement(w: WorkspaceClient, warehouse_id: str, sql: str, catalog: str, schema: str) -> None:
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=sql,
        parameters=[
            StatementParameterListItem(name="catalog", value=catalog),
            StatementParameterListItem(name="schema", value=schema),
        ],
        wait_timeout="30s",
    )
    while resp.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(3)
        resp = w.statement_execution.get_statement(resp.statement_id)
    if resp.status.state != StatementState.SUCCEEDED:
        message = resp.status.error.message if resp.status.error else resp.status.state
        raise RuntimeError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target", required=True)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    summary = bundle_summary(args.target)
    host = summary["workspace"]["host"]
    warehouse_id = summary["variables"]["sql_warehouse_id"]["value"]
    schemas = summary["resources"]["schemas"]

    files = sorted(
        (Path(f) for f in args.files),
        key=lambda p: (LAYER_ORDER.index(layer_of(p)), p.name),
    )

    w = WorkspaceClient(host=host)
    for path in files:
        layer = layer_of(path)
        catalog = schemas[layer]["catalog_name"]
        schema = schemas[layer]["name"]
        print(f"Running {path} on {catalog}.{schema} ...")
        run_statement(w, warehouse_id, path.read_text(), catalog, schema)
        print(f"  OK: {path}")

    print(f"Done: {len(files)} DDL file(s) applied to target '{args.target}'.")


if __name__ == "__main__":
    main()
