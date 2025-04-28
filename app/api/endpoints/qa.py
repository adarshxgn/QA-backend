from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import document as models
from app.schemas import document as schemas
from app.services.qa_service import QAService
import time
from typing import Optional, Dict
import asyncio
from fastapi.responses import JSONResponse

router = APIRouter()
qa_service = QAService()

# Enhanced rate limiting with request tracking
class RateLimiter:
    def __init__(self):
        self.last_request_time: Dict[int, float] = {}  # Track per document
        self.consecutive_failures = 0
        self.backoff_time = 60  # Initial backoff time in seconds
        self.max_backoff_time = 300  # Maximum backoff time (5 minutes)
        self.min_request_interval = 3.0

    def get_wait_time(self, document_id: int) -> float:
        current_time = time.time()
        last_time = self.last_request_time.get(document_id, 0)
        return max(0, self.min_request_interval - (current_time - last_time))

    def update_backoff(self, success: bool):
        if not success:
            self.consecutive_failures += 1
            self.backoff_time = min(
                self.backoff_time * 2,
                self.max_backoff_time
            )
        else:
            self.consecutive_failures = 0
            self.backoff_time = 60

    def record_request(self, document_id: int):
        self.last_request_time[document_id] = time.time()

rate_limiter = RateLimiter()

@router.post("/question", response_model=schemas.QuestionResponse)
async def ask_question(
    question_request: schemas.QuestionRequest,
    db: Session = Depends(get_db)
):
    document_id = question_request.document_id
    
    # Check rate limiting
    wait_time = rate_limiter.get_wait_time(document_id)
    if wait_time > 0:
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Please wait {wait_time:.1f} seconds before making another request",
                "retry_after": wait_time
            }
        )
    
    try:
        document = db.query(models.Document).filter(
            models.Document.id == document_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        answer = await qa_service.get_answer(
            question_request.question,
            document.content
        )
        
        # Record successful request
        rate_limiter.record_request(document_id)
        rate_limiter.update_backoff(success=True)
        
        return schemas.QuestionResponse(
            answer=answer,
            document_id=document_id
        )
    except Exception as e:
        error_message = str(e).lower()
        rate_limiter.update_backoff(success=False)
        
        if "insufficient_quota" in error_message:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Gemini API rate limit exceeded. Please wait {rate_limiter.backoff_time} seconds before trying again.",
                    "retry_after": rate_limiter.backoff_time
                }
            )
        elif "rate_limit" in error_message:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Too many requests. Please wait {rate_limiter.backoff_time} seconds before trying again.",
                    "retry_after": rate_limiter.backoff_time
                }
            )
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request."
        )