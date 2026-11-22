import io

import docx
import fitz
from fastapi.testclient import TestClient
import openpyxl
import pytest

from app.providers.base import ChatRequest, ChatResponse
from app.providers.ollama import OllamaProvider


def test_project_crud_archive_restore_and_safe_deletion(client: TestClient) -> None:
    created = client.post(
        "/api/v1/projects",
        json={
            "name": "Python Learning",
            "description": "Step-by-step Python exercises",
            "instructions": "Explain concepts simply with short examples.",
            "icon": "code",
            "color": "blue",
        },
    )
    assert created.status_code == 201
    proj = created.json()
    pid = proj["id"]
    assert proj["instructions"] == "Explain concepts simply with short examples."

    # Associate a conversation with this project
    conv = client.post(
        "/api/v1/conversations",
        json={"title": "List Comprehensions", "project_id": pid},
    ).json()

    detail = client.get(f"/api/v1/projects/{pid}").json()
    assert detail["conversations_count"] == 1

    # Archive & restore
    archived = client.post(f"/api/v1/projects/{pid}/archive").json()
    assert archived["is_archived"] is True
    assert client.get("/api/v1/projects").json()["total"] == 0
    assert client.get("/api/v1/projects?include_archived=true").json()["total"] == 1

    restored = client.post(f"/api/v1/projects/{pid}/restore").json()
    assert restored["is_archived"] is False

    # Delete project -> conversation must still exist (project_id set to null)
    assert client.delete(f"/api/v1/projects/{pid}").status_code == 204
    conv_after = client.get(f"/api/v1/conversations/{conv['id']}")
    assert conv_after.status_code == 200
    assert conv_after.json()["project_id"] is None


def test_file_upload_extraction_download_and_delete(client: TestClient) -> None:
    proj = client.post("/api/v1/projects", json={"name": "Docs Project"}).json()

    # 1. Plain text / code upload
    py_resp = client.post(
        "/api/v1/files/upload",
        data={"project_id": proj["id"]},
        files={"file": ("hello.py", b"def greet():\n    return 'hi'\n", "text/x-python")},
    )
    assert py_resp.status_code == 201
    py_file = py_resp.json()
    assert py_file["extraction_status"] == "completed"
    assert "def greet()" in py_file["extracted_text_preview"]

    # Download original
    dl = client.get(f"/api/v1/files/{py_file['id']}/download")
    assert dl.status_code == 200
    assert b"def greet()" in dl.content

    # 2. PDF upload (real PDF generated via PyMuPDF)
    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text((72, 72), "Local Workspace PDF Extraction Works")
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    pdf_resp = client.post(
        "/api/v1/files/upload",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )
    assert pdf_resp.status_code == 201
    assert pdf_resp.json()["extraction_status"] == "completed"
    assert "Local Workspace PDF Extraction Works" in pdf_resp.json()["extracted_text_preview"]

    # 3. Scanned/empty-text PDF -> gracefully reports ocr_required
    blank_pdf = fitz.open()
    blank_pdf.new_page()
    blank_bytes = blank_pdf.tobytes()
    blank_pdf.close()

    scan_resp = client.post(
        "/api/v1/files/upload",
        files={"file": ("scanned.pdf", blank_bytes, "application/pdf")},
    )
    assert scan_resp.status_code == 201
    assert scan_resp.json()["extraction_status"] == "ocr_required"

    # 4. DOCX upload
    doc = docx.Document()
    doc.add_paragraph("DOCX quarterly summary paragraph.")
    docx_buf = io.BytesIO()
    doc.save(docx_buf)
    docx_resp = client.post(
        "/api/v1/files/upload",
        files={
            "file": (
                "summary.docx",
                docx_buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert docx_resp.status_code == 201
    assert docx_resp.json()["extraction_status"] == "completed"
    assert "DOCX quarterly summary" in docx_resp.json()["extracted_text_preview"]

    # 5. XLSX upload
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"
    ws.append(["Month", "Revenue"])
    ws.append(["Jan", 1200])
    xlsx_buf = io.BytesIO()
    wb.save(xlsx_buf)
    xlsx_resp = client.post(
        "/api/v1/files/upload",
        files={
            "file": (
                "metrics.xlsx",
                xlsx_buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert xlsx_resp.status_code == 201
    assert xlsx_resp.json()["extraction_status"] == "completed"
    assert "1200" in xlsx_resp.json()["extracted_text_preview"]

    # 6. Unsupported executable rejected
    bad_resp = client.post(
        "/api/v1/files/upload",
        files={"file": ("malware.exe", b"MZ...", "application/octet-stream")},
    )
    assert bad_resp.status_code == 400

    # 7. Delete file
    assert client.delete(f"/api/v1/files/{py_file['id']}").status_code == 204
    assert client.get(f"/api/v1/files/{py_file['id']}").status_code == 404


def test_project_instructions_and_file_context_in_chat(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proj = client.post(
        "/api/v1/projects",
        json={
            "name": "IELTS Prep",
            "instructions": "Grade essays using official IELTS band descriptors.",
        },
    ).json()
    uploaded = client.post(
        "/api/v1/files/upload",
        data={"project_id": proj["id"]},
        files={"file": ("essay.txt", b"Technology has transformed education.", "text/plain")},
    ).json()
    prov = client.post(
        "/api/v1/providers",
        json={
            "provider_key": "ollama",
            "display_name": "Local Ollama",
            "base_url": "http://127.0.0.1:11434",
            "default_model": "llama3.2",
        },
    ).json()
    conv = client.post(
        "/api/v1/conversations",
        json={"title": "Essay Review", "project_id": proj["id"]},
    ).json()

    captured: dict[str, str] = {}

    async def fake_generate(
        self: OllamaProvider,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> ChatResponse:
        captured["system_prompt"] = request.system_prompt
        return ChatResponse(content="Band 7.5 feedback.", model_id=request.model_id)

    monkeypatch.setattr(OllamaProvider, "generate_response", fake_generate)

    resp = client.post(
        f"/api/v1/conversations/{conv['id']}/messages",
        json={
            "content": "Review my attached essay.",
            "provider_id": prov["id"],
            "model_id": "llama3.2",
            "attachment_ids": [uploaded["id"]],
        },
    )
    assert resp.status_code == 201
    assert "official IELTS band descriptors" in captured["system_prompt"]
    assert "Technology has transformed education." in captured["system_prompt"]


def test_artifact_crud_duplicate_and_export(client: TestClient) -> None:
    proj = client.post("/api/v1/projects", json={"name": "Web Dev"}).json()

    created = client.post(
        "/api/v1/artifacts",
        json={
            "title": "Landing Page",
            "artifact_type": "html",
            "content": "<h1>Hello Local World</h1>",
            "project_id": proj["id"],
        },
    )
    assert created.status_code == 201
    art = created.json()

    # Update
    updated = client.put(
        f"/api/v1/artifacts/{art['id']}",
        json={"content": "<h1>Updated Landing Page</h1>"},
    )
    assert updated.status_code == 200
    assert "Updated Landing Page" in updated.json()["content"]

    # Duplicate
    dup = client.post(f"/api/v1/artifacts/{art['id']}/duplicate")
    assert dup.status_code == 201
    assert dup.json()["title"] == "Landing Page (Copy)"

    # Export
    exp = client.get(f"/api/v1/artifacts/{art['id']}/export")
    assert exp.status_code == 200
    assert "Landing_Page.html" in exp.headers["content-disposition"]
    assert b"<h1>Updated Landing Page</h1>" in exp.content

    # Delete
    assert client.delete(f"/api/v1/artifacts/{art['id']}").status_code == 204
