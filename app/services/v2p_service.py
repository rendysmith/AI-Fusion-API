import os
import time

from google import genai
from google.genai import types
from google.genai.errors import APIError

api_key='AIzaSyBCcpjMbdRQvQHRFQPf1n3BPittZWjAO3E'
def analyze_video_for_prompt_vertex(video_path: str, prompt_instruction: str = None, vertex=True) -> str:
    """
    Анализирует видеофайл с помощью Gemini API и генерирует подробный промпт.

    Args:
        video_path (str): Локальный путь к видеофайлу (например, 'my_video.mp4').
        prompt_instruction (str, optional): Инструкция для Gemini,
            как именно нужно сформировать промпт. Если None, используется стандартная.

    Returns:
        str: Сгенерированный текстовый промпт.
    """

    # 1. Инициализация клиента.
    # Ключ API автоматически берется из переменной окружения GEMINI_API_KEY.
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"Ошибка инициализации клиента. Убедитесь, что GEMINI_API_KEY установлен. Детали: {e}"

    # 2. Определение инструкции для генерации промпта
    if not prompt_instruction:
        prompt_instruction = (
            "Проанализируй это видео. Сгенерируй **подробный, структурированный промпт**, "
            "который можно использовать в Text-to-Video AI моделях (например, Veo или Sora). "
            "Промпт должен включать: "
            "1) Тип кадра (Close-up, Wide shot и т.д.), "
            "2) Освещение и настроение, "
            "3) Ключевые объекты и их действия, "
            "4) Стиль и качество (например, 'Cinematic 4K, high detail'). "
            "Избегай лишних слов и предоставь только сам промпт."
        )

    # 3. Загрузка файла в сервис Gemini (Files API)
    print(f"Загрузка видеофайла: {video_path}...")
    video_file = None
    try:
        # Модель автоматически определяет MIME-тип, но лучше явно использовать video/mp4
        video_file = client.files.upload(file=video_path)
        print(f"Файл успешно загружен. Имя файла в API: {video_file.name}")

        # 4. Отправка запроса с файлом и промптом
        print("Запуск анализа и генерации промпта...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",  # Рекомендуется для мультимодальных задач
            contents=[video_file, prompt_instruction],
            # Для генерации чистого промпта может быть полезно понизить температуру
            config=types.GenerateContentConfig(temperature=0.2)
        )

        return response.text.strip()

    except Exception as e:
        return f"Произошла ошибка во время работы с API: {e}"

    finally:
        # 5. Удаление файла (ОЧЕНЬ ВАЖНО для больших файлов и очистки хранилища)
        if video_file:
            print(f"Удаление временного файла: {video_file.name}")
            client.files.delete(name=video_file.name)


# --- КОНФИГУРАЦИЯ ---
MODEL_NAME = "gemini-2.5-flash"
MAX_POLLING_TIME_SEC = 120  # Максимальное время ожидания активации файла
POLLING_INTERVAL_SEC = 5  # Интервал между проверками


# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ---
def wait_for_file_active(client: genai.Client, file_name: str):
    """Ожидает, пока видеофайл перейдет в состояние ACTIVE, или выбрасывает исключение."""
    start_time = time.time()

    while time.time() - start_time < MAX_POLLING_TIME_SEC:
        try:
            file_obj = client.files.get(name=file_name)
        except APIError as e:
            raise RuntimeError(f"Ошибка при получении состояния файла {file_name}: {e}")

        # Проверка состояния
        if file_obj.state == types.FileState.ACTIVE:
            print(f"Файл {file_name} активен.")
            return
        elif file_obj.state == types.FileState.FAILED:
            raise RuntimeError(f"Загрузка файла {file_name} не удалась. Состояние: FAILED.")

        # Ожидание
        print(f"Файл {file_name} еще обрабатывается ({file_obj.state}). Ожидание {POLLING_INTERVAL_SEC}с...")
        time.sleep(POLLING_INTERVAL_SEC)

    raise TimeoutError(f"Файл {file_name} не перешел в ACTIVE за {MAX_POLLING_TIME_SEC} секунд.")


# --- ОСНОВНАЯ ФУНКЦИЯ ---
async def analyze_video_for_prompt(video_path: str, prompt_instruction: str = None) -> str:
    """
    Анализирует видеофайл с помощью Gemini API SDK, дожидается его активации и генерирует промпт.

    Args:
        video_path (str): Локальный путь к видеофайлу (например, 'my_video.mp4').
        prompt_instruction (str, optional): Инструкция для Gemini.

    Returns:
        str: Сгенерированный текстовый промпт.
    """

    # 1. Инициализация клиента
    try:
        # API ключ берется из переменной окружения GEMINI_API_KEY.
        # Убедитесь, что эта переменная установлена (например, через load_dotenv() или export).
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"Ошибка инициализации клиента. Убедитесь, что GEMINI_API_KEY установлен. Детали: {e}"

    # 2. Определение инструкции
    if not prompt_instruction:
        prompt_instruction = (
            "Проанализируй это видео. Сгенерируй **подробный, структурированный промпт**, "
            "который можно использовать в Text-to-Video AI моделях (например, Veo или Sora). "
            "Промпт должен включать: 1) Тип кадра (Close-up, Wide shot и т.д.), "
            "2) Освещение и настроение, 3) Ключевые объекты и их действия, "
            "4) Стиль и качество (например, 'Cinematic 4K, high detail'). "
            "Избегай лишних слов и предоставь только сам промпт."
        )

    # 3. Загрузка файла в сервис Gemini (Files API)
    print(f"Загрузка видеофайла: {video_path}...")
    video_file = None
    try:
        # Загрузка файла
        video_file = client.files.upload(file=video_path)
        print(f"Файл успешно загружен. Имя файла в API: {video_file.name}")

        # 4. Ожидание активации файла (Критически важный шаг для видео)
        wait_for_file_active(client, video_file.name)

        # 5. Отправка запроса с файлом и промптом
        print("Запуск анализа и генерации промпта...")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[video_file, prompt_instruction],
            config=types.GenerateContentConfig(temperature=0.2)
        )

        return response.text.strip()

    except (RuntimeError, TimeoutError, APIError, Exception) as e:
        # Обработка ошибок загрузки, таймаута или генерации
        return f"Произошла ошибка во время работы с API: {e}"

    finally:
        # 6. Удаление файла
        if video_file:
            try:
                print(f"Удаление временного файла: {video_file.name}")
                client.files.delete(name=video_file.name)
            except Exception as e:
                # На случай, если удаление не удалось
                print(f"Не удалось удалить файл {video_file.name}: {e}")

#--- ПРИМЕР ИСПОЛЬЗОВАНИЯ (Раскомментируйте для проверки) ---
if __name__ == '__main__':
    # Укажите путь к вашему видеофайлу
    VIDEO_FILE_PATH = "/home/andrewsmith/PycharmProjects/Viralix/1d53d110-5dc2-4a6a-aef7-5de38fa86269.mp4"

    # Создайте фиктивный файл, если у вас нет реального для теста
    if not os.path.exists(VIDEO_FILE_PATH):
        print("Создайте реальный видеофайл или замените путь.")
    else:
        generated_prompt = analyze_video_for_prompt(VIDEO_FILE_PATH)
        print("\n--- СГЕНЕРИРОВАННЫЙ ПРОМПТ ---")
        print(generated_prompt)
        print("------------------------------")