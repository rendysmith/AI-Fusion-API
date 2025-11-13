from sqlalchemy import Column, Integer, Text, String, DateTime, func

from app.database.base import Base


class VideoTemplate(Base):
    __tablename__ = "video_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)


    video_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text, nullable=False)
    title = Column(String(255), nullable=False)
    views_count = Column(String(50), nullable=True)
    prompt = Column(Text, nullable=False)
    platform_icon = Column(String(50), nullable=True)
    row_number = Column(Integer, default=1)
    position = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)