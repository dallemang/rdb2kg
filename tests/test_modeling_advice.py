from rdb2kg.mcp_server import read_modeling_advice, _modeling_advice_path


def test_advice_file_exists_at_repo_root():
    assert _modeling_advice_path().exists()


def test_read_returns_content():
    text = read_modeling_advice()
    assert text.startswith("# Modeling Advice")


def test_env_override(tmp_path, monkeypatch):
    custom = tmp_path / "advice.md"
    custom.write_text("custom rules", encoding="utf-8")
    monkeypatch.setenv("RDB2KG_MODELING_ADVICE", str(custom))
    assert read_modeling_advice() == "custom rules"


def test_missing_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("RDB2KG_MODELING_ADVICE", str(tmp_path / "nope.md"))
    assert read_modeling_advice() == ""
