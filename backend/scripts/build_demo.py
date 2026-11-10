"""Rebuild fictional, upload-ready archives using only the Python standard library.

Run from backend: python scripts/build_demo.py
Expected results and project metadata stay OUTSIDE uploaded archives.
"""

import json
import zipfile
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "demo"
CLIENT = "Maya Chen <maya@northstar.example>"
FREELANCER = "Alex Morgan <alex@studio.example>"
CONTRACT = """FICTIONAL DEMO - Northstar website agreement
Client: Maya Chen, Northstar Studio, maya@northstar.example
Freelancer: Alex Morgan, alex@studio.example
Currency: EUR. This demo has no taxes or discounts.

1. Milestone: Website launch. Fixed price EUR 600 for the home page, contact page
and responsive layout together. Invoice only after the client accepts delivery.
2. Authentication, dark theme and analytics are excluded from the fixed milestone.
Additional work needs explicit client approval of scope and price.
3. Approved extras may be invoiced only after client acceptance of delivery.
4. Later mutually agreed written changes supersede earlier prices.
"""
# (day, sender-is-client, subject, body). Each thread has stable message IDs.
MAILS = [
    (
        1,
        True,
        "Website launch",
        "I agree to the attached Northstar website agreement, including the EUR 600 "
        "milestone and acceptance terms.",
    ),
    (
        2,
        False,
        "Website launch",
        "The website launch milestone is complete. The home page, contact page and "
        "responsive layout are ready for your review.",
    ),
    (
        3,
        True,
        "Website launch",
        "I reviewed and accept the completed website launch milestone. Please "
        "invoice the agreed EUR 600.",
    ),
    (4, True, "Authentication", "Could you add authentication to the website?"),
    (5, False, "Authentication", "I can implement authentication as an extra for EUR 200."),
    (6, True, "Authentication", "I approve the authentication extra for EUR 200. Please go ahead."),
    (7, False, "Authentication", "Authentication is implemented and ready for review."),
    (
        8,
        True,
        "Authentication",
        "I tested authentication and accept the completed extra. You can invoice EUR 200.",
    ),
    (9, True, "Dark theme", "Could we add a dark theme?"),
    (
        10,
        False,
        "Dark theme",
        "The dark theme would cost EUR 150. Please confirm the price before I "
        "start. I have not started it.",
    ),
    (11, False, "Analytics", "I propose analytics integration for EUR 100."),
    (12, True, "Analytics", "I approve analytics integration for EUR 100."),
    (
        13,
        False,
        "Analytics",
        "For the reduced analytics scope I propose replacing the earlier EUR 100 "
        "price with a final fixed price of EUR 80.",
    ),
    (
        14,
        True,
        "Analytics",
        "Agreed: replace the earlier analytics price with EUR 80 for the reduced scope.",
    ),
    (
        15,
        False,
        "Analytics",
        "The reduced-scope analytics integration is complete and ready for review.",
    ),
    (
        16,
        True,
        "Analytics",
        "I accept the completed reduced-scope analytics integration. Please invoice "
        "the final agreed EUR 80.",
    ),
    (
        17,
        True,
        "Future mobile app",
        "For a separate future project, perhaps next year, we might budget EUR 5000 "
        "for a mobile app. This is not part of the website project or an approval "
        "to start.",
    ),
]


def email_files(mails):
    previous = {}
    files = {}
    for day, client, subject, body in mails:
        msg = EmailMessage(policy=SMTP)
        msg["From"] = CLIENT if client else FREELANCER
        msg["To"] = FREELANCER if client else CLIENT
        msg["Subject"] = subject if subject not in previous else f"Re: {subject}"
        msg["Date"] = f"{day:02d} Oct 2026 10:00:00 +0000"
        msg_id = f"<demo-{day}-{subject.lower().replace(' ', '-')}@scopeproof.example>"
        msg["Message-ID"] = msg_id
        if subject in previous:
            msg["In-Reply-To"] = previous[subject]
            msg["References"] = previous[subject]
        previous[subject] = msg_id
        msg.set_content(body)
        files[f"emails/{day:02d}-{subject.lower().replace(' ', '-')}.eml"] = msg.as_bytes()
    return files


def build():
    ROOT.mkdir(exist_ok=True)
    datasets = {
        "website": {"contract.txt": CONTRACT.encode(), **email_files(MAILS)},
        "insufficient": email_files(
            [
                (
                    1,
                    True,
                    "Website launch",
                    "Could you redesign our website? We have not agreed a price or "
                    "delivery date yet.",
                ),
                (
                    2,
                    False,
                    "Website launch",
                    "Happy to discuss. I have not started work; please send the "
                    "requirements first.",
                ),
            ]
        ),
    }
    for name, files in datasets.items():
        with zipfile.ZipFile(ROOT / f"{name}.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for filename, data in sorted(files.items()):
                info = zipfile.ZipInfo(filename, date_time=(2026, 10, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
    expected = {
        "project": {
            "name": "Northstar website",
            "currency": "EUR",
            "client_name": "Maya Chen",
            "client_email": "maya@northstar.example",
        },
        "website": {
            "clear_items": {
                "Website launch": "600.00",
                "Authentication": "200.00",
                "Analytics": "80.00",
            },
            "flagged_items": {"Dark theme": ["missing_approval", "not_ready"]},
            "excluded_topics": ["Future mobile app"],
            "expected_total_after_review": "880.00",
        },
        "insufficient": {"no_clear_items": True, "expected_total_after_review": "0.00"},
    }
    (ROOT / "expected.json").write_text(json.dumps(expected, indent=2) + "\n")
    return datasets


if __name__ == "__main__":
    build()
    print(f"Wrote demo archives to {ROOT}")
