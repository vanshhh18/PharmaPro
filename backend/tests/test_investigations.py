def make_payload(reference="INV-001", **overrides):
    payload = {
        "title": "Impurity OOS on batch API-102",
        "reference": reference,
        "description": "Release testing found 2.1% impurity vs 1.0% limit.",
        "report_text": "Batch API-102 HPLC impurity 2.1% against 1.0% limit.",
        "cause_hypotheses": (
            [
                {
                    "description": "Process deviation during manufacturing",
                    "category": "process",
                    "status": "proposed",
                }
            ]
            if overrides.get("with_related")
            else []
        ),
        "evidence_gaps": (
            [{"description": "Batch temperature trends missing", "resolved": False}]
            if overrides.get("with_related")
            else []
        ),
        "rca_steps": (
            [{"method": "5whys", "question": "Why was the result out of spec?", "answer": "", "position": 1}]
            if overrides.get("with_related")
            else []
        ),
        "capa_actions": (
            [{"description": "Retrain QC analysts on method", "type": "corrective", "status": "proposed"}]
            if overrides.get("with_related")
            else []
        ),
        **{k: v for k, v in overrides.items() if k != "with_related"},
    }
    return payload


def test_dashboard_counts_zero(client):
    response = client.get("/api/investigations/dashboard")
    assert response.status_code == 200
    assert all(v == 0 for v in response.json().values())


def test_dashboard_counts_after_create(client):
    create = client.post("/api/investigations", json=make_payload(with_related=True))
    assert create.status_code == 201
    response = client.get("/api/investigations/dashboard")
    counts = response.json()
    assert counts["investigations_total"] == 1
    assert counts["investigations_open"] == 1
    assert counts["investigations_archived"] == 0
    assert counts["cause_hypotheses"] == 1
    assert counts["evidence_gaps"] == 1
    assert counts["evidence_gaps_unresolved"] == 1
    assert counts["rca_steps"] == 1
    assert counts["capa_actions"] == 1
    assert counts["capa_open"] == 1
    assert counts["audit_events"] == 1


def test_create_and_get_with_related_data(client):
    create = client.post("/api/investigations", json=make_payload(with_related=True))
    assert create.status_code == 201
    body = create.json()
    assert body["status"] == "open"
    assert len(body["cause_hypotheses"]) == 1
    assert len(body["evidence_gaps"]) == 1
    assert len(body["rca_steps"]) == 1
    assert len(body["capa_actions"]) == 1
    assert body["audit_events"][0]["action"] == "created"

    fetched = client.get(f"/api/investigations/{body['id']}")
    assert fetched.status_code == 200
    detail = fetched.json()
    assert detail["reference"] == "INV-001"
    assert detail["cause_hypotheses"][0]["status"] == "proposed"
    assert detail["evidence_gaps"][0]["description"].startswith("Batch temperature")
    assert detail["rca_steps"][0]["method"] == "5whys"
    assert detail["capa_actions"][0]["type"] == "corrective"


def test_create_duplicate_reference_conflict(client):
    assert client.post("/api/investigations", json=make_payload()).status_code == 201
    response = client.post("/api/investigations", json=make_payload())
    assert response.status_code == 409
    assert "reference already exists" in response.json()["detail"]


def test_create_validation_errors(client):
    missing_title = client.post("/api/investigations", json=make_payload(title=""))
    assert missing_title.status_code == 422

    bad_reference = client.post("/api/investigations", json=make_payload(reference="bad ref!"))
    assert bad_reference.status_code == 422

    invalid_capa = make_payload(
        reference="INV-002",
        capa_actions=[{"description": "x", "type": "urgent", "status": "proposed"}],
    )
    assert client.post("/api/investigations", json=invalid_capa).status_code == 422

    invalid_hypothesis_status = make_payload(
        reference="INV-003",
        cause_hypotheses=[{"description": "x", "status": "confirmed-root-cause"}],
    )
    assert client.post("/api/investigations", json=invalid_hypothesis_status).status_code == 422


def test_list_investigations_and_status_filter(client):
    client.post("/api/investigations", json=make_payload(reference="INV-A"))
    archived = client.post("/api/investigations", json=make_payload(reference="INV-B"))
    inv_id = archived.json()["id"]
    client.post(f"/api/investigations/{inv_id}/archive")

    response = client.get("/api/investigations")
    assert response.status_code == 200
    assert len(response.json()) == 2

    open_only = client.get("/api/investigations?status=open")
    assert [item["reference"] for item in open_only.json()] == ["INV-A"]

    archived_only = client.get("/api/investigations?status=archived")
    assert [item["reference"] for item in archived_only.json()] == ["INV-B"]

    assert client.get("/api/investigations?status=pending").status_code == 422

    limited = client.get("/api/investigations?limit=1&offset=0")
    assert len(limited.json()) == 1


def test_get_not_found(client):
    assert client.get("/api/investigations/9999").status_code == 404
    assert client.get("/api/investigations/9999/audit").status_code == 404
    assert client.post("/api/investigations/9999/archive").status_code == 404
    assert client.post("/api/investigations/9999/reopen").status_code == 404


def test_update_fields_and_related_lists(client):
    created = client.post("/api/investigations", json=make_payload(with_related=True)).json()
    inv_id = created["id"]

    update = client.patch(
        f"/api/investigations/{inv_id}",
        json={
            "title": "Updated title",
            "related": {
                "capa_actions": [
                    {"description": "Place chromatogram under review hold", "type": "corrective", "status": "accepted"},
                    {"description": "Add trending review to next release", "type": "preventive", "status": "completed"},
                ]
            },
        },
    )
    assert update.status_code == 200
    body = update.json()
    assert body["title"] == "Updated title"
    assert len(body["capa_actions"]) == 2
    assert {action["status"] for action in body["capa_actions"]} == {"accepted", "completed"}
    assert len(body["cause_hypotheses"]) == 1

    history = client.get(f"/api/investigations/{inv_id}/audit").json()
    actions = [event["action"] for event in history]
    assert actions[-1] == "updated"
    assert history[-1]["detail"] == "fields: title; related: capa_actions: 1->2 (+1)"

    dashboard = client.get("/api/investigations/dashboard").json()
    assert dashboard["capa_actions"] == 2


def test_update_empty_body_makes_no_audit_change(client):
    created = client.post("/api/investigations", json=make_payload()).json()
    inv_id = created["id"]
    response = client.patch(f"/api/investigations/{inv_id}", json={})
    assert response.status_code == 200
    history = client.get(f"/api/investigations/{inv_id}/audit").json()
    assert len(history) == 1
    assert history[0]["action"] == "created"

    dashboard = client.get("/api/investigations/dashboard").json()
    assert dashboard["audit_events"] == 1


def test_archive_and_reopen_preserves_data(client):
    created = client.post("/api/investigations", json=make_payload(with_related=True)).json()
    inv_id = created["id"]

    archived = client.post(f"/api/investigations/{inv_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert client.post(f"/api/investigations/{inv_id}/archive").status_code == 409

    reopened = client.post(f"/api/investigations/{inv_id}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"
    assert client.post(f"/api/investigations/{inv_id}/reopen").status_code == 409

    detail = client.get(f"/api/investigations/{inv_id}").json()
    assert detail["title"] == created["title"]
    assert detail["evidence_gaps"] == created["evidence_gaps"]
    assert detail["cause_hypotheses"] == created["cause_hypotheses"]
    assert [s["question"] for s in detail["rca_steps"]] == [
        s["question"] for s in created["rca_steps"]
    ]
    assert [c["description"] for c in detail["capa_actions"]] == [
        c["description"] for c in created["capa_actions"]
    ]

    actions = [event["action"] for event in detail["audit_events"]]
    assert actions == ["created", "archived", "reopened"]


def test_audit_history_endpoint(client):
    created = client.post("/api/investigations", json=make_payload()).json()
    inv_id = created["id"]
    client.patch(f"/api/investigations/{inv_id}", json={"description": "New description"})
    client.post(f"/api/investigations/{inv_id}/archive")

    response = client.get(f"/api/investigations/{inv_id}/audit")
    assert response.status_code == 200
    events = response.json()
    assert [event["action"] for event in events] == ["created", "updated", "archived"]
    assert all(event["created_at"] for event in events)


def test_reopening_restores_data_after_list_removal(client):
    client.post("/api/investigations", json=make_payload(reference="INV-P", with_related=True))
    dash = client.get("/api/investigations/dashboard").json()
    assert dash["investigations_open"] == 1
    assert dash["evidence_gaps"] == 1
    listed = client.get("/api/investigations").json()
    assert listed[0]["reference"] == "INV-P"


def test_edits_persist_after_reopen_with_entity_audit_details(client):
    created = client.post("/api/investigations", json=make_payload(with_related=True)).json()
    inv_id = created["id"]

    update = client.patch(
        f"/api/investigations/{inv_id}",
        json={
            "related": {
                "cause_hypotheses": [
                    {"description": "Equipment wear during cleaning", "category": "machine", "status": "proposed"},
                    {"description": "Process deviation during manufacturing", "category": "process", "status": "rejected"},
                ],
                "evidence_gaps": [
                    {"description": "Batch temperature trends missing", "resolved": True},
                    {"description": "Raw material test results missing", "resolved": False},
                ],
                "rca_steps": [
                    {"method": "5whys", "question": "Why was the result OOS?", "answer": "Process drift", "position": 1},
                    {"method": "fishbone", "question": "Which fishbone category explains the drift?", "answer": "", "position": 2},
                ],
                "capa_actions": [
                    {"description": "Recalibrate HPLC", "type": "corrective", "status": "accepted"},
                    {"description": "Add trend review step", "type": "preventive", "status": "completed"},
                ],
            }
        },
    )
    assert update.status_code == 200

    history = client.get(f"/api/investigations/{inv_id}/audit").json()
    update_event = history[-1]
    assert update_event["action"] == "updated"
    # Entity-level change details with counts, no content dumped into the log
    for expected in (
        "cause_hypotheses: 1->2 (+1)",
        "evidence_gaps: 1->2 (+1)",
        "rca_steps: 1->2 (+1)",
        "capa_actions: 1->2 (+1)",
    ):
        assert expected in update_event["detail"]
    assert "API-102" not in update_event["detail"]

    archived = client.post(f"/api/investigations/{inv_id}/archive")
    assert archived.status_code == 200
    reopened = client.post(f"/api/investigations/{inv_id}/reopen")
    assert reopened.status_code == 200

    restored = client.get(f"/api/investigations/{inv_id}").json()
    assert sorted(h["description"] for h in restored["cause_hypotheses"]) == [
        "Equipment wear during cleaning",
        "Process deviation during manufacturing",
    ]
    assert {h["status"] for h in restored["cause_hypotheses"]} == {"proposed", "rejected"}
    assert {g["resolved"] for g in restored["evidence_gaps"]} == {True, False}
    rca = {s["method"]: s for s in restored["rca_steps"]}
    assert rca["5whys"]["answer"] == "Process drift"
    assert rca["fishbone"]["question"].startswith("Which fishbone category")
    capa = {c["description"]: c for c in restored["capa_actions"]}
    assert capa["Recalibrate HPLC"]["status"] == "accepted"
    assert capa["Add trend review step"]["status"] == "completed"

    actions = [e["action"] for e in restored["audit_events"]]
    assert actions == ["created", "updated", "archived", "reopened"]


def test_removal_and_clearing_recorded_in_audit(client):
    created = client.post("/api/investigations", json=make_payload(with_related=True)).json()
    inv_id = created["id"]

    cleared = client.patch(
        f"/api/investigations/{inv_id}",
        json={"related": {"capa_actions": []}},
    )
    assert cleared.status_code == 200
    detail = cleared.json()["audit_events"][-1]["detail"]
    assert "capa_actions: 1->0 (cleared)" in detail

    dashboard = client.get("/api/investigations/dashboard").json()
    assert dashboard["capa_actions"] == 0


def test_same_length_replacement_recorded_as_rebuilt(client):
    created = client.post("/api/investigations", json=make_payload(with_related=True)).json()
    inv_id = created["id"]

    replaced = client.patch(
        f"/api/investigations/{inv_id}",
        json={
            "related": {
                "capa_actions": [
                    {"description": "Completely different action", "type": "preventive", "status": "accepted"}
                ]
            }
        },
    )
    assert replaced.status_code == 200
    detail = replaced.json()["audit_events"][-1]["detail"]
    assert "capa_actions: 1->1 (rebuilt)" in detail

def test_export_report_contains_details_and_escapes_untrusted_content(client):
    created = client.post(
        "/api/investigations",
        json=make_payload(
            title="<script>alert(1)</script>",
            with_related=True,
        ),
    ).json()
    inv_id = created["id"]

    res = client.get(f"/api/investigations/{inv_id}/export")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "INV-001-report.html" in res.headers["content-disposition"]

    body = res.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "<script>alert(1)</script>" not in body
    assert "HPLC impurity 2.1% against 1.0% limit" in body
    assert "Process deviation during manufacturing" in body
    assert "5 Whys" in body
    assert "CAPA actions" in body
    assert "Review notice and disclaimer" in body
    assert "created" in body


def test_export_reports_incomplete_data_without_selection_errors(client):
    created = client.post(
        "/api/investigations",
        json=make_payload(title="Sparse case"),
    ).json()
    res = client.get(f"/api/investigations/{created['id']}/export")
    assert res.status_code == 200
    assert res.text.count("No records.") == 4
    assert "Review notice and disclaimer" in res.text


def test_export_unknown_investigation_returns_404(client):
    res = client.get("/api/investigations/9999/export")
    assert res.status_code == 404
