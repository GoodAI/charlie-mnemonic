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

load_dotenv()

stopPressed = {}


class OpenAIResponser:
    def __init__(self, api_key: str, default_params=None):
        if default_params is None:
            default_params = {}
        self.client = AsyncOpenAI(api_key=api_key)
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
        # print(f"Loaded addons: {addons}")
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

    async def get_image_description(self, image_path, prompt, filename):
        """Asynchronously get a description of an image using the OpenAI Vision API."""
        # Encode the image to base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        # Craft the prompt with the base64-encoded image
        prompt_message = {
            "role": "user",
            "content": [
                prompt,
                {"image": base64_image, "resize": 768},
            ],
        }

        params = {
            "model": "gpt-4-vision-preview",
            "messages": [prompt_message],
            "max_tokens": 200,
        }

        response = await self.client.chat.completions.create(**params)
        if response:
            description = response.choices[0].message.content
            return description
        else:
            return "Failed to get a description."

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
        # debug print
        # print(
        #    f"username: {username}, message: {message}, stream: {stream}, function_metadata: {function_metadata}, function_call: {function_call}, chat_id: {chat_id}, role: {role}"
        # )
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

        now = datetime.datetime.now()
        current_date_time = now.strftime("%d/%m/%Y %H:%M:%S")
        role_content = self.get_role_content(role, current_date_time)

        # If a role is present, add the role content to the message
        if role is not None:
            messages = [
                {"role": "system", "content": role_content},
                {"role": "user", "content": message},
            ]
        else:
            messages = message

        # # print the messages in different colors
        # for message in messages:
        #     if message["role"] == "user":
        #         print(
        #             f"\033[1;32m{message['content']}\033[0m"
        #         )  # Green color for user messages
        #     elif message["role"] == "system":
        #         print(
        #             f"\033[1;33m{message['content']}\033[0m"
        #         )  # Yellow color for system messages
        #     elif message["role"] == "assistant":
        #         print(
        #             f"\033[1;34m{message['content']}\033[0m"
        #         )  # Blue color for assistant messages

        params = self.default_params.copy()
        params.update(
            {
                "model": self.default_params.get("model", "gpt-4-turbo-preview"),
                "temperature": self.default_params.get("temperature", 0.7),
                "max_tokens": self.default_params.get("max_tokens", 250),
                "n": self.default_params.get("n", 1),
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "messages": messages,
                "stream": stream,
                "tools": function_metadata,
                "tool_choice": function_call,
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
                        # print(
                        #     f"Current chunk finish_reason: {chunk.choices[0].finish_reason}"
                        # )
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
                        # print("chunk", chunk)
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
                                try:
                                    # print(
                                    #     f"Final accumulated arguments: {accumulated_arguments}"
                                    # )
                                    try:
                                        parsed_arguments = json.loads(
                                            accumulated_arguments
                                        )
                                    except json.JSONDecodeError as e:
                                        # GPT tends to concatenate multiple JSON objects together so we need to split them
                                        json_objects = re.findall(
                                            r"\{.*?\}", accumulated_arguments
                                        )
                                        parsed_arguments = []
                                        for json_str in json_objects:
                                            data = json.loads(json_str)
                                            parsed_arguments.append(data)
                                    # print(f"Parsed arguments: {parsed_arguments}")
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
                                # print(
                                #     f"toolcall_chunk: {toolcall_chunk}"
                                # )

                                # Only set the name if it's not None and accumulated_name is not already set
                                if (
                                    toolcall_chunk.function.name
                                    and not accumulated_name
                                ):
                                    accumulated_name = toolcall_chunk.function.name
                                    # print(
                                    #     f"Function name set to: {accumulated_name}"
                                    # )

                                # Accumulate arguments
                                accumulated_arguments += (
                                    toolcall_chunk.function.arguments
                                )
                                # print(
                                #     f"Accumulated arguments: {accumulated_arguments}"
                                # )

                            # Use finish_reason to determine if tool calls are complete
                            if chunk.choices[0].finish_reason == "tool_calls":
                                tool_calls_complete = True
                                break

                        # define the content of the message
                        content = (
                            chunk.choices[0].delta.content
                            if chunk.choices[0].delta.content
                            else ""
                        )
                        if not content:
                            continue
                        response = "".join(collected_messages)
                        yield response
                # if no stream, return the full message
                else:
                    yield response.choices[0].message.content
                elapsed = time.time() - now
                await utils.MessageSender.update_token_usage(
                    response, username, False, elapsed=elapsed
                )
        except asyncio.TimeoutError:
            yield "The request timed out. Please try again."
        except Exception as e:
            yield f"An error occurred: {e}"
            print(f"An error occurred: {e}")
            await utils.MessageSender.send_message(
                {"error": f"An error occurred: {e}", "chat_id": chat_id},
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
            role_content = "You get a small chathistory and a last message. Break the last message down in a category (Factual Information, Personal Information, Procedural Knowledge, Conceptual Knowledge, Meta-knowledge or Temporal Information) and a search query to retrieve relevant messages with a vectorsearch. 1 category and 1 query per line. It is important to only reply in this format: category: query\ncategory: query\n,..\nExample:\nProcedural Knowledge: Antony shared my memory code\nPersonal Information: Antony created me\n\nnothing else! It is important to adhere to this format and structure."
        if role == "categorise":
            role_content = "You get a small chathistory and a last message. Break the last message down in a category (Factual Information, Personal Information, Procedural Knowledge, Conceptual Knowledge, Meta-knowledge or Temporal Information). 1 category per line. Only reply in this format: category\ncategory\n\nExample:\nProcedural Knowledge\nPersonal Information\n"
        if role == "retriever":
            role_content = "You get a small chathistory and a last message. Break the last message down in multiple search queries to retrieve relevant messages with a vectorsearches. Only reply in this format: query\nquery\n,...\nExample:\nWhat is the capital of France?\nInfo about the capital of France\n"
        if role == "notetaker":
            role_content = 'You are an advanced note and task processing Assistant. You get a list of the current notes, a small chathistory and a last message. Your task is to determine if the last message should be added or if existing tasks or notes are completed and/or should be updated or deleted. Only store notes if explicitly asked or things like shopping lists, reminders, the user\'s info, procedural instructions,.. DO NOT save Imperative Instructions, DO NOT save chat history, DO NOT save regular messages! Delete completed tasks or questions. Use timestamps only if needed. Reply in an escaped json format with the following keys: \'action\' (add, create, delete, update, skip), \'file\' (shoppinglist, notes, etc.), \'content\' (the message to be added, updated, deleted, etc.), comma separated, when updating a list repeat the whole updates list or the rest gets removed. Example: [ {"action": "create", "file": "shoppinglist", "content": "cookies"}, {"action": "update", "file": "shoppinglist", "content": "cookies\napples\nbananas\npotatoes"} ]'
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


# Example usage
# async def main():
#     api_key = os.getenv("OPENAI_API_KEY")
#     default_params = {
#         "model": "gpt-4-1106-preview",
#         "temperature": 0.3,
#         "max_tokens": 150,
#     }
#     responser = OpenAIResponser(api_key, default_params)

#     messages = [{"role": "user", "content": "What's 1+1, use 10 words!"}]
#     async for response in responser.get_response("test", messages, stream=False):
#         print(response)

#     async for chunk in responser.get_response("test", messages, stream=True):
#         print(chunk)


# if __name__ == "__main__":
#     asyncio.run(main())
