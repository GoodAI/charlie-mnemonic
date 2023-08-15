import asyncio
import uuid
import openai
import os
import time
from tenacity import retry, stop_after_attempt, wait_fixed
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import unittest
from termcolor import colored

import traceback

class Config:
    MAX_RETRY_ATTEMPTS = 10
    openai.api_key = os.environ["OPENAI_API_KEY"]



class DatabaseManager:
    def __init__(self):
        self.current_retry_attempt = 0

    @retry(stop=stop_after_attempt(Config.MAX_RETRY_ATTEMPTS), wait=wait_fixed(5))
    def init_db(self, memory_name):
        #EMBEDDING_MODEL = config.OPENAI_EMBEDDING_MODEL

        if not os.path.exists(memory_name):
            os.makedirs(memory_name)
        chroma_client = chromadb.PersistentClient(path=memory_name)
        if os.environ['PRODUCTION'] == 'false':
            from crossencoder import CrossEncoderEmbeddingFunction
            embedding_function = CrossEncoderEmbeddingFunction()
        else:
            # using openai on production for now because the server went OOM with the cross-encoder
            # revert to cross-encoder when we have a better server
            embedding_function = OpenAIEmbeddingFunction()
        collection = chroma_client.get_or_create_collection(name="conversations", embedding_function=embedding_function)
        collection_count = collection.count()
        print(f"LTM Entries: {collection_count}")
        return collection

    def add_to_collection(self, collection, chat_history, chat_metadata, history_ids):
        print(colored(f"Adding to collection: \n{chat_history}", 'blue'))
        try:
            for chat, meta, id in zip(chat_history, chat_metadata, history_ids):
                result = collection.get(where_document={"$contains":chat})
                containsExactMatch = False
                for doc in result['documents']:
                    if doc == chat:
                        containsExactMatch = True
                print(colored(f"Input: {chat}", 'blue'))
                print(colored(f"Result: {result}", 'blue'))
                # Check if the document already exists in the collection
                if containsExactMatch == False:
                    collection.add(
                        documents=[chat],
                        metadatas=[meta],
                        ids=[id]
                    )
                else:
                    print(colored(f"Document already exists in collection: {chat}", 'blue'))
        except (openai.error.APIError, openai.error.APIConnectionError, openai.error.RateLimitError) as e:
            error_messages = {
                openai.error.APIError: f"OpenAI API returned an API Error: {e}\nRetrying...",
                openai.error.APIConnectionError: f"Failed to connect to OpenAI API: {e}\nRetrying..",
                openai.error.RateLimitError: f"OpenAI API request exceeded rate limit: {e}\nRetrying.."
            }
            print(error_messages[type(e)])
            self.current_retry_attempt += 1
            if self.current_retry_attempt < Config.MAX_RETRY_ATTEMPTS:
                self.add_to_collection(collection, chat_history, chat_metadata, history_ids)
            else:
                print(f'Failed to add to collection: {chat_history}')
            return
        self.current_retry_attempt = 0

    def query_collection(self, collection, message, amount=10):
        result = None
        try:
            result = collection.query(
                    query_texts=[message],
                    n_results=min(collection.count(), amount)
            )
        except (openai.error.APIError, openai.error.APIConnectionError, openai.error.RateLimitError) as e:
            error_messages = {
                openai.error.APIError: f"OpenAI API returned an API Error: {e}\nRetrying...",
                openai.error.APIConnectionError: f"Failed to connect to OpenAI API: {e}\nRetrying..",
                openai.error.RateLimitError: f"OpenAI API request exceeded rate limit: {e}\nRetrying.."
            }
            print(error_messages[type(e)])
            self.current_retry_attempt += 1
            if self.current_retry_attempt < Config.MAX_RETRY_ATTEMPTS:
                self.query_collection(collection, message)
            else:
                print(f'Failed to query collection: {collection}')
            return
        self.current_retry_attempt = 0
        return result
    
    def process_observation(self, string):
        parts = string.split('\n')
        # remove the : and the space after it
        parts = [part.split(':', 1)[1].lstrip() if ':' in part else part for part in parts]
        print(colored(f"Queries: {parts}", 'blue'))
        return parts


class OpenAIManager:
    @retry(stop=stop_after_attempt(Config.MAX_RETRY_ATTEMPTS), wait=wait_fixed(5))
    async def ask_openai(self, prompt, role, model_choice='gpt-4-0613', tokens=400, temp=0.1):
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
            return response

        except Exception as e:
            print(e)
            raise e

    def get_role_content(self, role, current_date_time):
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
        return role_content

class TestQueryCollection(unittest.TestCase):
    def setUp(self):
        db_manager = DatabaseManager()
        self.collection = db_manager.init_db('memory2')
        print(colored('Initialized database', 'green'))
        print(colored(f"Collection count: {self.collection.count()}", 'green'))
        print(colored(f"Collection name: {self.collection.name}", 'green'))

    def test_query_collection(self):
        db_manager = DatabaseManager()
        predefined_messages = ['its antony, whats my favorite dish?', 'whats my favorite dish?', 'what do i like to eat?', 'whats antony his favorite dish?', 'what does antony like to eat?']  # Add your predefined messages here
        scores = {}
        for message in predefined_messages:
            result = db_manager.query_collection(self.collection, message)
            # Reverse the order of the results (for local llm)
            # result['documents'][0] = result['documents'][0][::-1]
            # result['distances'][0] = result['distances'][0][::-1]
            # result['metadatas'][0] = result['metadatas'][0][::-1]
            result_length = len(result['documents'][0])
            print(colored(f"Result length: {result_length}", 'blue'))
            result_string = 'Input: ' + message + '\nResults: \n'
            total_score = 0
            for i in range(result_length):
                score = round(result['distances'][0][i], 2)
                total_score += score
                if result['metadatas'][0][i]['role'] == 'user':
                    result_string += f"{result['documents'][0][i]} (score: {score})\n"
                else:
                    result_string += f"Assistant: {result['documents'][0][i]} (score: {score})\n"
            scores[message] = total_score
            print(colored(result_string, 'yellow'))
            print(colored(f"Total score: {total_score}", 'yellow'))

        winner = max(scores, key=scores.get)
        print(colored(f"Message: '{winner}' with a score of {scores[winner]}", "green"))

        for message in scores:
            if message != winner:
                print(colored(f"Message: '{message}' with a score of {scores[message]}", "red"))


class BrainManager:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.openai_manager = OpenAIManager()

    async def run(self, user_input, last_messages, memory_name='memory2', users_dir='users'):
        memory_file = os.path.join(users_dir, memory_name)
        self.collection = self.db_manager.init_db(memory_file)
        combined_messages = last_messages + "\nLast Message: " + user_input
        print(colored(f"Combined messages: {combined_messages}", 'blue'))
        try:
            # change this to a local llm for context extraction
            subject_query = await self.openai_manager.ask_openai(combined_messages, 'observation', 'gpt-4-0613', 100, 0.1)
            if 'choices' in subject_query and len(subject_query['choices']) > 0 and 'message' in subject_query['choices'][0] and 'content' in subject_query['choices'][0]['message']:
                subject = subject_query['choices'][0]['message']['content']
            else:
                print("Error: subject_query does not contain the required elements")
            subject = subject_query['choices'][0]['message']['content']
            print(colored(f"Subject: {subject}", 'green'))
            result = {'documents': [], 'distances': [], 'metadatas': []}

            if subject.lower() == 'none':
                subject = user_input
            
            queries = self.db_manager.process_observation(subject)

            if self.collection.count() > 0:
                query_result = [self.db_manager.query_collection(self.collection, key, 3) for key in [user_input] + queries]
                for res in query_result:
                    if isinstance(res['documents'], list) and isinstance(res['distances'], list) and isinstance(res['metadatas'], list):
                        min_len = min(len(res['documents'][0]), len(res['distances'][0]), len(res['metadatas'][0]))
                        for i in range(min(3, min_len)): 
                            result['documents'].append(res['documents'][0][i])
                            result['distances'].append(res['distances'][0][i])
                            result['metadatas'].append(res['metadatas'][0][i])
                    else:
                        print("One of the results is not a list or is empty.")



            # Remove duplicates and sort results by score
            zipped_results = list(zip(result['documents'], result['distances'], result['metadatas']))
            zipped_results = list(dict((x[0], x) for x in zipped_results).values())
            zipped_results.sort(key=lambda x: x[1], reverse=True)
            if zipped_results:
                result['documents'], result['distances'], result['metadatas'] = zip(*zipped_results)
            else:
                print("No results to unpack")
                result['documents'], result['distances'], result['metadatas'] = [], [], []

            result_length = len(result['documents'])
            print(colored(f"Result length: {result_length}", 'blue'))

            result_string = 'Input: ' + user_input + '\nResults: \n'
            total_score = 0
            for i in range(result_length):
                score = round(result['distances'][i], 2)
                total_score += score
                role = result['metadatas'][i]['role']
                if role == 'user':
                    result_string += f"{result['documents'][i]} (score: {score})\n"
                else:
                    result_string += f"{role.title()}: {result['documents'][i]} (score: {score})\n"
            
            print(colored(result_string, 'yellow'))


            # add the input to the collection
            # disabled for now, adding it to the collection when we get a reply from the llm
            # chat_history = [user_input]
            # chat_metadata = [{"role": "user"}]
            # history_ids = [str(uuid.uuid4())]
            #self.db_manager.add_to_collection(self.collection, chat_history, chat_metadata, history_ids)
            
            # return the list of results
            return result
        
        except Exception as e:
            print(f"An brain error occurred: {e}")
            traceback.print_exc()

    def add_to_collection(self, chat_history, chat_metadata, history_ids):
        self.db_manager.add_to_collection(self.collection, chat_history, chat_metadata, history_ids)



if __name__ == '__main__':
    # unittest.main()
    brainManager = BrainManager()

    while True:
        user_input = input('User: ')
        if user_input.lower() == 'exit':
            break
        asyncio.run(brainManager.run(user_input))
