import json

from literature_agent import cli
from literature_agent.models import Paper
from tests.conftest import FakeProvider, FakeSource


def test_database_workflow(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LITAGENT_DB_PATH", str(tmp_path / "lit.db"))
    paper = Paper(source="openalex", source_id="W1", title="Some long enough paper title", abstract="A")
    monkeypatch.setattr(cli, "make_source", lambda name, settings: FakeSource(name, [paper]))
    fake = FakeProvider(['{"is_relevant": true, "reason": "fits"}'])
    monkeypatch.setattr(cli.GroqProvider, "from_settings", classmethod(lambda cls, s: fake))

    assert cli.main(["project", "create", "demo", "--topic", "human in the loop"]) == 0
    assert cli.main(["search", "hitl", "--project", "demo", "--limit", "5"]) == 0
    assert cli.main(["screen", "--project", "demo"]) == 0
    capsys.readouterr()
    assert cli.main(["status", "--project", "demo"]) == 0
    out = capsys.readouterr().out
    assert "Papers: 1" in out and "'include': 1" in out


def test_import_json_creates_project(tmp_path, monkeypatch):
    monkeypatch.setenv("LITAGENT_DB_PATH", str(tmp_path / "lit.db"))
    papers = tmp_path / "papers_dataset.json"
    papers.write_text(json.dumps([{"id": "https://openalex.org/W9", "title": "Legacy record title here"}]))
    assert cli.main(["import-json", str(papers), "--project", "old", "--legacy-topic", "Human in the loop"]) == 0


def test_unknown_project_is_a_clear_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LITAGENT_DB_PATH", str(tmp_path / "lit.db"))
    assert cli.main(["status", "--project", "nope"]) == 2
    assert "not found" in capsys.readouterr().out
