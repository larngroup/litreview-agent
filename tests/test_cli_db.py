import json

from literature_agent import cli
from literature_agent.models import Paper
from tests.conftest import FakeProvider, FakeSource

REPLY = '{"decision": "include", "reason": "fits", "matched_inclusion": ["empirical"], "matched_exclusion": []}'


def setup(tmp_path, monkeypatch, replies):
    monkeypatch.setenv("LITAGENT_DB_PATH", str(tmp_path / "lit.db"))
    paper = Paper(source="openalex", source_id="W1", title="Some long enough paper title", abstract="A")
    monkeypatch.setattr(cli, "make_source", lambda name, settings: FakeSource(name, [paper]))
    fake = FakeProvider(replies)
    monkeypatch.setattr(cli, "get_provider", lambda settings, name=None, model=None: fake)
    return fake


def test_full_database_workflow(tmp_path, monkeypatch, capsys):
    setup(tmp_path, monkeypatch, [REPLY])
    assert cli.main(["project", "create", "demo", "--topic", "human in the loop",
                     "--include", "empirical", "--exclude", "editorial"]) == 0
    assert cli.main(["search", "hitl", "--project", "demo", "--source", "openalex", "--source", "crossref"]) == 0
    assert cli.main(["screen", "--project", "demo"]) == 0
    assert cli.main(["review", "--project", "demo", "--paper", "1", "--decision", "exclude", "--note", "x"]) == 0
    capsys.readouterr()
    assert cli.main(["status", "--project", "demo"]) == 0
    out = capsys.readouterr().out
    # Check that the status output contains the expected information - changed stage 5
    assert cli.main(["papers", "--project", "demo"]) == 0
    out = capsys.readouterr().out
    assert "Paper #1" in out
    assert "Title: Some long enough paper title" in out
    assert "DOI: Not available" in out
    assert "Link: Not available" in out
    assert "Abstract (database): YES" in out
    assert "LLM decision: include" in out
    assert "Human decision: exclude" in out
    #assert "model=include   human=exclude" in capsys.readouterr().out

    assert cli.main(["evaluate", "--project", "demo"]) == 0
    assert '"compared": 1' in capsys.readouterr().out


def test_criteria_update_and_failures(tmp_path, monkeypatch, capsys):
    setup(tmp_path, monkeypatch, ["bad", "bad"])
    cli.main(["project", "create", "demo", "--topic", "t"])
    cli.main(["project", "criteria", "demo", "--include", "a", "--include", "b"])
    assert '"a"' in capsys.readouterr().out
    cli.main(["search", "q", "--project", "demo"])
    cli.main(["screen", "--project", "demo"])
    capsys.readouterr()
    cli.main(["failures", "--project", "demo"])
    assert "1 failed screening(s)" in capsys.readouterr().out


def test_review_rejects_unknown_paper(tmp_path, monkeypatch, capsys):
    setup(tmp_path, monkeypatch, [])
    cli.main(["project", "create", "demo", "--topic", "t"])
    assert cli.main(["review", "--project", "demo", "--paper", "99", "--decision", "include"]) == 2


def test_import_json_creates_project(tmp_path, monkeypatch):
    monkeypatch.setenv("LITAGENT_DB_PATH", str(tmp_path / "lit.db"))
    papers = tmp_path / "papers_dataset.json"
    papers.write_text(json.dumps([{"id": "https://openalex.org/W9", "title": "Legacy record title here"}]))
    assert cli.main(["import-json", str(papers), "--project", "old", "--legacy-topic", "Human in the loop"]) == 0


def test_unknown_project_is_a_clear_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LITAGENT_DB_PATH", str(tmp_path / "lit.db"))
    assert cli.main(["status", "--project", "nope"]) == 2
    assert "not found" in capsys.readouterr().out
