"""APScheduler for periodic background tasks."""

import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database.engine import async_session_factory
from app.database.redis_db import get_redis_client
from app.database.subscription_models import UserSubscription
from app.database.repositories.plan_repository import SubscriptionPlanRepository

logger = logging.getLogger(__name__)


async def check_expired_subscriptions_job():
    """Find expired subscriptions and downgrade them to the Free plan."""
    redis = get_redis_client()
    lock = redis.lock("cron_subs_check_lock", timeout=300, blocking=False)

    acquired = await lock.acquire()

    if not acquired:
        await redis.close()
        return

    logger.info("[CRON] Checking for expired subscriptions (Lock acquired)...")

    try:
        temp_plan_repo = SubscriptionPlanRepository(async_session_factory)
        free_plan = await temp_plan_repo.get_by_slug("free")

        if not free_plan:
            logger.error("[CRON] 'free' plan not found! Cannot downgrade users.")
            return

        free_plan_id = free_plan.id

        async with async_session_factory() as session:
            now = datetime.now(timezone.utc)

            stmt = select(UserSubscription).where(
                UserSubscription.status.in_(["active", "pending_cancellation"]),
                UserSubscription.current_period_end < now,
            )
            result = await session.execute(stmt)
            expired_subs = result.scalars().all()

            if not expired_subs:
                logger.info("[CRON] No expired subscriptions found.")
                return

            count = 0
            for sub in expired_subs:
                logger.info(
                    f"[CRON] Downgrading User {sub.user_id} "
                    f"(Plan: {sub.plan_id}) to FREE",
                )

                sub.status = "expired"

                new_free_sub = UserSubscription(
                    id=f"sub_{sub.user_id}_{int(datetime.now().timestamp())}",
                    user_id=sub.user_id,
                    plan_id=free_plan_id,
                    status="active",
                    is_manual=True,
                    current_period_start=now,
                    current_period_end=now + timedelta(days=365 * 100),
                )
                session.add(new_free_sub)
                count += 1

            await session.commit()
            logger.info(f"[CRON] Processed {count} expired subscriptions.")

    except Exception as e:
        logger.error(f"[CRON] Error checking subscriptions: {e}", exc_info=True)

    finally:
        try:
            await lock.release()
        except Exception:
            pass

        await redis.close()


scheduler = AsyncIOScheduler()


def start_scheduler():
    """Start the APScheduler with all periodic jobs."""
    scheduler.add_job(check_expired_subscriptions_job, "interval", minutes=60)
    scheduler.start()
    logger.info("APScheduler started.")


def shutdown_scheduler():
    """Shut down the APScheduler."""
    scheduler.shutdown()
    logger.info("APScheduler stopped.")
