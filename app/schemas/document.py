from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DocumentBase(BaseModel):
    filename: str

class DocumentCreate(DocumentBase):
    pass

class Document(DocumentBase):
    id: int
    file_path: str
    upload_date: datetime
    
    class Config:
        from_attributes = True

class QuestionRequest(BaseModel):
    document_id: int
    question: str

class QuestionResponse(BaseModel):
    answer: str
    document_id: int