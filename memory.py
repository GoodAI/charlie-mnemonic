import asyncio
import datetime
import json
import os
import re
import secrets
import time
import aiohttp
from fastapi import HTTPException
import openai
from tenacity import retry, stop_after_attempt, wait_fixed
from agentmemory import (
    create_memory,
    create_unique_memory,
    get_memories,
    search_memory,
    get_memory,
    update_memory,
    delete_memory,
    delete_similar_memories,
    count_memories,
    wipe_category,
    wipe_all_memories,
    import_file_to_memory,
    export_memory_to_file,
    stop_database,
    search_memory_by_date,
    create_alternative_memory,
    get_last_message,
    update_memory,
    delete_memory,
)
import utils
from dateutil.parser import parse
import textwrap
from nltk.tokenize import sent_tokenize
import config
import logs
import llmcalls
import simple_utils

logger = logs.Log("memory", "memory.log").get_logger()


class MemoryManager:
    """A class to manage the memory of the agent."""

    def __init__(self):
        self.model_used = config.api_keys["memory_model"]
        pass

    async def create_memory(
        self,
        category,
        document,
        metadata={},
        username=None,
        mUsername=None,
        regenerate=False,
    ):
        """Create a new memory and return the ID."""
        return create_memory(
            category,
            document,
            metadata,
            username=username,
            mUsername=mUsername,
            regenerate=regenerate,
        )

    async def create_unique_memory(
        self, category, content, metadata={}, similarity=0.15, username=None
    ):
        """Create a new memory if it doesn't exist yet and return the ID."""
        return create_unique_memory(
            category, content, metadata, similarity, username=username
        )

    async def create_alternative_memory(
        self, category, content, metadata={}, username=None
    ):
        """Create a new memory if it doesn't exist yet and return the ID."""
        return create_alternative_memory(category, content, metadata, username=username)

    async def get_memories(self, category, username=None):
        """Return all memories in the category."""
        return get_memories(category, username=username)

    async def search_memory(
        self,
        category,
        search_term,
        username=None,
        min_distance=0.0,
        max_distance=1.0,
        contains_text=None,
        n_results=5,
        filter_metadata=None,
    ):
        """Search the memory and return the results."""
        return search_memory(
            category,
            search_term,
            username=username,
            min_distance=min_distance,
            max_distance=max_distance,
            contains_text=contains_text,
            n_results=n_results,
            filter_metadata=filter_metadata,
        )

    async def search_memory_by_date(
        self, category, search_term, username=None, n_results=100, filter_date=None
    ):
        """Search the memory by date and return the results."""
        return search_memory_by_date(
            category,
            search_term,
            username=username,
            n_results=n_results,
            filter_date=filter_date,
        )

    async def get_memory(self, category, id, username=None):
        """Return the memory with the given ID."""
        # id format is 0000000000000019, add the leading zeros back so its 16 characters long
        id = id.zfill(16)
        return get_memory(category, id, username=username)

    async def update_memory(
        self, category, id, document=None, metadata={}, username=None
    ):
        """Update the memory with the given ID and return the ID."""
        return update_memory(category, id, document, metadata, username=username)

    async def delete_memory(self, category, id, username=None):
        """Delete the memory with the given ID and return the ID."""
        return delete_memory(category, id, username=username)

    async def delete_similar_memories(
        self, category, content, similarity_threshold=0.95, username=None
    ):
        """Delete all memories with a similarity above the threshold and return the number of deleted memories."""
        return delete_similar_memories(
            category, content, similarity_threshold, username=username
        )

    async def count_memories(self, category, username=None):
        """Return the number of memories in the category."""
        return count_memories(category, username=username)

    async def wipe_category(self, category, username=None):
        """Delete all memories in the category and return the number of deleted memories."""
        return wipe_category(category, username=username)

    async def wipe_all_memories(self, username=None):
        """Delete all memories and return the number of deleted memories."""
        return wipe_all_memories(username=username)

    async def import_memories(self, path, username=None):
        """Import memories from a file and return the number of imported memories."""
        return import_file_to_memory(path, username=username)

    async def export_memories(self, path, username=None):
        """Export memories to a file and return the number of exported memories."""
        return export_memory_to_file(path, username=username)

    async def stop_database(self, username=None):
        """Stop the database."""
        return stop_database(username=username)

    async def split_text_into_chunks(self, text, max_chunk_len=200):
        """Split the text into chunks of up to `max_chunk_len`."""
        # Check if text is a string; if not, directly return it in a list assuming it's already chunked properly
        if not isinstance(text, str):
            return [text]

        chunks = []
        chunk = []
        token_count = 0

        def add_to_chunk(line):
            nonlocal chunk, token_count, chunks
            current_line_token_count = utils.MessageParser.num_tokens_from_string(line)
            if token_count + current_line_token_count > max_chunk_len:
                # If the current chunk is full, add it to chunks and start a new chunk
                chunks.append("\n".join(chunk))
                chunk = [line]
                token_count = current_line_token_count
            else:
                # Add the current line to the chunk and update the token count
                chunk.append(line)
                token_count += current_line_token_count

        # Split text into lines if it contains newline characters; otherwise, process it as a single line
        lines = text.split("\n") if "\n" in text else [text]

        for line in lines:
            if "\n" in text or len(lines) == 1:
                add_to_chunk(line)
            else:
                while line:
                    part = line[:max_chunk_len]
                    add_to_chunk(part)
                    line = line[max_chunk_len:]

        if chunk:
            chunks.append("\n".join(chunk))

        return chunks

    async def get_most_recent_messages(
        self, category, username=None, n_results=100, chat_id=None
    ):
        """Return the most recent messages in the category."""
        category = category.lower().replace(" ", "_")
        if chat_id is None:
            memories = get_memories(category, username=username, n_results=n_results)
        else:
            memories = get_memories(
                category,
                username=username,
                n_results=n_results,
                filter_metadata={"chat_id": chat_id},
            )
        memories.sort(key=lambda x: x["metadata"]["created_at"], reverse=False)
        for memory in memories:
            if memory["metadata"].get("username") == "user":
                memory["document"].replace("User :", username + ":")
        return memories[:n_results]

    async def process_episodic_memory(
        self,
        new_messages,
        username=None,
        all_messages=None,
        remaining_tokens=1000,
        verbose=False,
    ):
        category = "active_brain"
        process_dict = {"input": new_messages}

        subject = "none"
        openai_response = llmcalls.OpenAIResponser(
            config.api_keys["openai"], config.default_params
        )
        async for resp in openai_response.get_response(
            username,
            all_messages,
            function_metadata=config.fakedata,
            role="date-extractor",
        ):
            if resp:
                subject = resp
            else:
                process_dict[
                    "error"
                ] = "timeline does not contain the required elements"

        if (
            subject.lower() == "none"
            or subject.lower() == "'none'"
            or subject.lower() == '"none"'
            or subject.lower() == '""'
        ):
            return "", ""
        logger.debug(f"Timeline: {subject}")
        if isinstance(subject, str):
            # List of date formats
            date_formats = [
                "%Y-%m-%d",
                "%d/%m/%Y %H:%M:%S",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%d-%m-%Y %H:%M:%S",
            ]

            # Try parsing the date with each format
            for date_format in date_formats:
                try:
                    parsed_date = datetime.datetime.strptime(
                        subject.strip(), date_format
                    )
                    logger.debug(f"parsed_date: {parsed_date}")
                    break
                except ValueError:
                    parsed_date = None
                    continue
            else:
                return "", ""

        if parsed_date is not None:
            results_string = ""
            logger.debug(
                f"searching for episodic messages on a specific date: {parsed_date} in category: {category} for user: {username} and message: {new_messages}"
            )
            episodic_messages = search_memory_by_date(
                category, new_messages, username=username, filter_date=parsed_date
            )
            logger.debug(f"episodic_messages: {len(episodic_messages)}")
            for memory in episodic_messages:
                date = memory["metadata"]["created_at"]
                formatted_date = datetime.datetime.fromtimestamp(date).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                results_string += f"{formatted_date} - {memory['document']} (score: {memory['distance']})\n"
            logger.debug(f"results_string:\n{results_string}")

            # Check tokens
            token_count = utils.MessageParser.num_tokens_from_string(results_string)
            while token_count > min(1000, remaining_tokens):
                # Split the result_string by newline and remove the last line if possible
                result_lines = results_string.split("\n")
                if len(result_lines) > 1:
                    result_lines.pop(-1)
                    results_string = "\n".join(result_lines)
                else:
                    # If there are no newline characters, remove a certain number of characters from the endsecretso
                    results_string = results_string[:-100]
                token_count = utils.MessageParser.num_tokens_from_string(results_string)
            return results_string, subject

    async def process_active_brain(
        self,
        new_messages,
        username=None,
        all_messages=None,
        remaining_tokens=1000,
        verbose=False,
        chat_id=None,
        regenerate=False,
        uid=None,
    ):
        """Process the active brain and return the updated active brain data."""
        category = "active_brain"
        process_dict = {"input": new_messages}
        seen_ids = set()

        chunks = await self.split_text_into_chunks(new_messages, 200)
        if uid is None:
            uid = secrets.token_hex(10)
        for chunk in chunks:
            # Create a memory for each chunk
            await self.create_memory(
                category,
                chunk,
                username=username,
                metadata={"uid": uid, "chat_id": chat_id},
                mUsername="user",
                regenerate=regenerate,
            )
            logger.debug(
                f"adding memory: {chunk} to category: {category} with uid: {uid} for user: {username} and chat_id: {chat_id}"
            )
            process_dict["created_new_memory"] = "yes"
        if remaining_tokens > 100:
            openai_response = llmcalls.OpenAIResponser(
                config.api_keys["openai"], config.default_params
            )
            subject_query = None
            response = ""
            async for resp in openai_response.get_response(
                username,
                all_messages,
                function_metadata=config.fakedata,
                role="retriever",
            ):
                if resp:
                    subject_query = resp

            if subject_query:
                if subject_query.lower() == "none":
                    response = new_messages

            process_dict[category] = {}
            parsed_data = self.process_observation(response)
            results_list = []
            process_dict[category]["query_results"] = {}
            for data in parsed_data:
                data_results = await self.search_memory(
                    category,
                    data,
                    username,
                    min_distance=0.0,
                    max_distance=2.0,
                    n_results=10,
                )
                # Initialize the list for this data item in the dictionary
                process_dict[category]["query_results"][data] = []
                for result in data_results:
                    if result.get("id") not in seen_ids:
                        seen_ids.add(result.get("id"))
                        id = result.get("id")
                        id = id.lstrip("0") or "0"
                        document = result.get("document")
                        distance = round(result.get("distance"), 3)
                        date = result["metadata"]["created_at"]
                        formatted_date = datetime.datetime.fromtimestamp(date).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        results_list.append((id, document, distance, formatted_date))
                        # Add the result to the list for this data item
                        process_dict[category]["query_results"][data].append(
                            (id, document, distance, formatted_date)
                        )

            process_dict["results_list_before_token_check"] = results_list.copy()
            result_string = ""
            result_string = "\n".join(
                f"({id}) {formatted_date} - {document} (score: {distance})"
                for id, document, distance, formatted_date in results_list
            )
            token_count = utils.MessageParser.num_tokens_from_string(result_string)
            while token_count > min(1000, remaining_tokens):
                if len(results_list) > 1:
                    results_list.sort(key=lambda x: int(x[2]), reverse=True)
                    results_list.pop(0)
                    result_string = "\n".join(
                        f"({id}) {formatted_date} - {document} (score: {distance})"
                        for id, document, distance, formatted_date in results_list
                    )
                else:
                    # If there's only one entry, shorten the document content
                    id, document, distance, formatted_date = results_list[0]
                    document = document[:-100]
                    result_string = (
                        f"({id}) {formatted_date} - {document} (score: {distance})"
                    )
                token_count = utils.MessageParser.num_tokens_from_string(result_string)

            unique_results = set()  # Create a set to store unique results
            for id, document, distance, formatted_date in results_list:
                unique_results.add((id, document, distance, formatted_date))
                results_list.sort(key=lambda x: int(x[0]))
            result_string = "\n".join(
                f"({id}) {formatted_date} - {document} (score: {distance})"
                for id, document, distance, formatted_date in results_list
            )

            process_dict["results_list_after_token_check"] = results_list
            process_dict["result_string"] = result_string
            process_dict["token_count"] = token_count
            if verbose:
                await utils.MessageSender.send_message(
                    {"type": "relations", "content": process_dict}, "blue", username
                )
            return result_string, token_count, unique_results
        else:
            return "", 0, set()

    async def process_incoming_memory(
        self, category, content, username=None, remaining_tokens=1000, verbose=False
    ):
        """Process the incoming memory and return the updated active brain data."""
        process_dict = {"input": content}
        unique_results = set()
        logger.debug(f"Processing incoming memory: {content}")
        subject_query = "none"
        openai_response = llmcalls.OpenAIResponser(
            config.api_keys["openai"], config.default_params
        )
        async for resp in openai_response.get_response(
            username,
            content,
            function_metadata=config.fakedata,
            role="categorise_query",
        ):
            if resp:
                subject_query = resp
            else:
                logger.error("Error: choice does not contain 'message' or 'content'")

        subject = subject_query

        if (
            subject.lower() == "none"
            or subject.lower() == "'none'"
            or subject.lower() == '"none"'
            or subject.lower() == '""'
        ):
            subject = "personal_information: " + content[:40]

        result_string = ""
        parts = self.process_category_query(subject)

        if len(parts) < 1:
            logger.error(
                "Error: parts does not contain the required elements: "
                + str(parts)
                + "query: "
                + str(subject)
            )
            process_dict["error"] = "parts does not contain the required elements"
        else:
            for part in parts:
                category, query = part
                process_dict[category] = {}
                process_dict[category]["query_results"] = {}
                process_dict[category]["query_results"][query] = []
                search_result, new_process_dict = await self.search_queries(
                    category,
                    [query],
                    username,
                    process_dict[category]["query_results"][query],
                )
                process_dict[category]["query_results"][query] = new_process_dict
                for id, document, distance, formatted_date in process_dict[category][
                    "query_results"
                ][query]:
                    try:
                        unique_results.add((id, document, distance, formatted_date))
                    except Exception as e:
                        logger.error(
                            f"Error while adding result to unique_results: {e}"
                        )
                result_string += search_result
                result_string = "\n".join(
                    f"({id}) {formatted_date} - {document} (score: {distance})"
                    for id, document, distance, formatted_date in unique_results
                )

        # Check tokens
        token_count = utils.MessageParser.num_tokens_from_string(result_string)
        while token_count > min(1000, remaining_tokens):
            # Split the result_string by newline and remove the last line if possible
            result_lines = result_string.split("\n")
            if len(result_lines) > 1:
                result_lines.pop(-1)
                result_string = "\n".join(result_lines)
            else:
                # If there are no newline characters, remove a certain number of characters from the end
                result_string = result_string[:-100]
            token_count = utils.MessageParser.num_tokens_from_string(result_string)

        similar_messages = None
        if len(parts) > 0:
            for part in parts:
                category, query = part
                similar_messages = await self.search_memory(
                    category, content, username, max_distance=0.15, n_results=10
                )

        if similar_messages:
            logger.debug(
                "Not adding to memory, message is similar to a previous message(s):"
            )
            process_dict["similar_messages"] = [
                (m["document"], m["id"], m["distance"], m["metadata"]["created_at"])
                for m in similar_messages
            ]
            process_dict["created_new_memory"] = "no"
            for similar_message in similar_messages:
                logger.debug(
                    f"({similar_message['id']}){similar_message['metadata']['created_at']} - {similar_message['document']} - score: {similar_message['distance']}"
                )
        else:
            subject_category = "none"
            openai_response = llmcalls.OpenAIResponser(
                config.api_keys["openai"], config.default_params
            )
            async for resp in openai_response.get_response(
                username,
                content,
                function_metadata=config.fakedata,
                role="categorise",
            ):
                if resp:
                    subject_category = resp
                else:
                    logger.error(
                        "Error: subject_query does not contain the required elements"
                    )
            else:
                logger.error(
                    "Error: subject_query does not contain the required elements"
                )
            category = subject_category

            if category.lower() == "none":
                category = content

            categories = self.process_category(category)
            uid = secrets.token_hex(10)
            for category in categories:
                chunks = await self.split_text_into_chunks(content, 200)
                for chunk in chunks:
                    # Create a memory for each chunk
                    await self.create_memory(
                        category,
                        chunk,
                        username=username,
                        metadata={"uid": uid},
                        mUsername="user",
                    )
                    logger.debug(f"adding memory: {chunk} to category: {category}")
            process_dict["created_new_memory"] = "yes, categories: " + ", ".join(
                categories
            )

        process_dict["result_string"] = result_string
        process_dict["token_count"] = token_count
        if verbose:
            await utils.MessageSender.send_message(
                {"type": "relations", "content": process_dict}, "blue", username
            )
        return result_string, token_count, unique_results

    async def search_queries(self, category, queries, username, process_dict):
        """Search the queries in the memory and return the results."""
        seen_ids = set()
        full_search_result = ""
        for query in queries:
            search_result = await self.search_memory(
                category, query, username, n_results=10
            )
            for result in search_result:
                if result.get("id") not in seen_ids:
                    seen_ids.add(result.get("id"))
                    id = result.get("id")
                    id = id.lstrip("0") or "0"
                    document = result.get("document")
                    distance = round(result.get("distance"), 3)
                    date = result["metadata"]["created_at"]
                    formatted_date = datetime.datetime.fromtimestamp(date).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    full_search_result += (
                        f"({id}) {formatted_date} - {document} - score: {distance}\n"
                    )
                    process_dict.append((id, document, distance, formatted_date))
        return full_search_result, process_dict

    async def process_incoming_memory_assistant(
        self, category, content, username=None, chat_id=None, regenerate=False, uid=None
    ):
        """Process the incoming memory and return the updated active brain data."""
        logger.debug(f"Processing incoming memory: {content}")
        # todo: get version from the memory
        version = 0
        if regenerate:
            version = 1
        # create a new memory
        if uid is None:
            uid = secrets.token_hex(10)
        chunks = await self.split_text_into_chunks(content, 200)
        for chunk in chunks:
            await self.create_memory(
                category,
                chunk,
                username=username,
                metadata={"uid": uid, "chat_id": chat_id, "version": version},
                mUsername="assistant",
            )
            logger.debug(f"adding memory: {chunk} to category: {category}")
        return

    def process_observation(self, string):
        """Process the observation and returns each part"""
        parts = string.split("\n")
        # remove the : and the space after it
        parts = [
            part.split(":", 1)[1].lstrip() if ":" in part else part for part in parts
        ]
        return parts

    def process_category_query(self, string):
        """Process the input data and return the results"""
        lines = string.split("\n")
        result = []
        valid_categories = [
            "factual_information",
            "personal_information",
            "procedural_knowledge",
            "conceptual_knowledge",
            "meta_knowledge",
            "temporal_information",
        ]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Check if the line contains a colon separator
            if ":" in line:
                category, query = line.split(":", 1)
                category = category.strip().lower()
                query = query.strip()
            else:
                # Split the line into category and query
                parts = line.split(" ", 1)
                if len(parts) == 1:
                    category = "active_brain"
                    query = parts[0]
                else:
                    category, query = parts
                    category = category.lower()
            # Check if the category is valid
            if category not in valid_categories:
                category = "active_brain"
            # Clean the category name
            category = re.sub(r"[^a-zA-Z0-9_-]", "", category)
            category = category[:63]
            if not category:
                category = "active_brain"
            # Make sure the category starts and ends with an alphanumeric character
            category = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", category)
            # Remove consecutive periods (..)
            category = re.sub(r"\.{2,}", ".", category)
            # Check if the category is a valid IPv4 address
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", category):
                category = "active_brain"
            # Truncate the query to a maximum of 100 characters
            query = query[:100]
            result.append((category, query))
        return result

    def process_category(self, string):
        """Process the input data and return the results"""
        lines = string.split("\n")
        result = []
        for line in lines:
            if not line.strip():
                continue
            line = line.lower().replace(" ", "_")
            line = re.sub(r"[^a-z0-9-_]", "", line)  # Remove invalid characters
            line = re.sub(
                r"\.{2,}", ".", line
            )  # Replace consecutive periods with a single one
            line = re.sub(
                r"^[^a-z0-9]*|[^a-z0-9]*$", "", line
            )  # Remove leading/trailing invalid characters

            # If line is still too long or too short, replace it with a default category
            if len(line) < 3 or len(line) > 63:
                line = "active_brain"

            result.append(line)
        return result

    async def note_taking(
        self,
        content,
        message,
        user_dir,
        username,
        show=True,
        verbose=False,
        tokens_notes=1000,
    ):
        max_tokens = tokens_notes
        process_dict = {
            "actions": [],
            "content": content,
            "message": message,
            "timestamp": None,
            "final_message": None,
            "note_taking_query": None,
            "files_content_string": None,
            "error": None,
        }

        filedir = "notes"
        filedir = os.path.join(user_dir, username, filedir)
        if not os.path.exists(filedir):
            os.makedirs(filedir)

        dir_list = os.listdir(filedir)
        files_content_string = ""
        for file in dir_list:
            with open(f"{filedir}/{file}", "r") as f:
                files_content_string += f"{file}:\n{f.read()}\n\n"

        process_dict["files_content_string"] = files_content_string

        token_count = utils.MessageParser.num_tokens_from_string(files_content_string)
        if token_count > max_tokens:
            new_files_content_string = ""
            # take each file, ask gpt to summarize it, and overwrite the original file with the summary
            for file in dir_list:
                # calculate tokens based on max tokens divided by the number of files
                max_tokens_per_file = max_tokens / len(dir_list)
                current_file = f"{filedir}/{file}"
                with open(current_file, "r") as f:
                    file_content = f.read()
                    openai_response = llmcalls.OpenAIResponser(
                        config.api_keys["openai"], config.default_params
                    )
                    async for response in openai_response.get_response(
                        username,
                        file_content,
                        function_metadata=config.fakedata,
                        role="summary_memory",
                    ):
                        if response:
                            summary = response
                        else:
                            logger.error(
                                "Error: summary does not contain the required elements"
                            )
                    with open(current_file, "w") as f:
                        new_content = summary
                        f.write(new_content)
                        new_files_content_string += f"{file}:\n{new_content}\n\n"
            files_content_string = new_files_content_string

        if show:
            return f"{files_content_string}"

        else:
            timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
            process_dict["timestamp"] = timestamp

            # count tokens of the message
            token_count = utils.MessageParser.num_tokens_from_string(message)
            if token_count > 500:
                openai_response = llmcalls.OpenAIResponser(
                    config.api_keys["openai"], config.default_params
                )
                async for response in openai_response.get_response(
                    username,
                    message,
                    function_metadata=config.fakedata,
                    role="summarize",
                ):
                    if response:
                        message = response
                    else:
                        logger.error(
                            "Error: message does not contain the required elements"
                        )

            final_message = f"Current Time: {timestamp}\nCurrent Notes:\n{files_content_string}\n\nRelated messages:\n{content}\n\nLast Message:{message}\n"
            process_dict["final_message"] = final_message

            retry_count = 0
            while retry_count < 5:
                try:
                    # todo: inform gpt about the remaining tokens available, if it exceeds the limit, summarize the existing list and purge unneeded items
                    # self.openai_manager.set_username(username)
                    # note_taking_query = await self.openai_manager.ask_openai(
                    #     final_message,
                    #     "notetaker",
                    #     self.model_used,
                    #     1000,
                    #     0.1,
                    #     username=username,
                    # )
                    note_taking_query = {}
                    openai_response = llmcalls.OpenAIResponser(
                        config.api_keys["openai"], config.default_params
                    )
                    async for resp in openai_response.get_response(
                        username,
                        final_message,
                        function_metadata=config.fakedata,
                        role="notetaker",
                    ):
                        if resp:
                            note_taking_query = resp
                        else:
                            logger.error(
                                "Error: note_taking_query does not contain the required elements"
                            )
                    process_dict["note_taking_query"] = json.dumps(note_taking_query)
                    actions = self.process_note_taking_query(note_taking_query)
                    break  # If no error, break the loop
                except json.decoder.JSONDecodeError:
                    logger.error("Error in JSON decoding, retrying...")
                    retry_count += 1
            else:
                logger.error("Error in JSON decoding, exceeded retry limit.")
            process_dict["actions"] = actions

            for action, file, content in actions:
                filepath = os.path.join(filedir, file)

                # Check if the directory exists, if not, create it
                if not os.path.isdir(filedir):
                    os.makedirs(filedir, exist_ok=True)

                if action == "create":
                    with open(f"{filedir}/{file}", "w") as f:
                        f.write(content)
                elif action == "add":
                    with open(f"{filedir}/{file}", "a") as f:
                        if f.tell() != 0 and not content.startswith("\n"):
                            f.write("\n")
                        f.write(content)
                elif action == "read":
                    if not os.path.exists(f"{filedir}/{file}"):
                        process_dict["error"] = "Error: File does not exist"
                        return process_dict
                    with open(f"{filedir}/{file}", "r") as f:
                        return f.read()
                elif action == "delete":
                    if not content:
                        os.remove(f"{filedir}/{file}")
                    else:
                        with open(f"{filedir}/{file}", "r") as f:
                            lines = f.readlines()
                        with open(f"{filedir}/{file}", "w") as f:
                            for line in lines:
                                if line.strip("\n") != content:
                                    f.write(line)
                elif action == "update":
                    with open(f"{filedir}/{file}", "w") as f:
                        f.write(content)
                elif action == "skip":
                    pass
                else:
                    process_dict["error"] = "Error: Invalid action"

        if verbose:
            await utils.MessageSender.send_message(
                {"type": "note_taking", "content": process_dict}, "blue", username
            )
        return await self.note_taking(content, message, user_dir, username, show=True)

    def process_note_taking_query(self, query):
        # extract the actions from the query
        actions = []
        query_string = query.replace("```json", "").replace("```", "").strip()
        try:
            query_json = json.loads(query_string)
        except json.JSONDecodeError:
            if not query_string.startswith("["):
                query_string = "[" + query_string
            if not query_string.endswith("]"):
                query_string = query_string + "]"
            try:
                query_json = json.loads(query_string)
            except:
                logger.error("Error: query is not valid json: " + query_string)
                return actions

        if isinstance(query_json, list):
            for action_dict in query_json:
                if (
                    "action" in action_dict
                    and "file" in action_dict
                    and "content" in action_dict
                ):
                    action = action_dict["action"]
                    file = action_dict["file"]
                    content = action_dict["content"]
                elif "action" in action_dict and action_dict["action"] == "skip":
                    action = action_dict["action"]
                    file = ""
                    content = ""
                else:
                    logger.error(
                        "Error: action list does not contain the required elements: "
                        + str(action_dict)
                    )
                    continue
                actions.append((action, file, content))
        elif isinstance(query_json, dict):
            if (
                "action" in query_json
                and "file" in query_json
                and "content" in query_json
            ):
                action = query_json["action"]
                file = query_json["file"]
                content = query_json["content"]
            elif "action" in query_json and query_json["action"] == "skip":
                action = query_json["action"]
                file = ""
                content = ""
            else:
                logger.error(
                    "Error: action does not contain the required elements: "
                    + str(query_json)
                )
                return
            actions.append((action, file, content))

        return actions
