"""Check that oversized uploads are rejected without being read in full."""

import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from app.routes.upload import MAX_FILE_SIZE_BYTES, upload_risk_register


def test_oversized_upload_reads_only_one_byte_past_the_limit() -> None:
    stream = BytesIO(b"A" * (MAX_FILE_SIZE_BYTES * 2))
    upload = UploadFile(file=stream, filename="risk-register.csv")

    with pytest.raises(HTTPException) as error:
        asyncio.run(upload_risk_register(upload))

    assert error.value.status_code == 413
    assert error.value.detail == "File exceeds the 5 MB size limit."
    assert stream.tell() == MAX_FILE_SIZE_BYTES + 1
