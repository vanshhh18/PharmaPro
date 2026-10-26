from fastapi import APIRouter, HTTPException

from .. import schemas
from ..ai import AIError
from ..ai.schemas import AnalysisResult
from ..ai.workflow import run_analysis
from ..intake.normalize import IntakeError, normalize_text

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("", response_model=AnalysisResult)
def analyze_report(payload: schemas.ReportTextInput) -> AnalysisResult:
    try:
        text = normalize_text(payload.text)
    except IntakeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    try:
        result = run_analysis(text)
    except AIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return AnalysisResult(**result)
