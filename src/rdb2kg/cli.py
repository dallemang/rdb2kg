from pathlib import Path
from typing import Optional, Annotated
import typer

app = typer.Typer(
    help="rdb2kg -- turn relational databases into RDF knowledge graphs.",
    no_args_is_help=True,
)


def _db_url(db_path: Path) -> str:
    s = str(db_path)
    if "://" in s:
        return s
    return f"sqlite:///{db_path.resolve()}"


@app.command()
def inspect(
    db_path: Annotated[
        Path,
        typer.Argument(help="Path to a SQLite file, or any SQLAlchemy connection URL"),
    ],
) -> None:
    """Print the database schema as YAML."""
    from .inspect_db import inspect_database, schema_to_yaml
    schema = inspect_database(_db_url(db_path))
    print(schema_to_yaml(schema))


@app.command()
def materialize(
    db_path: Annotated[
        Path,
        typer.Argument(help="Path to a SQLite file, or any SQLAlchemy connection URL"),
    ],
    mapping: Annotated[
        Path,
        typer.Argument(help="R2RML mapping file (Turtle)"),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option("-o", "--output", help="Output Turtle file (default: output.ttl)"),
    ] = None,
) -> None:
    """Apply an R2RML mapping to a database and write RDF triples."""
    from .r2rml import parse_mapping
    from .materialize import materialize as do_materialize

    if output is None:
        output = Path("output.ttl")

    r2rml = parse_mapping(mapping)
    _, report = do_materialize(_db_url(db_path), r2rml, output)

    for stats in report.map_stats:
        label = stats.map_id.split("#")[-1] if "#" in stats.map_id else stats.map_id
        print(f"{label}: {stats.triples_produced} triples ({stats.rows_read} rows)")
        for w in stats.warnings:
            print(f"  WARNING: {w}")
    print(f"total: {report.total_triples} triples -> {output}")
