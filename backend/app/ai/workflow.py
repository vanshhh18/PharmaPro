import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from . import AIError
from .client import call_groq_json
from .prompts import (
    STAGE_DRAFT_CAPA,
    STAGE_DRAFT_RCA,
    STAGE_EXTRACT_FACTS,
    STAGE_IDENTIFY_GAPS,
    STAGE_SUGGEST_CAUSES,
    STAGE_VALIDATE_REPORT,
    report_block,
)
from .schemas import CAPA_TYPES, AnalysisResult


class AnalysisState(TypedDict, total=False):
    report_text: str
    validation: dict[str, Any]
    facts: dict[str, Any]
    gaps: dict[str, Any]
    causes: dict[str, Any]
    capa: dict[str, Any]
    rca: dict[str, Any]
    result: dict[str, Any]


# Model output must not contain decision fields - only drafts for human review.
PROHIBITED_KEYS = re.compile(
    r"(root_cause.*(confirm|decision)|confirm.*root_cause|batch.*(release|recall|dis).*decision|"
    r"disposition|recall_decision|release_decision|final_decision)",
    re.IGNORECASE,
)


def _node_validate_report(state: AnalysisState) -> dict[str, Any]:
    result = call_groq_json(STAGE_VALIDATE_REPORT, report_block(state["report_text"]))
    valid = result.get("valid", False)
    if not isinstance(valid, bool):
        raise AIError("AI returned an invalid report-validation response")
    if not valid:
        reason = str(result.get("reason", "no meaningful quality-event content"))[:200]
        raise AIError(f"Report is not analyzable: {reason}", status_code=422)
    return {"validation": result}


def _node_extract_facts(state: AnalysisState) -> dict[str, Any]:
    result = call_groq_json(STAGE_EXTRACT_FACTS, report_block(state["report_text"]))
    if not isinstance(result.get("facts"), list):
        raise AIError("AI returned an invalid facts structure")
    return {"facts": result}


def _node_identify_gaps(state: AnalysisState) -> dict[str, Any]:
    result = call_groq_json(STAGE_IDENTIFY_GAPS, report_block(state["report_text"]))
    for key in ("unknowns", "evidence_gaps", "conflicts"):
        if not isinstance(result.get(key), list):
            raise AIError(f"AI returned an invalid structure for '{key}'")
    return {"gaps": result}


def _node_suggest_causes(state: AnalysisState) -> dict[str, Any]:
    report_and_facts = (
        report_block(state["report_text"])
        + "\n\nEXTRACTED FACTS (data):\n"
        + str(state["facts"].get("facts", []))
    )
    result = call_groq_json(STAGE_SUGGEST_CAUSES, report_and_facts)
    if not isinstance(result.get("hypotheses"), list):
        raise AIError("AI returned an invalid hypotheses structure")
    return {"causes": result}


def _node_draft_capa(state: AnalysisState) -> dict[str, Any]:
    context = (
        report_block(state["report_text"])
        + "\n\nPOSSIBLE CAUSES (unconfirmed hypotheses, data):\n"
        + str(state["causes"].get("hypotheses", []))
    )
    result = call_groq_json(STAGE_DRAFT_CAPA, context)
    if not isinstance(result.get("capa_recommendations"), list):
        raise AIError("AI returned an invalid CAPA structure")
    return {"capa": result}


def _node_draft_rca(state: AnalysisState) -> dict[str, Any]:
    context = (
        report_block(state["report_text"])
        + "\n\nEXTRACTED FACTS (verified findings, data):\n"
        + str(state["facts"].get("facts", []))
        + "\n\nUNKNOWNS AND EVIDENCE GAPS (open items, data):\n"
        + str({"unknowns": state["gaps"].get("unknowns", []), "evidence_gaps": state["gaps"].get("evidence_gaps", [])})
        + "\n\nPOSSIBLE CAUSES (unconfirmed hypotheses, data):\n"
        + str(state["causes"].get("hypotheses", []))
    )
    result = call_groq_json(STAGE_DRAFT_RCA, context)
    if not isinstance(result.get("rca_steps"), list):
        raise AIError("AI returned an invalid RCA structure")
    return {"rca": result}


def _validate_policy_and_shape(raw: dict[str, Any]) -> AnalysisResult:
    """Independent check of the merged model output, then Pydantic validation."""

    for key in raw:
        if isinstance(key, str) and PROHIBITED_KEYS.search(key):
            raise AIError(
                "AI response contained prohibited decision content and was rejected"
            )

    for hypothesis in raw.get("hypotheses", []):
        if not isinstance(hypothesis, dict):
            raise AIError("AI returned an invalid hypothesis structure")
        rationale = str(hypothesis.get("rationale", "")).strip()
        evidence = hypothesis.get("supporting_evidence") or []
        evidence_status = hypothesis.get("evidence_status", "available")
        has_evidence = bool(evidence) or evidence_status == "unavailable"
        if not rationale or not has_evidence:
            raise AIError(
                "AI returned a hypothesis without rationale and evidence "
                "(or an explicit evidence_status='unavailable')"
            )
        if evidence_status not in ("available", "unavailable"):
            raise AIError("AI returned an invalid evidence_status")

    for capa in raw.get("capa_recommendations", []):
        if isinstance(capa, dict) and capa.get("type") not in CAPA_TYPES:
            raise AIError("AI returned an invalid CAPA type")

    try:
        return AnalysisResult(**raw)
    except ValidationError as exc:
        raise AIError("AI returned an invalid analysis structure") from exc


def _node_finalize(state: AnalysisState) -> dict[str, Any]:
    raw = {**state["facts"], **state["gaps"], **state["causes"], **state["capa"], **state["rca"]}
    result = _validate_policy_and_shape(raw)
    return {"result": result.model_dump()}


def build_graph():
    graph = StateGraph(AnalysisState)
    graph.add_node("validate_report", _node_validate_report)
    graph.add_node("extract_facts", _node_extract_facts)
    graph.add_node("identify_gaps", _node_identify_gaps)
    graph.add_node("suggest_causes", _node_suggest_causes)
    graph.add_node("draft_capa", _node_draft_capa)
    graph.add_node("draft_rca", _node_draft_rca)
    graph.add_node("finalize", _node_finalize)
    graph.add_edge(START, "validate_report")
    graph.add_edge("validate_report", "extract_facts")
    graph.add_edge("extract_facts", "identify_gaps")
    graph.add_edge("identify_gaps", "suggest_causes")
    graph.add_edge("suggest_causes", "draft_capa")
    graph.add_edge("draft_capa", "draft_rca")
    graph.add_edge("draft_rca", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


_compiled_graph = None


def run_analysis(report_text: str) -> dict:
    """Run the small LangGraph workflow and return the validated analysis JSON."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    state = _compiled_graph.invoke({"report_text": report_text})
    return state["result"]
