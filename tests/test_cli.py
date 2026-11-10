import json

from literature_agent import cli
from literature_agent.models import Paper
from tests.conftest import FakeProvider, FakeSource


def test_search_then_screen(tmp_path, monkeypatch):
    paper = Paper(source="openalex", source_id="W1", title="T", abstract="A", query="hitl")
    monkeypatch.setattr(cli, "make_source", lambda name, settings: FakeSource(name, [paper]))
    monkeypatch.setenv("LITAGENT_DATA_DIR", str(tmp_path))
    out = tmp_path / "papers.json"
    assert cli.main(["search", "hitl", "--limit", "1", "--out", str(out)]) == 0
    assert json.loads(out.read_text())[0]["source_id"] == "W1"
    assert (tmp_path / "papers_search_run.json").exists()

    fake = FakeProvider(['{"is_relevant": false, "reason": "off-topic"}'])
    monkeypatch.setattr(cli.GroqProvider, "from_settings", classmethod(lambda cls, s: fake))
    evaluated = tmp_path / "evaluated.json"
    assert cli.main(["screen", str(out), "--out", str(evaluated)]) == 0
    result = json.loads(evaluated.read_text())[0]
    assert result["screening_topic"] == "hitl"        # topic taken from the stored query
    assert result["is_relevant"] is False
