from sqlalchemy import Column, String, Float, BigInteger, DECIMAL, Boolean, Integer, DateTime, func

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    firebase_uid = Column(String(128), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)
    coefficient = Column(Float, default=1.0, nullable=False)

    balance = Column(DECIMAL(precision=15, scale=6), default=0.0, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )



class Price(Base):
    __tablename__ = "prices"

    model_name = Column(String(50), primary_key=True, index=True)
    cost = Column(DECIMAL(precision=15, scale=6), nullable=False)
    prime_cost = Column(DECIMAL(precision=15, scale=6), default=0.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)