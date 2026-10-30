"""Streamlit app: upload a requirements document → generate test cases → export / automate.

Run with:  streamlit run app.py
"""
import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from testgen import config
from testgen.coverage import coverage_report
from testgen.export import COLUMNS, to_csv_bytes, to_excel_bytes, to_rows
from testgen.generator import generate_test_cases
from testgen.ingest import load_document, load_text, split_documents
from testgen.models import MissingAPIKeyError, get_embeddings, get_llm
from testgen.parsing import GenerationError
from testgen.schema import TEST_TYPES
from testgen.scriptgen import generate_playwright_script
from testgen.vectorstore import build_vectorstore, get_retriever

st.set_page_config(page_title="AI Test Case Generator", page_icon="🧪", layout="wide")
st.title("🧪 AI Test Case Generator")
st.caption("Requirements → test cases → Playwright scripts · RAG with LangChain, FAISS and Gemini")

# Streamlit re-runs the script on every interaction, so state lives in st.session_state
for key, default in {"retriever": None, "file_name": None, "suite": None, "sources": [], "scripts": {}}.items():
    st.session_state.setdefault(key, default)

# ---------- Sidebar: upload and index the requirements ----------
with st.sidebar:
    st.header("1. Requirements")
    uploaded = st.file_uploader("PDF, DOCX, TXT or MD (SRS, user stories, spec)", type=["pdf", "docx", "txt", "md"])
    pasted = st.text_area("...or paste notes / user stories", height=120,
                          placeholder="LOG-01 A user shall log in with email and password.\nLOG-02 ...")

    if (uploaded or pasted.strip()) and st.button("Process", type="primary"):
        tmp_path = None
        with st.spinner("Reading, chunking and embedding..."):
            try:
                if uploaded:
                    suffix = Path(uploaded.name).suffix
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded.getvalue())
                        tmp_path = tmp.name
                    pages, name = load_document(tmp_path), uploaded.name
                else:
                    pages, name = load_text(pasted), "pasted text"
                chunks = split_documents(pages)
                store = build_vectorstore(chunks, get_embeddings())
                st.session_state.update(
                    retriever=get_retriever(store), file_name=name,
                    suite=None, sources=[], scripts={},
                )
                st.success(f"Ready! {len(pages)} page(s) → {len(chunks)} chunks indexed.")
            except MissingAPIKeyError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Could not process the input: {e}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

    if st.session_state.file_name:
        st.info(f"Loaded: **{st.session_state.file_name}**")

if st.session_state.retriever is None:
    st.write("👈 Upload or paste requirements to start. Try `sample_docs/foodies_paradise_srs.pdf`.")
    st.stop()

# ---------- Step 2: choose what to test ----------
st.subheader("2. What should be tested?")
col1, col2, col3 = st.columns([3, 1, 2])
feature = col1.text_input("Feature / module", placeholder="e.g. User login, Recipe search, Profile photo upload")
num_cases = col2.number_input("How many cases", config.MIN_CASES, config.MAX_CASES, 8)
types = col3.multiselect("Test types", TEST_TYPES, default=list(TEST_TYPES))

if st.button("Generate test cases", type="primary", disabled=not feature.strip()):
    with st.spinner("Retrieving requirements and writing test cases..."):
        try:
            suite, sources = generate_test_cases(
                feature, st.session_state.retriever, get_llm(), int(num_cases), tuple(types)
            )
            st.session_state.update(suite=suite, sources=sources, scripts={})
        except (ValueError, GenerationError, MissingAPIKeyError) as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Something went wrong: {e}")

suite = st.session_state.suite
if suite is None:
    st.stop()

# ---------- Step 3: results ----------
st.subheader(f"3. Test cases — {suite.feature}")
summary = suite.summary()
metrics = st.columns(1 + len(TEST_TYPES) + 1)
metrics[0].metric("Total", summary["total"])
for i, t in enumerate(TEST_TYPES, start=1):
    metrics[i].metric(t, summary["by_type"][t])
metrics[-1].metric("High priority", summary["by_priority"]["High"])

st.dataframe(pd.DataFrame(to_rows(suite), columns=COLUMNS), hide_index=True)

safe_name = "".join(ch if ch.isalnum() else "_" for ch in suite.feature.lower()).strip("_")
d1, d2, _ = st.columns([1, 1, 3])
d1.download_button("⬇️ Excel", to_excel_bytes(suite), f"test_cases_{safe_name}.xlsx",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
d2.download_button("⬇️ CSV", to_csv_bytes(suite), f"test_cases_{safe_name}.csv", "text/csv")

report = coverage_report(suite, st.session_state.sources)
if report["covered"]:
    st.markdown(f"**Requirements covered:** {', '.join(report['covered'])}")
if report["missing"]:
    st.info("Other requirement IDs in the retrieved text with no test case (they may belong to other features): "
            + ", ".join(report["missing"]))
if report["unknown"]:
    st.warning("Cited by a test case but not found in the requirements (possibly invented): "
               + ", ".join(report["unknown"]))

with st.expander("Requirements used (retrieved chunks)"):
    for doc in st.session_state.sources:
        page = doc.metadata.get("page", 0) + 1
        st.markdown(f"**Page {page}:** {doc.page_content[:400]}...")

# ---------- Step 4: automation ----------
st.subheader("4. Generate an automation script")
options = {f"{c.id} — {c.title}": c for c in suite.test_cases}
choice = st.selectbox("Pick a test case", list(options))
if st.button("Generate Playwright script"):
    with st.spinner("Writing the script..."):
        try:
            st.session_state.scripts[choice] = generate_playwright_script(options[choice], get_llm())
        except Exception as e:
            st.error(f"Could not generate the script: {e}")

if choice in st.session_state.scripts:
    code = st.session_state.scripts[choice]
    st.code(code, language="python")
    st.download_button("⬇️ Download .py", code, f"test_{options[choice].id.lower().replace('-', '_')}.py")
    st.caption("Starter script: confirm the selectors marked TODO against your real app before running.")
