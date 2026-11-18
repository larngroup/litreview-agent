"""Local web interface. Run with:  streamlit run app/streamlit_app.py --server.address localhost

The interface contains no research logic of its own: every button calls the same
functions in `literature_agent.pipeline` and `literature_agent.storage` that the
CLI uses, so CLI and web always behave identically.
"""

from __future__ import annotations

import streamlit as st

from literature_agent import pipeline
from literature_agent.config import load_settings
from literature_agent.discovery import SOURCE_NAMES, make_source
from literature_agent.exports import search_history_csv, select_papers, to_bibtex, to_csv, to_json
from literature_agent.providers import PROVIDER_NAMES, LLMError, get_provider
from literature_agent.screening.evaluation import agreement_report
from literature_agent.screening.relevance import Criteria
from literature_agent.storage import database as db

DECISIONS = ["include", "exclude", "uncertain"]

st.set_page_config(page_title="Literature Agent", layout="wide")
settings = load_settings()


@st.cache_resource
def get_connection(path: str):
    return db.connect(path)


conn = get_connection(str(settings.db_path))


def lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


# --------------------------------------------------------------------------- sidebar
st.sidebar.title("Literature Agent")
projects = db.list_projects(conn)
names = [p["name"] for p in projects]

with st.sidebar.expander("New project", expanded=not projects):
    with st.form("new_project", clear_on_submit=True):
        new_name = st.text_input("Project name")
        new_topic = st.text_input("Topic")
        new_question = st.text_area("Research question")
        if st.form_submit_button("Create project"):
            try:
                db.create_project(conn, new_name, new_topic, new_question)
                st.session_state["project"] = new_name.strip()
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

if not projects:
    st.info("Create a project in the sidebar to start.")
    st.stop()

default_index = names.index(st.session_state["project"]) if st.session_state.get("project") in names else 0
project_name = st.sidebar.selectbox("Project", names, index=default_index)
st.session_state["project"] = project_name
project = db.require_project(conn, project_name)
project_id = project["id"]

st.sidebar.subheader("Language model")
provider_name = st.sidebar.selectbox("Provider", PROVIDER_NAMES,
                                     index=PROVIDER_NAMES.index(settings.llm_provider)
                                     if settings.llm_provider in PROVIDER_NAMES else 0)
default_model = settings.groq_model if provider_name == "groq" else settings.ollama_model
model_name = st.sidebar.text_input("Model", value=default_model, key=f"model_{provider_name}")
if provider_name == "groq":
    st.sidebar.warning("Groq is a hosted service: titles and abstracts are sent to Groq.")
else:
    st.sidebar.caption("Ollama runs locally (unless OLLAMA_BASE_URL points to another machine).")
st.sidebar.caption(f"Database: {settings.db_path}")

criteria = Criteria.from_project(project)
criteria_hash = criteria.fingerprint()
papers = db.project_papers(conn, project_id, criteria_hash)

st.title(project["name"])
st.caption(f"Topic: {project['topic']}")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Papers", len(papers))
col2.metric("Without abstract", sum(not p["has_abstract"] for p in papers))
col3.metric("Screened (current criteria)", sum(p["screening"] is not None for p in papers))
col4.metric("Human-reviewed", sum(p["review"] is not None for p in papers))

tab_criteria, tab_search, tab_screen, tab_review, tab_fulltext, tab_export, tab_log = st.tabs(
    ["Criteria", "Search", "Screening", "Review", "Full text", "Export", "Log"])

# --------------------------------------------------------------------------- criteria
with tab_criteria:
    st.write("Changing the topic, question or criteria creates a new screening round; "
             "earlier screenings are kept in the database.")
    with st.form("criteria"):
        topic = st.text_input("Topic", value=project["topic"])
        question = st.text_area("Research question", value=project["research_question"])
        inclusion = st.text_area("Inclusion criteria (one per line)", value="\n".join(project["inclusion_criteria"]))
        exclusion = st.text_area("Exclusion criteria (one per line)", value="\n".join(project["exclusion_criteria"]))
        if st.form_submit_button("Save criteria"):
            try:
                db.update_project(conn, project_id, topic=topic, research_question=question,
                                  inclusion_criteria=lines(inclusion), exclusion_criteria=lines(exclusion))
                db.log_event(conn, project_id, "info", "criteria_updated", "Criteria changed in web UI",
                             {"topic": topic, "inclusion": lines(inclusion), "exclusion": lines(exclusion)})
                st.success("Saved.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

# --------------------------------------------------------------------------- search
with tab_search:
    with st.form("search"):
        query = st.text_input("Search query", value=project["topic"])
        sources = st.multiselect("Sources", SOURCE_NAMES, default=["openalex"])
        limit = st.number_input("Maximum records per source", min_value=1, max_value=10_000, value=100)
        run = st.form_submit_button("Run search")
    if run:
        if not sources:
            st.error("Choose at least one source.")
        else:
            with st.spinner("Searching..."):
                summaries = pipeline.run_multi_search(conn, project_id, query, int(limit),
                                                      [make_source(name, settings) for name in sources])
            for summary in summaries:
                if "error" in summary:
                    st.error(f"{summary['source']}: {summary['error']}")
                else:
                    st.success(f"{summary['source']}: {summary['retrieved']} retrieved, {summary['new']} new, "
                               f"{summary['duplicates']} already in the project")
    st.caption("Results depend on each source's coverage; no search is exhaustive.")
    st.subheader("Search history")
    st.dataframe(db.list_search_runs(conn, project_id), hide_index=True)

# --------------------------------------------------------------------------- screening
with tab_screen:
    st.info("This is preliminary title/abstract screening. 'include' means 'read the full text', "
            "not 'eligible for the review'. Papers without an abstract are marked 'uncertain' "
            "and are never sent to the model.")
    if not project["inclusion_criteria"]:
        st.warning("No inclusion criteria yet: the model will only judge against the topic.")
    retry_failed = st.checkbox("Retry failed screenings")
    max_papers = st.number_input("Maximum papers in this run (0 = all)", min_value=0, value=0)
    if st.button("Run screening"):
        try:
            provider = get_provider(settings, provider_name, model_name)
        except (LLMError, ValueError) as exc:
            st.error(str(exc))
        else:
            bar = st.progress(0.0, text="Starting...")

            def progress(index: int, total: int, result) -> None:
                bar.progress(index / total, text=f"{index}/{total}: {result.status} {result.decision or ''}")

            counts = pipeline.run_screening(conn, project_id, provider, retry_failed=retry_failed,
                                            max_papers=int(max_papers) or None, on_progress=progress)
            st.success(f"Finished: {dict(counts) or 'nothing to screen'}")
            st.rerun()
    failed = [p for p in papers if (p["screening"] or {}).get("status") == "failed"]
    if failed:
        st.subheader(f"Failed screenings ({len(failed)})")
        st.dataframe([{"paper_id": p["id"], "title": p["title"], "error": p["screening"]["error"],
                       "raw_response": (p["screening"]["raw_response"] or "")[:300]} for p in failed],
                     hide_index=True)
    st.subheader("Agreement with human decisions")
    st.json(agreement_report(papers))

# --------------------------------------------------------------------------- review
with tab_review:
    filter_col1, filter_col2 = st.columns(2)
    suggestion_filter = filter_col1.selectbox("Model suggestion", ["any", *DECISIONS, "not screened"])
    unreviewed_only = filter_col2.checkbox("Only papers without a human decision", value=True)

    def keep(paper: dict) -> bool:
        suggestion = (paper["screening"] or {}).get("decision")
        if unreviewed_only and paper["review"]:
            return False
        if suggestion_filter == "not screened":
            return paper["screening"] is None
        return suggestion_filter == "any" or suggestion == suggestion_filter

    shown = [p for p in papers if keep(p)]
    st.caption(f"{len(shown)} papers match the filter.")
    if shown:
        labels = {p["id"]: f"[{p['id']}] {(p['title'] or '(no title)')[:90]}" for p in shown}
        paper_id = st.selectbox("Paper", list(labels), format_func=labels.get)
        paper = next(p for p in shown if p["id"] == paper_id)
        st.markdown(f"### {paper['title'] or '(no title)'}")
        st.write(f"{', '.join(paper['authors'][:6]) or 'Unknown authors'} · {paper['year'] or 'year unknown'}")
        if paper["doi"]:
            st.markdown(f"DOI: [{paper['doi']}](https://doi.org/{paper['doi']})")
        st.write(paper["abstract"] or "_No abstract available._")
        screening = paper["screening"]
        if screening:
            st.write(f"**Model suggestion:** {screening['decision'] or 'failed'} "
                     f"({screening['model']}, prompt {screening['prompt_version']})")
            st.write(screening["reason"] or screening["error"] or "")
            details = screening.get("details") or {}
            if details.get("matched_inclusion") or details.get("matched_exclusion"):
                st.write(f"Inclusion matched: {details.get('matched_inclusion')}; "
                         f"exclusion matched: {details.get('matched_exclusion')}")
        conflicts = db.find_conflicts(conn, paper["id"])
        if conflicts:
            st.warning(f"Sources disagree on: {conflicts}")
        with st.form(f"review_{paper['id']}"):
            current = paper["review"]["decision"] if paper["review"] else (screening or {}).get("decision")
            decision = st.radio("Your decision", DECISIONS,
                                index=DECISIONS.index(current) if current in DECISIONS else 2, horizontal=True)
            note = st.text_input("Note (reason, especially when you disagree with the model)")
            reviewer = st.text_input("Reviewer initials")
            if st.form_submit_button("Save decision"):
                db.add_review(conn, project_id, paper["id"], decision, note, reviewer)
                st.success("Saved.")
                st.rerun()

# --------------------------------------------------------------------------- full text
with tab_fulltext:
    from literature_agent.discovery.http import PoliteClient
    from literature_agent.fulltext.store import project_assets

    st.write("Only open-access copies reported by OpenAlex or Unpaywall are downloaded. "
             "Papers without an accessible copy stay in the project with their abstract and DOI.")
    ft_subset = st.selectbox("Papers", pipeline.FULLTEXT_SUBSETS,
                             format_func={"human_include": "Included by a human",
                                          "include_any": "Included by a human or suggested by the model",
                                          "all": "All papers"}.get)
    ft_retry = st.checkbox("Retry failed look-ups, downloads and parsing")
    if st.button("Retrieve full texts"):
        http = PoliteClient(timeout=settings.http_timeout_seconds, max_retries=settings.http_max_retries,
                            min_interval_seconds=0.2, contact_email=settings.contact_email)
        ft_bar = st.progress(0.0, text="Starting...")
        ft_counts = pipeline.run_fulltext(
            conn, project_id, http=http, data_dir=settings.data_dir, openalex_api_key=settings.openalex_api_key,
            contact_email=settings.contact_email, subset=ft_subset, retry_failed=ft_retry,
            on_progress=lambda i, n, state: ft_bar.progress(i / n, text=f"{i}/{n}: {state}"))
        st.success(f"Finished: {dict(ft_counts) or 'no papers in this subset'}")
    st.dataframe([{k: a[k] for k in ("paper_id", "title", "access_status", "download_status", "parse_status",
                                     "license", "oa_version", "n_pages", "pdf_url", "landing_url", "error")}
                  for a in project_assets(conn, project_id)], hide_index=True)

# --------------------------------------------------------------------------- export
with tab_export:
    subset_labels = {"human_include": "Included by a human reviewer",
                     "model_include_unreviewed": "Model suggests include, not yet reviewed",
                     "all": "All papers"}
    subset = st.radio("Papers to export", list(subset_labels), format_func=subset_labels.get)
    chosen = select_papers(papers, subset)
    runs = db.list_search_runs(conn, project_id)
    st.write(f"{len(chosen)} papers selected.")
    st.download_button("BibTeX", to_bibtex(chosen), file_name=f"{project_name}.bib", mime="text/plain")
    st.download_button("CSV (with screening decisions)", to_csv(chosen), file_name=f"{project_name}.csv",
                       mime="text/csv")
    st.download_button("JSON (full records)", to_json(chosen, project, runs), file_name=f"{project_name}.json",
                       mime="application/json")
    st.download_button("Search history (CSV)", search_history_csv(runs),
                       file_name=f"{project_name}_searches.csv", mime="text/csv")

# --------------------------------------------------------------------------- log
with tab_log:
    st.dataframe(db.list_events(conn, project_id), hide_index=True)
