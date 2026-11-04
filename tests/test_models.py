from literature_agent.models import Paper, normalise_doi


def test_normalise_doi_variants():
    assert normalise_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalise_doi("doi:10.1/x") == "10.1/x"
    assert normalise_doi("  10.5/Y ") == "10.5/y"
    for bad in (None, "", "n/a", "10.5", 42):
        assert normalise_doi(bad) is None


def test_paper_cleans_fields():
    paper = Paper(source="openalex", title="  A   title ", year=True, abstract=None, doi="https://doi.org/10.1/A")
    assert paper.title == "A title"
    assert paper.year is None
    assert paper.abstract == "" and paper.has_abstract is False
    assert paper.doi == "10.1/a"
    assert paper.display_title == "A title"


def test_paper_round_trips_through_json():
    paper = Paper(source="openalex", title="T", abstract="text", year=2020)
    data = paper.model_dump(mode="json")
    assert data["has_abstract"] is True
    again = Paper.model_validate(data)   # extra "has_abstract" key is ignored on input
    assert again == paper
