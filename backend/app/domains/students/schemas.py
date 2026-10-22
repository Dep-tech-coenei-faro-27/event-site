from pydantic import BaseModel

from app.domains.users.models import StudentVerificationStatus


class StudentProofRead(BaseModel):
    """Where the account stands after sending a proof (``verified`` if it passed)."""

    status: StudentVerificationStatus
