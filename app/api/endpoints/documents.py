from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import document as models
from app.schemas import document as schemas
from app.services.document_processor import DocumentProcessor

router = APIRouter()
document_processor = DocumentProcessor()

@router.post("/upload", response_model=schemas.Document)  # Changed from "/" to "/upload"
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    file_path = await document_processor.save_pdf(file)
    content = document_processor.extract_text(file_path)
    
    db_document = models.Document(
        filename=file.filename,
        file_path=file_path,
        content=content
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

@router.get("/", response_model=List[schemas.Document])
def get_documents(db: Session = Depends(get_db)):
    return db.query(models.Document).all()