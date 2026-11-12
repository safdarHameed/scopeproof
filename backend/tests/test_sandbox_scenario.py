import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.models import InvoiceItem, Project, User
from app.models.analysis import ItemStatus
from app.services import invoice_service
from app.services.analysis.base import (
    Category,
    EvidenceRole,
    FlagCode,
    ProjectContext,
    SourceDocument,
)
from app.services.analysis.rag import RagAnalyzer
from app.services.analysis.rag_models import Candidates, Citation, Decision
from app.services.analysis.retrieval import chunk_documents
from app.services.payments.paypal import build_invoice_payload


class SandboxScenarioProvider:
    """Simulates AI structured extraction for the exact $800 Sandbox test case."""

    def __init__(self, contract_chunk_id: str, email_chunk_id: str):
        self.contract_chunk_id = contract_chunk_id
        self.email_chunk_id = email_chunk_id

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Return deterministic dummy embedding vectors
        return [[1.0, 0.0] for _ in texts]

    async def structured(self, instructions: str, content: str, schema: type):
        if schema is Candidates:
            return Candidates(
                work_items=[
                    "Phase 1 contract milestone",
                    "Drainage line change order",
                    "Window fittings",
                ]
            )
        if schema is Decision:
            import json

            payload = json.loads(content)
            work_item = payload.get("work_item", "")

            if "Phase 1" in work_item:
                return Decision(
                    description="Phase 1 contract milestone",
                    category=Category.MILESTONE,
                    quantity="1",
                    unit_price="600.00",
                    currency="USD",
                    rationale="Contractually agreed milestone for Phase 1 site preparation.",
                    price_approved=True,
                    ready_to_invoice=True,
                    conflicting_price=False,
                    confidence=0.95,
                    evidence=[
                        Citation(
                            chunk_id=self.contract_chunk_id,
                            quote="Phase 1 milestone: Initial site preparation for USD 600.00",
                            role=EvidenceRole.CONTRACT_TERM,
                        ),
                        Citation(
                            chunk_id=self.email_chunk_id,
                            quote="I accept the Phase 1 site preparation delivery.",
                            role=EvidenceRole.ACCEPTANCE,
                        ),
                        Citation(
                            chunk_id=self.email_chunk_id,
                            quote="I approve the Phase 1 milestone billing.",
                            role=EvidenceRole.APPROVAL,
                        ),
                    ],
                )
            elif "Drainage" in work_item:
                return Decision(
                    description="Drainage line change order",
                    category=Category.EXTRA,
                    quantity="1",
                    unit_price="200.00",
                    currency="USD",
                    rationale="Explicitly approved change order for drainage line.",
                    price_approved=True,
                    ready_to_invoice=True,
                    conflicting_price=False,
                    confidence=0.95,
                    evidence=[
                        Citation(
                            chunk_id=self.email_chunk_id,
                            quote=(
                                "I explicitly approve the USD 200.00 for the "
                                "drainage line change order and accept the delivery of this work."
                            ),
                            role=EvidenceRole.APPROVAL,
                        ),
                        Citation(
                            chunk_id=self.email_chunk_id,
                            quote=(
                                "I explicitly approve the USD 200.00 for the "
                                "drainage line change order and accept the delivery of this work."
                            ),
                            role=EvidenceRole.ACCEPTANCE,
                        ),
                        Citation(
                            chunk_id=self.email_chunk_id,
                            quote=(
                                "I explicitly approve the USD 200.00 for the "
                                "drainage line change order and accept the delivery of this work."
                            ),
                            role=EvidenceRole.PRICE,
                        ),
                    ],
                )
            else:  # Window fittings
                return Decision(
                    description="Window fittings",
                    category=Category.EXTRA,
                    quantity="1",
                    unit_price="150.00",
                    currency="USD",
                    rationale=(
                        "Unapproved estimate for window fittings. "
                        "Client explicitly did not approve work."
                    ),
                    price_approved=False,
                    ready_to_invoice=False,
                    conflicting_price=False,
                    confidence=0.40,
                    evidence=[
                        Citation(
                            chunk_id=self.email_chunk_id,
                            quote=(
                                "Regarding the window fittings: "
                                "I received your estimate of USD 150.00"
                            ),
                            role=EvidenceRole.PRICE,
                        ),
                        Citation(
                            chunk_id=self.email_chunk_id,
                            quote=(
                                "I explicitly do not approve the window fitting work at this time."
                            ),
                            role=EvidenceRole.OTHER,
                        ),
                    ],
                )
        raise ValueError(f"Unexpected schema {schema}")

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_exact_sandbox_scenario_ai_extraction_review_and_invoice():
    """Validates the exact $800 Sandbox test case:
    - Contract: Phase 1 milestone: USD 600.
    - Client email:
        * Explicitly approves drainage line change order: USD 200.
        * Requests window fitting estimate: USD 150 (explicitly NOT approved).
    Expected outcome:
        - Phase 1 milestone: Contractually agreed ($600).
        - Drainage change: Explicitly approved ($200).
        - Window fittings: Not approved ($150 excluded).
        - Expected invoice total: USD 800.00.
        - The $150 estimate must NOT enter the invoice.
    """
    client_email = "sb-uww9m53877143@personal.example.com"
    project_context = ProjectContext(
        name="Scope Proof Demo Project",
        currency="USD",
        client_name="Sandbox Buyer",
        client_email=client_email,
    )

    contract_text = (
        "SCOPE OF WORK CONTRACT\n"
        "Phase 1 milestone: Initial site preparation for USD 600.00. "
        "Payment is due upon completion and acceptance."
    )
    email_text = (
        "From: Sandbox Buyer <sb-uww9m53877143@personal.example.com>\n"
        "Subject: Work updates and approvals\n\n"
        "Hi Alex,\n"
        "I accept the Phase 1 site preparation delivery. "
        "I approve the Phase 1 milestone billing.\n\n"
        "Regarding the drainage line change order: "
        "I explicitly approve the USD 200.00 for the drainage line change order "
        "and accept the delivery of this work.\n\n"
        "Regarding the window fittings: I received your estimate of USD 150.00. "
        "I explicitly do not approve the window fitting work at this time. "
        "Do not proceed with window fittings.\n"
    )

    doc_contract = SourceDocument(
        id=uuid.uuid4(),
        filename="Contract.txt",
        kind="contract",
        text=contract_text,
        author="Alex Builder <alex@builder.example>",
    )
    doc_email = SourceDocument(
        id=uuid.uuid4(),
        filename="Client_Approval.eml",
        kind="email",
        text=email_text,
        author=f"Sandbox Buyer <{client_email}>",
        sent_at=datetime(2026, 11, 12, tzinfo=UTC),
    )

    chunks = chunk_documents([doc_contract, doc_email])
    contract_chunk = next(c for c in chunks if c.document.id == doc_contract.id)
    email_chunk = next(c for c in chunks if c.document.id == doc_email.id)

    provider = SandboxScenarioProvider(contract_chunk.id, email_chunk.id)
    analyzer = RagAnalyzer(provider=provider)

    # 1. Run AI analysis
    suggestions = await analyzer.analyze(project_context, [doc_contract, doc_email])
    assert len(suggestions) == 3

    phase1 = next(s for s in suggestions if "Phase 1" in s.description)
    drainage = next(s for s in suggestions if "Drainage" in s.description)
    windows = next(s for s in suggestions if "Window" in s.description)

    # Validate Phase 1 Milestone
    assert phase1.unit_price == Decimal("600.00")
    assert not phase1.flags, f"Phase 1 should not have flags, got: {phase1.flags}"
    assert phase1.confidence >= 0.8

    # Validate Drainage Change Order
    assert drainage.unit_price == Decimal("200.00")
    assert not drainage.flags, f"Drainage should not have flags, got: {drainage.flags}"
    assert drainage.confidence >= 0.8

    # Validate Window Fittings: must be flagged as missing approval / not ready
    assert windows.unit_price == Decimal("150.00")
    flag_codes = {f.code for f in windows.flags}
    assert FlagCode.MISSING_APPROVAL in flag_codes
    assert FlagCode.LOW_CONFIDENCE in flag_codes

    # 2. Simulate human review and invoice creation via Database session
    from tests.conftest import TestSession

    async with TestSession() as db:
        user = User(
            id=uuid.uuid4(),
            email="alex@builder.example",
            full_name="Alex Builder",
            company_name="Alex Construction Studio",
            hashed_password="pw_hash_test_123",
            is_active=True,
        )
        db.add(user)

        project = Project(
            id=uuid.uuid4(),
            owner_id=user.id,
            name="Scope Proof Demo Project",
            currency="USD",
            client_name="Sandbox Buyer",
            client_email=client_email,
        )
        db.add(project)

        # Create the 3 items as stored in the DB
        item_phase1 = InvoiceItem(
            id=uuid.uuid4(),
            project_id=project.id,
            origin="analysis",
            category=Category.MILESTONE,
            description=phase1.description,
            quantity=Decimal("1.00"),
            unit_price=phase1.unit_price,
            status=ItemStatus.APPROVED,  # Freelancer approves valid contract milestone
            confidence=phase1.confidence,
            position=0,
        )
        item_drainage = InvoiceItem(
            id=uuid.uuid4(),
            project_id=project.id,
            origin="analysis",
            category=Category.EXTRA,
            description=drainage.description,
            quantity=Decimal("1.00"),
            unit_price=drainage.unit_price,
            status=ItemStatus.APPROVED,  # Freelancer approves explicitly approved change order
            confidence=drainage.confidence,
            position=1,
        )
        item_windows = InvoiceItem(
            id=uuid.uuid4(),
            project_id=project.id,
            origin="analysis",
            category=Category.EXTRA,
            description=windows.description,
            quantity=Decimal("1.00"),
            unit_price=windows.unit_price,
            status=ItemStatus.EXCLUDED,  # Freelancer EXCLUDES unapproved estimate
            confidence=windows.confidence,
            flags=[{"code": f.code, "message": f.message} for f in windows.flags],
            position=2,
        )
        db.add_all([item_phase1, item_drainage, item_windows])
        await db.commit()

        # Confirm invoice
        invoice = await invoice_service.confirm(
            db, project, due_date=date(2026, 11, 26), note="Phase 1 and drainage work."
        )

        # Assertions on created invoice
        assert invoice.total == Decimal("800.00"), f"Expected USD 800.00, got {invoice.total}"
        assert len(invoice.lines) == 2, f"Expected 2 approved lines, got {len(invoice.lines)}"

        line_descriptions = [line.description for line in invoice.lines]
        assert "Phase 1 contract milestone" in line_descriptions
        assert "Drainage line change order" in line_descriptions
        assert "Window fittings" not in line_descriptions

        line_amounts = {line.description: line.amount for line in invoice.lines}
        assert line_amounts["Phase 1 contract milestone"] == Decimal("600.00")
        assert line_amounts["Drainage line change order"] == Decimal("200.00")

        # 3. Test PayPal payload generation with the confirmed $800 invoice
        payload = build_invoice_payload(
            invoice,
            project,
            user,
            invoicer_email="sb-seller@business.example.com",
        )
        assert payload["amount"]["value"] == "800.00"
        assert payload["amount"]["breakdown"]["item_total"]["value"] == "800.00"
        assert payload["invoicer"]["email_address"] == "sb-seller@business.example.com"
        assert payload["primary_recipients"][0]["billing_info"]["email_address"] == client_email
        assert len(payload["items"]) == 2
        assert payload["items"][0]["unit_amount"]["value"] == "600.00"
        assert payload["items"][1]["unit_amount"]["value"] == "200.00"
