# AIVOA — Simple Project Brief

## 1. Goal
Build a practical web app for pharma quality teams to investigate deviations and possible root causes. Users should be able to upload or paste an incident report, review extracted facts, identify missing evidence, draft CAPA actions, and save or reopen investigations.

**Important:** AI suggestions are drafts. A qualified quality professional must review and approve them. The app must not invent facts or make batch-release, recall, or other quality decisions.

## 2. Required technology
- **Frontend:** React + Redux Toolkit
- **Backend:** Python + FastAPI
- **AI workflow:** LangGraph + Groq API
- **Database:** PostgreSQL
- **Validation:** Pydantic

Keep the code simple and easy to explain. Reuse existing code where sensible.

## 3. Main user flow
1. Create a new investigation or open a saved one.
2. Upload a PDF, TXT, MD, or EML report, or paste report text.
3. Extract incident facts and show missing or conflicting information.
4. Suggest possible causes, evidence to collect, investigation prompts, and draft CAPA actions.
5. Let the user edit the investigation and all AI suggestions.
6. Save the case, reopen it later, review its history, and print/export a summary.

## 4. Required features
- Dashboard with counts taken from the database.
- Create, view, edit, save, reopen, and archive investigations.
- Document upload and pasted-text intake.
- AI-assisted fact extraction and root-cause investigation.
- 5 Whys and Fishbone investigation prompts.
- Editable cause hypotheses, evidence gaps, and CAPA actions.
- Audit history for important changes.
- Printable investigation report.
- Useful loading, success, empty, and error states.
- No decorative buttons or fake integrations. Keep advanced analytics, complex approval workflows, and authentication out unless the existing project requires them.

## 5. AI workflow
Use a small, understandable LangGraph workflow:
1. Validate the supplied report.
2. Extract only facts explicitly present in the report.
3. Identify unknown, missing, or conflicting information.
4. Suggest possible causes and investigation questions.
5. Draft corrective and preventive actions.
6. Validate the response with Pydantic and return it for human review.

Keep facts, hypotheses, unknowns, and recommendations separate. Never present a hypothesis as a confirmed root cause. If the API key is missing or the AI response is invalid, show a clear error. Keep the API key in an environment variable, not in source code. Tests should be able to use mocked AI responses.

## 6. Suggested database records
Create suitable tables/models for:
- Investigations
- Cause hypotheses
- Evidence gaps
- RCA steps
- CAPA actions
- Audit events

Saving and reopening a case must preserve its associated investigation data.

## 7. API endpoints
Provide sensible FastAPI endpoints for:
- Health check and dashboard counts
- Investigation create/read/update/archive
- Report intake and analysis
- Updating causes, evidence gaps, RCA steps, and CAPA actions
- Audit history
- Report export

Use Pydantic request and response models and return useful, safe error messages.

## 8. Security and quality
- Add `.env.example`; never commit secrets.
- Validate uploaded file types and enforce a 10 MB size limit.
- Treat report contents as untrusted input.
- Do not log full reports or secrets unnecessarily.
- Clearly label demo data and AI-generated content.
- Describe the app as decision support, not validated GMP software.

## 9. Demo report for testing
Use this example:

> HPLC testing of API batch API-102, manufactured on 20 October 2026, found an impurity result of 2.1% against a specification limit of 1.0%. Quality Control identified the issue during release testing. The report does not include the batch temperature trends, raw material test results, equipment calibration status, or detailed process parameters. Batch disposition has not been documented.

Expected behavior:
- Extract the batch ID, result, limit, and detection context as facts.
- Flag the missing records as evidence gaps.
- Suggest process, raw-material, and analytical-method hypotheses without confirming any of them.
- Draft CAPA suggestions for review.
- Do not decide batch disposition.
- Save the case and verify that reopening it restores its data.

## 10. Tests and documentation
Test at least:
- Health check and investigation CRUD
- Saving and reopening cases
- Invalid and oversized uploads
- Extraction failures and invalid AI output
- Missing API key behavior
- Editing evidence gaps and CAPA actions
- Ensuring AI output cannot confirm a root cause or make disposition decisions

Write a README with exact setup, environment, run, and test commands. Run the backend tests, frontend tests, and production build. Report the actual results; do not claim checks passed unless they were run.

## 11. Build order
1. Inspect the repository and reuse useful existing code.
2. Set up the required frontend, backend, and database.
3. Implement investigation models and API endpoints.
4. Implement report intake and fact extraction.
5. Add the LangGraph/Groq workflow and response validation.
6. Connect the frontend to the real API.
7. Finish cause hypotheses, evidence gaps, CAPA editing, saving, reopening, and audit history.
8. Run tests and production build; fix failures.
9. Complete the README and `revision.md`.

After every meaningful step, append to `revision.md`: what changed, which files changed, checks run and their actual results, and any remaining issues.

## Definition of done
The app runs locally using the documented commands; users can create and investigate a case, review AI suggestions, edit and save the results, reopen the case with its data intact, and export a report. Tests and build results are documented honestly. Implement the working application, not just a plan or code snippets.
