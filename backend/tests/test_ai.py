import pytest

from app.ai import AIError

ANALYSIS_URL = "/api/analysis"

REPORT = (
    "HPLC testing of API batch API-102, manufactured on 20 October 2026, found an "
    "impurity result of 2.1% against a specification limit of 1.0%. Quality Control "
    "identified the issue during release testing."
)

STAGE_FACTS = {
    "facts": [
        {
            "statement": "Impurity result 2.1% exceeded the 1.0% specification limit",
            "quote": "impurity result of 2.1% against a specification limit of 1.0%",
        }
    ]
}
STAGE_GAPS = {
    "unknowns": [
        {"question_or_item": "Why were batch temperature trends absent?", "why_unclear": "not provided"}
    ],
    "evidence_gaps": [
        {"record_or_data": "Batch temperature trends", "why_needed": "Process context"}
    ],
    "conflicts": [],
}
STAGE_CAUSES = {
    "hypotheses": [
        {
            "statement": "Temperature excursion during crystallization",
            "rationale": "Consistent with a process deviation affecting impurity profile",
            "supporting_evidence": ["Batch manufactured on 20 October 2026"],
            "evidence_status": "available",
        }
    ],
    "investigation_prompts": [
        {"method": "5whys", "question": "Why was no temperature trend recorded?"}
    ],
}
STAGE_CAPA = {
    "capa_recommendations": [
        {
            "description": "Review chromatograms and batch record",
            "type": "corrective",
            "rationale": "Confirms report accuracy",
        }
    ]
}
STAGE_RCA = {
    "rca_steps": [
        {
            "method": "5whys",
            "question": "Why was the impurity 2.1% against the 1.0% limit?",
            "answer": "The report states the result exceeded the specification limit.",
            "status": "grounded",
            "position": 1,
        },
        {
            "method": "5whys",
            "question": "Why did the impurity profile deviate from the expected profile?",
            "answer": "Cannot be determined from the report; process data is not included.",
            "status": "speculative",
            "position": 2,
        },
        {
            "method": "fishbone",
            "question": "Which method factors (test conditions) explain the result?",
            "answer": "No test-condition data is available in the report.",
            "status": "speculative",
            "position": 3,
        },
    ]
}


def make_fake_groq(**stage_overrides):
    stages = {
        "validate": {"valid": True, "reason": "ok"},
        "facts": dict(STAGE_FACTS),
        "gaps": dict(STAGE_GAPS),
        "causes": dict(STAGE_CAUSES),
        "capa": dict(STAGE_CAPA),
        "rca": dict(STAGE_RCA),
        **stage_overrides,
    }

    def fake_groq(instruction: str, content: str) -> dict:
        lower = instruction.lower()
        if "validating" in lower:
            return stages["validate"]
        if "you extract facts" in lower:
            return stages["facts"]
        if "review a pharmaceutical" in lower:
            return stages["gaps"]
        if "you draft corrective" in lower:
            return stages["capa"]
        if "root cause analysis chain" in lower:
            return stages["rca"]
        if "possible causes" in lower:
            return stages["causes"]
        raise AssertionError(f"Unexpected AI stage: {instruction[:60]}")

    return fake_groq


@pytest.fixture
def mock_groq(monkeypatch):
    holder = {"fake": make_fake_groq()}
    monkeypatch.setattr("app.ai.workflow.call_groq_json", lambda i, c: holder["fake"](i, c))
    return holder


def test_successful_analysis(mock_groq, client):
    response = client.post(ANALYSIS_URL, json={"text": REPORT})
    assert response.status_code == 200
    body = response.json()
    assert len(body["facts"]) == 1
    assert body["facts"][0]["quote"].startswith("impurity result")
    assert body["unknowns"] and body["evidence_gaps"]
    assert body["conflicts"] == []
    assert len(body["hypotheses"]) == 1
    hypothesis = body["hypotheses"][0]
    assert hypothesis["rationale"]
    assert hypothesis["supporting_evidence"] == ["Batch manufactured on 20 October 2026"]
    assert body["investigation_prompts"][0]["method"] == "5whys"
    assert len(body["rca_steps"]) == 3
    grounded = body["rca_steps"][0]
    assert grounded["answer"].startswith("The report states the result")
    assert grounded["status"] == "grounded"
    speculative = body["rca_steps"][1]
    assert speculative["status"] == "speculative"
    assert "not available" in speculative["answer"] or "does not contain" in speculative["answer"]
    assert body["capa_recommendations"][0]["type"] == "corrective"
    assert "draft" in body["note"]


def test_missing_api_key_clear_error(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "groq_api_key", "")
    from app.ai import client as ai_client

    ai_client.get_groq_client.cache_clear()
    try:
        response = client.post(ANALYSIS_URL, json={"text": REPORT})
        assert response.status_code == 503
        assert "GROQ_API_KEY is not configured" in response.json()["detail"]
    finally:
        ai_client.get_groq_client.cache_clear()


def test_provider_failure_maps_to_502(client, monkeypatch):
    def failing(instruction, content):
        raise AIError("AI provider request failed: boom", status_code=502)

    monkeypatch.setattr("app.ai.workflow.call_groq_json", failing)
    response = client.post(ANALYSIS_URL, json={"text": REPORT})
    assert response.status_code == 502
    assert "AI provider request failed" in response.json()["detail"]


def test_malformed_model_json_maps_to_502(client, monkeypatch):
    def malformed(instruction, content):
        raise AIError("AI provider returned malformed JSON", status_code=502)

    monkeypatch.setattr("app.ai.workflow.call_groq_json", malformed)
    response = client.post(ANALYSIS_URL, json={"text": REPORT})
    assert response.status_code == 502
    assert "malformed" in response.json()["detail"]


def test_invalid_stage_structure_rejected(mock_groq, client):
    mock_groq["fake"] = make_fake_groq(facts={"facts": "everything looked fine"})
    response = client.post(ANALYSIS_URL, json={"text": REPORT})
    assert response.status_code == 502
    assert "invalid" in response.json()["detail"]


def test_report_rejected_by_validator(mock_groq, client):
    mock_groq["fake"] = make_fake_groq(
        validate={"valid": False, "reason": "content is not a deviation report"}
    )
    response = client.post(ANALYSIS_URL, json={"text": REPORT})
    assert response.status_code == 422
    assert "not analyzable" in response.json()["detail"]


def test_hypothesis_without_rationale_or_evidence_rejected(mock_groq, client):
    mock_groq["fake"] = make_fake_groq(
        causes={
            "hypotheses": [
                {
                    "statement": "Equipment wear",
                    "rationale": "",
                    "supporting_evidence": [],
                    "evidence_status": "available",
                }
            ],
            "investigation_prompts": STAGE_CAUSES["investigation_prompts"],
        }
    )
    response = client.post(ANALYSIS_URL, json={"text": REPORT})
    assert response.status_code == 502
    assert "rationale and evidence" in response.json()["detail"]


def test_hypothesis_with_explicitly_unavailable_evidence_accepted(mock_groq, client):
    mock_groq["fake"] = make_fake_groq(
        causes={
            "hypotheses": [
                {
                    "statement": "Raw material variability",
                    "rationale": "Plausible with no support in report",
                    "supporting_evidence": [],
                    "evidence_status": "unavailable",
                }
            ],
            "investigation_prompts": STAGE_CAUSES["investigation_prompts"],
        }
    )
    response = client.post(ANALYSIS_URL, json={"text": REPORT})
    assert response.status_code == 200
    assert response.json()["hypotheses"][0]["statement"] == "Raw material variability"


def test_prohibited_decision_content_rejected(mock_groq, client):
    mock_groq["fake"] = make_fake_groq(
        capa={
            "capa_recommendations": STAGE_CAPA["capa_recommendations"],
            "batch_release_decision": "release batch API-102",
        }
    )
    response = client.post(ANALYSIS_URL, json={"text": REPORT})
    assert response.status_code == 502
    assert "prohibited decision content" in response.json()["detail"]


def test_invalid_capa_type_rejected(mock_groq, client):
    mock_groq["fake"] = make_fake_groq(
        capa={
            "capa_recommendations": [
                {"description": "Sort batch for immediate release", "type": "disposition", "rationale": ""}
            ]
        }
    )
    response = client.post(ANALYSIS_URL, json={"text": REPORT})
    assert response.status_code == 502
    assert "invalid CAPA type" in response.json()["detail"]


def test_empty_text_rejected_before_ai(client):
    response = client.post(ANALYSIS_URL, json={"text": "   "})
    assert response.status_code == 422


def test_invalid_rca_status_rejected(mock_groq, client):
    mock_groq["fake"] = make_fake_groq(
        rca={
            "rca_steps": [
                {
                    "method": "5whys",
                    "question": "Why was the result out of spec?",
                    "answer": "Speculation presented as fact",
                    "status": "confirmed-root-cause",
                    "position": 1,
                }
            ]
        }
    )
    response = client.post(ANALYSIS_URL, json={"text": REPORT})
    assert response.status_code == 502
    assert "invalid" in response.json()["detail"]


def test_graph_runs_without_extra_pollution(mock_groq):
    from app.ai.workflow import run_analysis

    result = run_analysis(REPORT)
    assert set(result) <= set(
        {
            "facts", "unknowns", "evidence_gaps", "conflicts",
            "hypotheses", "investigation_prompts", "rca_steps",
            "capa_recommendations", "note",
        }
    )
