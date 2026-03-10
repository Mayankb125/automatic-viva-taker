from sqlalchemy import Column, Text, DateTime, Float
from datetime import datetime
from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Text, primary_key=True)
    student_id = Column(Text, nullable=False)
    subject = Column(Text, nullable=True)
    topic = Column(Text, nullable=True)
    topic_list = Column(Text, nullable=True)   # JSON array stored as string
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(Text, default="active")    # active / completed
    overall_score = Column(Float, nullable=True)
