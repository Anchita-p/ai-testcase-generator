# Learning guide: know this project well enough to explain it in an interview

Read this top to bottom once, then open each code file next to its section. Plan on about 3–4 hours spread over a few days.

---

## 1. The 30-second pitch (memorise this)

> "Writing test cases from long requirement documents is slow, repetitive work for QA teams. I built an AI Test Case Generator: you upload an SRS, name a feature, and it uses RAG to pull only the relevant requirements, then an LLM drafts positive, negative, edge and boundary test cases with steps, test data and expected results. Each case traces back to a requirement ID. The output is validated with Pydantic, exported to Excel, and any case can be turned into a Playwright script. I tested it with 58 Pytest tests using a fake LLM, running in GitHub Actions."

---

## 2. The idea behind it: RAG

An LLM only knows what it saw in training. It has never seen *your* requirements document. If you just ask "write test cases for login", it makes up generic ones that don't match your app.

**RAG (Retrieval-Augmented Generation)** fixes this:
1. **Retrieve** the parts of the document relevant to the feature
2. **Augment** the prompt by pasting them in
3. **Generate** the answer based only on them

Why not paste the whole document? Long documents exceed or waste the model's context window, cost more, and the model gets distracted by unrelated requirements. Retrieval sends only what matters.

---

## 3. Key terms

| Term | Simple meaning | Where in the code |
|---|---|---|
| **LLM** | Large Language Model (Gemini, GPT). Predicts text. | `models.py` → `get_llm()` |
| **Chunk** | A small piece of the document (~1000 characters) | `ingest.py` → `split_documents()` |
| **Chunk overlap** | Neighbouring chunks share ~150 chars so a requirement cut at a boundary still appears whole | `config.CHUNK_OVERLAP` |
| **Embedding** | A list of numbers representing the *meaning* of text. Similar meaning → nearby vectors | `models.py` → `get_embeddings()` |
| **Vector store** | Stores embeddings and finds the closest ones fast. We use **FAISS** (Meta). Others: Pinecone, Chroma, pgvector | `vectorstore.py` |
| **Retriever / top-k** | Returns the k most relevant chunks (we use 6) | `get_retriever()` |
| **Prompt engineering** | Writing clear instructions, rules and an output format so the LLM behaves predictably | `generator.py` → `PROMPT` |
| **Structured output** | Making the LLM reply in a fixed format (JSON) that code can use | `JSON_SHAPE` in `generator.py` |
| **Pydantic** | Python library that validates data against a schema (types, required fields, custom rules) | `schema.py` |
| **Grounding** | Forcing the model to use only the given requirements, not invent features | "based ONLY on the requirements" in the prompt |
| **Hallucination** | The LLM confidently making something up | reduced by grounding + validation + human review |
| **Temperature** | Randomness. We use 0.3: consistent, with a little variety to find edge cases | `get_llm(temperature=0.3)` |
| **LangChain / LCEL** | Framework of building blocks for LLM apps; LCEL joins steps with `\|` | `PROMPT \| llm \| StrOutputParser()` |

---

## 4. Walk through the code in order

1. **`ingest.py`** loads a PDF (one Document per page, with a page number) or a TXT/MD file, removes empty pages, and splits text into chunks. Unsupported types and scanned PDFs fail with clear messages.
2. **`vectorstore.py`** embeds every chunk and stores them in FAISS; `get_retriever` returns the top-6 matches for a query.
3. **`schema.py`** defines what a valid test case looks like. Validators clean up common LLM quirks: `"negative"` → `"Negative"`, steps given as one string → a list, blank titles rejected.
4. **`generator.py`** is the heart:
   ```python
   docs = retriever.invoke(feature)             # 1. Retrieve requirements for this feature
   context = format_requirements(docs)          # 2. Augment: label chunks with page numbers
   raw = (PROMPT | llm | StrOutputParser()).invoke({...})   # 3. Generate JSON
   return parse_suite(raw, feature), docs       # 4. Validate
   ```
   The prompt gives the LLM a role (senior QA engineer), rules (only use the given requirements, concrete steps, exact test data, what each test type means) and the exact JSON shape to return.
5. **`parsing.py`** has no LLM in it on purpose, so it's easy to test. It finds the JSON even if the model wraps it in ```` ```json ```` fences or adds chatter, validates it with Pydantic, removes duplicate titles and numbers cases TC-001, TC-002, …
6. **`scriptgen.py`** sends one test case to the LLM with rules for a pytest-playwright script: `page` fixture, role/label locators, `expect()` assertions, TODO comments for unknown selectors.
7. **`export.py`** writes a formatted Excel sheet (bold header, wrapped text, frozen header row, filters, a "Status: Not Run" column) or CSV.
8. **`app.py`** is the Streamlit UI. Streamlit re-runs the whole script on each click, so the retriever and results live in `st.session_state`.

---

## 5. Testing concepts this project shows (your QA strength)

### Test design techniques the generator is told to use
- **Positive testing:** valid input works (login with correct email/password).
- **Negative testing:** invalid input is handled (wrong password shows the right error).
- **Boundary Value Analysis (BVA):** test at and around limits. Password must be 8–20 characters → test 7, 8, 20, 21.
- **Equivalence partitioning:** group inputs that behave the same and test one from each group (valid email, invalid format, already registered).
- **Edge cases:** unusual but valid situations (email typed in capitals, search with extra spaces).

The sample SRS has many of these built in (5 failed logins, 2 MB photo limit, 1–10 ingredients, 200 favourites), so you can show the tool finding them.

### How the project itself is tested
- Real LLM output changes every time and costs money, so unit tests use **`FakeListChatModel`** (always returns a fixed reply) and **`DeterministicFakeEmbedding`** (same text → same vector).
- Tests cover the *behaviour of our code*: loading, chunking, retrieval, prompt contents, validation of good and bad LLM replies, input limits (min/max case count = boundary tests!), Excel/CSV output, and code extraction.
- `@pytest.mark.parametrize` runs one test with many inputs.
- `monkeypatch` removes the API key to test the error message.
- **GitHub Actions** runs all 58 tests on every push.

Interview line: *"You can't unit test an LLM's creativity, so I isolated everything deterministic: parsing, validation, retrieval and export. I test those with fakes, and the LLM call itself is a thin layer. To judge real output quality I'd compare generated cases against a hand-written reference set."*

---

## 6. Likely interview questions (with short answers)

1. **Why RAG instead of sending the whole document?**
   Keeps the prompt small and focused, costs less, stays within context limits, and each test case traces back to specific requirements.

2. **Why RAG instead of fine-tuning?**
   Fine-tuning changes a model's behaviour and needs lots of training data; RAG gives it knowledge at question time, works with any new document instantly, and shows sources.

3. **How do you stop the LLM from inventing requirements?**
   The prompt says "based ONLY on the requirements", every case must name the requirement it verifies, the retrieved requirements are shown for review, and a tester reviews the draft.

4. **What if the LLM returns broken or messy output?**
   `parse_suite` extracts JSON from fences or chatter, Pydantic validates required fields, validators normalise labels, duplicates are removed, and anything unusable raises a clear `GenerationError`.

5. **What are embeddings? Why FAISS?**
   Vectors that capture meaning, so "sign in" matches a requirement about "log in". FAISS is free, fast and runs locally; for a multi-user product I'd use a hosted vector DB.

6. **How did you choose chunk size and top-k?**
   ~1000 characters holds a few requirements; 150 overlap avoids cutting one in half; top-6 gives enough context for a feature without unrelated noise. All are in `config.py` to tune.

7. **What is Boundary Value Analysis? Give an example from your project.**
   Testing at the edges of valid ranges. Password 8–20 chars → test 7, 8, 20 and 21. In my own tests, number of cases 3–25 → I test 2, 3, 25 and 26.

8. **Can this replace testers?**
   No. It's a first-draft assistant that saves time on repetitive writing. Testers still review, add domain knowledge, and fix the selectors in generated scripts.

9. **Why Playwright? How is it different from Selenium?**
   Playwright auto-waits for elements (fewer flaky tests), supports Chromium/Firefox/WebKit, and is fast. Selenium is older, supports more languages and has a larger ecosystem. Both drive real browsers.

10. **How did you test code that calls an LLM?**
    Fakes for the LLM and embeddings, plus testing the deterministic parts separately (see section 5).

11. **What would you add next?**
    A coverage report listing requirement IDs with no test cases, JIRA/TestRail export, API test cases from OpenAPI specs, and an evaluation against a reference set.

12. **What's temperature and why 0.3?**
    It controls randomness. 0.3 keeps output consistent but allows some variety, which helps it think of edge cases.

---

## 7. Your checklist

- [ ] Get the free Gemini key; run the app with the sample SRS
- [ ] Generate cases for 3–4 features; open the Excel file
- [ ] Check them critically: are the boundary tests right? Any invented requirements? (This is what a real QA engineer does, and it's a great interview story.)
- [ ] Generate a Playwright script and read it line by line
- [ ] Run `pytest` and see 58 tests pass
- [ ] Push to GitHub as `ai-testcase-generator`; check the Actions tab is green
- [ ] Add 3 screenshots to the README (upload, test-case table, Playwright script)
- [ ] Deploy free on Streamlit Community Cloud (share.streamlit.io), adding your key under **Secrets**, then put the live link in the README and on your resume
- [ ] Change something yourself (prompt rules, TOP_K, a new column) and see what happens
- [ ] Practise the pitch and the 12 questions out loud

---

## 8. For your resume (once it's on GitHub)

**AI Test Case Generator** | Python, LangChain, Gemini, RAG, FAISS, Pydantic, Streamlit, Playwright
- Built an LLM tool that turns requirement documents into traceable positive, negative, edge and boundary test cases, using RAG over a FAISS vector store, with Excel/CSV export.
- Converts test cases into pytest-playwright scripts; validates LLM output with Pydantic (normalisation, de-duplication, error handling).
- Wrote 58 offline Pytest tests using a fake LLM and deterministic embeddings, run on every push via GitHub Actions CI.
