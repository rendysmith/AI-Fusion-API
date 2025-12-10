from sqlalchemy import Column, String, Float, BigInteger, DECIMAL, Boolean, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.services.referral_service import HasherRef


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    firebase_uid = Column(String(128), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    username = Column(String(30), unique=True, index=True, nullable=True)
    display_name = Column(String(100), nullable=True)
    photo_url = Column(String(255), nullable=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)

    registration_method = Column(String(20), nullable=False, default='unknown')

    coefficient = Column(Float, default=1.0, nullable=False)
    balance = Column(DECIMAL(precision=15, scale=6), default=0.0, nullable=False)

    is_admin = Column(Boolean, default=False, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)

    referred_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

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

    visitor_info = relationship(
        "Visitor",
        primaryjoin="foreign(Visitor.user_id) == User.id",
        uselist=False,
        viewonly=True
    )


    subscription = relationship(
        "UserSubscription",
        primaryjoin="and_(User.id == UserSubscription.user_id, UserSubscription.status == 'active')",
        uselist=False,
        lazy="joined"
    )

    referrer = relationship(
        "User",
        remote_side=[id])

    # === ИСПРАВЛЕНИЕ ===
    @property
    def referral_code(self) -> str | None:
        # Проверка на случай, если объект создан, но еще не сохранен в БД (нет ID)
        if self.id is None:
            return None

        # Вызываем синхронный статический метод.
        # Не создаем экземпляр класса (hr = HasherRef()) каждый раз — это лишняя нагрузка.
        return HasherRef.encode(self.id)


class TelegramAuthToken(Base):
    __tablename__ = "telegram_auth_tokens"

    token = Column(String(100), primary_key=True)
    firebase_uid = Column(String(128), ForeignKey("users.firebase_uid"), index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    status = Column(String(20), default='pending', nullable=False, index=True)

    telegram_id = Column(BigInteger, nullable=True)
    telegram_username = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Price(Base):
    __tablename__ = "prices"

    model_name = Column(String(50), primary_key=True, index=True)
    cost = Column(DECIMAL(precision=15, scale=6), nullable=False)
    prime_cost = Column(DECIMAL(precision=15, scale=6), default=0.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)