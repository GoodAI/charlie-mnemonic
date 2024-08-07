import asyncio
import base64
import datetime
import json
import os
from pathlib import Path
import re
import time
import uuid
from openai import AsyncOpenAI
from dotenv import load_dotenv
import aiohttp
import utils
from config import CHATGPT_MODEL

from anthropic import AsyncAnthropic, APIStatusError
from anthropic.types import ToolUseBlock

load_dotenv()

stopPressed = {}


class ClaudeResponser:
    def __init__(self, api_key: str, default_params=None):
        if default_params is None:
            default_params = {}

        self.client = AsyncAnthropic(api_key=api_key)
        self.default_params = default_params

    async def get_response(
        self,
        username,
        message,
        stream=False,
        function_metadata=None,
        function_call="auto",
        chat_id=None,
        role=None,
        uid=None,
    ):
        """Get a response from the Anthropic Claude API."""
        if function_metadata is None:
            function_metadata = []

        current_date_time = await utils.SettingsManager.get_current_date_time(username)
        role_content = self.get_role_content(role, current_date_time)

        # Prepare the messages for Claude API
        if isinstance(message, list):
            system_messages = [msg for msg in message if msg["role"] == "system"]
            messages = [msg for msg in message if msg["role"] != "system"]

            if system_messages:
                system_message = " ".join([msg["content"] for msg in system_messages])
            else:
                system_message = role_content if role is not None else None

            # Ensure messages alternate between user and assistant
            # Very hacky way to do this, but it works for now
            formatted_messages = []
            last_role = None
            for msg in messages:
                if msg["role"] == last_role:
                    if last_role == "user":
                        formatted_messages.append(
                            {"role": "assistant", "content": "Understood."}
                        )
                    else:
                        formatted_messages.append(
                            {"role": "user", "content": "Please continue."}
                        )
                formatted_messages.append(msg)
                last_role = msg["role"]

            # Ensure the last message is from the user
            if formatted_messages[-1]["role"] != "user":
                formatted_messages.append(
                    {"role": "user", "content": "Please respond to the above."}
                )

            messages = formatted_messages
        else:
            messages = [{"role": "user", "content": message}]
            system_message = role_content if role is not None else None

        # debug print
        for msg in messages:
            if msg["role"] == "user":
                print(f"\033[92m{msg['content']}\033[0m")
            else:
                print(f"\033[94m{msg['content']}\033[0m")

        tools = self.convert_to_claude_tools(function_metadata)
        print(f"function_metadata: {json.dumps(function_metadata, indent=2)}")
        print(f"Converted tools: {json.dumps(tools, indent=2)}")

        params = self.default_params.copy()
        params.update(
            {
                "model": self.default_params.get("model", "claude-3-opus-20240229"),
                "max_tokens": self.default_params.get("max_tokens", 1000),
                "messages": messages,
                "stream": stream,
            }
        )

        if tools:
            params["tools"] = tools

        if system_message:
            params["system"] = system_message

        print(f"Final params for Claude API: {json.dumps(params, indent=2)}")

        timeout = 180.0
        now = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                self.client.session = session
                response = await asyncio.wait_for(
                    self.client.messages.create(**params),
                    timeout=timeout,
                )
                if stream:
                    collected_messages = []
                    async for event in response:
                        # Check if the user pressed stop
                        global stopPressed
                        stopStream = False
                        if username in stopPressed:
                            stopStream = stopPressed[username]
                        if stopStream:
                            stopPressed[username] = False
                            stopStream = False
                            await utils.MessageSender.send_message(
                                {"cancel_message": True, "chat_id": chat_id},
                                "blue",
                                username,
                            )
                            break

                        if event.type == "content_block_start":
                            continue
                        elif event.type == "content_block_delta":
                            content = event.delta.text
                            if content:
                                collected_messages.append(content)
                                yield await utils.MessageSender.send_message(
                                    {"chunk_message": content, "chat_id": chat_id},
                                    "blue",
                                    username,
                                )
                        elif event.type == "message_delta":
                            continue
                        elif event.type == "message_stop":
                            full_response = "".join(collected_messages)
                            print(f"\nFull response: {full_response}\n")
                            yield full_response
                            await utils.MessageSender.send_message(
                                {"stop_message": True, "chat_id": chat_id},
                                "blue",
                                username,
                            )
                            break

                else:
                    print(f"Response: {response}")
                    yield response.content[0].text

                elapsed = time.time() - now
                # await utils.MessageSender.update_token_usage(
                #     response, username, False, elapsed=elapsed
                # )
        except asyncio.TimeoutError:
            yield "The request timed out. Please try again."
        except Exception as e:
            yield f"An error occurred (claude): {e}"
            print(f"An error occurred (claude): {e}")
            await utils.MessageSender.send_message(
                {"error": f"An error occurred (claude): {e}", "chat_id": chat_id},
                "blue",
                username,
            )

    def convert_to_claude_tools(self, function_metadata):
        """Convert OpenAI function metadata to Claude's tool format."""
        tools = []
        if not function_metadata:
            return tools

        for func in function_metadata:
            try:
                tool = {
                    "name": func.get("function", {}).get("name") or func.get("name"),
                    "description": func.get("function", {}).get("description")
                    or func.get("description"),
                    "input_schema": {
                        "type": "object",
                        "properties": func.get("function", {})
                        .get("parameters", {})
                        .get("properties")
                        or func.get("parameters", {}).get("properties", {}),
                        "required": func.get("function", {})
                        .get("parameters", {})
                        .get("required")
                        or func.get("parameters", {}).get("required", []),
                    },
                }
                # Ensure all required fields are present
                if all(key in tool for key in ["name", "description", "input_schema"]):
                    tools.append(tool)
                else:
                    print(
                        f"Warning: Skipping tool due to missing required fields: {tool}"
                    )
            except Exception as e:
                print(f"Error processing function metadata: {e}")
                print(f"Problematic function metadata: {func}")

        return tools

    def get_role_content(self, role, current_date_time):
        """Return the content for the role."""
        # If this turns out to be the same as openai's prompts we can move this to a shared function
        role_content = "You are an Claude-powered chat bot."
        if role == "machine":
            role_content = "You are a computer program attempting to comply with the user's wishes."
        if role == "brain":
            role_content = f"""Your role is an AI Brain Emulation. You will receive two types of data: 'old active_brain data' and 'new messages'. Each new message will be associated with a specific user. Your task is to update the 'old active_brain data' for each individual user, based on the 'new messages' you receive.
            You should focus on retaining important keywords, instructions, numbers, dates, and events from each user. You can add or remove categories per user request. However, it's crucial that you retain and do not mix up information between users. Each user's data should be kept separate and not influence the data of others. New memories should be added instantly.
            Also, DO NOT include any recent or last messages, home info, settings or observations in the updated data. Any incoming data that falls into these categories must be discarded and not stored in the 'active_brain data'.
            The output must be in a structured plain text format, and the total word count of the updated data for each user should not exceed 300 words.  the current date is: '{current_date_time}'.
            Remember, the goal is to mimic a human brain's ability to retain important information while forgetting irrelevant details. Please follow these instructions carefully. If nothing changes, return the old active_brain data in a a structured plain text format with nothing in front or behind!"""
        if role == "subject":
            role_content = "What is the observed entity in the following observation? If no entity is observed, say None. Only reply with the observed entity, nothing else."
        if role == "observation":
            role_content = "You get a small chathistory and a last message. Break the last message down in 4 search queries to retrieve relevant messages with a vectorsearch. A subject, 2 queries, a category. Only reply in this format: subject\nquery\nquery\ncategory"
        if role == "categorise_query":
            role_content = "You get a small chathistory and a last message. Break the last message down in a category (Factual Information, Personal Information, Procedural Knowledge, Conceptual Knowledge, Meta-knowledge or Temporal Information) and a search query to retrieve relevant messages with a vectorsearch. 1 category and 1 query per line. It is important to adhere to this format and structure. Expected collection name that (1) contains 3-63 characters, (2) starts and ends with an alphanumeric character, (3) otherwise contains only alphanumeric characters, underscores or hyphens (-), (4) contains no two consecutive periods (..) and (5) is not a valid IPv4 address. It is important to reply in this format: category query\ncategory query\n,..\n\n\nExample:\n\nPersonal_Information Antony loves the game Space Engineers\nTemporal_Information Antony went shopping this morning\n"
        if role == "categorise":
            role_content = "You get a small chathistory and a last message. Break the last message down in a category (Factual Information, Personal Information, Procedural Knowledge, Conceptual Knowledge, Meta-knowledge or Temporal Information). 1 category per line. Only reply in this format: category\ncategory\n\nExample:\nProcedural Knowledge\nPersonal Information\n"
        if role == "retriever":
            role_content = "You get a small chathistory and a last message. Break the last message down in multiple search queries to retrieve relevant messages with a vector search. Only reply in this format: query\nquery\n,...\nExample:\nWhat is the capital of France?\nInfo about the capital of France\n"
        if role == "notetaker":
            role_content = """
You are a Memory Organizer. You will receive a list of the current notes, a small chat history, and a last message. Your task is to determine if the last message should be added, or if existing tasks or notes are completed and should be updated or deleted. Only store notes and memories if explicitly asked (e.g., the user asks to remember or learn a task or notes) or things like shopping lists, reminders, user info, instructions or a history of changes. Keep everything in appropriate seperate files. DO NOT save chat history, or regular messages! Mark completed tasks or questions. Use timestamps. Reply in a JSON format with the following keys: 'action' (add, create, delete, edit, skip), 'file' (shoppinglist, notes, etc.), 'content' (the message to be added, updated, deleted, etc.). When updating notes, repeat everything; otherwise, the rest gets removed. 

Example:
[
    {"action": "create", "file": "shoppinglist", "content": "cookies"},
    {"action": "add", "file": "shoppinglist", "content": "apples\nbananas\npotatoes"},
    {"action": "create", "file": "userdetails", "content": "Username: Robin"},
    {"action": "edit", "file": "userdetails", "content": "Old Usernames: Robin\nNew username: Antony"},
    {"action": "create", "file": "events", "content": "Antony went to a concert of Metallica on 12/07/2024"},
]
Remember to only reply with the JSON format, nothing else.
"""
        if role == "summary_memory":
            role_content = "You are a memory summarizer. You get a list of the current notes, your task is to summarize the current notes as short as possible while maintaining all details. Only keep memories worth remembering, like shopping lists, reminders, procedural instructions,.. DO NOT store Imperative Instructions! Use timestamps only if needed. Reply in a plain text format with only the notes, nothing else."
        if role == "summarize":
            role_content = "You are a summarizer. Your task is to summarize the current message as short as possible while maintaining all details. Reply in a plain text format with only the summary, nothing else."
        if role == "date-extractor":
            role_content = f"The current date is {current_date_time}.\nYou are a date extractor. You get a small chathistory and a last message. Your task is to extract the target date for the last message. Only reply with the date in one of these date formats %d-%m-%Y or %d-%m-%Y %H:%M:%S or with 'none', nothing else. Do not include the time if not needed. Examples: today is 26/09/2023; user asked for info about yesterday, you reply with '25/09/2023'. user asked for info about 2 days ago around noon, you reply with '24/09/2023 12:00:00'."
        return role_content

    @staticmethod
    def user_pressed_stop(username):
        global stopPressed
        stopPressed[username] = True

    @staticmethod
    def reset_stop_stream(username):
        global stopPressed
        stopPressed[username] = False


class OpenAIResponser:
    def __init__(self, api_key: str, default_params=None):
        if default_params is None:
            default_params = {}

        base_url = os.getenv("BASE_URL", None)
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.default_params = default_params
        self.addons = self.load_addons()

    def load_addons(self):
        """Load the addons from the addons directory."""
        addons = {}
        for filename in os.listdir("addons"):
            if filename.endswith(".py") and filename != "__init__.py":
                addon_name = filename.replace(".py", "")
                addon = __import__(f"addons.{addon_name}", fromlist=[""])
                addons[addon_name] = addon
        return addons

    async def generate_audio(self, text, username, users_dir, voice="alloy", speed=1.0):
        """Asynchronously generate audio from text using the OpenAI API."""
        # Make sure the directory exists
        audio_dir = os.path.join(users_dir, username, "audio")
        Path(audio_dir).mkdir(parents=True, exist_ok=True)
        audio_path = os.path.join(audio_dir, f"{uuid.uuid4()}.mp3")

        async with self.client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="shimmer",
            input=text,
        ) as response:
            await response.stream_to_file(audio_path)
            return audio_path

    async def get_audio_transcription(self, audio_path, language, filename):
        from pathlib import Path

        # Create transcription from audio file
        transcription = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=Path(audio_path),
            language=language,
        )
        return transcription

    async def get_image_description(self, image_paths, prompt):
        """Asynchronously get descriptions of multiple images using the OpenAI Vision API."""
        image_contents = []
        for image_path in image_paths:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                image_contents.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    }
                )

        prompt_message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt,
                }
            ]
            + image_contents,
        }

        params = {
            "model": "gpt-4o",
            "messages": [prompt_message],
            "max_tokens": 1000,
        }

        response = await self.client.chat.completions.create(**params)
        if response:
            description = response.choices[0].message.content
            return description
        else:
            return "Failed to get descriptions."

    async def get_response(
        self,
        username,
        message,
        stream=False,
        function_metadata=None,
        function_call="auto",
        chat_id=None,
        role=None,
        uid=None,
    ):
        """Get a response from the OpenAI API."""
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

        current_date_time = await utils.SettingsManager.get_current_date_time(username)
        role_content = self.get_role_content(role, current_date_time)

        # If a role is present, add the role content to the message
        if role is not None:
            messages = [
                {"role": "system", "content": role_content},
                {"role": "user", "content": message},
            ]
        else:
            messages = message

        params = self.default_params.copy()
        params.update(
            {
                "model": self.default_params.get("model", "gpt-4o"),
                "temperature": self.default_params.get("temperature", 0.1),
                "max_tokens": self.default_params.get("max_tokens", 1000),
                "n": self.default_params.get("n", 1),
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "messages": messages,
                "stream": stream,
                "tools": function_metadata,
                "tool_choice": function_call,
                "parallel_tool_calls": False,
            }
        )

        timeout = 180.0
        now = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                self.client.session = session
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**params),
                    timeout=timeout,
                )
                if stream:
                    func_call = {
                        "name": None,
                        "arguments": "",
                    }
                    collected_messages = []
                    tool_calls = []
                    tool_calls_complete = False
                    accumulated_name = ""
                    accumulated_arguments = ""
                    async for chunk in response:
                        delta = chunk.choices[0].delta
                        # check if the user pressed stop
                        global stopPressed
                        stopStream = False
                        if username in stopPressed:
                            stopStream = stopPressed[username]
                        if stopStream:
                            stopPressed[username] = False
                            stopStream = False
                            await utils.MessageSender.send_message(
                                {"cancel_message": True, "chat_id": chat_id},
                                "blue",
                                username,
                            )
                            break
                        content = (
                            chunk.choices[0].delta.content
                            if chunk.choices[0].delta.content
                            else ""
                        )
                        if content:
                            collected_messages.append(content)
                            yield await utils.MessageSender.send_message(
                                {"chunk_message": content, "chat_id": chat_id},
                                "blue",
                                username,
                            )
                        if (
                            chunk.choices[0].finish_reason == "stop"
                            or chunk.choices[0].finish_reason == "tool_calls"
                            or tool_calls_complete
                        ):
                            if accumulated_arguments:
                                # TODO: Fix JSON errors on some function calls (especially the python code ones)
                                try:
                                    try:
                                        parsed_arguments = json.loads(
                                            accumulated_arguments
                                        )
                                    except json.JSONDecodeError as e:
                                        json_objects = re.findall(
                                            r"\{.*?\}", accumulated_arguments
                                        )
                                        parsed_arguments = []
                                        for json_str in json_objects:
                                            data = json.loads(json_str)
                                            parsed_arguments.append(data)

                                    tool_response = (
                                        await utils.MessageParser.process_function_call(
                                            accumulated_name,
                                            parsed_arguments,
                                            self.addons,
                                            function_metadata,
                                            message,
                                            message,
                                            username,
                                            None,
                                            chat_id=chat_id,
                                        )
                                    )
                                    yield tool_response
                                    break
                                except json.JSONDecodeError as e:
                                    yield f"Error parsing JSON arguments: {e}"
                                    print(f"JSON parsing error: {e}")
                                    break
                            await utils.MessageSender.send_message(
                                {"stop_message": True, "chat_id": chat_id},
                                "blue",
                                username,
                            )
                            break
                        # Check and accumulate content
                        content = (
                            chunk.choices[0].delta.content
                            if chunk.choices[0].delta.content
                            else ""
                        )
                        if delta.tool_calls:
                            for toolcall_chunk in delta.tool_calls:
                                if (
                                    toolcall_chunk.function.name
                                    and not accumulated_name
                                ):
                                    accumulated_name = toolcall_chunk.function.name

                                accumulated_arguments += (
                                    toolcall_chunk.function.arguments
                                )

                            if chunk.choices[0].finish_reason == "tool_calls":
                                tool_calls_complete = True
                                break

                        content = (
                            chunk.choices[0].delta.content
                            if chunk.choices[0].delta.content
                            else ""
                        )
                        if not content:
                            continue
                        response = "".join(collected_messages)
                        yield response
                else:
                    yield response.choices[0].message.content
                elapsed = time.time() - now
                await utils.MessageSender.update_token_usage(
                    response, username, False, elapsed=elapsed
                )
        except asyncio.TimeoutError:
            yield "The request timed out. Please try again."
        except Exception as e:
            yield f"An error occurred (openai): {e}"
            print(f"An error occurred (openai): {e}")
            await utils.MessageSender.send_message(
                {"error": f"An error occurred (openai): {e}", "chat_id": chat_id},
                "blue",
                username,
            )

    def get_role_content(self, role, current_date_time):
        """Return the content for the role."""
        role_content = "You are an ChatGPT-powered chat bot."
        if role == "machine":
            role_content = "You are a computer program attempting to comply with the user's wishes."
        if role == "brain":
            role_content = f"""Your role is an AI Brain Emulation. You will receive two types of data: 'old active_brain data' and 'new messages'. Each new message will be associated with a specific user. Your task is to update the 'old active_brain data' for each individual user, based on the 'new messages' you receive.
            You should focus on retaining important keywords, instructions, numbers, dates, and events from each user. You can add or remove categories per user request. However, it's crucial that you retain and do not mix up information between users. Each user's data should be kept separate and not influence the data of others. New memories should be added instantly.
            Also, DO NOT include any recent or last messages, home info, settings or observations in the updated data. Any incoming data that falls into these categories must be discarded and not stored in the 'active_brain data'.
            The output must be in a structured plain text format, and the total word count of the updated data for each user should not exceed 300 words.  the current date is: '{current_date_time}'.
            Remember, the goal is to mimic a human brain's ability to retain important information while forgetting irrelevant details. Please follow these instructions carefully. If nothing changes, return the old active_brain data in a a structured plain text format with nothing in front or behind!"""
        if role == "subject":
            role_content = "What is the observed entity in the following observation? If no entity is observed, say None. Only reply with the observed entity, nothing else."
        if role == "observation":
            role_content = "You get a small chathistory and a last message. Break the last message down in 4 search queries to retrieve relevant messages with a vectorsearch. A subject, 2 queries, a category. Only reply in this format: subject\nquery\nquery\ncategory"
        if role == "categorise_query":
            role_content = "You get a small chathistory and a last message. Break the last message down in a category (Factual Information, Personal Information, Procedural Knowledge, Conceptual Knowledge, Meta-knowledge or Temporal Information) and a search query to retrieve relevant messages with a vectorsearch. 1 category and 1 query per line. It is important to adhere to this format and structure. Expected collection name that (1) contains 3-63 characters, (2) starts and ends with an alphanumeric character, (3) otherwise contains only alphanumeric characters, underscores or hyphens (-), (4) contains no two consecutive periods (..) and (5) is not a valid IPv4 address. It is important to reply in this format: category query\ncategory query\n,..\n\n\nExample:\n\nPersonal_Information Antony loves the game Space Engineers\nTemporal_Information Antony went shopping this morning\n"
        if role == "categorise":
            role_content = "You get a small chathistory and a last message. Break the last message down in a category (Factual Information, Personal Information, Procedural Knowledge, Conceptual Knowledge, Meta-knowledge or Temporal Information). 1 category per line. Only reply in this format: category\ncategory\n\nExample:\nProcedural Knowledge\nPersonal Information\n"
        if role == "retriever":
            role_content = "You get a small chathistory and a last message. Break the last message down in multiple search queries to retrieve relevant messages with a vector search. Only reply in this format: query\nquery\n,...\nExample:\nWhat is the capital of France?\nInfo about the capital of France\n"
        if role == "notetaker":
            role_content = """
You are a Memory Organizer. You will receive a list of the current notes, a small chat history, and a last message. Your task is to determine if the last message should be added, or if existing tasks or notes are completed and should be updated or deleted. Only store notes and memories if explicitly asked (e.g., the user asks to remember or learn a task or notes) or things like shopping lists, reminders, user info, instructions or a history of changes. Keep everything in appropriate seperate files. DO NOT save chat history, or regular messages! Mark completed tasks or questions. Use timestamps. Reply in a JSON format with the following keys: 'action' (add, create, delete, edit, skip), 'file' (shoppinglist, notes, etc.), 'content' (the message to be added, updated, deleted, etc.). When updating notes, repeat everything; otherwise, the rest gets removed. 

Example:
[
    {"action": "create", "file": "shoppinglist", "content": "cookies"},
    {"action": "add", "file": "shoppinglist", "content": "apples\nbananas\npotatoes"},
    {"action": "create", "file": "userdetails", "content": "Username: Robin"},
    {"action": "edit", "file": "userdetails", "content": "Old Usernames: Robin\nNew username: Antony"},
    {"action": "create", "file": "events", "content": "Antony went to a concert of Metallica on 12/07/2024"},
]
"""
        if role == "summary_memory":
            role_content = "You are a memory summarizer. You get a list of the current notes, your task is to summarize the current notes as short as possible while maintaining all details. Only keep memories worth remembering, like shopping lists, reminders, procedural instructions,.. DO NOT store Imperative Instructions! Use timestamps only if needed. Reply in a plain text format with only the notes, nothing else."
        if role == "summarize":
            role_content = "You are a summarizer. Your task is to summarize the current message as short as possible while maintaining all details. Reply in a plain text format with only the summary, nothing else."
        if role == "date-extractor":
            role_content = f"The current date is {current_date_time}.\nYou are a date extractor. You get a small chathistory and a last message. Your task is to extract the target date for the last message. Only reply with the date in one of these date formats %d-%m-%Y or %d-%m-%Y %H:%M:%S or with 'none', nothing else. Do not include the time if not needed. Examples: today is 26/09/2023; user asked for info about yesterday, you reply with '25/09/2023'. user asked for info about 2 days ago around noon, you reply with '24/09/2023 12:00:00'."
        return role_content


def user_pressed_stop(username):
    global stopPressed
    stopPressed[username] = True


def reset_stop_stream(username):
    global stopPressed
    stopPressed[username] = False


def get_responder(api_key: str, model: str, default_params=None):
    if model.startswith("gpt"):
        return OpenAIResponser(api_key, default_params)
    elif model.startswith("claude"):
        return ClaudeResponser(api_key, default_params)
    else:
        raise ValueError(f"Unsupported model: {model}")
