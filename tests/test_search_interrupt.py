
"""Regression test: interrupted searches must not remain 'running'.
simular a interrupção com uma função falsa, utilizando uma base SQLite temporária e o pipeline.run_search() real.

1-Cria uma base de dados SQLite temporária, sem tocar no projeto hitl.
2-Inicia uma pesquisa com run_search().
3-Simula Ctrl+C com KeyboardInterrupt.
4-Confirma que a interrupção é propagada.
5-Consulta a run persistida e exige status='interrupted' e finished_at preenchido.
"""

import pytest

from literature_agent import pipeline
from literature_agent.storage import database as db


def test_search_keyboard_interrupt_updates_run_status(tmp_path):
    # Isolated SQLite database; does not touch the real project.
    conn = db.connect(tmp_path / "test_interrupt.sqlite")

    project_id = db.create_project(
        conn,
        name="test-interrupt",
        topic="test interruption",
    )

    # Simulate Ctrl+C while OpenAlex is fetching papers.
    def fake_search(query, limit):
        raise KeyboardInterrupt

    # The interruption should still propagate.
    with pytest.raises(KeyboardInterrupt):
        pipeline.run_search(
            conn,
            project_id,
            query="papers",
            limit=3,
            search_fn=fake_search,
        )

    # Inspect the persisted run.
    runs = db.list_search_runs(conn, project_id)

    assert len(runs) == 1

    run = runs[0]

    # Desired behaviour after fixing the bug.
    assert run["status"] == "interrupted"
    assert run["finished_at"] is not None
    assert run["n_retrieved"] == 0
    assert run["n_new"] == 0

    conn.close()
