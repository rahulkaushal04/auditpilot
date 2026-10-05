from datetime import date, timedelta
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app
from app.routes.upload import MAX_FILE_SIZE_BYTES

client = TestClient(app)

CSV_HEADER = (
    "Risk ID,Title,Description,Owner,Treatment,Likelihood,Impact,Review Date\n"
)


def valid_csv_of_size(size: int) -> bytes:
    """Build a valid one-risk CSV padded in its description to ``size`` bytes."""
    review = (date.today() + timedelta(days=365)).isoformat()
    row = "R001,Missing MFA,{description},Security Team,Roll out MFA,4,5,{review}\n"
    base = CSV_HEADER + row.format(description="", review=review)
    padding = size - len(base.encode())
    assert padding > 0
    content = CSV_HEADER + row.format(description="A" * padding, review=review)
    return content.encode()


def test_upload_valid_csv() -> None:
    first_review = (date.today() + timedelta(days=365)).isoformat()
    second_review = (date.today() + timedelta(days=540)).isoformat()
    csv_content = (
        "Risk ID,Title,Description,Owner,Treatment,Likelihood,Impact,Review Date\n"
        "R001,Weak Password Policy,Weak passwords across systems,IT Manager,"
        f"Implement MFA,4,5,{first_review}\n"
        "R002,Missing MFA,MFA is not enabled,Security Team,"
        f"Roll out MFA,5,5,{second_review}\n"
    ).encode()

    response = client.post(
        "/upload/risk-register",
        files={
            "file": (
                "risk-register.csv",
                BytesIO(csv_content),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
    "filename": "risk-register.csv",
    "status": "validated",
    "rows": 2,
    "columns": 8,
    "column_names": [
        "Risk ID",
        "Title",
        "Description",
        "Owner",
        "Treatment",
        "Likelihood",
        "Impact",
        "Review Date",
    ],
    "score": 100,
    "audit_readiness": "Ready",
    "findings": [],
}


def test_reject_unsupported_file_type() -> None:
    response = client.post(
        "/upload/risk-register",
        files={
            "file": (
                "risk-register.txt",
                BytesIO(b"unsupported"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_reject_empty_file() -> None:
    response = client.post(
        "/upload/risk-register",
        files={
            "file": (
                "risk-register.csv",
                BytesIO(b""),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400


def test_reject_csv_with_unterminated_quoted_field() -> None:
    csv_content = (
        CSV_HEADER
        + 'R001,"Unterminated title,Description,Owner,Treatment,4,5,2099-01-01\n'
    ).encode()

    response = client.post(
        "/upload/risk-register",
        files={
            "file": (
                "risk-register.csv",
                BytesIO(csv_content),
                "text/csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "The uploaded file could not be parsed.",
    }


def test_reject_file_above_size_limit() -> None:
    csv_content = valid_csv_of_size(MAX_FILE_SIZE_BYTES + 1)

    response = client.post(
        "/upload/risk-register",
        files={
            "file": (
                "risk-register.csv",
                BytesIO(csv_content),
                "text/csv",
            )
        },
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "File exceeds the 5 MB size limit."}


def test_accept_valid_csv_exactly_at_size_limit() -> None:
    csv_content = valid_csv_of_size(MAX_FILE_SIZE_BYTES)
    assert len(csv_content) == MAX_FILE_SIZE_BYTES

    response = client.post(
        "/upload/risk-register",
        files={
            "file": (
                "risk-register.csv",
                BytesIO(csv_content),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["rows"] == 1
    assert result["score"] == 100
    assert result["findings"] == []
