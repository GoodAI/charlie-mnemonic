import asyncio
import importlib
import inspect
import json
import ast
import os
import re
import sys
import time
import uuid
import requests
from tenacity import retry, stop_after_attempt, wait_fixed
import aiohttp
from termcolor import colored
import memory as _memory
import openai
from fastapi import HTTPException, BackgroundTasks, UploadFile
from elevenlabs import generate, play, set_api_key
from werkzeug.utils import secure_filename
from pathlib import Path
from config import api_keys, default_params, fakedata
from database import Database
import tiktoken
from pydub import audio_segment
import logs
import prompts
from unidecode import unidecode
import llmcalls

from simple_utils import get_root

logger = logs.Log("utils", "utils.log").get_logger()

# Parameters for OpenAI
max_responses = 1
COT_RETRIES = {}
stopPressed = {}


class MessageSender:
    """This class contains functions to send messages to the user"""

    @staticmethod
    async def send_debug(message, number, color, username):
        """Send a debug message to the user and print it to the console with a color"""
        from importlib import import_module

        routes = import_module("routes")
        if number <= 2:
            message = f"{'-' * 50}\n{message}\n{'-' * 50}"
            new_message = {"debug": number, "color": color, "message": message}
        else:
            new_message = {"message": message}

        await routes.send_debug_message(username, json.dumps(new_message))

    @staticmethod
    async def send_message(message, color, username):
        """Send a message to the user and print it to the console with a color"""
        from importlib import import_module

        routes = import_module("routes")
        await routes.send_debug_message(username, json.dumps(message))

    @staticmethod
    async def update_token_usage(response, username, brain=False, elapsed=0):
        """Update the token usage in the database"""
        try:
            with Database() as db:
                result = db.update_token_usage(
                    username,
                    total_tokens_used=response["usage"]["total_tokens"],
                    prompt_tokens=response["usage"]["prompt_tokens"],
                    completion_tokens=response["usage"]["completion_tokens"],
                )
                if result is not None:
                    await MessageSender.send_debug(
                        f"Last message: Prompt tokens: {response['usage']['prompt_tokens']}, Completion tokens: {response['usage']['completion_tokens']}\nTotal tokens used: {result[0]}, Prompt tokens: {result[1]}, Completion tokens: {result[2]}",
                        2,
                        "red",
                        username,
                    )
                    # cost based on these formulas prompt: $0.03 / 1K tokens completion: $0.06 / 1K tokens
                    prompt_cost = round(
                        response["usage"]["prompt_tokens"] * 0.03 / 1000, 5
                    )
                    completion_cost = round(
                        response["usage"]["completion_tokens"] * 0.06 / 1000, 5
                    )
                    this_message_total_cost = round(prompt_cost + completion_cost, 5)

                    total_prompt_cost = round(result[1] * 0.03 / 1000, 5)
                    total_completion_cost = round(result[2] * 0.06 / 1000, 5)
                    total_cost = round(total_prompt_cost + total_completion_cost, 5)
                    await MessageSender.send_message(
                        {
                            "usage": {
                                "total_tokens": result[0],
                                "total_cost": total_cost,
                            }
                        },
                        "red",
                        username,
                    )

                daily_stats = db.get_daily_stats(username)
                if daily_stats is not None:
                    current_spending_count = daily_stats["spending_count"] or 0
                else:
                    current_spending_count = 0
                spending_count = current_spending_count + this_message_total_cost

                await MessageSender.send_message(
                    {"daily_usage": {"daily_cost": spending_count}}, "red", username
                )
                # update the daily_stats table
                if brain:
                    db.update_daily_stats_token_usage(
                        username,
                        brain_tokens=response["usage"]["total_tokens"],
                        spending_count=this_message_total_cost,
                    )
                else:
                    db.update_daily_stats_token_usage(
                        username,
                        prompt_tokens=response["usage"]["prompt_tokens"],
                        generation_tokens=response["usage"]["completion_tokens"],
                        spending_count=this_message_total_cost,
                    )
                current_stats_spending_count = (
                    db.get_statistic(username)["total_spending_count"] or 0
                )
                spending_count = round(
                    current_stats_spending_count + this_message_total_cost, 5
                )
                # update the statistics table
                db.update_statistic(username, total_spending_count=spending_count)
                # update the elapsed time
                # get the total response time and response count from the database
                stats = db.get_daily_stats(username)
                if stats is not None:
                    total_response_time = stats["total_response_time"] or 0
                    response_count = stats["response_count"] or 0
                else:
                    total_response_time = 0
                    response_count = 0
                # update the total response time and response count
                total_response_time += elapsed
                response_count += 1

                # calculate the new average response time
                average_response_time = total_response_time / response_count

                db.replace_daily_stats_token_usage(
                    username,
                    total_response_time=total_response_time,
                    average_response_time=average_response_time,
                    response_count=response_count,
                )
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
            await MessageSender.send_message(
                {"error": "An error occurred: " + str(e)}, "red", username
            )


class AddonManager:
    """This class contains functions to load addons"""

    @staticmethod
    async def load_addons(username, users_dir):
        default_settings = {
            "addons": {},
            "audio": {"voice_input": True, "voice_output": True},
            "avatar": {"avatar": False},
            "language": {"language": "en"},
            "system_prompt": {"system_prompt": "Not implemented yet"},
            "cot_enabled": {"cot_enabled": False},
            "verbose": {"verbose": False},
            "memory": {
                "functions": 500,
                "ltm1": 1000,
                "ltm2": 1000,
                "episodic": 300,
                "recent": 700,
                "notes": 1000,
                "input": 1000,
                "output": 1000,
                "max_tokens": 6500,
                "min_tokens": 500,
            },
        }

        name = unidecode(username)
        # replace spaces and @ with underscores
        name = name.replace(" ", "_")
        name = name.replace("@", "_")
        name = name.replace(".", "_")
        # lowercase the name
        data_username = name.lower()

        function_dict = {}
        function_metadata = []
        module_timestamps = {}

        data_dir = os.path.join(users_dir, data_username, "data")
        # create the users directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        user_path = os.path.join(users_dir, username)
        settings_file = os.path.join(user_path, "settings.json")

        if not os.path.exists(user_path):
            os.makedirs(user_path)

        if not os.path.exists(settings_file):
            with open(settings_file, "w") as f:
                json.dump(default_settings, f)

        # Check if settings file exists and is not empty
        if os.path.exists(settings_file) and os.path.getsize(settings_file) > 0:
            try:
                with open(settings_file, "r") as f:
                    settings = json.load(f)
            except json.JSONDecodeError:
                settings = default_settings
        else:
            settings = default_settings

        # Validate and correct the settings
        for key, default_value in default_settings.items():
            # If the key is not in the settings or the type is not the same as the default value, set it to the default value
            if key not in settings or type(settings[key]) != type(default_value):
                settings[key] = default_value
            # If the key is a dict, validate and correct the sub keys
            elif isinstance(default_value, dict):
                for sub_key, sub_default_value in default_value.items():
                    if sub_key not in settings[key] or type(
                        settings[key][sub_key]
                    ) != type(sub_default_value):
                        settings[key][sub_key] = sub_default_value

        # Save the settings
        with open(settings_file, "w") as f:
            json.dump(settings, f)

        # Delete addons that don't exist anymore
        for addon in list(settings["addons"].keys()):
            if not os.path.exists(os.path.join("addons", f"{addon}.py")):
                del settings["addons"][addon]

        # Load addons
        for filename in os.listdir("addons"):
            if filename.endswith(".py"):
                addon_name = filename[:-3]
                if addon_name not in settings["addons"]:
                    settings["addons"][addon_name] = False

                # Only load the addon if it is enabled
                if settings["addons"].get(addon_name, True):
                    file_path = os.path.join("addons", filename)
                    spec = importlib.util.spec_from_file_location(
                        filename[:-3], file_path
                    )
                    module = importlib.util.module_from_spec(spec)

                    # Check if the module has been modified since it was last imported
                    file_timestamp = os.path.getmtime(file_path)
                    if (
                        filename in module_timestamps
                        and file_timestamp > module_timestamps[filename]
                    ):
                        module = importlib.reload(module)
                    module_timestamps[filename] = file_timestamp

                    spec.loader.exec_module(module)

                    # Check for the function in the module and add it with the required structure
                    if module.__name__ in module.__dict__:
                        function_detail = {
                            "name": module.__name__,
                            "description": getattr(
                                module, "description", "No description"
                            ),
                            "parameters": getattr(
                                module, "parameters", "No parameters"
                            ),
                        }
                        # Wrap the function detail in the required structure
                        tool_metadata = {
                            "type": "function",
                            "function": function_detail,
                        }
                        function_metadata.append(tool_metadata)
                    else:
                        await MessageSender.send_debug(
                            f"Module {module.__name__} does not have a function with the same name.",
                            2,
                            "red",
                            username,
                        )

        with open(settings_file, "w") as f:
            json.dump(settings, f)

        if not function_metadata:
            function_metadata = fakedata

        return function_dict, function_metadata


class OpenAIResponser:
    """This class contains functions to get responses from OpenAI"""

    error503 = "OpenAI server is busy, try again later"

    def __init__(self, openai_model, temperature, max_tokens, max_responses, username):
        self.openai_model = openai_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_responses = max_responses
        self.username = username

        async def log_response_headers(
            session, trace_config_ctx, params: aiohttp.TraceRequestEndParams
        ):
            # Extract the headers
            tokens_used = params.response.headers.get(
                "x-ratelimit-remaining-tokens", 40000
            )
            requests_remaining = params.response.headers.get(
                "x-ratelimit-remaining-requests", 200
            )
            tokens_limit = params.response.headers.get(
                "x-ratelimit-limit-tokens", 40000
            )
            requests_limit = params.response.headers.get(
                "x-ratelimit-limit-requests", 200
            )

            # Calculate the usage
            tokens_usage = (1 - int(tokens_used) / int(tokens_limit)) * 100
            requests_usage = (1 - int(requests_remaining) / int(requests_limit)) * 100

            # Print the normal usage
            # logger.debug(f'OpenAI tokens used: {tokens_used} ({tokens_usage:.2f}% of limit)')
            # logger.debug(f'OpenAI requests remaining: {requests_remaining} ({requests_usage:.2f}% of limit)')
            # await MessageSender.send_message({"type": "rate_limit", "content": {"message": f"tokens_usage: " + str(round(tokens_usage, 2)) + "%, requests_usage: " + str(round(requests_usage, 2)) + "%"}}, "blue", self.username)

            # Print the warning if above 50% of the rate limit
            if tokens_usage > 20 or requests_usage > 20:
                logger.warning(
                    "WARNING: You have used more than 20% of your rate limit: tokens_usage: "
                    + str(tokens_usage)
                    + "%, requests_usage: "
                    + str(requests_usage)
                    + "%"
                )
                await MessageSender.send_message(
                    {
                        "type": "rate_limit",
                        "content": {
                            "warning": "WARNING: You have used more than 20% of your rate limit: tokens_usage: "
                            + str(tokens_usage)
                            + "%, requests_usage: "
                            + str(requests_usage)
                            + "%"
                        },
                    },
                    "blue",
                    self.username,
                )

            # Print the error if above rate limit
            if tokens_usage >= 100 or requests_usage >= 100:
                logger.error(
                    "ERROR: You have exceeded your rate limit: tokens_usage: "
                    + str(tokens_usage)
                    + "%, requests_usage: "
                    + str(requests_usage)
                    + "%"
                )
                await MessageSender.send_message(
                    {
                        "type": "rate_limit",
                        "content": {
                            "error": "ERROR: You have exceeded your rate limit: tokens_usage: "
                            + str(tokens_usage)
                            + "%, requests_usage: "
                            + str(requests_usage)
                            + "%"
                        },
                    },
                    "blue",
                    self.username,
                )

        self.trace_config = aiohttp.TraceConfig()
        self.trace_config.on_request_end.append(log_response_headers)

    @staticmethod
    def user_pressed_stop(username):
        global stopPressed
        stopPressed[username] = True

    @staticmethod
    def reset_stop_stream(username):
        global stopPressed
        stopPressed[username] = False

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
    async def get_response(
        self,
        username,
        messages,
        stream=False,
        function_metadata=None,
        function_call="auto",
        chat_id=None,
    ):
        if function_metadata is None:
            function_metadata = [
                {
                    "name": "none",
                    "description": "you have no available functions",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                }
            ]

        max_retries = 5
        timeout = 180.0  # timeout in seconds
        now = time.time()

        session = aiohttp.ClientSession(trace_configs=[self.trace_config])
        openai.aiosession.set(session)

        for i in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    openai.ChatCompletion.acreate(
                        model=self.openai_model,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        n=self.max_responses,
                        top_p=1,
                        frequency_penalty=0,
                        presence_penalty=0,
                        messages=messages,
                        stream=stream,
                        functions=function_metadata,
                        function_call=function_call,
                    ),
                    timeout=timeout,
                )

            except asyncio.TimeoutError:
                logger.error(
                    f"Request timed out to OpenAI servers, retrying {i+1}/{max_retries}"
                )
                await MessageSender.send_message(
                    {
                        "error": f"Request timed out to OpenAI servers, retrying {i+1}/{max_retries}"
                    },
                    "red",
                    username,
                )
            except Exception as e:
                logger.error(
                    f"Error from openAI: {str(e)}, retrying {i+1}/{max_retries}"
                )
                await MessageSender.send_message(
                    {
                        "error": f"Error from openAI: {str(e)}, retrying {i+1}/{max_retries}"
                    },
                    "red",
                    username,
                )

        elapsed = time.time() - now
        if stream:
            func_call = {
                "name": None,
                "arguments": "",
            }
            collected_messages = []
            # check if the user pressed stop to stop the stream
            async for chunk in response:
                # check if the user pressed stop to stop the stream
                global stopPressed
                stopStream = False
                if username in stopPressed:
                    stopStream = stopPressed[username]
                if stopStream:
                    await session.close()
                    stopStream = False
                    stopPressed[username] = False
                    await MessageSender.send_message(
                        {"cancel_message": True, "chat_id": chat_id}, "blue", username
                    )
                    await session.close()
                    break
                delta = chunk["choices"][0]["delta"]
                if "content" in chunk["choices"][0]["delta"]:
                    chunk_message = chunk["choices"][0]["delta"]["content"]
                    collected_messages.append(chunk_message)
                    await MessageSender.send_message(
                        {"chunk_message": chunk_message, "chat_id": chat_id},
                        "blue",
                        username,
                    )
                if chunk["choices"][0]["finish_reason"] == "stop":
                    await MessageSender.send_message(
                        {"stop_message": True, "chat_id": chat_id}, "blue", username
                    )
                    await session.close()
                    break
                if "function_call" in delta:
                    if "name" in delta.function_call:
                        func_call["name"] = delta.function_call["name"]
                    if "arguments" in delta.function_call:
                        func_call["arguments"] += delta.function_call["arguments"]
                if chunk.choices[0].finish_reason == "function_call":
                    # convert the function call to an openai function call structure
                    full_response = {
                        "choices": [
                            {
                                "message": {
                                    "function_call": {
                                        "name": func_call["name"],
                                        "arguments": func_call["arguments"],
                                    }
                                }
                            }
                        ],
                    }
                    await session.close()
                    return full_response
                if not delta.get("content", None):
                    continue
                response = "".join(collected_messages)
        else:
            await MessageSender.update_token_usage(
                response, username, False, elapsed=elapsed
            )
        await session.close()
        return response


class AudioProcessor:
    """This class contains functions to process audio"""

    @staticmethod
    async def upload_audio(user_dir, username, audio_file: UploadFile):
        # save the file to the user's folder
        userdir = os.path.join(user_dir, username)
        filename = secure_filename(audio_file.filename)
        audio_dir = os.path.join(userdir, "audio")
        if not os.path.exists(audio_dir):
            os.makedirs(audio_dir)
        filepath = os.path.join(audio_dir, filename)
        with open(filepath, "wb") as f:
            f.write(audio_file.file.read())

        # check the audio for voice
        if not AudioProcessor.check_voice(filepath):
            return {"transcription": ""}

        # get the user settings language
        settings_file = os.path.join(userdir, "settings.json")
        with open(settings_file, "r") as f:
            settings = json.load(f)
        language = settings.get("language", {}).get("language", "en")

        # if no language is set, default to english
        if language is None:
            language = "en"

        # use the saved file path to transcribe the audio
        transcription = await AudioProcessor.transcribe_audio(filepath, language)
        return {"transcription": transcription}

    @staticmethod
    def check_voice(filepath):
        audio = audio_segment.AudioSegment.from_file(filepath)
        if (
            audio.dBFS < -40
        ):  #  Decrease for quieter voices (-50), increase for louder voices (-20)
            logger.info("No voice detected, dBFS: " + str(audio.dBFS))
            return False
        return True

    @staticmethod
    async def transcribe_audio(audio_file_path, language):
        with open(audio_file_path, "rb") as audio_file:
            transcription = await openai.Audio.atranscribe(
                model="whisper-1",
                file=audio_file,
                language=language,
                api_key=api_keys["openai"],
            )
        return transcription["text"]

    @staticmethod
    async def generate_audio(text, username, users_dir):
        # Make sure the directory exists
        audio_dir = os.path.join(users_dir, username, "audio")
        Path(audio_dir).mkdir(parents=True, exist_ok=True)
        audio_path = os.path.join(audio_dir, f"{uuid.uuid4()}.mp3")

        # Strip code blocks from text
        text = MessageParser.strip_code_blocks(text)

        # Retry mechanism for audio generation
        max_retries = 3
        for attempt in range(max_retries):
            try:
                audio = generate(
                    text=text,
                    voice="ThT5KcBeYPX3keUQqHPh",
                    model="eleven_multilingual_v1",
                )
                with open(audio_path, "wb") as f:
                    f.write(audio)
                return audio_path, audio
            except requests.exceptions.ChunkedEncodingError as e:
                if attempt < max_retries - 1:
                    continue
                else:
                    raise e
            except Exception as e:
                # Log other exceptions and re-raise
                logger.error(e)
                raise


class BrainProcessor:
    """This class contains functions to process the brain"""

    @staticmethod
    async def load_brain(username, users_dir):
        user_dir = os.path.join(users_dir, username)
        brain_path = os.path.join(user_dir, "kw_brain.txt")
        Path(user_dir).mkdir(parents=True, exist_ok=True)
        if not os.path.exists(brain_path):
            with open(brain_path, "w") as f:
                start_brain_path = os.path.join("data", "kw_brain_start.txt")
                with open(start_brain_path, "r") as f2:
                    f.write(f2.read())
        with open(brain_path, "r") as f:
            return f.read()

    @staticmethod
    def write_brain(brain, username, users_dir):
        user_dir = os.path.join(users_dir, username)
        brain_path = os.path.join(user_dir, "kw_brain.txt")
        with open(brain_path, "w") as f:
            f.write(brain)

    @staticmethod
    async def delete_recent_messages(user):
        print(f"Deleting recent messages for {user} !!!WIP!!!")


class MessageParser:
    """This class contains functions to parse messages and generate responses"""

    @staticmethod
    def strip_code_blocks(text):
        # Function to strip code blocks from text
        code_blocks = []
        code_block_start = 0
        code_block_end = 0
        for i in range(len(text)):
            if text[i : i + 3] == "```":
                if code_block_start == 0:
                    code_block_start = i
                else:
                    code_block_end = i
                    code_blocks.append(text[code_block_start : code_block_end + 3])
                    code_block_start = 0
                    code_block_end = 0
        for code_block in code_blocks:
            text = text.replace(code_block, "")
        return text

    @staticmethod
    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
    async def get_image_description(image_url, prompt, file_name):
        """Get the description of an image using a LLAVA 1.5 API"""
        import replicate

        output = replicate.run(
            "yorickvp/llava-13b:6bc1c7bb0d2a34e413301fee8f7cc728d2d4e75bfab186aa995f63292bda92fc",
            input={"image": open(image_url, "rb"), "prompt": prompt},
        )
        # The yorickvp/llava-13b model can stream output as it's running.
        # The predict method returns an iterator, and you can iterate over that output.
        full_response = "".join([item for item in output])
        return prompts.image_description.format(prompt, file_name, full_response)

    @staticmethod
    async def get_recent_messages(username, chat_id):
        memory = _memory.MemoryManager()
        recent_messages = await memory.get_most_recent_messages(
            "active_brain", username, chat_id=chat_id
        )

        return [
            {
                "document": message["document"],
                "metadata": message["metadata"],
                "id": message["id"],
            }
            for message in recent_messages
        ]

    @staticmethod
    def get_message(type, parameters):
        with Database() as db:
            display_name = db.get_display_name(parameters["username"])[0]
        """Parse the message based on the type and parameters"""
        if type == "start_message":
            return prompts.start_message.format(
                display_name, parameters["memory"], parameters["instruction_string"]
            )
        elif type == "keyword_generation":
            return prompts.keyword_generation.format(
                display_name,
                parameters["memory"],
                parameters["last_messages_string"],
                parameters["message"],
            )

    @staticmethod
    async def convert_function_call_arguments(arguments, username, tryAgain=True):
        try:
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
        except json.JSONDecodeError:
            try:
                arguments = ast.literal_eval(arguments)
            except (ValueError, SyntaxError):
                try:
                    arguments = re.sub(r"```.*?\n", "", arguments)
                    arguments = re.sub(r"```", "", arguments)
                    arguments = re.sub(r"\.\.\.|\…", "", arguments)
                    arguments = re.sub(r"[\r\n]+", "", arguments)
                    arguments = re.sub(r"[^\x00-\x7F]+", "", arguments)
                    arguments = json.loads(arguments)
                except Exception:
                    try:
                        arguments = eval(arguments)
                    except Exception:
                        if tryAgain:
                            # ask openai to re-generate the message
                            message = prompts.invalid_json.format(arguments)
                            logger.exception(
                                f"Invalid json: {arguments}, username: {username}, trying to re-generate the message..."
                            )
                            messages = [
                                {
                                    "role": "system",
                                    "content": prompts.invalid_json_system_prompt,
                                },
                                {"role": "user", "content": f"{message}"},
                            ]
                            # openai_response = OpenAIResponser(
                            #     openai_model, temperature, 1000, max_responses, username
                            # )
                            # response = await openai_response.get_response(
                            #     username,
                            #     messages,
                            #     stream=False,
                            #     function_metadata=None,
                            #     function_call="auto",
                            # )
                            response = None
                            openai_response = llmcalls.OpenAIResponser(
                                api_keys["openai"], default_params
                            )
                            async for resp in openai_response.get_response(
                                username,
                                messages,
                                stream=False,
                                function_metadata=fakedata,
                                function_call="auto",
                            ):
                                response = resp
                            await MessageParser.convert_function_call_arguments(
                                response,
                                username,
                                False,
                            )
                        else:
                            logger.exception(
                                f"Invalid json: {arguments}, username: {username}"
                            )
                            return None
        return arguments if isinstance(arguments, dict) else {}

    @staticmethod
    def handle_function_response(function, args):
        try:
            function_response = function(**args)
        except Exception as e:
            logger.error(f"Error: {e}")
            function_response = {"content": "error: " + str(e)}
        return function_response

    @staticmethod
    async def ahandle_function_response(function, args):
        try:
            function_response = await function(**args)
        except Exception as e:
            logger.error(f"Error: {e}")
            function_response = {"content": "error: " + str(e)}
        return function_response

    @staticmethod
    async def process_function_call(
        function_call_name,
        function_call_arguments,
        function_dict,
        function_metadata,
        message,
        og_message,
        username,
        exception_handler,
        merge=True,
        users_dir="users/",
        steps_string="",
        full_response=None,
        chat_id=None,
    ):
        converted_function_call_arguments = (
            await MessageParser.convert_function_call_arguments(
                function_call_arguments, username
            )
        )
        # add the username to the arguments
        if converted_function_call_arguments is not None:
            converted_function_call_arguments["username"] = username
        else:
            logger.error(
                "converted_function_call_arguments is None: "
                + str(function_call_arguments)
            )
            return {
                "content": "error: converted_function_call_arguments is None: "
                + str(function_call_arguments)
            }
        new_message = {
            "functioncall": "yes",
            "color": "red",
            "message": {
                "function": function_call_name,
                "arguments": function_call_arguments,
            },
            chat_id: chat_id,
        }
        await MessageSender.send_message(new_message, "red", username)
        try:
            # we are here, continue fix the function execution
            print(f"function dict: {function_dict}")
            # Initialize function to None
            function = None
            # Iterate over each function dictionary in the list
            for func_dict in function_dict:
                print(f'f d: {func_dict["function"]["name"]}')
                if (
                    "function" in func_dict
                    and func_dict["function"]["name"] == function_call_name
                ):
                    # If the function name matches the one you're looking for, assign it to function
                    function = func_dict["function"]
                    break  # Break the loop as we've found the matching function
            if inspect.iscoroutinefunction(function):
                function_response = await MessageParser.ahandle_function_response(
                    function, converted_function_call_arguments
                )
            else:
                function_response = MessageParser.handle_function_response(
                    function, converted_function_call_arguments
                )
        except KeyError as e:
            await MessageSender.send_message(
                {"error": f"Function {function_call_name} not found: {e}"},
                "red",
                username,
            )
            function_response = f"Function {function_call_name} not found: {e}"
        return await process_function_reply(
            function_call_name,
            function_response,
            message,
            og_message,
            function_dict,
            function_metadata,
            username,
            merge,
            users_dir,
        )

    @staticmethod
    def extract_content(data):
        try:
            response = json.loads(data)
        except:
            return data
        if isinstance(response, dict):
            if "content" in response:
                return MessageParser.extract_content(response["content"])
        return response

    @staticmethod
    async def process_response(
        response,
        function_dict,
        function_metadata,
        message,
        og_message,
        username,
        process_message,
        chat_history,
        chat_metadata,
        history_ids,
        history_string,
        last_messages_string,
        old_kw_brain,
        users_dir,
        chat_id,
    ):
        if "function_call" in response:
            function_call_name = response["function_call"]["name"]
            function_call_arguments = response["function_call"]["arguments"]
            response = await MessageParser.process_function_call(
                function_call_name,
                function_call_arguments,
                function_dict,
                function_metadata,
                message,
                og_message,
                username,
                process_message,
                False,
                "users/",
                "",
                None,
            )
        else:
            await MessageSender.send_debug(f"{message}", 1, "green", username)
            await MessageSender.send_debug(
                f"Assistant: {response['content']}", 1, "pink", username
            )
            if response["content"] is not None:
                with Database() as db:
                    display_name = db.get_display_name(username)[0]
                memory = _memory.MemoryManager()
                await memory.process_incoming_memory_assistant(
                    "active_brain", response["content"], username, chat_id=chat_id
                )
        return response

    @staticmethod
    def num_tokens_from_string(string, model="gpt-4"):
        """Returns the number of tokens in a text string."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except (KeyError, ValueError):
            logger.warning("Warning: model not found. Using cl100k_base encoding.")
            # encoding = tiktoken.get_encoding("cl100k_base")
            return len(string)
        num_tokens = len(encoding.encode(string))
        return num_tokens

    @staticmethod
    def num_tokens_from_functions(functions, model="gpt-4"):
        """Return the number of tokens used by a list of functions."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except (KeyError, ValueError):
            logger.warning("Warning: model not found. Using cl100k_base encoding.")
            return 0

        num_tokens = 0
        for tool in functions:  # Iterate over the tools
            if tool["type"] == "function":  # Ensure it's a function type
                function = tool["function"]  # Extract the function details
                function_tokens = len(encoding.encode(function["name"]))
                function_tokens += len(encoding.encode(function["description"]))

                if "parameters" in function:
                    parameters = function["parameters"]
                    if "properties" in parameters:
                        for propertiesKey, v in parameters["properties"].items():
                            function_tokens += len(encoding.encode(propertiesKey))
                            for field in v:
                                if field == "type":
                                    function_tokens += 2
                                    function_tokens += len(encoding.encode(v["type"]))
                                elif field == "description":
                                    function_tokens += 2
                                    function_tokens += len(
                                        encoding.encode(v["description"])
                                    )
                                elif field == "default":
                                    function_tokens += 2
                                elif field == "enum":
                                    function_tokens -= 3
                                    for o in v["enum"]:
                                        function_tokens += 3
                                        function_tokens += len(encoding.encode(o))
                                elif field == "items":
                                    function_tokens += 10
                                else:
                                    logger.warning(
                                        f"Warning: not supported field {field}"
                                    )
                        function_tokens += 11

                num_tokens += function_tokens

        num_tokens += 12  # Account for any additional overhead
        return num_tokens

    async def generate_full_message(username, merged_result_string, instruction_string):
        full_message = MessageParser.get_message(
            "start_message",
            {
                "username": username,
                "memory": merged_result_string,
                "instruction_string": instruction_string,
            },
        )
        return full_message


class SettingsManager:
    """This class contains functions to load settings"""

    @staticmethod
    def get_version():
        version = "0.0"
        with open(get_root("version.txt"), "r") as f:
            new_version = f.read().strip()
            if new_version:
                version = new_version
        return version

    @staticmethod
    async def load_settings(users_dir, username):
        settings = {}
        settings_file = os.path.join(users_dir, username, "settings.json")
        with open(settings_file, "r") as f:
            settings = json.load(f)
        return settings


def needsTabDescription(chat_id):
    # get the tab description for the chat
    with Database() as db:
        tab_description = db.get_tab_description(chat_id)
        if tab_description.startswith("New Chat"):
            return True
        else:
            return False


async def process_message(
    og_message,
    username,
    users_dir,
    display_name=None,
    image_prompt=None,
    chat_id=None,
):
    """Process the message and generate a response"""
    # reset the stopPressed variable
    llmcalls.OpenAIResponser.reset_stop_stream(username)
    if display_name is None:
        display_name = username

    # load the setting for the user
    settings = await SettingsManager.load_settings(users_dir, username)

    # Retrieve memory settings
    memory_settings = settings.get("memory", {})

    # start prompt = 54 tokens + 200 reserved for an image description + 23 for the notes string
    token_usage = 500
    # Extract individual settings with defaults if not found
    max_token_usage = max(memory_settings.get("max_tokens", 6500), 120000)
    tokens_active_brain = memory_settings.get("ltm1", 1000)
    tokens_cat_brain = memory_settings.get("ltm2", 700)
    tokens_episodic_memory = memory_settings.get("episodic", 650)
    tokens_recent_messages = memory_settings.get("recent", 650)
    tokens_notes = memory_settings.get("notes", 1000)
    tokens_input = memory_settings.get("input", 1000)
    tokens_output = memory_settings.get("output", 1000)

    chat_history, chat_metadata, history_ids = [], [], []
    function_dict, function_metadata = await AddonManager.load_addons(
        username, users_dir
    )

    function_call_token_usage = MessageParser.num_tokens_from_functions(
        function_metadata, "gpt-4"
    )
    logger.debug(f"function_call_token_usage: {function_call_token_usage}")
    token_usage += function_call_token_usage

    current_date_time = time.strftime("%d/%m/%Y %H:%M:%S")

    last_messages = await MessageParser.get_recent_messages(username, chat_id)
    last_messages_string = "\n".join(
        f"({message['metadata'].get('username')}: {message['document']}"
        for message in last_messages[-100:]
    )

    # keep the last messages below 1000 tokens, if it is above 1000 tokens, delete the oldest messages until it is below 1000 tokens
    last_messages_tokens = MessageParser.num_tokens_from_string(
        last_messages_string, "gpt-4"
    )
    if tokens_recent_messages > 100:
        logger.debug(
            f"last_messages_tokens: {last_messages_tokens} count: {len(last_messages)}"
        )
        while last_messages_tokens > tokens_recent_messages:
            last_messages.pop(0)
            last_messages_string = "\n".join(
                f"{message['metadata'].get('username')}: {message['document']}"
                for message in last_messages[-100:]
            )
            last_messages_tokens = MessageParser.num_tokens_from_string(
                last_messages_string, "gpt-4"
            )
            logger.debug(
                f"new last_messages_tokens: {last_messages_tokens} count: {len(last_messages)}"
            )
    else:
        last_messages_string = ""

    all_messages = last_messages_string + "\n" + og_message

    if needsTabDescription(chat_id) and len(last_messages) >= 2:
        response = None
        messages = [
            {
                "role": "system",
                "content": "You are a chat tab title generator. You will give a very short description of the given conversation, keep it under 5 words. Do not answer the conversation, only give a title to it!",
            },
            {"role": "user", "content": all_messages},
        ]
        response = "New Chat"
        openai_response = llmcalls.OpenAIResponser(api_keys["openai"], default_params)
        async for resp in openai_response.get_response(
            username,
            messages,
            stream=False,
            function_metadata=fakedata,
            chat_id=chat_id,
        ):
            response = resp
            print(f"tab description: {response}")

        with Database() as db:
            db.update_tab_description(chat_id, response)

        await MessageSender.send_message(
            {
                "tab_id": chat_id,
                "tab_description": response,
            },
            "blue",
            username,
        )

    message_tokens = MessageParser.num_tokens_from_string(all_messages, "gpt-4")
    token_usage += message_tokens
    remaining_tokens = max_token_usage - token_usage
    logger.debug(f"1. remaining_tokens: {remaining_tokens}")
    verbose = settings.get("verbose").get("verbose")
    memory = _memory.MemoryManager()
    (
        kw_brain_string,
        token_usage_active_brain,
        unique_results1,
    ) = await memory.process_active_brain(
        og_message,
        username,
        all_messages,
        tokens_active_brain,
        verbose,
        chat_id=chat_id,
    )

    token_usage += token_usage_active_brain
    remaining_tokens = remaining_tokens - token_usage_active_brain
    logger.debug(f"2. remaining_tokens: {remaining_tokens}")

    if tokens_episodic_memory > 100:
        episodic_memory, timezone = await memory.process_episodic_memory(
            og_message, username, all_messages, tokens_episodic_memory, verbose
        )
        if episodic_memory is None or episodic_memory == "":
            episodic_memory_string = ""
        else:
            episodic_memory_string = (
                f"""Episodic Memory of {timezone}:\n{episodic_memory}\n"""
            )
    else:
        episodic_memory_string = ""

    episodic_memory_tokens = MessageParser.num_tokens_from_string(
        episodic_memory_string, "gpt-4"
    )
    token_usage += episodic_memory_tokens
    remaining_tokens = remaining_tokens - episodic_memory_tokens
    logger.debug(f"3. remaining_tokens: {remaining_tokens}")

    if tokens_cat_brain > 100:
        (
            results,
            token_usage_relevant_memory,
            unique_results2,
        ) = await memory.process_incoming_memory(
            None, og_message, username, tokens_cat_brain, verbose
        )
        merged_results_dict = {
            id: (document, distance, formatted_date)
            for id, document, distance, formatted_date in unique_results1.union(
                unique_results2
            )
        }
        merged_results_list = [
            (id, document, distance, formatted_date)
            for id, (document, distance, formatted_date) in merged_results_dict.items()
        ]
        merged_results_list.sort(key=lambda x: int(x[0]))

        # Create the result string
        merged_result_string = "\n".join(
            f"({id}){formatted_date} - {document} (score: {distance})"
            for id, document, distance, formatted_date in merged_results_list
        )
    else:
        results = ""
        token_usage_relevant_memory = 0
        merged_result_string = ""

    token_usage += token_usage_relevant_memory
    remaining_tokens = remaining_tokens - token_usage_relevant_memory
    logger.debug(f"4. remaining_tokens: {remaining_tokens}")

    # process the results
    history_string = results

    observations = "No observations available."
    instruction_string = (
        f"""{episodic_memory_string}\nObservations:\n{observations}\n"""
    )

    if tokens_notes > 100:
        notes = await memory.note_taking(
            all_messages, og_message, users_dir, username, False, verbose, tokens_notes
        )

        if notes is not None or notes != "":
            notes_string = prompts.notes_string.format(notes)
            instruction_string += notes_string
    else:
        notes = ""
        notes_string = ""

    if image_prompt is not None:
        image_prompt_injection = (
            "Automatically generated image description:\n" + image_prompt
        )
        og_message += "\n" + image_prompt_injection

    full_message = await MessageParser.generate_full_message(
        username, merged_result_string, instruction_string
    )

    history_messages = []

    for message in last_messages:
        role = "assistant" if message["metadata"]["username"] == "assistant" else "user"
        content = message["document"]
        history_messages.append({"role": role, "content": content})

    await MessageSender.send_debug(f"[{full_message}]", 1, "gray", username)

    cot_settings = settings.get("cot_enabled")
    is_cot_enabled = cot_settings.get("cot_enabled")
    logger.debug(f"is_cot_enabled: {is_cot_enabled}")
    if is_cot_enabled:
        response = await start_chain_thoughts(
            full_message, og_message, username, users_dir, tokens_output
        )
    else:
        response = await generate_response(
            full_message,
            og_message,
            username,
            users_dir,
            tokens_output,
            history_messages,
            chat_id=chat_id,
        )
    print(f"gen response: {response}")
    response = MessageParser.extract_content(response)
    response = json.dumps({"content": response}, ensure_ascii=False)
    response = json.loads(response)

    # process the response
    response = await MessageParser.process_response(
        response,
        function_dict,
        function_metadata,
        og_message,
        og_message,
        username,
        process_message,
        chat_history,
        chat_metadata,
        history_ids,
        history_string,
        last_messages_string,
        kw_brain_string,
        users_dir,
        chat_id=chat_id,
    )

    with Database() as db:
        db.update_message_count(username)
    return response


async def start_chain_thoughts(
    message, og_message, username, users_dir, max_tokens_allowed
):
    function_dict, function_metadata = await AddonManager.load_addons(
        username, users_dir
    )
    system_prompt = prompts.chain_thoughts_system_prompt
    message_prompt = prompts.chain_thoughts_message_prompt.format(message)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message_prompt},
    ]

    openai_response = OpenAIResponser(
        openai_model, temperature, max_tokens_allowed, max_responses, username
    )
    response = await openai_response.get_response(
        username, messages, function_metadata=function_metadata
    )

    final_response = response

    await MessageSender.send_debug(
        f"cot final_response: {final_response}", 1, "green", username
    )
    cot_response = await process_chain_thoughts(
        response,
        message,
        og_message,
        function_dict,
        function_metadata,
        username,
        users_dir,
        max_tokens_allowed,
    )
    await MessageSender.send_debug(
        f"cot_response: {cot_response}", 1, "green", username
    )

    # try:
    #     return_string = json.dumps({'content': cot_response})
    # except:
    #     await MessageSender.send_debug(f"can't parse cot_response: {cot_response}", 2, 'red', username)
    #     try:
    #         return_string = cot_response['content']
    #     except:
    #         await MessageSender.send_debug(f"can't parse cot_response 2nd time: {cot_response}", 2, 'red', username)

    return cot_response


def prettyprint(msg, color):
    print(colored(msg, color))


async def generate_response(
    memory_message,
    og_message,
    username,
    users_dir,
    max_allowed_tokens,
    history_messages,
    chat_id=None,
):
    function_dict, function_metadata = await AddonManager.load_addons(
        username, users_dir
    )
    system_prompt = prompts.system_prompt

    # add time in front of system prompt
    current_date_time = time.strftime("%d/%m/%Y %H:%M:%S")
    system_prompt = current_date_time + "\n" + system_prompt
    messages = [
        {"role": "system", "content": system_prompt + "\n" + memory_message},
    ]

    for message in history_messages:
        messages.append(
            {"role": f"{message['role']}", "content": f"{message['content']}"}
        )
    messages.append({"role": "user", "content": f"{og_message}"})

    # print the message in a different color in the terminal
    # for message in messages:
    #     if message["role"] == "user":
    #         prettyprint(f"User: {message['content']}", "blue")
    #     elif message["role"] == "assistant":
    #         prettyprint(f"Assistant: {message['content']}", "yellow")
    #     else:
    #         prettyprint(f"System: {message['content']}", "green")

    # openai_response = OpenAIResponser(
    #     openai_model, temperature, max_allowed_tokens, max_responses, username
    # )
    # response = await openai_response.get_response(
    #     username,
    #     messages,
    #     function_metadata=function_metadata,
    #     stream=True,
    #     chat_id=chat_id,
    # )
    response = ""
    openai_response = llmcalls.OpenAIResponser(api_keys["openai"], default_params)
    async for resp in openai_response.get_response(
        username,
        messages,
        stream=True,
        function_metadata=function_metadata,
        chat_id=chat_id,
    ):
        response = resp
        # print(f"Generate response: {response}")
        await MessageSender.send_debug(f"response: {response}", 1, "green", username)

    return response


async def process_cot_messages(
    message,
    function_dict,
    function_metadata,
    username,
    users_dir,
    steps_string,
    full_message="",
    og_message="",
):
    global last_messages
    memory = _memory.MemoryManager()
    function_dict, function_metadata = await AddonManager.load_addons(
        username, users_dir
    )
    system_prompt = prompts.process_cot_system_prompt
    message_prompt = prompts.process_cot_message_prompt.format(
        full_message, steps_string, message
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message_prompt},
    ]
    await MessageSender.send_debug(
        f"process_cot_messages messages: {messages}", 1, "red", username
    )

    openai_response = OpenAIResponser(
        openai_model, temperature, max_tokens, max_responses, username
    )
    response = await openai_response.get_response(
        username, messages, function_metadata=function_metadata
    )
    await MessageSender.send_debug(
        f"process_cot_messages response: {response}", 2, "red", username
    )
    response = response["choices"][0]["message"]

    if "function_call" in response:
        function_call_name = response["function_call"]["name"]
        function_call_arguments = response["function_call"]["arguments"]
        response = await MessageParser.process_function_call(
            function_call_name,
            function_call_arguments,
            function_dict,
            function_metadata,
            message,
            og_message,
            username,
            process_cot_messages,
            False,
            users_dir,
            steps_string,
        )
        await memory.process_incoming_memory_assistant(
            "active_brain", f"Result: {response}", username
        )
        return response
    else:
        await memory.process_incoming_memory_assistant(
            "active_brain", f"Result: {response}", username
        )
        await MessageSender.send_debug(f"{response}", 1, "green", username)
        return response["content"]


async def summarize_cot_responses(
    steps_string, message, og_message, username, users_dir, max_allowed_tokens
):
    global COT_RETRIES
    global last_messages
    # kw_brain_string = await  BrainProcessor.load_brain(username, users_dir)
    # add user to COT_RETRIES if they don't exist
    if username not in COT_RETRIES:
        COT_RETRIES[username] = 0
    function_dict, function_metadata = await AddonManager.load_addons(
        username, users_dir
    )
    if COT_RETRIES[username] >= 2:
        await MessageSender.send_debug(
            f"Too many CoT retries, skipping...", 1, "red", username
        )
        system_prompt = prompts.cot_too_many_retries_system_prompt
        message_prompt = prompts.cot_too_many_retries_message_prompt.format(
            steps_string
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message_prompt},
        ]
    else:
        system_prompt = prompts.cot_system_prompt
        message_prompt = prompts.cot_message_prompt.format(steps_string)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message_prompt},
        ]

    openai_response = OpenAIResponser(
        openai_model, temperature, max_allowed_tokens, max_responses, username
    )
    response = await openai_response.get_response(
        username, messages, function_metadata=function_metadata
    )

    response = response["choices"][0]["message"]["content"]
    # return response
    if response.startswith("YES: "):
        COT_RETRIES[username] = 0
        # remove the YES: part
        response = response[5:]
        return response
    else:
        COT_RETRIES[username] += 1
        return await process_final_message(
            message, og_message, response, username, users_dir, max_allowed_tokens
        )


async def process_function_reply(
    function_call_name,
    function_response,
    message,
    og_message,
    function_dict,
    function_metadata,
    username,
    merge=True,
    users_dir="users/",
):
    await MessageSender.send_debug(
        f"processing function {function_call_name} response: {str(function_response)}",
        1,
        "pink",
        username,
    )
    new_message = {
        "functionresponse": "yes",
        "color": "red",
        "message": function_response,
    }
    await MessageSender.send_message(new_message, "red", username)

    second_response = None
    function_dict, function_metadata = await AddonManager.load_addons(
        username, users_dir
    )
    system_prompt = prompts.function_reply_system_prompt
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{message}"},
        {
            "role": "function",
            "name": function_call_name,
            "content": str(function_response),
        },
    ]
    # openai_response = OpenAIResponser(
    #     openai_model, temperature, max_tokens, max_responses, username
    # )
    # second_response = await openai_response.get_response(
    #     username, messages, stream=True
    # )
    openai_response = llmcalls.OpenAIResponser(api_keys["openai"], default_params)
    async for resp in openai_response.get_response(
        username, messages, stream=True, function_metadata=function_metadata
    ):
        second_response = resp
        print(f"Function response: {second_response}")
    return second_response

    # final_response = second_response["choices"][0]["message"]["content"]

    # final_message_string = f"Function {function_call_name} response: {str(function_response)}\n\n{final_response}"
    # if merge:
    #     return final_message_string
    # else:
    #     return final_response


async def process_final_message(
    message, og_message, response, username, users_dir, max_allowed_tokens
):
    if response.startswith("YES: "):
        # remove the YES: part
        response = await response[5:]
        return response

    function_dict, function_metadata = await AddonManager.load_addons(
        username, users_dir
    )

    if not function_metadata:
        # add a default function
        function_metadata.append(
            {
                "name": "none",
                "description": "you have no available functions",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            }
        )

    current_date_time = time.strftime("%d/%m/%Y %H:%M:%S")

    last_messages_string = "\n".join(last_messages[username][-10:])
    full_message = prompts.full_message.format(message, og_message, response)

    await MessageSender.send_debug(f"{full_message}", 1, "cyan", username)

    # response = generate_response(messages, function_dict, function_metadata)
    response = await start_chain_thoughts(
        full_message, og_message, username, users_dir, max_allowed_tokens
    )

    fc_check = None
    try:
        fc_check = json.loads(response)
    except:
        fc_check = response

    response = MessageParser.extract_content(response)

    await MessageSender.send_debug(
        f"Retry CoT Response: {response}", 1, "green", username
    )

    if "function_call" in fc_check:
        function_call_name = fc_check["function_call"]["name"]
        function_call_arguments = fc_check["function_call"]["arguments"]
        new_fc_check = await MessageParser.process_function_call(
            function_call_name,
            function_call_arguments,
            function_dict,
            function_metadata,
            message,
            og_message,
            username,
            process_final_message,
            False,
            users_dir,
            "",
            None,
        )
        return new_fc_check
    else:
        await MessageSender.send_debug(f"{message}", 1, "green", username)
        await MessageSender.send_debug(f"Assistant: {response}", 1, "pink", username)

        # if settings.get('voice_output', True):
        #     audio_path, audio = generate_audio(response['content'])
        #     play(audio)
        #     return response
        # else:
        return response
