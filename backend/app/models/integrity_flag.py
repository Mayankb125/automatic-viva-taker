from sqlalchemy import Column, Text, DateTime
from datetime import datetime
from app.core.database import Base


class IntegrityFlag(Base):
    __tablename__ = "integrity_flags"

    id = Column(Text, primary_key=True)
    session_id = Column(Text, nullable=False)
    question_id = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    flag_type = Column(Text, nullable=False)   # gaze_away / head_turned / phone / book / laptop / extra_person
    description = Column(Text, nullable=True)
    video_clip_path = Column(Text, nullable=True)
