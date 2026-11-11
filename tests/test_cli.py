import json

from literature_agent import cli
from literature_agent.models import Paper
from tests.conftest import FakeSource


def test_search_to_json_file(tmp_path, monkeypatch):
    paper = Paper(source="openalex", source_id="W1", title="T", abstract="A", query="hitl")
    monkeypatch.setattr(cli, "make_source", lambda name, settings: FakeSource(name, [paper]))
    out = tmp_path / "papers.json"
    assert cli.main(["search", "hitl", "--limit", "1", "--out", str(out)]) == 0
    assert json.loads(out.read_text())[0]["source_id"] == "W1"
    assert (tmp_path / "papers_search_run.json").exists()
