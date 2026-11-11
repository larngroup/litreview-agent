from literature_agent.screening.evaluation import agreement_report


def row(human, model, status="ok"):
    return {"review": {"decision": human} if human else None,
            "screening": {"decision": model, "status": status} if model or status != "ok" else None}


def test_agreement_report():
    papers = [row("include", "include"), row("include", "exclude"), row("exclude", "exclude"),
              row("exclude", "uncertain"), row(None, "include"), row("include", None, status="failed")]
    report = agreement_report(papers)
    assert report["compared"] == 4
    assert report["agreement"] == 0.5
    assert report["include_recall"] == 0.5
    assert report["includes_wrongly_excluded"] == 1


def test_empty_report():
    assert agreement_report([])["agreement"] is None
