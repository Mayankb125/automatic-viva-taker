from sqlalchemy import Column, Text, Integer, DateTime
from datetime import datetime
from app.core.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(Text, primary_key=True)
    session_id = Column(Text, nullable=False)
    question_text = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    key_keywords = Column(Text, nullable=True)   # JSON array as string
    key_points = Column(Text, nullable=True)     # JSON array as string
    level = Column(Integer, default=1)
    topic = Column(Text, nullable=True)
    asked_at = Column(DateTime, default=datetime.utcnow)
