import asyncio
import importlib
import inspect
import json
import ast
import os
import sys
import time
import uuid
from fastapi.responses import JSONResponse, PlainTextResponse
import openai
from fastapi import HTTPException, BackgroundTasks, UploadFile
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import chromadb
from elevenlabs import generate, play, set_api_key
import requests
import urllib3
from brain import BrainManager
from classes import AsciiColors
from werkzeug.utils import secure_filename
import routes
from pathlib import Path
from config import api_keys


# Set ElevenLabs API key
set_api_key(api_keys['elevenlabs'])

# Parameters for OpenAI
openai_model = api_keys['chatgpt_model']
max_responses = 1
temperature = 0.1
max_tokens = 512


last_messages = {}

COT_RETRIES = {}

async def send_debug(message, number, color, username):
    """Send a debug message to the user and print it to the console with a color, 1 is llm debug, 2 is system debug"""
    new_message = ''
    if number <= 2:
        # add a horizontal line in front and after the message
        message = f"{'-' * 50}\n{message}\n{'-' * 50}"  
        #socketio.send(json.dumps({'debug' + str(number): message, 'color': color}))
        new_message = f"debug{number}:{color}: \n{message}"
    else:
        new_message = message
    await routes.send_debug_message(username, new_message)
    # print the message to the console with the color
    print(f"{getattr(AsciiColors, color.upper())}{new_message}{AsciiColors.END}")
    #socketio.sleep(0.01)

async def send_message(message, color, username):
    """Send a debug message to the user and print it to the console with a color, 1 is llm debug, 2 is system debug"""
    new_message = ''
    
    new_message = f"{message}"
    
    await routes.send_debug_message(username, new_message)
    # print the message to the console with the color
    print(f"{getattr(AsciiColors, color.upper())}{new_message}{AsciiColors.END}")
    #socketio.sleep(0.01)

async def load_addons(username, users_dir):
    settings = {}

    function_dict = {}
    function_metadata = []

    module_timestamps = {}

    # create the username folder if it doesn't exist
    user_path = os.path.join(users_dir, username)
    settings_file = os.path.join(user_path, 'settings.json')

    # create the user dir if it doesn't exist
    if not os.path.exists(user_path):
        os.makedirs(user_path)

    # create the settings file if it doesn't exist
    if not os.path.exists(settings_file):
        with open(settings_file, 'w') as f:
            json.dump({}, f)

    # Load the settings
    with open(settings_file, 'r') as f:
        settings = json.load(f)

    # Check if voice input and output settings exist in settings
    if 'voice_input' not in settings:
        settings['voice_input'] = False
    if 'voice_output' not in settings:
        settings['voice_output'] = False

    # Check if addons in settings exist in addons folder
    for addon in list(settings.keys()):
        if addon not in ['voice_input', 'voice_output'] and not os.path.exists(os.path.join('addons', f"{addon}.py")):
            # If addon doesn't exist, remove it from settings
            del settings[addon]

    for filename in os.listdir('addons'):
        if filename.endswith('.py'):
            addon_name = filename[:-3]
            # Check if the addon is in the settings
            if addon_name not in settings:
                # If not, add it with a default value of False
                settings[addon_name] = False

            if settings.get(addon_name, True):
                file_path = os.path.join('addons', filename)
                spec = importlib.util.spec_from_file_location(filename[:-3], file_path)
                module = importlib.util.module_from_spec(spec)

                # Check if the module has been modified since it was last imported
                file_timestamp = os.path.getmtime(file_path)
                if filename in module_timestamps and file_timestamp > module_timestamps[filename]:
                    module = importlib.reload(module)
                module_timestamps[filename] = file_timestamp

                spec.loader.exec_module(module)

                # Check if the module name exists in the module's dictionary
                if module.__name__ in module.__dict__:
                    function_dict[module.__name__] = module.__dict__[module.__name__]

                    # Check if the module has a doc and parameters attribute
                    function_metadata.append({
                        "name": module.__name__,
                        "description": getattr(module, 'description', 'No description'),
                        "parameters": getattr(module, 'parameters', 'No parameters'),
                    })
                else:
                    await send_debug(f"Module {module.__name__} does not have a function with the same name.", 2, 'red', username)

    # Write the new settings back to the file
    with open(settings_file, 'w') as f:
        json.dump(settings, f)

    if not function_metadata:
        # no functions activated, quick hacky fix -> add a default function
        function_metadata.append({
            "name": "none",
            "description": "you have no available functions",
            "parameters": {
                "type": "object",
                "properties": {
                },
            },
        })

    return function_dict, function_metadata

class OpenAIResponser:

    error503 = "OpenAI server is busy, try again later"
    
    def __init__(self, openai_model, temperature, max_tokens, max_responses):
        self.openai_model = openai_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_responses = max_responses

    async def get_response(self, messages, stream=False, function_metadata=None, function_call="auto"):
        if function_metadata is None:
            function_metadata = [{
                "name": "none",
                "description": "you have no available functions",
                "parameters": {
                    "type": "object",
                    "properties": {
                    },
                },
            }]
        try:
            response = await openai.ChatCompletion.acreate(
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
            )
        except Exception as e:
            print("Error from openAI:", str(e))
            raise HTTPException(503, self.error503)
        try:
            return response
        except Exception as e:
            print(f"OpenAI Response ({'Streaming' if stream else 'Non-Streaming'}) Error: " + str(e))
            raise HTTPException(503, self.error503)

    async def get_response_stream(self, messages):
        response = await self.get_response(messages, stream=True)
        print("Streaming response")
        for chunk in response:
            current_content = chunk["choices"][0]["delta"].get("content", "")
            yield current_content

async def upload_audio(user_dir, username, audio_file: UploadFile, background_tasks: BackgroundTasks):
    # save the file to the user's folder
    userdir = os.path.join(user_dir, username)
    filename = secure_filename(audio_file.filename)
    audio_dir = os.path.join(userdir, 'audio')
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)
    filepath = os.path.join(audio_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(audio_file.file.read())

    # Now you can use the saved file path to transcribe the audio
    transcription = await transcribe_audio(filepath)
    return {'transcription': transcription}


async def transcribe_audio(audio_file_path):
    with open(audio_file_path, 'rb') as audio_file:
        transcription = await openai.Audio.atranscribe(
            model = "whisper-1",
            file =  audio_file,
            language = "en", # af for the drone demo?
            api_key=api_keys['openai']
            )
    return transcription['text']


async def generate_audio(text, username, users_dir):
    # make sure the dir exists
    audio_dir = os.path.join(users_dir, username, 'audio')
    Path(audio_dir).mkdir(parents=True, exist_ok=True)
    audio_path = os.path.join(audio_dir, f'{uuid.uuid4()}.mp3')
    # find pairs of 3 backticks and strip the code inside them including the backticks
    # because we don't want to generate audio for code blocks
    code_blocks = []
    code_block_start = 0
    code_block_end = 0
    for i in range(len(text)):
        if text[i:i+3] == '```':
            if code_block_start == 0:
                code_block_start = i
            else:
                code_block_end = i
                code_blocks.append(text[code_block_start:code_block_end+3])
                code_block_start = 0
                code_block_end = 0
    for code_block in code_blocks:
        text = text.replace(code_block, '')

    audio = generate(
        text=text,
        voice="ThT5KcBeYPX3keUQqHPh",
        model="eleven_multilingual_v1"
        )
    try:
        with open(audio_path, 'wb') as f:
            f.write(audio)

        return audio_path, audio

    except Exception as e:
        return print(e)

async def load_brain(username, users_dir):
    user_dir = os.path.join(users_dir, username)
    brain_path = os.path.join(user_dir, 'kw_brain.txt')
    Path(user_dir).mkdir(parents=True, exist_ok=True)
    if not os.path.exists(brain_path):
        with open(brain_path, 'w') as f:
            start_brain_path = os.path.join('data', 'kw_brain_start.txt')
            with open(start_brain_path, 'r') as f2:
                f.write(f2.read())
    with open(brain_path, 'r') as f:
        return f.read()
    
def write_brain(brain, username, users_dir):
    user_dir = os.path.join(users_dir, username)
    brain_path = os.path.join(user_dir, 'kw_brain.txt')
    with open(brain_path, 'w') as f:
        f.write(brain)

def extract_content(data):
    try:
        response = json.loads(data)
    except:
        return data
    if isinstance(response, dict):
        if 'content' in response:
            return extract_content(response['content'])
    return response

async def get_drone_state(username):
    try:
        # call the drone API for drone state
        url = "http://localhost:8000/api/vehicle/3/llm/state"
        response = requests.get(url)
        if response.status_code == 200:
            final_response = 'Drone state:\n' + json.dumps(response.json(), indent=4, sort_keys=True) + '\n'
            return final_response
        else:
            return "Drone state: Failed to get state"
    except requests.exceptions.ConnectionError as e:
        await send_debug(f"ConnectionError: {e}\nSkipping drone state", 2, 'red', username)
        return "Drone state: Failed to get drone state"


async def process_message(og_message, username, background_tasks: BackgroundTasks, users_dir):
        chat_history = []
        chat_metadata = []
        history_ids = []

        function_dict, function_metadata = await load_addons(username, users_dir)

        # load the setting for the user
        settings = {}
        settings_file = os.path.join(users_dir, username, 'settings.json')
        with open(settings_file, 'r') as f:
            settings = json.load(f)

        message = username + ': ' + og_message

        old_kw_brain = {}
        kw_brain_string = ''

        history_string = ''
        last_messages_string = ''

        
        if not function_metadata:
            # add a default function
            function_metadata.append({
                "name": "none",
                "description": "you have no available functions",
                "parameters": {
                    "type": "object",
                    "properties": {
                    },
                },
            })

        old_kw_brain = await load_brain(username, users_dir)

        current_date_time = time.strftime("%d/%m/%Y %H:%M:%S")
        if username not in last_messages:  # If the user doesn't exist in the dictionary, add them
            last_messages[username] = []

        if last_messages[username] != []:
            last_messages_string = '\n'.join(last_messages[username][-10:])
        else:
            last_messages_string = 'No messages yet.'

        brainManager = BrainManager()
        result_length = 0
        results = await brainManager.run(message, last_messages_string, username, users_dir)

        if results is not None and 'documents' in results and results['documents']:
            result_length = len(results['documents'])

        # send the results to debug in a human readable way format Result: {'ids': ['e8972ed9-7411-4391-93e5-29a2da9a120e'], 'embeddings': None, 'metadatas': [{'role': 'assistant'}], 'documents': ['Hello Alice! How can I assist you today?']}
        result_string = ''
        for i in range(result_length):
            role = results['metadatas'][i]['role']
            if role == 'user':
                result_string += f"Result {i}: {results['documents'][i]} (score: {round(results['distances'][i], 3)})\n"
                history_string += f"{results['documents'][i]} (score: {round(results['distances'][i], 3)})\n"
            else:
                result_string += f"Result {i}: {results['metadatas'][i]['role']}: {results['documents'][i]} (score: {round(results['distances'][i], 3)})\n"
                history_string += f"Assistant: {results['documents'][i]} (score: {round(results['distances'][i], 3)})\n"
        await send_debug(f"Fetching relevant past messages\nbased on the message:\n'{message}'\nResult length: {result_length}\n\nResults:\n{result_string}", 2, 'pink', username)
        
        home_info = ''
        try:
            # call the house API for home info
            # todo: make this configurable in the frontend
            home_info = requests.get(api_keys['house_api_url'] + 'home_info?key=' + api_keys['house_api_key']).text
        except requests.exceptions.ConnectionError as e:
            await send_debug(f"ConnectionError: {e}\nSkipping home info", 2, 'red', username)
        # check if the home info is empty
        if home_info == '':
            home_info = "No home info available."
        else:
            await send_debug(f"Home info: {home_info}", 2, 'cyan', username)

# {await get_drone_state(username)}
        instruction_string = f"""
Observations:
{{"object":"house","coordinates":[45,65]}}
{{"object":"car","coordinates":[12,43]}}

Home info:
{home_info}
"""

        kw_brain_string = old_kw_brain

        full_message = f"You are talking to {username}\nActive Brain Module (read this carefully as it contains important instructions):\n{kw_brain_string}\n\nMost relevant past messages (higher score = better relevancy):\n{history_string}\n\n10 most recent messages:\n{last_messages_string}\n\n{instruction_string}\n\nEverything above this line is for context only, only reply to the last message.\nLast message: {message}"

        await send_debug(f'Full prompt:\n{full_message}', 1, 'cyan', username)

        #response = generate_response(messages, function_dict, function_metadata)
        response = await start_chain_thoughts(full_message, og_message, username, users_dir)
        await send_debug(f"Response after CoT: {response}", 1, 'green', username)
        
        response = extract_content(response)
        response = json.dumps({'content': response})
        response = json.loads(response)

        await send_debug(f"Response after CoT json loads: {response}", 1, 'green', username)

        if 'function_call' in response:
            function_call_name = response['function_call']['name']
            function_call_arguments = response['function_call']['arguments']
            await send_debug(f"[Executing {function_call_name} function with arguments: {function_call_arguments}]", 3, 'green', username)
            #socketio.send(json.dumps({'content': '[Executing ' + function_call_name + ' function with arguments: ' + str(function_call_arguments) + ']'}), room=user_id)
            #socketio.sleep(0.01)
            
            response = await process_function_call_pm(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, False, background_tasks)
            return response
        else:
            #write_brain(json_str, username)
            await send_debug(f"{message}", 1, 'green', username)
            await send_debug(f"Assistant: {response['content']}", 1, 'pink', username)
            if response['content'] is not None:
                chat_metadata.append({"role": "user"})
                chat_history.append(message)
                last_messages[username].append(f"{username}: "  + message)
                chat_metadata.append({"role": "assistant"})
                chat_history.append(str(response['content']))
                last_messages[username].append("assistant: " + str(response['content']))
                history_ids.append(str(uuid.uuid4()))
                history_ids.append(str(uuid.uuid4()))
                brainManager.add_to_collection(chat_history, chat_metadata, history_ids)
                background_tasks.add_task(keyword_generation, response['content'], username, history_string, last_messages_string, old_kw_brain, users_dir)
                if settings.get('voice_output', True):
                    # audio_path, audio = await generate_audio(response['content'], username)
                    return response
                    # socketio.send(json.dumps({'content': response['content'], 'audio': audio_path}), room=user_id)
                    # socketio.sleep(0.01)
                    # socketio.send(json.dumps({'end': 'true'}), room=user_id)
                    # socketio.sleep(0.01)
                    #play(audio)
                else:
                    # socketio.send(json.dumps({'content': response['content']}), room=user_id)
                    # socketio.sleep(0.01)
                    # socketio.send(json.dumps({'end': 'true'}), room=user_id)
                    # socketio.sleep(0.01)
                    return response

async def keyword_generation(message, username, history_string, last_messages_string, old_kw_brain, users_dir):
    # Generate a new kw_brain
    almost_full_message = f"Most relevant past messages (higher score = better relevancy):\n{history_string}\n\n10 most recent messages:\n{last_messages_string}\n\nLast message: {message}"
    kw_brain = await generate_keywords(almost_full_message, old_kw_brain, username)
    json_str = kw_brain
    kw_brain_string = ''
    full_brain_string = f"Old Brain Data: {old_kw_brain}\n\nNew messages:\n{almost_full_message}\n\n"
    
    kw_brain_string = json_str
    file_message = {
        "prompt": str(full_brain_string) + ' ->',
        "completion": ' ' + str(kw_brain_string)
    }
    # save the user message and bot message to a file
    brain_responses_file = os.path.join('data', 'brain_responses.jsonl')
    with open(brain_responses_file, 'a') as f:
        f.write(json.dumps(file_message) + '\n')
    write_brain(json_str, username, users_dir)
    await send_debug(f"New Brain Data: {json_str}", 2, 'cyan', username)

async def start_chain_thoughts(message, og_message, username, users_dir):
    function_dict, function_metadata = await load_addons(username, users_dir)
    kw_brain_string = await load_brain(username, users_dir)
    messages = [
        {"role": "system", "content": f'You are a GoodAI chat Agent. Instructions or messages towards you memory or brain will be handled by a different module, just confirm those messages. Else, write a reply in the form of SAY: what to say, or PLAN: a step plan, separated with newlines between steps. each step is a function call and its instructions, nothing else!\nEither PLAN, or SAY something, but not both. Do NOT use function calls straight away, make a plan first, this plan will be executed step by step by another ai, so include all the details in as few steps as possible!'},
        {"role": "user", "content": f'\n\nRemember, SAY: what to say, or PLAN: a step plan, separated with newlines between steps. Example: Plan: 1. this is step 1\n2. this is step 2\n\n{message}'},
    ]

    openai_response = OpenAIResponser(openai_model, temperature, max_tokens, max_responses)
    response = await openai_response.get_response(messages, function_metadata=function_metadata)

    final_response = response
    
    await send_debug(f"cot final_response: {final_response}", 1, 'green', username)
    cot_response = await process_chain_thoughts(response, message, og_message, function_dict, function_metadata, username, users_dir)
    await send_debug(f"cot_response: {cot_response}", 1, 'green', username)
    
    # try:
    #     return_string = json.dumps({'content': cot_response})
    # except:
    #     await send_debug(f"can't parse cot_response: {cot_response}", 2, 'red', username)
    #     try:
    #         return_string = cot_response['content']
    #     except:
    #         await send_debug(f"can't parse cot_response 2nd time: {cot_response}", 2, 'red', username)

    return cot_response

async def process_chain_thoughts(full_response, message, og_message, function_dict, function_metadata, username, users_dir):
    kw_brain_string = await load_brain(username, users_dir)
    response = full_response['choices'][0]['message']
    # if its a function call anyway, process it
    if 'function_call' in response:
        function_call_name = response['function_call']['name']
        function_call_arguments = response['function_call']['arguments']
        await send_debug(f"[Executing {function_call_name} function with arguments: {function_call_arguments}]", 3, 'green', username)
        #socketio.send(json.dumps({'content': '[Executing ' + function_call_name + ' function with arguments: ' + str(function_call_arguments) + ']'}), room=user_id)
        #socketio.sleep(0.01)
        response = await process_function_call_ct(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, False, users_dir, full_response)
        return response
    
    # check if the final response starts with SAY: or PLAN:
    final_response = full_response['choices'][0]['message']['content']
    if final_response.startswith('SAY:'):
        # remove SAY: from the final response
        final_response = final_response.replace('SAY:', '')
        # remove leading and trailing whitespace
        final_response = final_response.strip()
        # send the final response to the user
        #send(json.dumps({'content': final_response}))
        #socketio.sleep(0.1)
        return final_response
    
    elif final_response.startswith('PLAN:'):
        await send_message(f"[{final_response}]", 'green', username)
        # remove PLAN: from the final response
        final_response = final_response.replace('PLAN:', '')
        # remove leading and trailing whitespace
        final_response = final_response.strip()
        # split the final response into a list of steps
        steps = final_response.split('\n')  # Splitting the string at each newline
        steps = [step.strip() for step in steps if step]  # Remove any empty strings from the list
        
        # If there's only 1 step, take each number as a step
        if len(steps) == 1 and steps[0].isdigit():
            steps = list(steps[0])

        # If no different steps, take the whole text as a step
        if len(set(steps)) == 1:
            steps = [final_response]

        # create a string of the steps
        steps_list = []
        for i, step in enumerate(steps):
            await send_debug(f"processing step: {step}", 1, 'green', username)
            # convert the list to a string before passing it to process_cot_messages
            steps_string = ''.join(steps_list)
            response = await process_cot_messages(step, steps_string, function_dict, function_metadata, og_message, username, users_dir, message)
            # truncate the response string if it's not one of the last three steps
            response_str = str(response)
            if i < len(steps) - 3:
                truncated_response = response_str
            else:
                truncated_response = response_str
            steps_list.append('step:' + step + '\nresponse:' + truncated_response + '\n')
        # convert the final list to a string
        steps_string = ''.join(steps_list)
        return await summarize_cot_responses(steps_string, message, og_message, username, users_dir)


    else:
        await send_debug(f"Invalid response: {final_response}", 1, 'red', username)
        await send_debug(f"retrying CoT...", 1, 'red', username)
        await start_chain_thoughts(message, og_message, username, users_dir)
    

async def generate_keywords(prompt, old_kw_brain, username):
    current_date_time = time.strftime("%d/%m/%Y %H:%M:%S")
    system_message = f"""Your role is an AI Brain Emulation. You will receive two types of data: 'old active_brain data' and 'new messages'. Each new message will be associated with a specific user. Your task is to update the 'old active_brain data' for each individual user, based on the 'new messages' you receive.
You should focus on retaining important keywords, instructions, numbers, dates, and events from each user. You can add or remove categories per user request. However, it's crucial that you retain and do not mix up information between users. Each user's data should be kept separate and not influence the data of others. New memories should be added instantly.
Also, DO NOT include any recent or last messages, home info, settings or observations in the updated data. Any incoming data that falls into these categories must be discarded and not stored in the 'active_brain data'.
The output must be in a structured plain text format, and the total word count of the updated data for each user should not exceed 300 words.  the current date is: '{current_date_time}'.
Remember, the goal is to mimic a human brain's ability to retain important information while forgetting irrelevant details. Please follow these instructions carefully. If nothing changes, return the old active_brain data in a a structured plain text format with nothing in front or behind!"""

    new_message = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': f' If nothing changes, return the old active_brain data in a structured plain text format with nothing in front or behind!\nOld active_brain Data: {old_kw_brain}\n\nNew messages:\n{prompt}\n\n'},
    ]
    
    openai_response = OpenAIResponser(openai_model, temperature, max_tokens, max_responses)
    response = await openai_response.get_response(new_message)

    await send_debug(f"kw resp: {response}", 1, 'green', username)
    return response['choices'][0]['message']['content']


def convert_function_call_arguments(function_call_arguments):
    # If function_call_arguments is a string representation of a dictionary
    if isinstance(function_call_arguments, str):
        try:
            # Try to convert the string into a dictionary
            converted_function_call_arguments = json.loads(function_call_arguments)
        except json.JSONDecodeError:
            print(f'Could not convert {function_call_arguments} to a dictionary using json.loads')
            try:
                converted_function_call_arguments = ast.literal_eval(function_call_arguments)
            except:
                print(f'Could not convert {function_call_arguments} to a dictionary using ast.literal_eval')
                try:
                    # decode the string into a dictionary
                    converted_function_call_arguments = urllib3.parse.unquote(function_call_arguments)
                except:
                    print(f'Could not convert {function_call_arguments} to a dictionary using urllib3.parse.unquote')
                    # If the conversion fails, return the original string
                    converted_function_call_arguments = function_call_arguments
    # If function_call_arguments is already a dictionary
    elif isinstance(function_call_arguments, dict):
        # Just return it as is
        converted_function_call_arguments = function_call_arguments
    else:
        # If function_call_arguments is neither a string nor a dictionary, return it as is
        converted_function_call_arguments = function_call_arguments

    return converted_function_call_arguments

async def process_function_call_fm(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, merge=True, users_dir='users/', steps_string=''):
    try:
        converted_function_call_arguments = convert_function_call_arguments(function_call_arguments)
    except:
        process_final_message(message, og_message, function_dict, function_metadata, username, users_dir)
        raise

    await send_debug(f'function {function_call_name} call arguments: {str(function_call_arguments)}', 1, 'blue', username)

    function = function_dict[function_call_name]
    if inspect.iscoroutinefunction(function):
        function_response = await function(**converted_function_call_arguments)
    else:
        function_response = function(**converted_function_call_arguments)
    return await process_function_reply(function_call_name, function_response, message, og_message, function_dict, function_metadata, username, merge, users_dir)

async def process_function_call_ct(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, merge=True, users_dir='users/', steps_string='', full_response=None):
    try:
        converted_function_call_arguments = convert_function_call_arguments(function_call_arguments)
    except:
        process_chain_thoughts(full_response, message, og_message, function_dict, function_metadata, username, users_dir)
        raise

    await send_debug(f'function {function_call_name} call arguments: {str(function_call_arguments)}', 1, 'blue', username)

    function = function_dict[function_call_name]
    if inspect.iscoroutinefunction(function):
        function_response = await function(**converted_function_call_arguments)
    else:
        function_response = function(**converted_function_call_arguments)
    return await process_function_reply(function_call_name, function_response, message, og_message, function_dict, function_metadata, username, merge, users_dir)

async def process_function_call_ctm(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, merge=True, users_dir='users/', steps_string='', full_response=None):
    try:
        converted_function_call_arguments = convert_function_call_arguments(function_call_arguments)
    except:
        process_cot_messages(message, steps_string, function_dict, function_metadata, og_message, username, users_dir)
        raise

    await send_debug(f'function {function_call_name} call arguments: {str(function_call_arguments)}', 1, 'blue', username)

    function = function_dict[function_call_name]
    if inspect.iscoroutinefunction(function):
        function_response = await function(**converted_function_call_arguments)
    else:
        function_response = function(**converted_function_call_arguments)
    return await process_function_reply(function_call_name, function_response, message, og_message, function_dict, function_metadata, username, merge, users_dir)


async def process_function_call_pm(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, merge=True, users_dir='users/', steps_string='', background_tasks: BackgroundTasks = None):
    try:
        converted_function_call_arguments = convert_function_call_arguments(function_call_arguments)
    except:
        process_message(og_message, username, background_tasks, users_dir)
        raise

    await send_debug(f'function {function_call_name} call arguments: {str(function_call_arguments)}', 1, 'blue', username)

    function = function_dict[function_call_name]
    if inspect.iscoroutinefunction(function):
        function_response = await function(**converted_function_call_arguments)
    else:
        function_response = function(**converted_function_call_arguments)
    return await process_function_reply(function_call_name, function_response, message, og_message, function_dict, function_metadata, username, merge, users_dir)

async def process_cot_messages(message, steps_string, function_dict, function_metadata, og_message, username, users_dir, full_message=''):
        function_dict, function_metadata = await load_addons(username, users_dir)
        kw_brain_string = await load_brain(username, users_dir)
        messages = [
            {"role": "system", "content": f'You are executing functions for the user step by step, focus on the current step only, the rest of the info is for context only. Don\'t say you can\'t do things or can\'t write complex code because you can.'},
            {"role": "user", "content": f'Memory:{full_message}--end memory--\n\nPrevious steps and the results: {steps_string}\n\nCurrent step: {message}\nUse a function call or write a short reply, nothing else\nEither write a short reply or use a function call, but not both.  Don\'t say you can\'t do things or can\'t write complex code because you can. Just do it.'},
        ]
        await send_debug(f"process_cot_messages messages: {messages}", 1, 'red', username)

        openai_response = OpenAIResponser(openai_model, temperature, max_tokens, max_responses)
        response = await openai_response.get_response(messages, function_metadata=function_metadata)

        await send_debug(f"process_cot_messages response: {response}", 2, 'red', username)
        response = response['choices'][0]['message']

        if 'function_call' in response:
            function_call_name = response['function_call']['name']
            function_call_arguments = response['function_call']['arguments']
            await send_debug(f"[Executing {function_call_name} function with arguments: {function_call_arguments}]", 3, 'green', username)
            #socketio.send(json.dumps({'content': '[Executing ' + function_call_name + ' function with arguments: ' + str(function_call_arguments) + ']'}), room=user_id)
            #socketio.sleep(0.01)
            response = await process_function_call_ctm(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, False, users_dir, steps_string)
            return response
        else:
            await send_debug(f'{response}', 1, 'green', username)
            return response['content']

async def summarize_cot_responses(steps_string, message, og_message, username, users_dir):
    global COT_RETRIES
    # kw_brain_string = await load_brain(username, users_dir)
    # add user to COT_RETRIES if they don't exist
    if username not in COT_RETRIES:
        COT_RETRIES[username] = 0
    function_dict, function_metadata = await load_addons(username, users_dir)
    if COT_RETRIES[username] > 1:
        await send_debug(f'Too many CoT retries, skipping...', 1, 'red', username)
        messages = [
            {"role": "system", "content": f'You have executed some functions for the user and here are the results, Communicate directly and actively in short with the user about what you have done. The user did not see any of the results yet. Respond with YES: <your summary>'},
            {"role": "user", "content": f'Steps Results:\n{steps_string}\nOnly reply with YES: <your summary> or a new plan, nothing else. Communicate directly and actively in short with the user about what you have done. The user did not see any of the steps results yet, so repeat everything in short. Respond with YES: <your summary>'},
        ]
        COT_RETRIES[username] = 0
    else:
        messages = [
            {"role": "system", "content": f'You have executed some functions for the user and here are the results, Communicate directly and actively in short with the user about what you have done. The user did not see any of the results yet. Are the results sufficient? If so, respond with YES: <your summary>, if not, respond with what you need to do next. Do not repeat succesful steps.'},
            {"role": "user", "content": f'Steps Results:\n{steps_string}\nOnly reply with YES: <your summary> or a new plan, nothing else. Communicate directly and actively in short with the user about what you have done. The user did not see any of the steps results yet, so repeat everything in short. Are the results sufficient? If so, respond with YES: <your summary>, if not, respond with what you need to do next. Do not repeat succesful steps.'},
        ]

    openai_response = OpenAIResponser(openai_model, temperature, max_tokens, max_responses)
    response = await openai_response.get_response(messages, function_metadata=function_metadata)

    #print(f"process_cot_messages response: {response}")
    response = response['choices'][0]['message']['content']
    #return response
    if response.startswith('YES: '):
        COT_RETRIES[username] = 0
        # remove the YES: part
        response = response[5:]
        return response
    else:
        COT_RETRIES[username] += 1
        return await process_final_message(message, og_message, response, username, users_dir)

async def process_function_reply(function_call_name, function_response, message, og_message, function_dict, function_metadata, username, merge=True, users_dir='users/'):
    await send_debug(f'processing function {function_call_name} response: {str(function_response)}', 1, 'pink', username)
    await send_message(f'[function response: {str(function_response)}]', 'red', username)

    second_response = None
    function_dict, function_metadata = await load_addons(username, users_dir)
    
    messages=[
                {"role": "system", "content": f'You have executed a function for the user, here is the result of the function call, Communicate directly and actively in a short conversational manner with the user about what you have done. The user only needs a summary of the result, do not repeat the results literally, respond in human readable language only.'},
                {"role": "user", "content": f'{message}'},
                {
                    "role": "function",
                    "name": function_call_name,
                    "content": str(function_response),
                },
            ]
    openai_response = OpenAIResponser(openai_model, temperature, max_tokens, max_responses)
    second_response = await openai_response.get_response(messages)

    #print(f'{AsciiColors.YELLOW}second_response: {second_response}{AsciiColors.END}')
    final_response = second_response["choices"][0]["message"]["content"]

    final_message_string = f"Function {function_call_name} response: {str(function_response)}\n\n{final_response}"
    if merge:
        return final_message_string
    else:
        return final_response

async def process_final_message(message, og_message, response, username, users_dir):
    kw_brain_string = await load_brain(username, users_dir)
    if response.startswith('YES: '):
        # remove the YES: part
        response = await response[5:]
        return response
        
    function_dict, function_metadata = await load_addons(username, users_dir)

    if not function_metadata:
        # add a default function
        function_metadata.append({
            "name": "none",
            "description": "you have no available functions",
            "parameters": {
                "type": "object",
                "properties": {
                },
            },
        })

    current_date_time = time.strftime("%d/%m/%Y %H:%M:%S")

    last_messages_string = '\n'.join(last_messages[username][-10:])

    full_message = f"Relevant info: {message}\n\nEverything above this line is for context only!\n\nThe user asked for {og_message}\nYour last response was:\n\n{response}\n\nTry to complete your task again with the new information."

    await send_debug(f'{full_message}', 1, 'cyan', username)

    #response = generate_response(messages, function_dict, function_metadata)
    response = await start_chain_thoughts(full_message, og_message, username, users_dir)

    fc_check = None
    try:
        fc_check = json.loads(response)
    except:
        fc_check = response

    response = extract_content(response)

    await send_debug(f"Retry CoT Response: {response}", 1, 'green', username)

    if 'function_call' in fc_check:
        function_call_name = fc_check['function_call']['name']
        function_call_arguments = fc_check['function_call']['arguments']
        await send_debug(f"[Executing {function_call_name} function with arguments: {function_call_arguments}]", 3, 'green', username)
        # socketio.send(json.dumps({'content': '[Executing ' + function_call_name + ' function with arguments: ' + str(function_call_arguments) + ']'}))
        # socketio.sleep(0.01)
        new_fc_check = await process_function_call_fm(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username)
        return new_fc_check
    else:
        await send_debug(f'{message}', 1, 'green', username)
        await send_debug(f'Assistant: {response}', 1, 'pink', username)

        # if settings.get('voice_output', True):
        #     audio_path, audio = generate_audio(response['content'])
        #     socketio.send(json.dumps({'content': response['content'], 'audio': audio_path}))
        #     socketio.sleep(0.1)
        #     socketio.send(json.dumps({'end': 'true'}))
        #     play(audio)
        #     return response['content']
        # else:
        #     socketio.send(json.dumps({'content': response['content']}))
        #     socketio.sleep(0.1)
        #     socketio.send(json.dumps({'end': 'true'}))
        #     return response['content']
        return response
    

def check_api_keys():
    OPENAI_API_KEY = api_keys['openai']
    if not len(OPENAI_API_KEY):
        print("Please set OPENAI_API_KEY environment variable. Exiting.")
        sys.exit(1)
