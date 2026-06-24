from dataclasses import asdict
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .inspect_db import inspect_database, schema_to_yaml
from .db_service import DatabaseService
from .r2rml import parse_mapping
from .materialize import materialize as do_materialize
from .sparql_service import query_sparql as run_sparql
from . import workspace_service as ws
from .report import validate_workspace, report_to_markdown, write_report
from .html_report import generate_html_report as _gen_html

mcp = FastMCP("rdb2kg")


@mcp.tool()
def inspect_schema(connection_string: str) -> str:
    """Return the database schema as a compact YAML string."""
    schema = inspect_database(connection_string)
    return schema_to_yaml(schema)


@mcp.tool()
def query_sql(connection_string: str, sql: str) -> list[dict[str, Any]]:
    """Run a SQL SELECT and return the rows as a list of dicts."""
    with DatabaseService(connection_string) as db:
        return db.query(sql).rows


@mcp.tool()
def materialize(connection_string: str, mapping_path: str, output_path: str) -> str:
    """Apply an R2RML mapping to the database, write RDF to output_path, return a report."""
    mapping = parse_mapping(Path(mapping_path))
    _, report = do_materialize(connection_string, mapping, Path(output_path))
    lines = []
    for stats in report.map_stats:
        label = stats.map_id.split("#")[-1] if "#" in stats.map_id else stats.map_id
        lines.append(f"{label}: {stats.triples_produced} triples ({stats.rows_read} rows)")
        for w in stats.warnings:
            lines.append(f"  WARNING: {w}")
    lines.append(f"total: {report.total_triples} triples -> {report.output_path}")
    return "\n".join(lines)


@mcp.tool()
def query_sparql(graph_path: str, sparql: str) -> list[dict[str, Any]]:
    """Run a SPARQL SELECT against a Turtle graph file and return the rows as a list of dicts."""
    return run_sparql(Path(graph_path), sparql).rows


@mcp.tool()
def read_background(workspace_dir: str) -> str:
    """Concatenate all text files in the workspace's background/ directory, with per-file headers."""
    return ws.read_background(Path(workspace_dir))


@mcp.tool()
def read_questions(workspace_dir: str) -> list[dict[str, Any]]:
    """Return all competency questions in the workspace's questions/ directory as a list of dicts."""
    return [asdict(q) for q in ws.read_questions(Path(workspace_dir))]


@mcp.tool()
def write_question(
    workspace_dir: str,
    name: str,
    question: str,
    notes: str | None = None,
    sql: str | None = None,
    source: str | None = None,
) -> str:
    """Write a competency question to questions/<name>.yaml. source traces it to a schema feature or background doc."""
    return str(ws.write_question(Path(workspace_dir), name, question, notes, sql, source))


@mcp.tool()
def update_question(
    workspace_dir: str,
    name: str,
    sparql: str | None = None,
    status: str | None = None,
) -> str:
    """Add or replace the sparql and/or status fields of an existing question, preserving the rest."""
    return str(ws.update_question(Path(workspace_dir), name, sparql, status))


@mcp.tool()
def diff_questions(workspace_dir: str) -> dict[str, Any]:
    """Diff the current questions against the last snapshot (added/removed/modified/unchanged), then refresh the snapshot."""
    return asdict(ws.diff_questions(Path(workspace_dir)))


@mcp.tool()
def write_ontology(workspace_dir: str, turtle: str) -> str:
    """Write the OWL ontology (Turtle) to output/ontology.ttl."""
    return str(ws.write_ontology(Path(workspace_dir), turtle))


@mcp.tool()
def write_mapping(workspace_dir: str, turtle: str) -> str:
    """Write the R2RML mapping (Turtle) to output/mapping.ttl."""
    return str(ws.write_mapping(Path(workspace_dir), turtle))


@mcp.tool()
def validate(workspace_dir: str, connection_string: str) -> str:
    """Materialize the graph, validate every question's SPARQL against its reference SQL, write output/report.md, and return the report."""
    report = validate_workspace(Path(workspace_dir), connection_string)
    write_report(Path(workspace_dir), report)
    return report_to_markdown(report)


@mcp.tool()
def generate_html_report(workspace_dir: str) -> str:
    """Generate a self-contained HTML report: Cytoscape ontology graph + competency question results. Writes output/report.html and returns its path."""
    html = _gen_html(Path(workspace_dir))
    path = ws.write_html_report(Path(workspace_dir), html)
    return str(path)


def _modeling_advice_path() -> Path:
    override = os.environ.get("RDB2KG_MODELING_ADVICE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "ModelingAdvice.md"


@mcp.tool()
def read_modeling_advice() -> str:
    """Return the project's authoritative modeling guidance (ModelingAdvice.md). Consult it before designing an ontology or R2RML mapping."""
    path = _modeling_advice_path()
    return path.read_text(encoding="utf-8") if path.exists() else ""


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
