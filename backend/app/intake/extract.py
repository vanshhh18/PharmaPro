import email
import email.policy
import io
import os

from pypdf import PdfReader

from .normalize import IntakeError

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".eml"}


def _decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise IntakeError(
        "Could not determine the text encoding of the uploaded file"
    )


def _extract_pdf(data: bytes, filename: str) -> str:
    if not data.startswith(b"%PDF-"):
        raise IntakeError(
            f"Uploaded file '{filename}' is not a valid PDF file (missing PDF signature)"
        )
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:  # untrusted, possibly corrupt file
        raise IntakeError(
            f"PDF extraction failed for '{filename}': the document appears to be damaged"
        ) from exc
    text = "\n".join(part for part in pages if part).strip()
    if not text or not any(ch.isalnum() for ch in text):
        raise IntakeError(
            f"No text could be extracted from '{filename}'. "
            "The PDF may be a scanned image or encrypted."
        )
    return text


def _extract_eml(data: bytes, filename: str) -> str:
    try:
        message = email.message_from_bytes(data, policy=email.policy.default)
    except Exception as exc:
        raise IntakeError(f"'{filename}' could not be parsed as an EML email") from exc

    parts: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and not part.is_attachment():
                payload = part.get_content()
                if isinstance(payload, str) and payload.strip():
                    parts.append(payload)
    else:
        if message.get_content_type() == "text/plain":
            payload = message.get_content()
            if isinstance(payload, str):
                parts.append(payload)

    text = "\n".join(part.strip() for part in parts if part.strip()).strip()
    if not text or not any(ch.isalnum() for ch in text):
        raise IntakeError(
            f"No plain-text content found in '{filename}'. "
            "HTML-only emails are not supported."
        )
    return text


def extract_text_from_file(filename: str, data: bytes) -> tuple[str, dict]:
    """Extract raw text from an uploaded file.

    Returns (text, file_metadata). Raises IntakeError for unsupported types or
    failed extraction - never returns placeholder text for a broken document.
    """
    metadata = {
        "name": os.path.basename(filename or "upload"),
        "size_bytes": len(data),
        "file_type": None,
    }

    if not metadata["name"] or "." not in metadata["name"]:
        raise IntakeError(
            "Uploaded file must have a supported extension (.pdf, .txt, .md, .eml)",
            status_code=415,
        )

    extension = os.path.splitext(metadata["name"])[1].lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise IntakeError(
            f"Unsupported file type '{extension}'. Supported types: .pdf, .txt, .md, .eml",
            status_code=415,
        )
    metadata["file_type"] = extension.lstrip(".")

    if extension == ".pdf":
        text = _extract_pdf(data, metadata["name"])
    elif extension == ".eml":
        text = _extract_eml(data, metadata["name"])
    else:  # .txt / .md
        text = _decode_bytes(data).strip()

    return text, metadata