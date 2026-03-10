from sqlalchemy import Column, Text, DateTime
from sqlalchemy.dialects.sqlite import BLOB
from datetime import datetime
from app.core.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    face_encoding = Column(BLOB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
