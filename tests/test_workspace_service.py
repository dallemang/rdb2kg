import yaml
import pytest

from rdb2kg.workspace_service import (
    read_background,
    read_questions,
    write_question,
    update_question,
    diff_questions,
    write_ontology,
    write_mapping,
)


# ── background ingestion ──────────────────────────────────────────────────────

def test_read_background_empty(tmp_path):
    assert read_background(tmp_path) == ""


def test_read_background_concatenates_with_headers(tmp_path):
    bg = tmp_path / "background"
    bg.mkdir()
    (bg / "glossary.md").write_text("An album is a collection of tracks.", encoding="utf-8")
    (bg / "demo.sql").write_text("SELECT * FROM Album;", encoding="utf-8")
    text = read_background(tmp_path)
    assert "# === glossary.md ===" in text
    assert "An album is a collection of tracks." in text
    assert "# === demo.sql ===" in text


def test_read_background_skips_binary_suffixes(tmp_path):
    bg = tmp_path / "background"
    bg.mkdir()
    (bg / "notes.txt").write_text("keep me", encoding="utf-8")
    (bg / "logo.png").write_bytes(b"\x89PNG\r\n")
    text = read_background(tmp_path)
    assert "keep me" in text
    assert "logo.png" not in text


# ── question read / write ─────────────────────────────────────────────────────

def test_write_then_read_question(tmp_path):
    write_question(
        tmp_path,
        "albums_by_artist",
        "What albums does a given artist have?",
        sql="SELECT a.Title FROM Album a\nWHERE a.ArtistId = 1",
        source="schema: Album.ArtistId -> Artist",
    )
    questions = read_questions(tmp_path)
    assert len(questions) == 1
    q = questions[0]
    assert q.name == "albums_by_artist"
    assert q.question == "What albums does a given artist have?"
    assert "SELECT a.Title" in q.sql
    assert q.source == "schema: Album.ArtistId -> Artist"
    assert q.sparql is None
    assert q.status is None


def test_written_question_is_valid_yaml_block_scalar(tmp_path):
    path = write_question(
        tmp_path,
        "q1",
        "Q?",
        sql="SELECT 1\nFROM t",
    )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["question"] == "Q?"
    assert data["sql"].strip() == "SELECT 1\nFROM t"


def test_update_question_adds_sparql_and_status(tmp_path):
    write_question(tmp_path, "q1", "Q?", sql="SELECT 1")
    update_question(tmp_path, "q1", sparql="SELECT ?x WHERE { ?x a ?y }", status="validated")
    q = read_questions(tmp_path)[0]
    assert q.sql == "SELECT 1"
    assert q.status == "validated"
    assert "?x" in q.sparql


def test_update_question_missing_raises(tmp_path):
    (tmp_path / "questions").mkdir()
    with pytest.raises(FileNotFoundError):
        update_question(tmp_path, "nope", status="validated")


def test_read_questions_empty(tmp_path):
    assert read_questions(tmp_path) == []


# ── diff / review gate ────────────────────────────────────────────────────────

def test_diff_first_run_all_added(tmp_path):
    write_question(tmp_path, "q1", "Q1?")
    write_question(tmp_path, "q2", "Q2?")
    diff = diff_questions(tmp_path)
    assert sorted(diff.added) == ["q1", "q2"]
    assert diff.removed == []
    assert diff.changed is True


def test_diff_detects_add_remove_modify(tmp_path):
    write_question(tmp_path, "q1", "Q1?")
    write_question(tmp_path, "q2", "Q2?")
    diff_questions(tmp_path)  # snapshot

    update_question(tmp_path, "q1", status="validated")  # modify
    (tmp_path / "questions" / "q2.yaml").unlink()        # remove
    write_question(tmp_path, "q3", "Q3?")                # add

    diff = diff_questions(tmp_path)
    assert diff.added == ["q3"]
    assert diff.removed == ["q2"]
    assert diff.modified == ["q1"]


def test_diff_no_changes(tmp_path):
    write_question(tmp_path, "q1", "Q1?")
    diff_questions(tmp_path)
    diff = diff_questions(tmp_path)
    assert diff.changed is False
    assert diff.unchanged == ["q1"]


# ── output artifacts ──────────────────────────────────────────────────────────

def test_write_ontology_and_mapping(tmp_path):
    o = write_ontology(tmp_path, "@prefix ex: <http://example.org/> .")
    m = write_mapping(tmp_path, "@prefix rr: <http://www.w3.org/ns/r2rml#> .")
    assert o.name == "ontology.ttl"
    assert m.name == "mapping.ttl"
    assert o.read_text(encoding="utf-8").startswith("@prefix ex:")
    assert m.parent.name == "output"
