from sqlalchemy import Column, Integer, String, Date, Float, UniqueConstraint, DateTime, func, ForeignKey

from app.database.base import Base


class DailySystemStats(Base):
    __tablename__ = 'daily_system_stats'

    date = Column(Date, primary_key=True)
    tasks_completed = Column(Integer, nullable=False, default=0)
    total_revenue = Column(Float, nullable=False, default=0.0)
    total_prime_cost = Column(Float, nullable=False, default=0.0)
    profit = Column(Float, nullable=False, default=0.0)


class UserModelStats(Base):
    __tablename__ = 'user_model_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_slug = Column(String(100), nullable=False)
    total_tasks_completed = Column(Integer, nullable=False, default=0)
    total_spending = Column(Float, nullable=False, default=0.0)


    __table_args__ = (
        UniqueConstraint('user_id', 'model_slug', name='uq_user_model_stats'),
    )


class CompletedTaskLog(Base):
    __tablename__ = 'completed_task_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_mongo_id = Column(String(36), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    model_slug = Column(String(100), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    cost = Column(Float, nullable=False)
    prime_cost = Column(Float, nullable=False)