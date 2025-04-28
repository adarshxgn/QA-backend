from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String)
    upload_date = Column(DateTime, default=datetime.utcnow)
    content = Column(String)  # Stored extracted text from PDF