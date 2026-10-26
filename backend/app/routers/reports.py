from fastapi import APIRouter, File, HTTPException, UploadFile, status

from .. import schemas
from ..config import settings
from ..intake.extract import extract_text_from_file
from ..intake.facts import extract_facts
from ..intake.normalize import IntakeError, normalize_text

router = APIRouter(prefix="/reports", tags=["reports"])


def _analyze(raw_text: str, source: schemas.ReportSourceOut) -> schemas.IntakeResult:
    text = normalize_text(raw_text)
    extracted = extract_facts(text)
    return schemas.IntakeResult(
        source=source,
        document=schemas.DocumentStatsOut(
            char_count=len(text),
            word_count=len(text.split()),
        ),
        facts=extracted["facts"],
        missing=extracted["missing"],
        conflicts=extracted["conflicts"],
        missing_information_statements=extracted["missing_information_statements"],
    )


def _read_upload_limited(file: UploadFile) -> bytes:
    """Read at most max_upload_bytes + 1 bytes so oversize is detectable."""
    limit = settings.max_upload_bytes
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise IntakeError(
            f"Uploaded file exceeds the {limit // (1024 * 1024)} MB size limit",
            status_code=413,
        )
    if not data:
        raise IntakeError("Uploaded file is empty", status_code=422)
    return data


@router.post("/intake/text", response_model=schemas.IntakeResult)
def intake_text(payload: schemas.ReportTextInput):
    source = schemas.ReportSourceOut(
        kind="text",
        name="pasted report text",
        size_bytes=len(payload.text.encode("utf-8")),
    )
    try:
        return _analyze(payload.text, source)
    except IntakeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/intake/file", response_model=schemas.IntakeResult)
def intake_file(file: UploadFile = File(...)):
    try:
        data = _read_upload_limited(file)
        raw_text, metadata = extract_text_from_file(file.filename, data)
        source = schemas.ReportSourceOut(
            kind="file",
            name=metadata["name"],
            size_bytes=metadata["size_bytes"],
            file_type=metadata["file_type"],
        )
        return _analyze(raw_text, source)
    except IntakeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
