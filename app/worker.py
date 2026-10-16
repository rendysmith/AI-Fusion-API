"""Background worker for processing generation tasks from SQS queue."""

import asyncio
import json
import logging
import time
import traceback
from datetime import datetime

import aiobotocore.client
import aiohttp
from aiobotocore.session import get_session
from aiohttp import ClientTimeout

from app.services.redis_publisher import RedisPublisher

from app.database.engine import async_session_factory
from app.database.redis_db import get_redis_client
from app.database.repositories.analytics_repository import AnalyticsRepository
from app.database.repositories.circuit_breaker_repository import (
    CircuitBreakerRepository,
)
from app.database.repositories.task_repository import TaskRepository
from app.database.repositories.user_repository import UserRepository
from app.exceptions import FatalProviderError, UserValidationError
from app.services.providers import unifically_provider, grsai_provider
from app.services.s3_uploader import S3UploaderService
from app.services.telegram_notifier import send_error_alert
from app.settings import settings
from app.utils.error_mapper import get_user_friendly_error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [WORKER] - %(message)s",
)

WORKER_ID = settings.WORKER_ID

MAX_CONCURRENT_TASKS = settings.WORKER_MAX_CONCURRENT_TASKS

logger = logging.getLogger(__name__)

MODEL_PROCESSORS_PRIMARY = {
    "sora-2": grsai_provider.generate_sora_grsai,
    "veo-3-quality": grsai_provider.generate_veo_grsai,
    "veo-3-fast": grsai_provider.generate_veo_grsai,
    "nano-banana": grsai_provider.generate_nano_banana_grsai,
    "nano-banana-pro": grsai_provider.generate_nano_banana_pro_grsai,
}

MODEL_PROCESSORS_FALLBACK = {
    "sora-2": unifically_provider.generate_sora_video,
}


async def process_task(
    session: aiohttp.ClientSession,
    task_data: dict,
    task_repo: TaskRepository,
    analytics_repo: AnalyticsRepository,
    user_repo: UserRepository,
    s3_uploader: S3UploaderService,
    circuit_breaker: CircuitBreakerRepository,
    publisher: RedisPublisher,
):
    """Process a single generation task from the queue."""
    start_time = time.time()

    task_id = task_data["_id"]
    logger.info(f"TaskID: {task_id} | Starting processing.")

    await task_repo.upsert_and_start_task(task_data, WORKER_ID)

    model_name = task_data["model"]
    params = task_data.get("params", {})

    plan_is_unlimited = task_data.get("plan_is_unlimited", False)
    delay_factor = task_data.get("unlimited_delay_factor", 1.0)

    try:
        is_circuit_open = await circuit_breaker.is_open(model_name)

        if is_circuit_open:
            reason = await circuit_breaker.get_last_error(model_name)
            logger.warning(
                f"TaskID: {task_id} | Circuit open ({reason}). "
                f"Using fallback directly.",
            )

            try:
                fallback_result = await _run_fallback(
                    session, task_data, s3_uploader,
                )
                await task_repo.complete_task(task_id, fallback_result)
                logger.info(
                    f"TaskID: {task_id} | "
                    f"Task completed via Fallback (circuit open).",
                )
            except Exception as e:
                logger.error(
                    f"TaskID: {task_id} | "
                    f"Fallback failed while circuit open: {e}",
                )
                await task_repo.fail_task(task_id, "Service unavailable")
                await refund_on_failure(task_data, user_repo)

            return

        else:
            processor = MODEL_PROCESSORS_PRIMARY.get(model_name)

            if not processor:
                raise FatalProviderError(
                    f"No processor found for {model_name}",
                )

            result_data = await processor(
                session=session,
                params=params,
                task_id=task_id,
                s3_uploader=s3_uploader,
            )

        await task_repo.complete_task(task_id, result_data)
        logger.info(f"TaskID: {task_id} | Task completed successfully.")

        try:
            user_id = task_data.get("user_id")
            if user_id:
                user = await user_repo.get_by_id(user_id)

                if user and user.telegram_id:
                    file_url = (
                        result_data.get("video_url")
                        or result_data.get("image_url")
                    )
                    prompt_text = params.get("prompt", "")[:100]

                    if file_url:
                        await publisher.publish_completion(
                            task_id=str(task_id),
                            telegram_id=user.telegram_id,
                            file_url=file_url,
                            prompt=prompt_text,
                        )
        except Exception as pub_e:
            logger.error(
                f"TaskID: {task_id} | "
                f"Redis notification error: {pub_e}",
            )

        if plan_is_unlimited and delay_factor > 1.0:
            original_duration = params.get("duration", 10)
            delay_seconds = (
                original_duration * delay_factor
            ) - original_duration
            final_delay = max(delay_seconds, 180.0)
            logger.info(
                f"TaskID: {task_id} | "
                f"Unlimited delay: {final_delay:.0f}s.",
            )
            await asyncio.sleep(final_delay)
            logger.info(f"TaskID: {task_id} | Delay completed.")

        try:
            created_time = datetime.fromisoformat(task_data["created_at"])
            await analytics_repo.log_and_update_stats_on_completion(
                task_id=task_data["_id"],
                user_id=task_data["user_id"],
                model_slug=task_data["model"],
                cost=task_data.get("cost", 0.0),
                prime_cost=task_data.get("prime_cost", 0.0),
                created_at=created_time,
            )
            logger.info(f"TaskID: {task_id} | Analytics saved.")

        except Exception as analytics_e:
            logger.error(
                f"TaskID: {task_id} | "
                f"Analytics error: {analytics_e}",
                exc_info=True,
            )

    except UserValidationError as e:
        logger.warning(f"TaskID: {task_id} | User Fault: {e}")

        friendly_error = get_user_friendly_error(e)
        await task_repo.fail_task(task_id, friendly_error)
        await refund_on_failure(task_data, user_repo)

    except FatalProviderError as e:
        error_str = str(e).lower()

        soft_fail_keywords = [
            "check the prompt",
            "image parameters",
            "timeout polling",
            "failed to generate",
            "system error",
            "max retry",
            "maximum retries",
        ]

        is_soft_error = any(
            keyword in error_str for keyword in soft_fail_keywords
        )

        if is_soft_error:
            logger.warning(
                f"TaskID: {task_id} | "
                f"Soft Provider Error (circuit not affected): {e}",
            )

            user_msg = (
                "Generation error on the neural network side. "
                "Try changing the prompt or retry later."
            )
            if "timeout" in error_str:
                user_msg = (
                    "Generation took too long. Please try again later."
                )

            await task_repo.fail_task(task_id, user_msg)
            await refund_on_failure(task_data, user_repo)

            return

        logger.error(f"TaskID: {task_id} | Provider Crash: {e}")

        current_tb = traceback.format_exc()
        asyncio.create_task(
            send_error_alert(
                task_data, e, current_tb, time.time() - start_time,
            ),
        )

        await circuit_breaker.trip(model_name, error_msg=str(e))

        logger.info(
            f"TaskID: {task_id} | "
            f"Trying fallback after crash...",
        )

        try:
            fallback_result = await _run_fallback(
                session, task_data, s3_uploader,
            )
            await task_repo.complete_task(task_id, fallback_result)
            logger.info(
                f"TaskID: {task_id} | "
                f"Task saved via Fallback.",
            )

        except Exception as fb_error:
            logger.critical(
                f"TaskID: {task_id} | "
                f"Fallback also failed: {fb_error}",
            )
            await task_repo.fail_task(
                task_id, "Service temporarily unavailable. Try later.",
            )
            await refund_on_failure(task_data, user_repo)

    except Exception as e:
        logger.critical(
            f"TaskID: {task_id} | "
            f"Critical Worker Error: {e}",
            exc_info=True,
        )
        await task_repo.fail_task(task_id, "Internal service error")
        await refund_on_failure(task_data, user_repo)


async def _run_fallback(session, task_data, s3_uploader):
    """Execute the fallback processor for a failed task."""
    task_id = task_data["_id"]
    model_name = task_data["model"]
    params = task_data.get("params", {})

    fallback_processor = MODEL_PROCESSORS_FALLBACK.get(model_name)
    if not fallback_processor:
        raise FatalProviderError(
            f"No fallback processor for {model_name}",
        )

    result_data = await fallback_processor(
        session=session,
        params=params,
        task_id=task_id,
        s3_uploader=s3_uploader,
    )

    return result_data


async def refund_on_failure(task: dict, user_repo: UserRepository):
    """Refund the user's balance after a failed task."""
    user_id_to_refund = task.get("user_id")
    cost_to_refund = task.get("cost")
    task_id = task["_id"]

    if user_id_to_refund and cost_to_refund is not None and cost_to_refund > 0:
        try:
            logger.warning(
                f"TaskID: {task_id} | "
                f"Refunding {cost_to_refund} to user ID: {user_id_to_refund}",
            )
            await user_repo.refund_balance(
                user_id=user_id_to_refund, amount=cost_to_refund,
            )
            logger.info(f"TaskID: {task_id} | Refund completed.")
        except Exception as refund_error:
            logger.critical(
                f"TaskID: {task_id} | "
                f"Refund error! User ID: {user_id_to_refund}, "
                f"Amount: {cost_to_refund}. Error: {refund_error}",
                exc_info=True,
            )
    else:
        logger.error(
            f"TaskID: {task_id} | "
            f"Cannot refund: no user_id or cost.",
        )


async def handle_message(
    message: dict,
    sqs_client: aiobotocore.client.BaseClient,
    http_session: aiohttp.ClientSession,
    s3_client: aiobotocore.client.BaseClient,
    task_repo: TaskRepository,
    analytics_repo: AnalyticsRepository,
    user_repo: UserRepository,
    circuit_breaker_repo: CircuitBreakerRepository,
    publisher: RedisPublisher,
):
    """Handle a single SQS message."""
    task_data = None
    receipt_handle = message["ReceiptHandle"]

    try:
        task_data = json.loads(message["Body"])
        s3_uploader = S3UploaderService(s3_client)
        task_id = task_data.get("_id", "unknown_id")

        logger.info(f"TaskID: {task_id} | Task received from queue.")

        await process_task(
            session=http_session,
            s3_uploader=s3_uploader,
            task_data=task_data,
            task_repo=task_repo,
            analytics_repo=analytics_repo,
            user_repo=user_repo,
            circuit_breaker=circuit_breaker_repo,
            publisher=publisher,
        )

        await sqs_client.delete_message(
            QueueUrl=settings.YANDEX_QUEUE_URL,
            ReceiptHandle=receipt_handle,
        )
        logger.info(
            f"TaskID: {task_id} | "
            f"Task processed and deleted from queue.",
        )

    except Exception as e:
        task_id = task_data["_id"] if task_data else "unknown_id"
        logging.error(
            f"TaskID: {task_id} | "
            f"Critical error. Message will return to queue (or DLQ). "
            f"Error: {e}",
            exc_info=True,
        )


async def run_task_with_semaphore(sem, *args):
    """Run a task handler with semaphore management."""
    try:
        await handle_message(*args)
    finally:
        sem.release()


async def main():
    """Main worker loop: poll SQS and process tasks."""
    task_repo = TaskRepository(async_session_factory)
    analytics_repo = AnalyticsRepository(async_session_factory)
    user_repo = UserRepository(async_session_factory)

    redis_client = get_redis_client()
    circuit_breaker_repo = CircuitBreakerRepository(redis_client)

    publisher = RedisPublisher(redis_client)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

    logger.info(
        f"Worker {WORKER_ID} started. "
        f"Concurrent tasks limit: {MAX_CONCURRENT_TASKS}",
    )

    timeout = ClientTimeout(total=600)
    aws_session = get_session()

    async with aiohttp.ClientSession(timeout=timeout) as http_session:
        async with aws_session.create_client(
            "s3",
            region_name=settings.YANDEX_REGION,
            endpoint_url=settings.YANDEX_STORAGE_ENDPOINT,
            aws_access_key_id=settings.YANDEX_ACCESS_KEY_ID,
            aws_secret_access_key=settings.YANDEX_SECRET_ACCESS_KEY,
        ) as s3_client:

            async with aws_session.create_client(
                "sqs",
                region_name=settings.YANDEX_QUEUE_REGION,
                endpoint_url=settings.YANDEX_QUEUE_ENDPOINT,
                aws_access_key_id=settings.YANDEX_SQS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.YANDEX_SQS_SECRET_ACCESS_KEY,
            ) as sqs_client:

                logger.info(
                    "Waiting for tasks from YMQS. "
                    "Press CTRL+C to exit.",
                )
                background_tasks = set()

                while True:
                    if semaphore.locked():
                        await asyncio.sleep(0.5)
                        continue

                    active_count = len(background_tasks)
                    free_slots = MAX_CONCURRENT_TASKS - active_count

                    if free_slots <= 0:
                        await asyncio.sleep(0.5)
                        continue

                    messages_to_fetch = min(free_slots, 10)

                    try:
                        response = await sqs_client.receive_message(
                            QueueUrl=settings.YANDEX_QUEUE_URL,
                            MaxNumberOfMessages=messages_to_fetch,
                            WaitTimeSeconds=10,
                        )

                        if "Messages" in response:
                            messages = response["Messages"]
                            fetched_count = len(messages)

                            if fetched_count > 0:
                                logger.info(
                                    f"Fetched {fetched_count} tasks. "
                                    f"(Active: {active_count} "
                                    f"+ {fetched_count})",
                                )

                                for message in messages:
                                    await semaphore.acquire()

                                    task = asyncio.create_task(
                                        run_task_with_semaphore(
                                            semaphore,
                                            message,
                                            sqs_client,
                                            http_session,
                                            s3_client,
                                            task_repo,
                                            analytics_repo,
                                            user_repo,
                                            circuit_breaker_repo,
                                            publisher,
                                        ),
                                    )

                                    background_tasks.add(task)
                                    task.add_done_callback(
                                        background_tasks.discard,
                                    )

                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        logger.error(
                            f"SQS loop error: {e}",
                            exc_info=True,
                        )
                        await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info(f"Worker {WORKER_ID} stopped.")
    except Exception as e:
        logging.critical(
            f"Worker {WORKER_ID} crashed: {e}",
            exc_info=True,
        )
