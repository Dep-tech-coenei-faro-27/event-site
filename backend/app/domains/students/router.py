from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import RateLimit, client_ip, enforce_rate_limits
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_verified_user
from app.domains.students.schemas import StudentProofRead
from app.domains.students.service import (
    AlreadyVerifiedError,
    ProofAlreadySubmittedError,
    UnsupportedFileError,
    submit_proof,
)
from app.domains.users.models import StudentVerificationStatus, User

router = APIRouter(prefix="/users/me", tags=["students"])

ONE_HOUR = 3600
READ_CHUNK_BYTES = 64 * 1024


def read_limited(upload: UploadFile, limit: int) -> bytes:
    """The whole file, or a 413 as soon as it is bigger than the limit."""
    chunks: list[bytes] = []
    total = 0
    while chunk := upload.file.read(READ_CHUNK_BYTES):
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="The file is too large",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post(
    "/student-proof",
    response_model=StudentProofRead,
    status_code=status.HTTP_201_CREATED,
)
def send_student_proof(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> StudentProofRead:
    """Send the proof of enrolment (PDF, JPG or PNG) of a non-institutional email."""
    enforce_rate_limits(
        db,
        [
            (
                RateLimit(
                    "student_proof",
                    settings.RATE_LIMIT_STUDENT_PROOF_PER_HOUR,
                    ONE_HOUR,
                ),
                f"user:{current_user.id}",
            ),
            (
                RateLimit(
                    "student_proof_ip",
                    settings.RATE_LIMIT_STUDENT_PROOF_PER_IP_PER_HOUR,
                    ONE_HOUR,
                ),
                client_ip(request),
            ),
        ],
    )
    if current_user.student_verification_status is StudentVerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The account is already a verified student",
        )

    data = read_limited(file, settings.STUDENT_PROOF_MAX_BYTES)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The file is empty",
        )
    try:
        submit_proof(db, current_user, data)
    except UnsupportedFileError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF, JPG or PNG files are accepted",
        ) from None
    except AlreadyVerifiedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The account is already a verified student",
        ) from None
    except ProofAlreadySubmittedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A proof is already waiting for a decision",
        ) from None
    db.refresh(current_user)
    return StudentProofRead(status=current_user.student_verification_status)
