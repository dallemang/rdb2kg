from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import re
import yaml

_PLAIN_SAFE = re.compile(r"^[A-Za-z0-9][\w .,?!'/()-]*$")

BACKGROUND_DIR = "background"
QUESTIONS_DIR = "questions"
OUTPUT_DIR = "output"
SNAPSHOT_FILE = "output/.question_snapshot.json"

TEXT_SUFFIXES = {".txt", ".md", ".rst", ".csv", ".sql", ".json", ".yaml", ".yml"}


@dataclass
class Question:
    name: str
    question: str
    notes: str | None = None
    sql: str | None = None
    sparql: str | None = None
    status: str | None = None
    source: str | None = None


@dataclass
class QuestionDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed or self.modified)


def read_background(workspace_dir: Path) -> str:
    bg = Path(workspace_dir) / BACKGROUND_DIR
    if not bg.is_dir():
        return ""
    parts = []
    for path in sorted(bg.iterdir()):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        parts.append(f"# === {path.name} ===\n{text.strip()}")
    return "\n\n".join(parts)


def read_questions(workspace_dir: Path) -> list[Question]:
    qdir = Path(workspace_dir) / QUESTIONS_DIR
    if not qdir.is_dir():
        return []
    questions = []
    for path in sorted(qdir.glob("*.yaml")):
        questions.append(_load_question(path))
    return questions


def _load_question(path: Path) -> Question:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sql = data.get("sql")
    sparql = data.get("sparql")
    return Question(
        name=path.stem,
        question=data.get("question", ""),
        notes=data.get("notes"),
        sql=sql.rstrip() if sql else sql,
        sparql=sparql.rstrip() if sparql else sparql,
        status=data.get("status"),
        source=data.get("source"),
    )


def _question_path(workspace_dir: Path, name: str) -> Path:
    qdir = Path(workspace_dir) / QUESTIONS_DIR
    qdir.mkdir(parents=True, exist_ok=True)
    return qdir / f"{name}.yaml"


def _inline(value: str) -> str:
    if _PLAIN_SAFE.match(value):
        return value
    return json.dumps(value)


def _block(value: str) -> str:
    body = "\n".join("  " + line for line in value.rstrip().splitlines())
    return f"|\n{body}"


def _render_question(q: Question) -> str:
    lines = [f"question: {_inline(q.question)}"]
    if q.notes:
        lines.append(f"notes: {_inline(q.notes)}")
    if q.source:
        lines.append(f"source: {_inline(q.source)}")
    if q.sql:
        lines.append(f"sql: {_block(q.sql)}")
    if q.sparql:
        lines.append(f"sparql: {_block(q.sparql)}")
    if q.status:
        lines.append(f"status: {_inline(q.status)}")
    return "\n".join(lines) + "\n"


def write_question(
    workspace_dir: Path,
    name: str,
    question: str,
    notes: str | None = None,
    sql: str | None = None,
    source: str | None = None,
) -> Path:
    q = Question(name=name, question=question, notes=notes, sql=sql, source=source)
    path = _question_path(workspace_dir, name)
    path.write_text(_render_question(q), encoding="utf-8")
    return path


def update_question(
    workspace_dir: Path,
    name: str,
    sparql: str | None = None,
    status: str | None = None,
) -> Path:
    path = _question_path(workspace_dir, name)
    if not path.exists():
        raise FileNotFoundError(f"No question named {name!r} in {QUESTIONS_DIR}/")
    q = _load_question(path)
    if sparql is not None:
        q.sparql = sparql
    if status is not None:
        q.status = status
    path.write_text(_render_question(q), encoding="utf-8")
    return path


def diff_questions(workspace_dir: Path) -> QuestionDiff:
    current = {q.name: asdict(q) for q in read_questions(workspace_dir)}
    snapshot_path = Path(workspace_dir) / SNAPSHOT_FILE
    previous = {}
    if snapshot_path.exists():
        previous = json.loads(snapshot_path.read_text(encoding="utf-8"))

    diff = QuestionDiff()
    for name, q in current.items():
        if name not in previous:
            diff.added.append(name)
        elif previous[name] != q:
            diff.modified.append(name)
        else:
            diff.unchanged.append(name)
    for name in previous:
        if name not in current:
            diff.removed.append(name)

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return diff


def _write_output(workspace_dir: Path, filename: str, content: str) -> Path:
    out = Path(workspace_dir) / OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    path = out / filename
    path.write_text(content, encoding="utf-8")
    return path


def write_ontology(workspace_dir: Path, turtle: str) -> Path:
    return _write_output(workspace_dir, "ontology.ttl", turtle)


def write_mapping(workspace_dir: Path, turtle: str) -> Path:
    return _write_output(workspace_dir, "mapping.ttl", turtle)


def write_html_report(workspace_dir: Path, html: str) -> Path:
    return _write_output(workspace_dir, "report.html", html)
