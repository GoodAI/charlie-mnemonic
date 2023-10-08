import datetime
import json
import os
import secrets
import time
import aiohttp
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
)
import utils
from dateutil.parser import parse
import nltk
import config
import logs

logger = logs.Log(__name__, 'full_log.log').get_logger()

class MemoryManager:
    """A class to manage the memory of the agent."""
    def __init__(self):
        self.openai_manager = OpenAIManager()
        self.model_used = config.api_keys["memory_model"]
        pass

    async def create_memory(self, category, document, metadata={}, username=None):
        """Create a new memory and return the ID."""
        return create_memory(category, document, metadata, username=username)

    async def create_unique_memory(self, category, content, metadata={}, similarity=0.15, username=None):
        """Create a new memory if it doesn't exist yet and return the ID."""
        return create_unique_memory(category, content, metadata, similarity, username=username)

    async def get_memories(self, category, username=None):
        """Return all memories in the category."""
        return get_memories(category, username=username)

    async def search_memory(self, category, search_term, username=None, min_distance=0.0, max_distance=1.0, contains_text=None, n_results=5, filter_metadata=None):
        """Search the memory and return the results."""
        return search_memory(category, search_term, username=username, min_distance=min_distance, max_distance=max_distance, contains_text=contains_text, n_results=n_results, filter_metadata=filter_metadata)

    async def search_memory_by_date(self, category, search_term, username=None, n_results=100, filter_date=None):
        """Search the memory by date and return the results."""
        return search_memory_by_date(category, search_term, username=username, n_results=n_results, filter_date=filter_date)
    
    async def get_memory(self, category, id, username=None):
        """Return the memory with the given ID."""
        # id format is 0000000000000019, add the leading zeros back so its 16 characters long
        id = id.zfill(16)
        return get_memory(category, id, username=username)

    async def update_memory(self, category, id, document=None, metadata={}, username=None):
        """Update the memory with the given ID and return the ID."""
        return update_memory(category, id, document, metadata, username=username)

    async def delete_memory(self, category, id, username=None):
        """Delete the memory with the given ID and return the ID."""
        return delete_memory(category, id, username=username)

    async def delete_similar_memories(self, category, content, similarity_threshold=0.95, username=None):
        """Delete all memories with a similarity above the threshold and return the number of deleted memories."""
        return delete_similar_memories(category, content, similarity_threshold, username=username)

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

    # Use the function
    async def split_text_into_chunks(self, text, max_chunk_len=150, overlap=25):
        """Split the text into chunks of up to `max_chunk_len` tokens each, with `overlap` tokens of overlap."""
        # Tokenize the text into sentences, then tokenize each sentence into words
        # todo: smarter chunking, split on punctuation etc...
        tokens = [word for sent in nltk.sent_tokenize(text) for word in nltk.word_tokenize(sent)]
        
        chunks = []
        current_chunk = []
        
        for i, token in enumerate(tokens):
            current_chunk.append(token)
            if (i + 1) % (max_chunk_len - overlap) == 0 or (i + 1) == len(tokens):
                chunks.append(' '.join(current_chunk))
                current_chunk = current_chunk[overlap:]
        
        return chunks
    
    async def process_episodic_memory(self, new_messages, username=None, all_messages=None, remaining_tokens=1000, verbose=False):
        category = 'active_brain'
        process_dict = {'input': new_messages}
        # todo: extract the needed date from the message and use that as the date
        # add the date-extractor
        self.openai_manager.set_username(username)
        timeline = await self.openai_manager.ask_openai(all_messages, 'date-extractor', self.model_used, 100, 0.1, username=username)
        if 'choices' in timeline and len(timeline['choices']) > 0 and 'message' in timeline['choices'][0] and 'content' in timeline['choices'][0]['message']:
            subject = timeline['choices'][0]['message']['content']
        else:
            process_dict['error'] = "timeline does not contain the required elements"

        if subject.lower() == 'none' or subject.lower() == "'none'" or subject.lower() == '"none"' or subject.lower() == '""':
            return "", ""
        logger.debug(f"Timeline: {subject}")
        if isinstance(subject, str):
            # List of date formats
            date_formats = ['%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d-%m-%Y', '%d/%m/%Y', '%d-%m-%Y', '%d-%m-%Y %H:%M:%S']
            
            # Try parsing the date with each format
            for date_format in date_formats:
                try:
                    parsed_date = datetime.datetime.strptime(subject.strip(), date_format)
                    logger.debug(f"parsed_date: {parsed_date}")
                    break
                except ValueError:
                    parsed_date = None
                    continue
            else:
                return "", ""
                
        if parsed_date is not None:
            results_string = ""
            logger.debug(f'searching for episodic messages on a specific date: {parsed_date} in category: {category} for user: {username} and message: {new_messages}')
            episodic_messages = search_memory_by_date(category, new_messages, username=username, filter_date=parsed_date)
            #episodic_messages_get = get_memory_by_date(category, username=username, filter_date=filter_date)
            logger.debug(f'episodic_messages: {len(episodic_messages)}')
            #print(f'episodic_messages_get: {len(episodic_messages_get)}')
            for memory in episodic_messages:
                date = memory['metadata']['created_at']
                formatted_date = datetime.datetime.fromtimestamp(date).strftime('%Y-%m-%d %H:%M:%S')
                #print(f"{formatted_date} - {memory['document']} (score: {memory['distance']})")
                results_string += f"{formatted_date} - {memory['document']} (score: {memory['distance']})\n"
            logger.debug(f"results_string:\n{results_string}")

            # Check tokens
            token_count = utils.MessageParser.num_tokens_from_string(results_string)
            while token_count > min(1000,remaining_tokens):
                # Split the result_string by newline and remove the last line if possible
                result_lines = results_string.split('\n')
                if len(result_lines) > 1:
                    result_lines.pop(-1)
                    results_string = '\n'.join(result_lines)
                else:
                    # If there are no newline characters, remove a certain number of characters from the endsecretso
                    results_string = results_string[:-100]
                token_count = utils.MessageParser.num_tokens_from_string(results_string)
            return results_string, subject
    
    async def process_active_brain(self, new_messages, username=None, all_messages=None, remaining_tokens=1000, verbose=False):
        category = 'active_brain'
        process_dict = {'input': new_messages}
        similar_messages = await self.search_memory(category, new_messages, username, max_distance=0.15)
        seen_ids = set()

        if similar_messages:
            process_dict['similar_messages'] = [(m['document'], m['id'], m['distance']) for m in similar_messages]
            process_dict['created_new_memory'] = 'no'
        else:
            chunks = await self.split_text_into_chunks(new_messages, 150, 25)
            uid = secrets.token_hex(10)
            for chunk in chunks:
                # Create a memory for each chunk
                await self.create_memory(category, chunk, username=username, metadata={'uid': uid})
                logger.debug(f"adding memory: {chunk} to category: {category}")
                process_dict['created_new_memory'] = 'yes'

        self.openai_manager.set_username(username)
        subject_query = await self.openai_manager.ask_openai(all_messages, 'retriever', self.model_used, 100, 0.1, username=username)
        if 'choices' in subject_query and len(subject_query['choices']) > 0 and 'message' in subject_query['choices'][0] and 'content' in subject_query['choices'][0]['message']:
            subject = subject_query['choices'][0]['message']['content']
        else:
            process_dict['error'] = "subject_query does not contain the required elements"

        if subject.lower() == 'none':
            subject = new_messages

        process_dict[category] = {}
        parsed_data = self.process_observation(subject)
        results_list = []
        process_dict[category]['query_results'] = {}
        for data in parsed_data:
            data_results = await self.search_memory(category, data, username, min_distance=0.0, max_distance=2.0, n_results=10)
            # Initialize the list for this data item in the dictionary
            process_dict[category]['query_results'][data] = []
            for result in data_results:
                if result.get('id') not in seen_ids:
                    seen_ids.add(result.get('id'))
                    id = result.get('id')
                    id = id.lstrip('0') or '0'
                    document = result.get('document')
                    distance = round(result.get('distance'), 3)
                    results_list.append((id, document, distance))
                    # Add the result to the list for this data item
                    process_dict[category]['query_results'][data].append((id, document, distance))

        process_dict['results_list_before_token_check'] = results_list.copy()
        result_string = ''
        result_string = '\n'.join(f"({id}) {document} (score: {distance})" for id, document, distance in results_list)
        token_count = utils.MessageParser.num_tokens_from_string(result_string)
        while token_count > min(1000,remaining_tokens):
            if len(results_list) > 1:
                results_list.sort(key=lambda x: int(x[2]), reverse=True)
                results_list.pop(0)
                result_string = '\n'.join(f"({id}) {document} (score: {distance})" for id, document, distance in results_list)
            else:
                # If there's only one entry, shorten the document content
                id, document, distance = results_list[0]
                document = document[:-100]
                result_string = f"({id}) {document} (score: {distance})"
            token_count = utils.MessageParser.num_tokens_from_string(result_string)

        unique_results = set()  # Create a set to store unique results
        for id, document, distance in results_list:
            unique_results.add((id, document, distance))
            results_list.sort(key=lambda x: int(x[0]))
        result_string = '\n'.join(f"({id}) {document} (score: {distance})" for id, document, distance in results_list)

        process_dict['results_list_after_token_check'] = results_list
        process_dict['result_string'] = result_string
        process_dict['token_count'] = token_count
        if verbose:
            await utils.MessageSender.send_message({"type": "relations", "content": process_dict}, "blue", username)
        return result_string, token_count, unique_results

    
    async def process_incoming_memory(self, category, content, username=None, remaining_tokens=1000, verbose=False):
        """Process the incoming memory and return the updated active brain data."""
        process_dict = {'input': content}
        logger.debug(f"Processing incoming memory: {content}")
        self.openai_manager.set_username(username)
        subject_query = await self.openai_manager.ask_openai(content, 'categorise_query', self.model_used, 100, 0.1, username=username)
        if 'choices' in subject_query and len(subject_query['choices']) > 0:
            choice = subject_query['choices'][0]
            if 'message' in choice and 'content' in choice['message']:
                subject = choice['message']['content']
            else:
                logger.error("Error: choice does not contain 'message' or 'content'")
        else:
            logger.error("Error: subject_query does not contain 'choices' or 'choices' is empty")
        subject = subject_query['choices'][0]['message']['content']
        
        if subject.lower() == 'none' or subject.lower() == "'none'" or subject.lower() == '"none"' or subject.lower() == '""':
            subject = 'personal_information: ' + content

        result_string = ''
        parts = self.process_category_query(subject)

        if len(parts) < 1:
            logger.error("Error: parts does not contain the required elements")
            process_dict['error'] = "parts does not contain the required elements"
        else:
            unique_results = set()
            for part in parts:
                category, query = part
                process_dict[category] = {}
                process_dict[category]['query_results'] = {}
                process_dict[category]['query_results'][query] = []
                search_result, new_process_dict = await self.search_queries(category, [query], username, process_dict[category]['query_results'][query])
                process_dict[category]['query_results'][query] = new_process_dict
                for id, document, distance in process_dict[category]['query_results'][query]:
                    try:
                        unique_results.add((id, document, distance))
                    except Exception as e:
                        logger.error(f"Error while adding result to unique_results: {e}")
                result_string += search_result
                result_string = '\n'.join(f"({id}) {document} (score: {distance})" for id, document, distance in unique_results)

        # Check tokens
        token_count = utils.MessageParser.num_tokens_from_string(result_string)
        while token_count > min(1000,remaining_tokens):
            # Split the result_string by newline and remove the last line if possible
            result_lines = result_string.split('\n')
            if len(result_lines) > 1:
                result_lines.pop(-1)
                result_string = '\n'.join(result_lines)
            else:
                # If there are no newline characters, remove a certain number of characters from the end
                result_string = result_string[:-100]
            token_count = utils.MessageParser.num_tokens_from_string(result_string)

        similar_messages = None
        if len(parts) > 0:
            for part in parts:
                category, query = part
                similar_messages = await self.search_memory(category, content, username, max_distance=0.15, n_results=10)

        if similar_messages:
            logger.debug("Not adding to memory, message is similar to a previous message(s):")
            process_dict['similar_messages'] = [(m['document'], m['id'], m['distance']) for m in similar_messages]
            process_dict['created_new_memory'] = 'no'
            for similar_message in similar_messages:
                    logger.debug(f"({similar_message['id']}) {similar_message['document']} - score: {similar_message['distance']}")
        else:
            self.openai_manager.set_username(username)
            subject_category = await self.openai_manager.ask_openai(content, 'categorise', self.model_used, 100, 0.1, username=username)
            if 'choices' in subject_category and len(subject_category['choices']) > 0 and 'message' in subject_category['choices'][0] and 'content' in subject_category['choices'][0]['message']:
                category = subject_category['choices'][0]['message']['content']
            else:
                logger.error("Error: subject_query does not contain the required elements")
            category = subject_category['choices'][0]['message']['content']
            
            if category.lower() == 'none':
                category = content

            categories = self.process_category(category)
            uid = secrets.token_hex(10)
            for category in categories:
                chunks = await self.split_text_into_chunks(content, 150, 25)
                for chunk in chunks:
                    # Create a memory for each chunk
                    await self.create_memory(category, chunk, username=username, metadata={'uid': uid})
                    logger.debug(f"adding memory: {chunk} to category: {category}")
            process_dict['created_new_memory'] = 'yes, categories: ' + ', '.join(categories)
            
        process_dict['result_string'] = result_string
        process_dict['token_count'] = token_count
        if verbose:
            await utils.MessageSender.send_message({"type": "relations", "content": process_dict}, "blue", username)
        return result_string, token_count, unique_results
    
    async def search_queries(self, category, queries, username, process_dict):
        """Search the queries in the memory and return the results."""
        seen_ids = set()
        full_search_result = ''
        for query in queries:
            search_result = await self.search_memory(category, query, username, n_results=10)
            for result in search_result:
                if result.get('id') not in seen_ids:
                    seen_ids.add(result.get('id'))
                    id = result.get('id')
                    id = id.lstrip('0') or '0'
                    document = result.get('document')
                    distance = round(result.get('distance'), 3)
                    full_search_result += f"({id}) {document} - score: {distance}\n"
                    process_dict.append((id, document, distance))
        return full_search_result, process_dict

    
    async def process_incoming_memory_assistant(self, category, content, username=None):
        """Process the incoming memory and return the updated active brain data."""
        logger.debug(f"Processing incoming memory: {content}")
        
        # search for the queries in the memory
        full_search_result, not_needed = await self.search_queries(category, [content], username, process_dict=[])

        # Check if a similar message already exists
        similar_messages = await self.search_memory(category, content, username, max_distance=0.15)

        if similar_messages:
            logger.debug("Message is similar to a previous message(s):")
            for similar_message in similar_messages:
                logger.debug(f"({similar_message['id']}) {similar_message['document']} - score: {similar_message['distance']}")
        else:
            # If no similar message, create a new memory
            uid = secrets.token_hex(10)
            chunks = await self.split_text_into_chunks(content, 150, 25)
            for chunk in chunks:
                # Create a memory for each chunk
                await self.create_memory(category, chunk, username=username, metadata={'uid': uid})
                logger.debug(f"adding memory: {chunk} to category: {category}")
        #print(f"Search results: {full_search_result}")
        return

    def process_observation(self, string):
        """Process the observation and returns each part"""
        parts = string.split('\n')
        # remove the : and the space after it
        parts = [part.split(':', 1)[1].lstrip() if ':' in part else part for part in parts]
        #print(f"Queries: {parts}")
        return parts
    
    def process_category_query(self, string):
        """Process the input data and return the results"""
        lines = string.split('\n')
        result = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.split(': ')
            if len(parts) != 2:
                continue
            category, query = parts
            category = category.lower().replace(' ', '_')
            result.append((category, query))
        return result    
    
    def process_category(self, string):
        """Process the input data and return the results"""
        lines = string.split('\n')
        result = []
        for line in lines:
            if not line.strip():
                continue
            result.append(line.lower().replace(' ', '_'))
        return result
    
    
    async def note_taking(self, content, message, user_dir, username, show=True, verbose=False):
        max_tokens = 1000
        process_dict = {
            'actions': [],
            'content': content,
            'message': message,
            'timestamp': None,
            'final_message': None,
            'note_taking_query': None,
            'files_content_string': None,
            'error': None,
        }

        filedir = "notes"
        filedir = os.path.join(user_dir, username, filedir)
        if not os.path.exists(filedir):
            os.makedirs(filedir)
        
        dir_list = os.listdir(filedir)
        files_content_string = ''
        for file in dir_list:
            with open(f"{filedir}/{file}", "r") as f:
                files_content_string += f"{file}:\n{f.read()}\n\n"
        
        process_dict['files_content_string'] = files_content_string

        token_count = utils.MessageParser.num_tokens_from_string(files_content_string)
        if token_count > max_tokens:
            new_files_content_string = ''
            # take each file, ask gpt to summarize it, and overwrite the original file with the summary
            for file in dir_list:
                # calculate tokens based on max tokens divided by the number of files
                max_tokens_per_file = max_tokens / len(dir_list)
                current_file = f"{filedir}/{file}"
                with open(current_file, "r") as f:
                    file_content = f.read()
                    self.openai_manager.set_username(username)
                    summary = await self.openai_manager.ask_openai(file_content, 'summary_memory', self.model_used, int(max_tokens_per_file), 0.1, username=username)
                    with open(current_file, "w") as f:
                        new_content = summary['choices'][0]['message']['content']
                        f.write(new_content)
                        new_files_content_string += f"{file}:\n{new_content}\n\n"
            files_content_string = new_files_content_string

        if show:
            return f"{files_content_string}"

        else:
            timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
            process_dict['timestamp'] = timestamp

            # count tokens of the message
            token_count = utils.MessageParser.num_tokens_from_string(message)
            if token_count > 500:
                # summarize the message
                self.openai_manager.set_username(username)
                message = await self.openai_manager.ask_openai(message, 'summarize', self.model_used, 500, 0.1, username=username)
                message = message['choices'][0]['message']['content']

            final_message = f"Current Time: {timestamp}\nCurrent Notes:\n{files_content_string}\n\nRelated messages:\n{content}\n\nLast Message:{message}\n"
            process_dict['final_message'] = final_message

            retry_count = 0
            while retry_count < 5:
                try:
                    # todo: inform gpt about the remaining tokens available, if it exceeds the limit, summarize the existing list and purge unneeded items
                    self.openai_manager.set_username(username)
                    note_taking_query = await self.openai_manager.ask_openai(final_message, 'notetaker', self.model_used, 1000, 0.1, username=username)
                    process_dict['note_taking_query'] = json.dumps(note_taking_query)
                    actions = self.process_note_taking_query(note_taking_query)
                    break  # If no error, break the loop
                except json.decoder.JSONDecodeError:
                    logger.error("Error in JSON decoding, retrying...")
                    retry_count += 1 
            else:
                logger.error("Error in JSON decoding, exceeded retry limit.")
            process_dict['actions'] = actions

            for action, file, content in actions:
                if action == "create":
                    with open(f"{filedir}/{file}", "w") as f:
                        f.write(content)
                elif action == "add":
                    with open(f"{filedir}/{file}", "a") as f:
                        if f.tell() != 0 and not content.startswith('\n'):
                            f.write('\n')
                        f.write(content)
                elif action == "read":
                    if not os.path.exists(f"{filedir}/{file}"):
                        process_dict['error'] = "Error: File does not exist"
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
                    process_dict['error'] = "Error: Invalid action"

        if verbose:
            await utils.MessageSender.send_message({"type": "note_taking", "content": process_dict}, "blue", username)
        return await self.note_taking(content, message, user_dir, username, show=True)


    def process_note_taking_query(self, query):
        # extract the actions from the query
        actions = []
        if 'choices' in query and len(query['choices']) > 0 and 'message' in query['choices'][0] and 'content' in query['choices'][0]['message']:
            # parse the query as json
            try:
                    query_string = query['choices'][0]['message']['content'].replace('\n', '\\n')
                    if not query_string.startswith('['):
                        query_string = '[' + query_string
                    if not query_string.endswith(']'):
                        query_string = query_string + ']'
                    query_json = json.loads(query_string)
            except:
                logger.error("Error: query is not valid json: " + query['choices'][0]['message']['content'])
                return actions

            # check if query_json is a list or a single object
            if isinstance(query_json, list):
                # loop through each action in the query
                for action_dict in query_json:
                    # extract the action, file and content from the action
                    if 'action' in action_dict and 'file' in action_dict and 'content' in action_dict:
                        action = action_dict['action']
                        file = action_dict['file']
                        content = action_dict['content']
                        actions.append((action, file, content))
                    else:
                        logger.error("Error: action list does not contain the required elements: " + str(action_dict))
            elif isinstance(query_json, dict):
                # extract the action, file and content from the action
                if 'action' in query_json and 'file' in query_json and 'content' in query_json:
                    action = query_json['action']
                    file = query_json['file']
                    content = query_json['content']
                    actions.append((action, file, content))
                else:
                    logger.error("Error: action does not contain the required elements: " + str(query_json))

        else:
            logger.error("Error: query does not contain the required elements")

        return actions


class OpenAIManager:
    """A class to manage the OpenAI API."""
    def set_username(self, username):
        self.username = username

    def __init__(self):
        async def log_response_headers(session, trace_config_ctx, params: aiohttp.TraceRequestEndParams):
                # Extract the headers
                tokens_used = params.response.headers['x-ratelimit-remaining-tokens']
                requests_remaining = params.response.headers['x-ratelimit-remaining-requests']
                tokens_limit = params.response.headers['x-ratelimit-limit-tokens']
                requests_limit = params.response.headers['x-ratelimit-limit-requests']

                # Calculate the usage
                tokens_usage = (1 - int(tokens_used) / int(tokens_limit)) * 100
                requests_usage = (1 - int(requests_remaining) / int(requests_limit)) * 100

                # Print the normal usage
                logger.debug(f'OpenAI tokens used: {tokens_used} ({tokens_usage:.2f}% of limit)')
                logger.debug(f'OpenAI requests remaining: {requests_remaining} ({requests_usage:.2f}% of limit)')
                await utils.MessageSender.send_message({"type": "rate_limit", "content": {"message": f"tokens_usage: " + str(round(tokens_usage, 2)) + "%, requests_usage: " + str(round(requests_usage, 2)) + "%"}}, "blue", self.username)

                # Print the warning if above 50% of the rate limit
                if tokens_usage > 50 or requests_usage > 50:
                    logger.warning('WARNING: You have used more than 50% of your rate limit.')
                    await utils.MessageSender.send_message({"type": "rate_limit", "content": {"warning": "WARNING: You have used more than 50% of your rate limit."}}, "blue", self.username)

                # Print the error if above rate limit
                if tokens_usage >= 100 or requests_usage >= 100:
                    logger.error('ERROR: You have exceeded your rate limit: tokens_usage: ' + str(tokens_usage) + '%, requests_usage: ' + str(requests_usage) + '%')
                    await utils.MessageSender.send_message({"type": "rate_limit", "content": {"error": "ERROR: You have exceeded your rate limit: tokens_usage: " + str(tokens_usage) + "%, requests_usage: " + str(requests_usage) + "%"}}, "blue", self.username)

        self.trace_config = aiohttp.TraceConfig()
        self.trace_config.on_request_end.append(log_response_headers)

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(5))
    async def ask_openai(self, prompt, role, model_choice='gpt-4-0613', tokens=1000, temp=0.1, username=None):
        """Ask the OpenAI API a question and return the response."""
        now = time.time()
        current_date_time = time.strftime("%d/%m/%Y %H:%M:%S")
        role_content = self.get_role_content(role, current_date_time)

        session = aiohttp.ClientSession(trace_configs=[self.trace_config])
        openai.aiosession.set(session)

        try:
            messages = [
                {"role": "system", "content": role_content},
                {"role": "user", "content": prompt},
            ]

            response = await openai.ChatCompletion.acreate(
                model=model_choice,
                messages=messages,
                temperature=temp,
                max_tokens=tokens,
                stream=False
            )

            elapsed = time.time() - now
            logger.info('OpenAI response time: ' + str(elapsed) + 's\n')
            logger.info(f"Completion tokens: {response['usage']['completion_tokens']}, Prompt tokens: {response['usage']['prompt_tokens']}, Total tokens: {response['usage']['total_tokens']}")
            await utils.MessageSender.update_token_usage(response, username, brain=True, elapsed=elapsed)
            return response

        except Exception as e:
            logger.error(e)
            raise e

        finally:
            await session.close()


    def get_role_content(self, role, current_date_time):
        """Return the content for the role."""
        role_content = "You are an ChatGPT-powered chat bot."
        if role == 'machine':
            role_content = "You are a computer program attempting to comply with the user's wishes."
        if role == 'brain':
            role_content = f"""Your role is an AI Brain Emulation. You will receive two types of data: 'old active_brain data' and 'new messages'. Each new message will be associated with a specific user. Your task is to update the 'old active_brain data' for each individual user, based on the 'new messages' you receive.
            You should focus on retaining important keywords, instructions, numbers, dates, and events from each user. You can add or remove categories per user request. However, it's crucial that you retain and do not mix up information between users. Each user's data should be kept separate and not influence the data of others. New memories should be added instantly.
            Also, DO NOT include any recent or last messages, home info, settings or observations in the updated data. Any incoming data that falls into these categories must be discarded and not stored in the 'active_brain data'.
            The output must be in a structured plain text format, and the total word count of the updated data for each user should not exceed 300 words.  the current date is: '{current_date_time}'.
            Remember, the goal is to mimic a human brain's ability to retain important information while forgetting irrelevant details. Please follow these instructions carefully. If nothing changes, return the old active_brain data in a a structured plain text format with nothing in front or behind!"""
        if role == 'subject':
            role_content = "What is the observed entity in the following observation? If no entity is observed, say None. Only reply with the observed entity, nothing else."
        if role == 'observation':
            role_content = "You get a small chathistory and a last message. Break the last message down in 4 search queries to retrieve relevant messages with a cross-encoder. A subject, 2 queries, a category. Only reply in this format: subject\nquery\nquery\ncategory"
        if role == 'categorise_query':
            role_content = "You get a small chathistory and a last message. Break the last message down in a category (Factual Information, Personal Information, Procedural Knowledge, Conceptual Knowledge, Meta-knowledge or Temporal Information) and a search query to retrieve relevant messages with a cross-encoder. 1 category and 1 query per line. Only reply in this format: category: query\ncategory: query\n,..\nExample:\nProcedural Knowledge: Antony shared my memory code\nPersonal Information: Antony created me\n"
        if role == 'categorise':
            role_content = "You get a small chathistory and a last message. Break the last message down in a category (Factual Information, Personal Information, Procedural Knowledge, Conceptual Knowledge, Meta-knowledge or Temporal Information). 1 category per line. Only reply in this format: category\ncategory\n\nExample:\nProcedural Knowledge\nPersonal Information\n"
        if role == 'retriever':
            role_content = "You get a small chathistory and a last message. Break the last message down in multiple search queries to retrieve relevant messages with a cross-encoder. Only reply in this format: query\nquery\n,...\nExample:\nWhat is the capital of France?\nInfo about the capital of France\n"
        if role == 'notetaker':
            role_content = "You are a note and task processing Assistant. You get a list of the current notes, a small chathistory and a last message. Your task is to determine if the last message should be added or if existing notes should be updated or deleted. Only store memories if explicitly asked or things like shopping lists, reminders, the user's info, procedural instructions,.. DO NOT store Imperative Instructions, or chat history or regular messages! Remove completed tasks or questions. Use timestamps only if needed. Reply in an escaped json format with the following keys: 'action' (add, create, delete, update, skip), 'file' (shoppinglist, notes, etc.), 'content' (the message to be added, updated, deleted, etc.), comma separated, when updating a list repeat the whole updates list or the rest gets removed. Example: [ {\"action\": \"create\", \"file\": \"shoppinglist\", \"content\": \"cookies\"}, {\"action\": \"update\", \"file\": \"shoppinglist\", \"content\": \"cookies\napples\nbananas\npotatoes\"} ]"
        if role == 'summary_memory':
            role_content = "You are a memory summarizer. You get a list of the current notes, your task is to summarize the current notes as short as possible while maintaining all details. Only keep memories worth remembering, like shopping lists, reminders, procedural instructions,.. DO NOT store Imperative Instructions! Use timestamps only if needed. Reply in a plain text format with only the notes, nothing else."
        if role == 'summarize':
            role_content = "You are a summarizer. Your task is to summarize the current message as short as possible while maintaining all details. Reply in a plain text format with only the summary, nothing else."
        if role == 'date-extractor':
            role_content = f"The date is {current_date_time}.\nYou are a date extractor. You get a small chathistory and a last message. Your task is to extract the target date from the last message. Only reply with the date in one of these date formats %d-%m-%Y or %d-%m-%Y %H:%M:%S or with 'none', nothing else. Do not include the time if not asked for. Example: user asked for info about yesterday, you reply with '25/09/2023', user asked for info about 2 days ago around noon, you reply with '23/09/2023 12:00:00'."
        return role_content