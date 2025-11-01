import asyncio
import json
import logging
from datetime import datetime

import aiobotocore.client
import aiohttp
from aiobotocore.session import get_session
from aiohttp import ClientTimeout

from app.database.engine import async_session_factory
from app.database.redis_db import get_redis_client
from app.database.repositories.analytics_repository import AnalyticsRepository
from app.database.repositories.circuit_breaker_repository import CircuitBreakerRepository
from app.database.repositories.task_repository import TaskRepository
from app.database.repositories.user_repository import UserRepository
from app.services.providers import kie_ai_provider, openai_provider
from app.services.s3_uploader import S3UploaderService
from app.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [WORKER] - %(message)s'
)

WORKER_ID = settings.WORKER_ID
MAX_CONCURRENT_TASKS = settings.WORKER_MAX_CONCURRENT_TASKS


logger = logging.getLogger(__name__)

MODEL_PROCESSORS_PRIMARY = {
    'sora-2': kie_ai_provider.generate_sora_kie_ai_video,
    'veo-3-quality': kie_ai_provider.generate_veo_kie_ai_video,
    'veo-3-fast': kie_ai_provider.generate_veo_kie_ai_video
}


MODEL_PROCESSORS_FALLBACK = {
    'sora-2': openai_provider.generate_sora_openai_video,
}


async def process_task(session: aiohttp.ClientSession,
                       task_data: dict,
                       task_repo: TaskRepository,
                       analytics_repo: AnalyticsRepository,
                       user_repo: UserRepository,
                       s3_uploader: S3UploaderService,
                       circuit_breaker: CircuitBreakerRepository
                       ):
    task_id = task_data["_id"]
    logger.info(f"TaskID: {task_id} | Начинаю обработку.")

    await task_repo.upsert_and_start_task(task_data, WORKER_ID)


    model_name = task_data["model"]
    params = task_data.get("params", {})

    try:

        is_circuit_open = await circuit_breaker.is_open(model_name)

        if is_circuit_open:

            logger.warning(f"TaskID: {task_id} | Цепь разорвана. Использую Fallback (OpenAI).")
            processor = MODEL_PROCESSORS_FALLBACK.get(model_name)
            if not processor:
                raise ValueError(f"Не найден Fallback-обработчик для {model_name}")

            result_data = await processor(
                session=session,
                params=params,
                task_id=task_id,
                s3_uploader=s3_uploader
            )

        else:

            processor = MODEL_PROCESSORS_PRIMARY.get(model_name)
            if not processor:
                raise ValueError(f"Не найден Primary-обработчик для {model_name}")

            try:

                result_data = await processor(
                    session=session,
                    params=params,
                    task_id=task_id,
                    s3_uploader=s3_uploader,
                    circuit_breaker=circuit_breaker,
                    model_name=model_name
                )
            except Exception as error:

                logger.warning(f"TaskID: {task_id} | Primary (Kie AI) упал. Пробую Fallback (OpenAI)...")


                fallback_processor = MODEL_PROCESSORS_FALLBACK.get(model_name)
                if not fallback_processor:
                    raise ValueError(f"Kie AI упал, но Fallback-обработчик не найден!")

                result_data = await fallback_processor(
                    session=session,
                    params=params,
                    task_id=task_id,
                    s3_uploader=s3_uploader
                )

        await task_repo.complete_task(task_id, result_data)
        logger.info(f"TaskID: {task_id} | Задача успешно завершена.")


        try:
            created_time = datetime.fromisoformat(task_data["created_at"])
            await analytics_repo.log_and_update_stats_on_completion(
                task_id=task_data["_id"],
                user_id=task_data["user_id"],
                model_name=task_data["model"],
                cost=task_data.get("cost", 0.0),
                prime_cost=task_data.get("prime_cost", 0.0),
                created_at=created_time
            )
            logger.info(f"TaskID: {task_id} | Аналитика сохранена.")

        except Exception as analytics_e:
            logger.error(f"TaskID: {task_id} | ОШИБКА ЗАПИСИ В АНАЛИТИКУ: {analytics_e}", exc_info=True)

    except Exception as e:
        logger.error(f"TaskID: {task_id} | Ошибка при обработке: {e}", exc_info=True)
        await task_repo.fail_task(task_id, str(e))
        await refund_on_failure(task_data, user_repo)


async def refund_on_failure(task: dict, user_repo: UserRepository):

    user_id_to_refund = task.get("user_id")
    cost_to_refund = task.get("cost")
    task_id = task["_id"]

    if user_id_to_refund and cost_to_refund is not None and cost_to_refund > 0:
        try:
            logger.warning(f"TaskID: {task_id} | Возврат {cost_to_refund} пользователю ID: {user_id_to_refund}")
            await user_repo.refund_balance(user_id=user_id_to_refund, amount=cost_to_refund)
            logger.info(f"TaskID: {task_id} | Возврат выполнен.")
        except Exception as refund_error:
            logger.critical(
                f"TaskID: {task_id} | Ошибка возврата! User ID: {user_id_to_refund}, Сумма: {cost_to_refund}. Ошибка: {refund_error}",
                exc_info=True)
    else:
        logger.error(f"TaskID: {task_id} | Невозможно выполнить возврат: нет user_id или cost.")


async def handle_message(
    message: dict,
    sqs_client: aiobotocore.client.BaseClient,
    http_session: aiohttp.ClientSession,
    s3_client: aiobotocore.client.BaseClient,
    task_repo: TaskRepository,
    analytics_repo: AnalyticsRepository,
    user_repo: UserRepository,
    circuit_breaker_repo: CircuitBreakerRepository
):

    task_data = None
    receipt_handle = message['ReceiptHandle']

    try:
        task_data = json.loads(message['Body'])

        s3_uploader = S3UploaderService(s3_client)

        task_id = task_data.get("_id", "unknown_id")
        logger.info(f"TaskID: {task_id} | Задача получена из очереди.")

        await process_task(
            session=http_session,
            s3_uploader=s3_uploader,
            task_data=task_data,
            task_repo=task_repo,
            analytics_repo=analytics_repo,
            user_repo=user_repo,
            circuit_breaker=circuit_breaker_repo
        )


        await sqs_client.delete_message(
            QueueUrl=settings.YANDEX_QUEUE_URL,
            ReceiptHandle=receipt_handle
        )
        logger.info(f"TaskID: {task_id} | Задача обработана и удалена из очереди.")

    except Exception as e:
        task_id = task_data['_id'] if task_data else "unknown_id"
        logging.error(
            f"TaskID: {task_id} | КРИТИЧЕСКАЯ ОШИБКА. "
            f"Сообщение НЕ будет удалено и вернется в очередь (или уйдет в DLQ). Ошибка: {e}",
            exc_info=True
        )


async def main():
    task_repo = TaskRepository(async_session_factory)
    analytics_repo = AnalyticsRepository(async_session_factory)
    user_repo = UserRepository(async_session_factory)

    redis_client = get_redis_client()
    circuit_breaker_repo = CircuitBreakerRepository(redis_client)

    logger.info(f"Воркер {WORKER_ID} запущен. Максимум одновременных задач: {MAX_CONCURRENT_TASKS}")

    timeout = ClientTimeout(total=600)
    aws_session = get_session()


    async with aiohttp.ClientSession(timeout=timeout) as http_session:
        async with aws_session.create_client(
                's3',
                region_name=settings.YANDEX_REGION,
                endpoint_url=settings.YANDEX_STORAGE_ENDPOINT,
                aws_access_key_id=settings.YANDEX_ACCESS_KEY_ID,
                aws_secret_access_key=settings.YANDEX_SECRET_ACCESS_KEY
        ) as s3_client:

            async with aws_session.create_client(
                'sqs',
                region_name=settings.YANDEX_QUEUE_REGION,
                endpoint_url=settings.YANDEX_QUEUE_ENDPOINT,
                aws_access_key_id=settings.YANDEX_SQS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.YANDEX_SQS_SECRET_ACCESS_KEY
            ) as sqs_client:

                logger.info(" [*] Ожидание задач из YMQS. Для выхода нажмите CTRL+C")

                while True:
                    try:

                        response = await sqs_client.receive_message(
                            QueueUrl=settings.YANDEX_QUEUE_URL,
                            MaxNumberOfMessages=MAX_CONCURRENT_TASKS,
                            WaitTimeSeconds=20
                        )

                        if 'Messages' in response:
                            messages = response['Messages']
                            logger.info(f"Получено {len(messages)} задач.")


                            tasks = []
                            for message in messages:
                                tasks.append(
                                    handle_message(
                                        message=message,
                                        sqs_client=sqs_client,
                                        http_session=http_session,
                                        s3_client=s3_client,
                                        task_repo=task_repo,
                                        analytics_repo=analytics_repo,
                                        user_repo=user_repo,
                                        circuit_breaker_repo=circuit_breaker_repo
                                    )
                                )
                            await asyncio.gather(*tasks)

                        else:
                            pass

                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        logger.error(f"Ошибка в цикле SQS: {e}", exc_info=True)
                        await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info(f"Воркер {WORKER_ID} остановлен.")
    except Exception as e:
        logging.critical(f"Воркер {WORKER_ID} упал с критической ошибкой: {e}", exc_info=True)