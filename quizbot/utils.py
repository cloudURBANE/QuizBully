import os
import logging
import asyncio
import random
import re
from typing import Callable, Dict, List, Tuple

try:
    from openai import AsyncOpenAI
except Exception:  # pragma: no cover - openai may be unavailable during tests
    AsyncOpenAI = None
from typing import Any

# OpenAI API client used by make_completion_request_with_retry
client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY', '')) if AsyncOpenAI else None

async def get_dm_channel_for_user(user: Any) -> Any:
    """Fetch or create a DM channel for the given user."""
    import discord
    dm_channel = user.dm_channel

    if not dm_channel:
        logging.info(f"No DM channel found for user ID {user.id}.")
        logging.info(f"Attempting to create a new DM channel for user ID {user.id}...")
        try:
            dm_channel = await user.create_dm()
            if dm_channel:
                logging.info(f"DM channel successfully created for user ID {user.id}.")
            else:
                logging.warning(
                    f"Created DM channel object for user ID {user.id} is None. This is unexpected."
                )
        except Exception as e:
            logging.error(f"Exception encountered while creating DM for user ID {user.id}: {e}")
    else:
        logging.info(f"Located existing DM channel for user ID {user.id}.")

    return dm_channel


def extract_questions_from_response(response: str) -> List[Dict]:
    """Extract questions, options, answers and hints from the given response string."""
    pattern = r"'question':\s*'([^']+)',\s*'options':\s*\[([^\]]+)\],\s*'answer':\s*(\d+),\s*'hint':\s*'([^']+)'"
    matches = re.findall(pattern, response)

    if not matches:
        # Log the response for debugging if the regular expression does not match
        print("No matches found. Response content:", response)
        return []

    questions = []
    for match in matches:
        question_text, options_string, correct_answer_index, hint_text = match
        options_list = [option.strip().strip("'") for option in options_string.split(",")]
        questions.append({
            "question": question_text,
            "options": options_list,
            "answer": int(correct_answer_index),
            "hint": hint_text,
        })

    return questions


def retry_with_exponential_backoff(
    function_to_retry: Callable,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    include_jitter: bool = True,
    maximum_retries: int = 10,
    error_types: Tuple[Exception] = (Exception,),
):
    """A decorator that retries the execution of a coroutine with exponential backoff."""

    async def wrapper(*arguments, **keyword_arguments):
        retry_count = 0
        delay = initial_delay
        while True:
            try:
                return await function_to_retry(*arguments, **keyword_arguments)
            except error_types as error_instance:
                retry_count += 1
                if retry_count > maximum_retries:
                    raise Exception(
                        f"Maximum number of retries ({maximum_retries}) exceeded."
                    ) from error_instance
                delay *= exponential_base * (1 + include_jitter * random.random())
                await asyncio.sleep(delay)
            except Exception as unexpected_error:
                raise unexpected_error

    return wrapper


@retry_with_exponential_backoff
async def make_completion_request_with_retry(**keyword_arguments):
    """Makes an OpenAI completion request using retry logic with exponential backoff."""
    completion_response = await client.chat.completions.create(
        model=keyword_arguments["model"],
        messages=keyword_arguments["messages"],
    )
    return completion_response
