"""
models/integrity_flag.py — Integrity Flag Table
=================================================
One row per proctoring violation detected during a viva session.

The CV (Computer Vision) service analyses each webcam frame and raises a flag
whenever suspicious behaviour is detected. Flags are stored here and shown
in the final report so an examiner can review them.

Flag types (stored in flag_type column):
    gaze_away      — Student looked away from the screen for too long
    head_turned    — Student's head rotated significantly sideways
    phone          — A phone was detected in the frame
    book           — An open book was detected in the frame
    laptop         — A second laptop/screen was detected
    extra_person   — More than one face was detected in the frame

Relationships:
  - Belongs to one Session   (session_id → sessions.id)
  - Optionally tied to the Question being asked at that moment (question_id)
"""

from sqlalchemy import Column, Text, DateTime
from datetime import datetime
from app.core.database import Base


class IntegrityFlag(Base):
    __tablename__ = "integrity_flags"

    # Unique flag ID — generated as a UUID string
    id = Column(Text, primary_key=True)

    # Foreign key: which session this flag occurred in
    session_id = Column(Text, nullable=False)

    # Foreign key: which question was being asked when the flag occurred.
    # Nullable because cheating can occur between questions.
    question_id = Column(Text, nullable=True)

    # UTC timestamp of when the violation was detected
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Category of the detected violation (see flag types list in docstring above)
    flag_type = Column(Text, nullable=False)   # gaze_away / head_turned / phone / book / laptop / extra_person

    # Optional human-readable description with more detail, e.g.:
    # "Student looked left for 4.2 seconds during question 3"
    description = Column(Text, nullable=True)

    # Path to the saved video clip evidence (relative to data/highlights/).
    # Null if video clip saving is disabled or hasn't been implemented yet.
    video_clip_path = Column(Text, nullable=True)
