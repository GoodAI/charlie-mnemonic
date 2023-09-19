import json
import os
import time
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
)
import utils

class MemoryManager:
    """A class to manage the memory of the agent."""
    def __init__(self):
        self.openai_manager = OpenAIManager()
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

    async def search_memory(self, category, search_term, username=None, min_distance=0.0, max_distance=1.0, contains_text=None, n_results=5):
        """Search the memory and return the results."""
        return search_memory(category, search_term, username=username, min_distance=min_distance, max_distance=max_distance, contains_text=contains_text, n_results=n_results)

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
    
    async def process_active_brain(self, new_messages, username=None, all_messages=None, remaining_tokens=1000):
        category = 'active_brain'
        similar_messages = await self.search_memory(category, new_messages, username, max_distance=0.15)
        seen_ids = set()

        if similar_messages:
            print("Message is similar to a previous message(s):")
            for similar_message in similar_messages:
                print(f"{similar_message['document']} with id {similar_message['id']} and distance {similar_message['distance']}")
        else:
            await self.create_memory(category, new_messages, username=username)
            print(f"adding to memory: {new_messages}")

        subject_query = await self.openai_manager.ask_openai(all_messages, 'retriever', 'gpt-4-0613', 100, 0.1, username=username)
        if 'choices' in subject_query and len(subject_query['choices']) > 0 and 'message' in subject_query['choices'][0] and 'content' in subject_query['choices'][0]['message']:
            subject = subject_query['choices'][0]['message']['content']
        else:
            print("Error: subject_query does not contain the required elements")

        if subject.lower() == 'none':
            subject = new_messages

        parsed_data = self.process_observation(subject)
        results_list = []
        for data in parsed_data:
            print(f"Category: {category}, Query: {data}")
            results = await self.search_memory(category, data, username, min_distance=0.0, max_distance=2.0, n_results=15)
            for result in results:
                if result.get('id') not in seen_ids:
                    seen_ids.add(result.get('id'))
                    id = result.get('id')
                    id = id.lstrip('0') or '0'
                    document = result.get('document')
                    distance = round(result.get('distance'), 3)
                    results_list.append((id, document, distance))

                    for i in range(-2, 3):
                        if i == 0:
                            continue
                        prev_next_id = str(int(id) + i).zfill(16)
                        if prev_next_id not in seen_ids:
                            prev_next_memory = await self.get_memory(category, prev_next_id, username=username)
                            if prev_next_memory:
                                seen_ids.add(prev_next_id)
                                stripped_id = prev_next_id.lstrip('0') or '0'
                                results_list.append((stripped_id, prev_next_memory['document'], distance))
        result_string =''
        # Check tokens
        result_string = '\n'.join(f"({id}) {document} (score: {distance})" for id, document, distance in results_list)
        token_count = utils.MessageParser.num_tokens_from_string(result_string)
        while token_count > remaining_tokens:
            # Sort results by distance and remove the one with the highest distance
            results_list.sort(key=lambda x: int(x[2]), reverse=True)
            results_list.pop(0)
            result_string = '\n'.join(f"({id}) {document} (score: {distance})" for id, document, distance in results_list)
            token_count = utils.MessageParser.num_tokens_from_string(result_string)

        # Sort the results list by ID after checking for token limit
        results_list.sort(key=lambda x: int(x[0]))
        result_string = '\n'.join(f"({id}) {document} (score: {distance})" for id, document, distance in results_list)

        print(f"Search results: {result_string}")
        return result_string, token_count

    
    async def process_incoming_memory(self, category, content, username=None, remaining_tokens=1000):
        """Process the incoming memory and return the updated active brain data."""
        print(f"Processing incoming memory: {content}")
        subject_query = await self.openai_manager.ask_openai(content, 'categorise', 'gpt-4-0613', 100, 0.1, username=username)
        if 'choices' in subject_query and len(subject_query['choices']) > 0 and 'message' in subject_query['choices'][0] and 'content' in subject_query['choices'][0]['message']:
            subject = subject_query['choices'][0]['message']['content']
        else:
            print("Error: subject_query does not contain the required elements")
        subject = subject_query['choices'][0]['message']['content']
        print(f"Subject: {subject}")
        
        if subject.lower() == 'none':
            subject = content

        result_string = ''
        parts = self.process_category_query(subject)
        if len(parts) < 1:
            print("Error: parts does not contain the required elements")
        else:
            for part in parts:
                category, query = part
                search_result = await self.search_queries(category, [query], username)
                result_string += search_result

        # Check tokens
        token_count = utils.MessageParser.num_tokens_from_string(result_string)
        while token_count > remaining_tokens:
            # Split the result_string by newline and remove the last line
            result_lines = result_string.split('\n')
            result_lines.pop(-1)
            result_string = '\n'.join(result_lines)
            token_count = utils.MessageParser.num_tokens_from_string(result_string)

        print(f"Search results: {result_string}")

        similar_messages = await self.search_memory(category, content, username, max_distance=0.15, n_results=10)

        if similar_messages:
            print("Message is similar to a previous message(s):")
            for similar_message in similar_messages:
                    print(f"({similar_message['id']}) {similar_message['document']} - score: {similar_message['distance']}")
        else:
            await self.create_memory(category, content, username=username)
            print(f"adding to memory: {content}")
        return result_string, token_count

    
    async def process_incoming_memory_assistant(self, category, content, username=None):
        """Process the incoming memory and return the updated active brain data."""
        print(f"Processing incoming memory: {content}")
        
        # search for the queries in the memory
        full_search_result = await self.search_queries(category, [content], username)

        
        # Check if a similar message already exists
        similar_messages = await self.search_memory(category, content, username, max_distance=0.15)

        if similar_messages:
            print("Message is similar to a previous message(s):")
            for similar_message in similar_messages:
                print(f"({similar_message['id']}) {similar_message['document']} - score: {similar_message['distance']}")
        else:
            # If no similar message, create a new memory
            await self.create_memory(category, content, username=username)
            print(f"adding to memory: {content}")
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
            category, query = line.split(': ')
            category = category.lower().replace(' ', '_')
            result.append((category, query))
        return result
    
    async def search_queries(self, category, queries, username):
        """Search the queries in the memory and return the results."""
        seen_ids = set()
        full_search_result = ''
        for query in queries:
            search_result = await self.search_memory(category, query, username, n_results=10)
            for result in search_result:
                if result.get('id') not in seen_ids:  # Only add the result if its ID hasn't been seen yet
                    seen_ids.add(result.get('id'))  # Add the ID to the set of seen IDs
                    id = result.get('id')
                    # id format is 0000000000000019, remove the leading zeros, unless it's only zeros, then keep 1 zero
                    id = id.lstrip('0') or '0'
                    document = result.get('document')
                    distance = round(result.get('distance'), 3)
                    full_search_result += f"({id}) {document} - score: {distance}\n"
        return full_search_result
    
    async def note_taking(self, content, message, user_dir, username, show=True):
        """function to process note taking memory, used to keep notes, lists, tasks, etc."""
        # read the notes directory in the user's folder
        filedir = "notes"
        filedir = os.path.join(user_dir, username, filedir)
        # check if the directory exists, if not, create it
        if not os.path.exists(filedir):
            os.makedirs(filedir)
        # print the files and folders in the directory
        dir_list = os.listdir(filedir)
        # print the content of each file
        files_content_string = ''
        for file in dir_list:
            with open(f"{filedir}/{file}", "r") as f:
                files_content_string += f"{file}:\n{f.read()}\n\n"
        if show:
            return f"{files_content_string}"

        else:
            timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
            # ask gpt-4 if the new message should be added to one of the existing notes or if a new note should be created
            final_message = f"Current Time: {timestamp}\nCurrent Notes:\n{files_content_string}\n\nRelated messages:\n{content}\n\nLast Message:{message}\n"
            print(f"Final message: {final_message}")
            note_taking_query = await self.openai_manager.ask_openai(final_message, 'notetaker', 'gpt-4-0613', 100, 0.1, username=username)
            print(f"Note taking query: {note_taking_query}")
            # process the query and perform the action
            action, file, content = self.process_note_taking_query(note_taking_query)
            print(f"Action: {action}, File: {file}, Content: {content}")

            # depending on the action, perform the corresponding operation
            if action == "create":
                # create a new file with the given content
                with open(f"{filedir}/{file}", "w") as f:
                    f.write(content)
            elif action == "add":
                # append the content to the existing file
                with open(f"{filedir}/{file}", "a") as f:
                    # add newline if the file is not empty and the content does not start with a newline
                    if f.tell() != 0 and not content.startswith('\n'):
                        f.write('\n')
                    f.write(content)
            elif action == "read":
                # if the file does not exist, return an error
                if not os.path.exists(f"{filedir}/{file}"):
                    return "Error: File does not exist"
                # read the content of the file
                with open(f"{filedir}/{file}", "r") as f:
                    print(f.read())
            elif action == "delete":
                # if content is empty, delete the file
                if not content:
                    os.remove(f"{filedir}/{file}")
                # else, delete a line from the file
                else:
                    with open(f"{filedir}/{file}", "r") as f:
                        lines = f.readlines()
                    with open(f"{filedir}/{file}", "w") as f:
                        for line in lines:
                            if line.strip("\n") != content:
                                f.write(line)
            elif action == "update":
                # update the content of the file
                with open(f"{filedir}/{file}", "w") as f:
                    f.write(content)
            elif action == "skip":
                # do nothing
                pass
            else:
                print("Error: Invalid action")
            # return the content of the files
            return await self.note_taking(content, message, user_dir, username, show=True)

    def process_note_taking_query(self, query):
        # extract the action, file and content from the query
        action, file, content = None, None, None
        if 'choices' in query and len(query['choices']) > 0 and 'message' in query['choices'][0] and 'content' in query['choices'][0]['message']:
            # parse the query as json
            query_json = json.loads(query['choices'][0]['message']['content'])
            # extract the action, file and content from the query
            if 'action' in query_json and 'file' in query_json and 'content' in query_json:
                action = query_json['action']
                file = query_json['file']
                content = query_json['content']
            else:
                print("Error: query does not contain the required elements")
        else:
            print("Error: query does not contain the required elements")
        return action, file, content



class OpenAIManager:
    """A class to manage the OpenAI API."""
    @retry(stop=stop_after_attempt(10), wait=wait_fixed(5))
    async def ask_openai(self, prompt, role, model_choice='gpt-4-0613', tokens=400, temp=0.1, username=None):
        """Ask the OpenAI API a question and return the response."""
        #print(colored(f"Prompt: {prompt}", 'red'))
        now = time.time()
        current_date_time = time.strftime("%d/%m/%Y %H:%M:%S")
        role_content = self.get_role_content(role, current_date_time)

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
            print('\nOpenAI response time: ' + str(elapsed) + 's\n')
            print(f"Completion tokens: {response['usage']['completion_tokens']}, Prompt tokens: {response['usage']['prompt_tokens']}, Total tokens: {response['usage']['total_tokens']}")
            await utils.MessageSender.update_token_usage(response, username)
            return response

        except Exception as e:
            print(e)
            raise e

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
        if role == 'categorise':
            role_content = "You get a small chathistory and a last message. Break the last message down in a category (Factual Information, Personal Information, Procedural Knowledge, Conceptual Knowledge, Meta-knowledge or Temporal Information) and a search query to retrieve relevant messages with a cross-encoder. 1 category and 1 query per line. Only reply in this format: category: query\ncategory: query\n,..\nExample:\nProcedural Knowledge: Antony shared my memory code\nPersonal Information: Antony created me\n"
        if role == 'retriever':
            role_content = "You get a small chathistory and a last message. Break the last message down in multiple search queries to retrieve relevant messages with a cross-encoder. Only reply in this format: query\nquery\n,...\nExample:\nWhat is the capital of France?\nInfo about the capital of France\n"
        if role == 'notetaker':
            role_content = "You are a note and task processing Assistant. You get a list of the current notes, a small chathistory and a last message. Your task is to determine if the last message should be added, updated or deleted, how and where it should be stored. Only store memories worth noting down, like shopping lists, reminders, specific instructions,.. Use timestamps. Reply in a json format with the following keys: 'action' (read, add, create, delete, update, skip), 'file' (shoppinglist, notes, etc.), 'content' (the message to be added, updated, deleted, etc.), Example: {\"action\": \"update\", \"file\": \"shoppinglist\", \"content\": \"apples\nbananas\npotatoes\"}"
        return role_content