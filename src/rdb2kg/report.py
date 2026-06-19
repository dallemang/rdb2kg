from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from .db_service import DatabaseService, DatabaseError, QueryResult
from .r2rml import parse_mapping
from .materialize import materialize
from .sparql_service import query_sparql
from .workspace_service import read_questions, OUTPUT_DIR

VALIDATED = "validated"
MISMATCH = "mismatch"
SPARQL_EMPTY = "sparql_empty"
SPARQL_ERROR = "sparql_error"
SQL_ERROR = "sql_error"
NO_SPARQL = "no_sparql"
MANUAL = "manual"

NEEDS_ATTENTION = {MISMATCH, SPARQL_EMPTY, SPARQL_ERROR, SQL_ERROR, NO_SPARQL}


@dataclass
class QuestionValidation:
    name: str
    question: str
    status: str
    detail: str
    sql_rows: int | None = None
    sparql_rows: int | None = None


@dataclass
class ValidationReport:
    results: list[QuestionValidation] = field(default_factory=list)
    total_triples: int = 0

    @property
    def validated(self) -> list[QuestionValidation]:
        return [r for r in self.results if r.status == VALIDATED]

    @property
    def needs_attention(self) -> list[QuestionValidation]:
        return [r for r in self.results if r.status in NEEDS_ATTENTION]

    @property
    def manual(self) -> list[QuestionValidation]:
        return [r for r in self.results if r.status == MANUAL]


def _norm(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float, Decimal)):
        f = float(v)
        return str(int(f)) if f == int(f) else repr(f)
    return str(v).strip()


def _rowset(result: QueryResult) -> list[tuple]:
    return sorted(tuple(sorted(_norm(v) for v in row.values())) for row in result.rows)


def validate_workspace(workspace_dir: Path, connection_string: str) -> ValidationReport:
    workspace_dir = Path(workspace_dir)
    mapping_path = workspace_dir / OUTPUT_DIR / "mapping.ttl"
    if not mapping_path.exists():
        raise FileNotFoundError(f"No mapping at {mapping_path}; run Step 3 first")

    graph_path = workspace_dir / OUTPUT_DIR / "materialized.ttl"
    mapping = parse_mapping(mapping_path)
    _, mat = materialize(connection_string, mapping, graph_path)

    report = ValidationReport(total_triples=mat.total_triples)

    for q in read_questions(workspace_dir):
        report.results.append(_validate_question(q, connection_string, graph_path))
    return report


def _validate_question(q, connection_string: str, graph_path: Path) -> QuestionValidation:
    if not q.sparql:
        return QuestionValidation(q.name, q.question, NO_SPARQL, "No SPARQL query written yet.")

    try:
        sparql_result = query_sparql(graph_path, q.sparql)
    except Exception as exc:
        return QuestionValidation(q.name, q.question, SPARQL_ERROR, f"SPARQL failed: {exc}")
    sparql_n = len(sparql_result)

    if not q.sql:
        return QuestionValidation(
            q.name, q.question, MANUAL,
            "No reference SQL; SPARQL ran but cannot be auto-compared.",
            sparql_rows=sparql_n,
        )

    try:
        with DatabaseService(connection_string) as db:
            sql_result = db.query(q.sql)
    except DatabaseError as exc:
        return QuestionValidation(
            q.name, q.question, SQL_ERROR, f"Reference SQL failed: {exc}",
            sparql_rows=sparql_n,
        )
    sql_n = len(sql_result)

    if _rowset(sql_result) == _rowset(sparql_result):
        return QuestionValidation(
            q.name, q.question, VALIDATED, "SPARQL results match the reference SQL.",
            sql_rows=sql_n, sparql_rows=sparql_n,
        )

    if sparql_n == 0 and sql_n > 0:
        detail = (
            "SPARQL returned no rows but the SQL did - likely a class or property "
            "name mismatch between ontology and mapping, or a mapping gap."
        )
        return QuestionValidation(q.name, q.question, SPARQL_EMPTY, detail,
                                  sql_rows=sql_n, sparql_rows=sparql_n)

    detail = (
        f"Result sets differ ({sql_n} SQL rows vs {sparql_n} SPARQL rows) - "
        "check for a wrong column mapped, a datatype mismatch, or an incomplete SPARQL pattern."
    )
    return QuestionValidation(q.name, q.question, MISMATCH, detail,
                              sql_rows=sql_n, sparql_rows=sparql_n)


def report_to_markdown(report: ValidationReport) -> str:
    lines = ["# Validation report", ""]
    lines.append(
        f"**Summary:** {len(report.validated)} validated, "
        f"{len(report.needs_attention)} need attention, "
        f"{len(report.manual)} for manual review "
        f"({report.total_triples} triples materialized)."
    )
    lines.append("")

    for r in report.results:
        counts = []
        if r.sql_rows is not None:
            counts.append(f"SQL rows: {r.sql_rows}")
        if r.sparql_rows is not None:
            counts.append(f"SPARQL rows: {r.sparql_rows}")
        suffix = f" ({', '.join(counts)})" if counts else ""
        lines.append(f"## {r.name} - {r.status}")
        lines.append(f"> {r.question}")
        lines.append(f"{r.detail}{suffix}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_report(workspace_dir: Path, report: ValidationReport) -> Path:
    out = Path(workspace_dir) / OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    path = out / "report.md"
    path.write_text(report_to_markdown(report), encoding="utf-8")
    return path
