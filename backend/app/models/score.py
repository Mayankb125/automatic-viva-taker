from sqlalchemy import Column, Text, Float
from app.core.database import Base


class Score(Base):
    __tablename__ = "scores"

    id = Column(Text, primary_key=True)
    question_id = Column(Text, nullable=False)
    session_id = Column(Text, nullable=False)
    student_answer = Column(Text, nullable=True)
    semantic_score = Column(Float, nullable=True)
    keyword_score = Column(Float, nullable=True)
    depth_score = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    depth_reason = Column(Text, nullable=True)
    completeness_reason = Column(Text, nullable=True)
    adaptive_decision = Column(Text, nullable=True)
