import io

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

DEMO_REPORT = (
    "HPLC testing of API batch API-102, manufactured on 20 October 2026, found an "
    "impurity result of 2.1% against a specification limit of 1.0%. Quality Control "
    "identified the issue during release testing. The report does not include the "
    "batch temperature trends, raw material test results, equipment calibration "
    "status, or detailed process parameters. Batch disposition has not been documented."
)

TEXT_URL = "/api/reports/intake/text"
FILE_URL = "/api/reports/intake/file"


def make_pdf(text: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(50, 750, DEMO_REPORT)
    pdf.save()
    return buffer.getvalue()


def make_eml(body: str) -> bytes:
    eml = (
        "From: qc@example.com\r\n"
        "To: quality@example.com\r\n"
        "Subject: Deviation report\r\n"
        "MIME-Version: 1.0\r\n"
        'Content-Type: text/plain; charset="utf-8"\r\n'
        "\r\n"
        + body.replace("\n", "\r\n")
    )
    return eml.encode("utf-8")


def upload(client, name: str, content: bytes):
    return client.post(
        FILE_URL,
        files={"file": (name, content, "application/octet-stream")},
    )


def demo_facts(client):
    response = upload(client, "report.txt", DEMO_REPORT.encode("utf-8"))
    assert response.status_code == 200
    return response.json()


# ---------- pasted text ----------

def test_pasted_text_extraction(client):
    response = client.post(TEXT_URL, json={"text": DEMO_REPORT})
    assert response.status_code == 200
    body = response.json()
    fields = {fact["field"]: fact for fact in body["facts"]}
    assert fields["batch_id"]["value"] == "API-102"
    assert fields["reported_result"]["value"] == "2.1%"
    assert fields["spec_limit"]["value"] == "1.0%"
    assert fields["event_date"]["value"].lower() == "20 october 2026"
    assert fields["event_date"]["iso_date"] == "2026-10-20"
    assert fields["detection_context"]["value"].rstrip(".").endswith("during release testing")
    assert body["missing"] == []
    assert body["conflicts"] == []
    assert len(body["missing_information_statements"]) >= 1
    assert "does not include" in " ".join(body["missing_information_statements"])
    assert body["document"]["word_count"] > 0
    assert body["source"]["kind"] == "text"


def test_pasted_text_missing_facts_listed(client):
    response = client.post(TEXT_URL, json={"text": "A minor event occurred on site."})
    assert response.status_code == 200
    body = response.json()
    assert body["facts"] == []
    assert set(body["missing"]) == {
        "batch_id", "reported_result", "spec_limit", "event_date", "detection_context"
    }


def test_pasted_text_empty_and_whitespace_rejected(client):
    assert client.post(TEXT_URL, json={"text": ""}).status_code == 422
    response = client.post(TEXT_URL, json={"text": "   \n\t  "})
    assert response.status_code == 422
    assert "empty" in response.json()["detail"]


def test_pasted_text_too_large_rejected(client):
    # Pydantic request validation caps pasted text; the endpoint-level 413 path
    # applies to files larger than 10 MB.
    response = client.post(TEXT_URL, json={"text": "A" * 200001})
    assert response.status_code == 422
    assert "200000" in str(response.json())


def test_conflicting_values_reported_not_resolved(client):
    text = (
        "Batch API-102 impurity result of 2.1% against a specification limit of 1.0%. "
        "Batch API-207 assay 3.4% against a specification limit of 1.5%."
    )
    response = client.post(TEXT_URL, json={"text": text})
    assert response.status_code == 200
    body = response.json()
    conflict_fields = {conflict["field"] for conflict in body["conflicts"]}
    assert "reported_result" in conflict_fields
    assert "spec_limit" in conflict_fields
    result_conflict = next(c for c in body["conflicts"] if c["field"] == "reported_result")
    assert set(result_conflict["values"]) == {"2.1%", "3.4%"}
    assert body["facts"][0]["field"] == "batch_id"


def test_control_characters_removed_but_content_kept(client):
    response = client.post(TEXT_URL, json={"text": "Batch API-102\x00 found impurity 2.1% against limit of 1.0%."})
    assert response.status_code == 200
    body = response.json()
    assert body["facts"][0]["value"] == "API-102"


# ---------- file uploads ----------

def test_upload_txt(client):
    body = demo_facts(client)
    assert body["source"]["kind"] == "file"
    assert body["source"]["name"] == "report.txt"
    assert body["source"]["file_type"] == "txt"
    fields = {fact["field"]: fact for fact in body["facts"]}
    assert fields["batch_id"]["value"] == "API-102"


def test_upload_md(client):
    md = "# Deviation report\n\n" + DEMO_REPORT + "\n"
    response = upload(client, "report.md", md.encode("utf-8"))
    assert response.status_code == 200
    fields = {fact["field"]: fact for fact in response.json()["facts"]}
    assert fields["batch_id"]["value"] == "API-102"


def test_upload_pdf(client):
    response = upload(client, "report.pdf", make_pdf(DEMO_REPORT))
    assert response.status_code == 200
    fields = {fact["field"]: fact for fact in response.json()["facts"]}
    assert fields["batch_id"]["value"] == "API-102"
    assert fields["spec_limit"]["value"] == "1.0%"


def test_upload_eml(client):
    response = upload(client, "report.eml", make_eml(DEMO_REPORT))
    assert response.status_code == 200
    fields = {fact["field"]: fact for fact in response.json()["facts"]}
    assert fields["batch_id"]["value"] == "API-102"
    assert fields["event_date"]["iso_date"] == "2026-10-20"


def test_upload_unsupported_type_rejected(client):
    response = upload(client, "malware.exe", b"MZ fake binary")
    assert response.status_code == 415
    assert ".exe" in response.json()["detail"]
    assert all(ext in response.json()["detail"] for ext in (".pdf", ".txt", ".md", ".eml"))


def test_upload_oversized_file_rejected(client):
    big = b"A" * (10 * 1024 * 1024 + 1)
    response = upload(client, "big.txt", big)
    assert response.status_code == 413
    assert "size limit" in response.json()["detail"]


def test_upload_empty_file_rejected(client):
    response = upload(client, "empty.txt", b"")
    assert response.status_code == 422
    assert "empty" in response.json()["detail"]


def test_upload_fake_pdf_rejected(client):
    response = upload(client, "notapdf.pdf", "This is plain text, not a real PDF.".encode())
    assert response.status_code == 422
    assert "valid PDF" in response.json()["detail"]


def test_upload_corrupt_pdf_rejected(client):
    response = upload(client, "corrupt.pdf", b"%PDF-1.4\n%%EOF broken garbage \x10\x11")
    assert response.status_code == 422
    assert "damaged" in response.json()["detail"]


def test_upload_scanned_pdf_without_text_rejected(client):
    image = Image.new("RGB", (400, 400), color="white")
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")

    pdf_buffer = io.BytesIO()
    pdf = canvas.Canvas(pdf_buffer)
    image_buffer.seek(0)
    pdf.drawImage(ImageReader(image_buffer), 10, 10)
    pdf.save()

    response = upload(client, "scanned.pdf", pdf_buffer.getvalue())
    assert response.status_code == 422
    assert "No text could be extracted" in response.json()["detail"]


def test_upload_html_only_eml_rejected(client):
    eml = (
        "From: qc@example.com\r\n"
        "Subject: html only\r\n"
        "MIME-Version: 1.0\r\n"
        'Content-Type: text/html; charset="utf-8"\r\n'
        "\r\n"
        "<html><body>Batch API-102</body></html>"
    )
    response = upload(client, "report.eml", eml.encode("utf-8"))
    assert response.status_code == 422
    assert "plain-text" in response.json()["detail"]


def test_upload_unreadable_binary_txt_rejected(client):
    payload = bytes(range(1, 256)) * 8
    response = upload(client, "weird.txt", payload)
    assert response.status_code in (200, 422)
    assert response.status_code == 200
    assert response.json()["document"]["char_count"] > 0


def test_filename_without_extension_rejected(client):
    response = upload(client, "noext", DEMO_REPORT.encode("utf-8"))
    assert response.status_code == 415


def test_facts_only_from_explicit_wording(client):
    text = "Investigator believed the root cause was probably equipment wear."
    response = client.post(TEXT_URL, json={"text": text})
    assert response.status_code == 200
    body = response.json()
    assert body["facts"] == []
    assert set(body["missing"]) == {
        "batch_id", "reported_result", "spec_limit", "event_date", "detection_context"
    }
    assert body["missing_information_statements"] == []
