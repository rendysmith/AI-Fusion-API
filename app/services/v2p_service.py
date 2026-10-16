"""Video-to-prompt service using Gemini API for video analysis."""

import os
import time

from google import genai
from google.genai import types
from google.genai.errors import APIError

MODEL_NAME = "gemini-2.5-flash"
MAX_POLLING_TIME_SEC = 120
POLLING_INTERVAL_SEC = 5


def analyze_video_for_prompt_vertex(
    video_path: str, prompt_instruction: str = None, vertex=True,
) -> str:
    """Analyze a video file and generate a detailed prompt using Gemini API."""
    try:
        api_key = os.environ["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"Client initialization error: {e}"

    if not prompt_instruction:
        prompt_instruction = (
            "Analyze this video. Generate a detailed, structured prompt "
            "for Text-to-Video AI models (e.g., Veo or Sora). "
            "Include: 1) Shot type, 2) Lighting and mood, "
            "3) Key objects and actions, "
            "4) Style and quality (e.g., 'Cinematic 4K, high detail'). "
            "Provide only the prompt."
        )

    print(f"Uploading video: {video_path}...")
    video_file = None
    try:
        video_file = client.files.upload(file=video_path)
        print(f"File uploaded: {video_file.name}")

        print("Starting analysis...")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[video_file, prompt_instruction],
            config=types.GenerateContentConfig(temperature=0.2),
        )

        return response.text.strip()

    except Exception as e:
        return f"API error: {e}"

    finally:
        if video_file:
            print(f"Deleting temp file: {video_file.name}")
            client.files.delete(name=video_file.name)


def wait_for_file_active(client: genai.Client, file_name: str):
    """Wait for a video file to become active in Gemini API."""
    start_time = time.time()

    while time.time() - start_time < MAX_POLLING_TIME_SEC:
        try:
            file_obj = client.files.get(name=file_name)
        except APIError as e:
            raise RuntimeError(
                f"Error getting file state {file_name}: {e}",
            )

        if file_obj.state == types.FileState.ACTIVE:
            print(f"File {file_name} active.")
            return
        elif file_obj.state == types.FileState.FAILED:
            raise RuntimeError(f"File {file_name} upload failed.")

        print(
            f"File {file_name} processing ({file_obj.state}). "
            f"Waiting {POLLING_INTERVAL_SEC}s..."
        )
        time.sleep(POLLING_INTERVAL_SEC)

    raise TimeoutError(
        f"File {file_name} did not become active in "
        f"{MAX_POLLING_TIME_SEC} seconds.",
    )


async def analyze_video_for_prompt(
    video_path: str, prompt_instruction: str = None,
) -> str:
    """Analyze a video file and generate a prompt with file activation wait."""
    try:
        api_key = os.environ["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"Client initialization error: {e}"

    if not prompt_instruction:
        prompt_instruction = (
            "Analyze this video. Generate a detailed, structured prompt "
            "for Text-to-Video AI models (e.g., Veo or Sora). "
            "Include: 1) Shot type, 2) Lighting and mood, "
            "3) Key objects and actions, "
            "4) Style and quality (e.g., 'Cinematic 4K, high detail'). "
            "Provide only the prompt."
        )

    print(f"Uploading video: {video_path}...")
    video_file = None
    try:
        video_file = client.files.upload(file=video_path)
        print(f"File uploaded: {video_file.name}")

        wait_for_file_active(client, video_file.name)

        print("Starting analysis...")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[video_file, prompt_instruction],
            config=types.GenerateContentConfig(temperature=0.2),
        )

        return response.text.strip()

    except (RuntimeError, TimeoutError, APIError, Exception) as e:
        return f"API error: {e}"

    finally:
        if video_file:
            try:
                print(f"Deleting temp file: {video_file.name}")
                client.files.delete(name=video_file.name)
            except Exception as e:
                print(f"Failed to delete file {video_file.name}: {e}")
