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
from tenacity import retry, stop_after_attempt, wait_fixed
import aiohttp
import memory as _memory
import openai
from fastapi import HTTPException, BackgroundTasks, UploadFile
from elevenlabs import generate, play, set_api_key
from werkzeug.utils import secure_filename
import routes
from pathlib import Path
from config import api_keys
from database import Database
import tiktoken
from pydub import audio_segment
import logs


# Set ElevenLabs API key
set_api_key(api_keys['elevenlabs'])

# Parameters for OpenAI
openai_model = api_keys['chatgpt_model']
max_responses = 1
temperature = 0.2
max_tokens = 1000
last_messages = {}
COT_RETRIES = {}


    
logger = logs.Log(__name__, 'full_log.log').get_logger()

class MessageSender:
    """This class contains functions to send messages to the user"""
    @staticmethod
    async def send_debug(message, number, color, username):
        """Send a debug message to the user and print it to the console with a color"""
        if number <= 2:
            message = f"{'-' * 50}\n{message}\n{'-' * 50}"  
            new_message = {"debug": number, "color": color, "message": message}
        else:
            new_message = {"message": message}

        await routes.send_debug_message(username, json.dumps(new_message))
        # print the message to the console with the color
        # print(f"{getattr(AsciiColors, color.upper())}{new_message}{AsciiColors.END}")

    @staticmethod
    async def send_message(message, color, username):
        """Send a message to the user and print it to the console with a color"""
        await routes.send_debug_message(username, json.dumps(message))
        # print the message to the console with the color
        # print(f"{getattr(AsciiColors, color.upper())}{message}{AsciiColors.END}")

    @staticmethod
    async def update_token_usage(response, username, brain=False, elapsed=0):
        """Update the token usage in the database"""
        try:
            with Database() as db:
                result = db.update_token_usage(username, 
                    total_tokens_used=response['usage']['total_tokens'],
                    prompt_tokens=response['usage']['prompt_tokens'],
                    completion_tokens=response['usage']['completion_tokens']
                )
                if result is not None:
                    await MessageSender.send_debug(f"Last message: Prompt tokens: {response['usage']['prompt_tokens']}, Completion tokens: {response['usage']['completion_tokens']}\nTotal tokens used: {result[0]}, Prompt tokens: {result[1]}, Completion tokens: {result[2]}", 2, 'red', username)
                    # cost based on these formulas prompt: $0.03 / 1K tokens completion: $0.06 / 1K tokens
                    prompt_cost = round(response['usage']['prompt_tokens'] * 0.03 / 1000, 5)
                    completion_cost = round(response['usage']['completion_tokens'] * 0.06 / 1000, 5)
                    this_message_total_cost = round(prompt_cost + completion_cost, 5)

                    total_prompt_cost = round(result[1] * 0.03 / 1000, 5)
                    total_completion_cost = round(result[2] * 0.06 / 1000, 5)
                    total_cost = round(total_prompt_cost + total_completion_cost, 5)
                    await MessageSender.send_message({"usage": {"total_tokens": result[0], "total_cost": total_cost}}, 'red', username)

                
                daily_stats = db.get_daily_stats(username)
                if daily_stats is not None:
                    current_spending_count = daily_stats['spending_count'] or 0
                else:
                    current_spending_count = 0
                spending_count = current_spending_count + this_message_total_cost

                await MessageSender.send_message({"daily_usage": {"daily_cost": spending_count}}, 'red', username)
                # update the daily_stats table
                if brain:
                    db.update_daily_stats_token_usage(username,
                        brain_tokens=response['usage']['total_tokens'],
                        spending_count=this_message_total_cost
                    )
                else:
                    db.update_daily_stats_token_usage(username,
                        prompt_tokens=response['usage']['prompt_tokens'],
                        generation_tokens=response['usage']['completion_tokens'],
                        spending_count=this_message_total_cost
                    )
                current_stats_spending_count = db.get_statistic(username)['total_spending_count'] or 0
                spending_count = round(current_stats_spending_count + this_message_total_cost, 5)
                # update the statistics table
                db.update_statistic(username,
                    total_spending_count=spending_count
                )
                # update the elapsed time
                # get the total response time and response count from the database
                stats = db.get_daily_stats(username)
                if stats is not None:
                    total_response_time = stats['total_response_time'] or 0
                    response_count = stats['response_count'] or 0
                else:
                    total_response_time = 0
                    response_count = 0
                # update the total response time and response count
                total_response_time += elapsed
                response_count += 1

                # calculate the new average response time
                average_response_time = total_response_time / response_count

                db.replace_daily_stats_token_usage(username,
                                                total_response_time=total_response_time,
                                                average_response_time=average_response_time,
                                                response_count=response_count
                                                )
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
            await MessageSender.send_message({"error": "An error occurred: " + str(e)}, 'red', username)



class AddonManager:
    """This class contains functions to load addons"""
    @staticmethod
    async def load_addons(username, users_dir):
        default_settings = {
            "addons": {},
            "audio": { "voice_input": True, "voice_output": True },
            "avatar": { "avatar": False },
            "language": { "language": "en" },
            "system_prompt": { "system_prompt": "Not implemented yet" },
            "cot_enabled": { "cot_enabled": False },
            "verbose": { "verbose": False },
        }

        function_dict = {}
        function_metadata = []
        module_timestamps = {}

        user_path = os.path.join(users_dir, username)
        settings_file = os.path.join(user_path, 'settings.json')

        if not os.path.exists(user_path):
            os.makedirs(user_path)

        if not os.path.exists(settings_file):
            with open(settings_file, 'w') as f:
                json.dump(default_settings, f)

        with open(settings_file, 'r') as f:
            settings = json.load(f)

        # Validate and correct the settings
        for key, default_value in default_settings.items():
            # If the key is not in the settings or the type is not the same as the default value, set it to the default value
            if key not in settings or type(settings[key]) != type(default_value):
                settings[key] = default_value
            # If the key is a dict, validate and correct the sub keys
            elif isinstance(default_value, dict):
                for sub_key, sub_default_value in default_value.items():
                    if sub_key not in settings[key] or type(settings[key][sub_key]) != type(sub_default_value):
                        settings[key][sub_key] = sub_default_value

        # Save the settings
        with open(settings_file, 'w') as f:
            json.dump(settings, f)

        # Delete addons that don't exist anymore
        for addon in list(settings["addons"].keys()):
            if not os.path.exists(os.path.join('addons', f"{addon}.py")):
                del settings["addons"][addon]
        
        # Load addons
        for filename in os.listdir('addons'):
            if filename.endswith('.py'):
                addon_name = filename[:-3]
                if addon_name not in settings["addons"]:
                    settings["addons"][addon_name] = False

                # Only load the addon if it is enabled
                if settings["addons"].get(addon_name, True):
                    file_path = os.path.join('addons', filename)
                    spec = importlib.util.spec_from_file_location(filename[:-3], file_path)
                    module = importlib.util.module_from_spec(spec)

                    # Check if the module has been modified since it was last imported
                    file_timestamp = os.path.getmtime(file_path)
                    if filename in module_timestamps and file_timestamp > module_timestamps[filename]:
                        module = importlib.reload(module)
                    module_timestamps[filename] = file_timestamp

                    spec.loader.exec_module(module)

                    # Add the functions to the function dict
                    if module.__name__ in module.__dict__:
                        function_dict[module.__name__] = module.__dict__[module.__name__]

                        function_metadata.append({
                            "name": module.__name__,
                            "description": getattr(module, 'description', 'No description'),
                            "parameters": getattr(module, 'parameters', 'No parameters'),
                        })
                    else:
                        await MessageSender.send_debug(f"Module {module.__name__} does not have a function with the same name.", 2, 'red', username)

        with open(settings_file, 'w') as f:
            json.dump(settings, f)

        if not function_metadata:
            function_metadata.append({
                "name": "none",
                "description": "you have no available functions",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            })

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

        async def log_response_headers(session, trace_config_ctx, params: aiohttp.TraceRequestEndParams):
            # Extract the headers
            tokens_used = params.response.headers.get('x-ratelimit-remaining-tokens', 40000)
            requests_remaining = params.response.headers.get('x-ratelimit-remaining-requests', 200)
            tokens_limit = params.response.headers.get('x-ratelimit-limit-tokens', 40000)
            requests_limit = params.response.headers.get('x-ratelimit-limit-requests', 200)

            # Calculate the usage
            tokens_usage = (1 - int(tokens_used) / int(tokens_limit)) * 100
            requests_usage = (1 - int(requests_remaining) / int(requests_limit)) * 100

            # Print the normal usage
            # logger.debug(f'OpenAI tokens used: {tokens_used} ({tokens_usage:.2f}% of limit)')
            # logger.debug(f'OpenAI requests remaining: {requests_remaining} ({requests_usage:.2f}% of limit)')
            # await MessageSender.send_message({"type": "rate_limit", "content": {"message": f"tokens_usage: " + str(round(tokens_usage, 2)) + "%, requests_usage: " + str(round(requests_usage, 2)) + "%"}}, "blue", self.username)

            # Print the warning if above 50% of the rate limit
            if tokens_usage > 20 or requests_usage > 20:
                logger.warning('WARNING: You have used more than 20% of your rate limit.')
                await MessageSender.send_message({"type": "rate_limit", "content": {"warning": "WARNING: You have used more than 20% of your rate limit."}}, "blue", self.username)

            # Print the error if above rate limit
            if tokens_usage >= 100 or requests_usage >= 100:
                logger.error('ERROR: You have exceeded your rate limit: tokens_usage: ' + str(tokens_usage) + '%, requests_usage: ' + str(requests_usage) + '%')
                await MessageSender.send_message({"type": "rate_limit", "content": {"error": "ERROR: You have exceeded your rate limit: tokens_usage: " + str(tokens_usage) + "%, requests_usage: " + str(requests_usage) + "%"}}, "blue", self.username)


        self.trace_config = aiohttp.TraceConfig()
        self.trace_config.on_request_end.append(log_response_headers)

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
    async def get_response(self, username, messages, stream=False, function_metadata=None, function_call="auto"):
        if function_metadata is None:
            function_metadata = [{
                "name": "none",
                "description": "you have no available functions",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            }]

        max_retries = 5
        timeout = 180.0  # timeout in seconds
        now = time.time()

        session = aiohttp.ClientSession(trace_configs=[self.trace_config])
        openai.aiosession.set(session)

        try:
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
                        timeout=timeout
                    )
                    elapsed = time.time() - now
                    await MessageSender.update_token_usage(response, username, False, elapsed=elapsed)
                    return response
                except asyncio.TimeoutError:
                    logger.error(f"Request timed out, retrying {i+1}/{max_retries}")
                    await MessageSender.send_message({"error": f"Request timed out, retrying {i+1}/{max_retries}"}, "red", username)
                except Exception as e:
                    logger.error(f"Error from openAI: {str(e)}, retrying {i+1}/{max_retries}")
                    await MessageSender.send_message({"error": f"Error from openAI: {str(e)}, retrying {i+1}/{max_retries}"}, "red", username)

            logger.error("Max retries exceeded")
            await MessageSender.send_message({"error": "Max retries exceeded"}, "red", username)
            raise HTTPException(503, self.error503)

        finally:
            await session.close()


    # Todo: add a setting to enable/disable this feature and add the necessary code
    async def get_response_stream(self, messages):
        response = await self.get_response(messages, stream=True)
        logger.info("Streaming response")
        for chunk in response:
            current_content = chunk["choices"][0]["delta"].get("content", "")
            yield current_content

class AudioProcessor:
    """This class contains functions to process audio"""
    @staticmethod
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

        # check the audio for voice
        if not AudioProcessor.check_voice(filepath):
            return {'transcription': ''}

        # get the user settings language
        settings_file = os.path.join(userdir, 'settings.json')
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        language = settings.get('language', {}).get('language', 'en')

        # if no language is set, default to english
        if language is None:
            language = 'en'

        # use the saved file path to transcribe the audio
        transcription = await AudioProcessor.transcribe_audio(filepath, language)
        return {'transcription': transcription}

    @staticmethod
    def check_voice(filepath):
        audio = audio_segment.AudioSegment.from_file(filepath)
        if audio.dBFS < -40:  #  Decrease for quieter voices (-50), increase for louder voices (-20)
            logger.info('No voice detected, dBFS: ' + str(audio.dBFS))
            return False
        return True

    @staticmethod
    async def transcribe_audio(audio_file_path, language):
        with open(audio_file_path, 'rb') as audio_file:
            transcription = await openai.Audio.atranscribe(
                model = "whisper-1",
                file =  audio_file,
                language = language,
                api_key=api_keys['openai']
                )
        return transcription['text']

    @staticmethod
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
            # Todo: add a choice for different voices
            # change to a cheaper solution
            voice="ThT5KcBeYPX3keUQqHPh",
            model="eleven_multilingual_v1"
            )
        try:
            with open(audio_path, 'wb') as f:
                f.write(audio)

            return audio_path, audio

        except Exception as e:
            return logger.error(e)

class BrainProcessor:
    """This class contains functions to process the brain"""
    @staticmethod
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
        
    @staticmethod
    def write_brain(brain, username, users_dir):
        user_dir = os.path.join(users_dir, username)
        brain_path = os.path.join(user_dir, 'kw_brain.txt')
        with open(brain_path, 'w') as f:
            f.write(brain)

    
    @staticmethod
    async def delete_recent_messages(user):
        global last_messages
        last_messages[user] = []

class MessageParser:
    """This class contains functions to parse messages and generate responses"""
    @staticmethod
    def get_message(type, parameters):
        with Database() as db:
            display_name = db.get_display_name(parameters['username'])[0]
        """Parse the message based on the type and parameters"""
        if (type == 'start_message'):
            return f"You are talking to {display_name}\nMemory Module: (low score = better relevancy):\n{parameters['memory']}\n\n10 most recent messages:\n{parameters['last_messages_string']}\n\n{parameters['instruction_string']}\n\nEverything above this line is for context only, only reply to the last message.\nLast message: {parameters['message']}"
        elif (type == 'keyword_generation'):
            return f"Memory Module: (low score = better relevancy):\n{parameters['memory']}\n\n10 most recent messages:\n{parameters['last_messages_string']}\n\nLast message: {parameters['message']}"
        
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
                            message = f"This is an invalid function call argument json, rewrite it so it's a valid json, only reply with the rewritten json: Invalid json: {arguments}\nValid Json: "
                            logger.exception(f"Invalid json: {arguments}, username: {username}, trying to re-generate the message...")
                            print(f"Invalid json: {arguments}, username: {username}, trying to re-generate the message...")
                            messages = [
                                {"role": "system", "content": f'You are an award winning json fixer, fix the following invalid json, only reply with the rewritten json.'},
                                {"role": "user", "content": f'{message}'},
                            ]
                            openai_response = OpenAIResponser(openai_model, temperature, 1000, max_responses, username)
                            response = await openai_response.get_response(username, messages, stream=False, function_metadata=None, function_call="auto")
                            await MessageParser.convert_function_call_arguments(response['choices'][0]['message']['content'], username, False)
                        else:
                            logger.exception(f"Invalid json: {arguments}, username: {username}")
                            print(f"Invalid json: {arguments}, username: {username}")
                            return None
        # print(f"Arguments:\n{str(arguments)}")
        return arguments

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
    async def process_function_call(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, exception_handler, merge=True, users_dir='users/', steps_string='', full_response=None, background_tasks: BackgroundTasks = None):
        converted_function_call_arguments = await MessageParser.convert_function_call_arguments(function_call_arguments, username)
        # add the username to the arguments
        if converted_function_call_arguments is not None:
            converted_function_call_arguments['username'] = username
        else:
            logger.error("converted_function_call_arguments is None: " + str(function_call_arguments))
            return {"content": "error: converted_function_call_arguments is None: " + str(function_call_arguments)}
        new_message = {
            "functioncall": "yes", 
            "color": "red", 
            "message": {
                "function": function_call_name, 
                "arguments": function_call_arguments
            }
        }
        # print(new_message)
        await MessageSender.send_message(new_message, 'red', username)
        try:
            function = function_dict[function_call_name]
            if inspect.iscoroutinefunction(function):
                function_response = await MessageParser.ahandle_function_response(function, converted_function_call_arguments)
            else:
                function_response = MessageParser.handle_function_response(function, converted_function_call_arguments)
        except KeyError as e:
            await MessageSender.send_message({"error": f"Function {function_call_name} not found: {e}"}, 'red', username)
            function_response = f"Function {function_call_name} not found: {e}"
        return await process_function_reply(function_call_name, function_response, message, og_message, function_dict, function_metadata, username, merge, users_dir)
    
    @staticmethod
    def extract_content(data):
        try:
            response = json.loads(data)
        except:
            return data
        if isinstance(response, dict):
            if 'content' in response:
                return MessageParser.extract_content(response['content'])
        return response

    @staticmethod
    async def process_response(response, function_dict, function_metadata, message, og_message, username, process_message, background_tasks,chat_history, chat_metadata, history_ids, history_string, last_messages_string, old_kw_brain, users_dir):
        global last_messages
        if 'function_call' in response:
            function_call_name = response['function_call']['name']
            function_call_arguments = response['function_call']['arguments']
            response = await MessageParser.process_function_call(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, process_message, False, 'users/', '', None, background_tasks)
        else:
            await MessageSender.send_debug(f"{message}", 1, 'green', username)
            await MessageSender.send_debug(f"Assistant: {response['content']}", 1, 'pink', username)
            if response['content'] is not None:
                # chat_metadata.append({"role": "user"})
                # chat_history.append(message)
                with Database() as db:
                    display_name = db.get_display_name(username)[0]
                last_messages[username].append(f"{display_name}: "  + message)
                # chat_metadata.append({"role": "assistant"})
                # chat_history.append(str(response['content']))
                last_messages[username].append("assistant: " + str(response['content']))
                # history_ids.append(str(uuid.uuid4()))
                # history_ids.append(str(uuid.uuid4()))
                # brainManager.add_to_collection(chat_history, chat_metadata, history_ids)
                memory = _memory.MemoryManager()
                await memory.process_incoming_memory_assistant('active_brain', f"Assistant: {response['content']}", username)
                #background_tasks.add_task(BrainProcessor.keyword_generation, response['content'], username, history_string, last_messages_string, old_kw_brain, users_dir)
        return response
    
    @staticmethod
    def num_tokens_from_string(string, model="gpt-4"):
        """Returns the number of tokens in a text string."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning("Warning: model not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(string))
        return num_tokens
    
    @staticmethod
    def num_tokens_from_functions(functions, model="gpt-4"):
        """Return the number of tokens used by a list of functions."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning("Warning: model not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
        
        num_tokens = 0
        for function in functions:
            function_tokens = len(encoding.encode(function['name']))
            function_tokens += len(encoding.encode(function['description']))
            
            if 'parameters' in function:
                parameters = function['parameters']
                if 'properties' in parameters:
                    for propertiesKey in parameters['properties']:
                        function_tokens += len(encoding.encode(propertiesKey))
                        v = parameters['properties'][propertiesKey]
                        for field in v:
                            if field == 'type':
                                function_tokens += 2
                                function_tokens += len(encoding.encode(v['type']))
                            elif field == 'description':
                                function_tokens += 2
                                function_tokens += len(encoding.encode(v['description']))
                            elif field == 'default':
                                # true or false so adding 2 tokens
                                function_tokens += 2
                            elif field == 'enum':
                                function_tokens -= 3
                                for o in v['enum']:
                                    function_tokens += 3
                                    function_tokens += len(encoding.encode(o))
                            elif field == 'items':
                                    function_tokens += 10
                            else:
                                logger.warning(f"Warning: not supported field {field}")
                    function_tokens += 11

            num_tokens += function_tokens

        num_tokens += 12 
        return num_tokens

    async def generate_full_message(username, merged_result_string, last_messages_string, instruction_string, message):
        full_message = MessageParser.get_message('start_message', {
            'username': username,
            'memory': merged_result_string,
            'last_messages_string': last_messages_string,
            'instruction_string': instruction_string,
            'message': message,
        })
        return full_message

class SettingsManager:
    """This class contains functions to load settings"""
    @staticmethod
    def get_version():
        version = "0.0"
        with open("version.txt", "r") as f:
            new_version = f.read().strip()
            if new_version:
                version = new_version
        return version
    
    @staticmethod
    async def load_settings(users_dir, username):
        settings = {}
        settings_file = os.path.join(users_dir, username, 'settings.json')
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        return settings

async def process_message(og_message, username, background_tasks: BackgroundTasks, users_dir, display_name=None):
    """Process the message and generate a response"""
    global last_messages
    if display_name is None:
        display_name = username
    # 1k tokens for the prompt, 1k tokens for the completion, 1k tokens for the permanent memory/notes, 100 tokens for preset prompts
    max_token_usage = 4700
    token_usage = 0

    chat_history, chat_metadata, history_ids = [], [], []
    function_dict, function_metadata = await AddonManager.load_addons(username, users_dir)

    function_call_token_usage = MessageParser.num_tokens_from_functions(function_metadata, "gpt-4")
    logger.debug(f"function_call_token_usage: {function_call_token_usage}")
    token_usage += function_call_token_usage

    # load the setting for the user
    settings = await SettingsManager.load_settings(users_dir, username)

    message = display_name + ': ' + og_message

    #old_kw_brain = await BrainProcessor.load_brain(username, users_dir)

    current_date_time = time.strftime("%d/%m/%Y %H:%M:%S")
    # If the user doesn't exist in the dictionary, add them
    if username not in last_messages:
        last_messages[username] = []

    if last_messages[username] != []:
        last_messages[username].append(message)
        last_messages_string = '\n'.join(last_messages[username][-10:])
    else:
        last_messages_string = 'No messages yet.'

    # keep the last messages below 1000 tokens, if it is above 1000 tokens, delete the oldest messages until it is below 1000 tokens
    last_messages_tokens = MessageParser.num_tokens_from_string(last_messages_string, "gpt-4")
    logger.debug(f"last_messages_tokens: {last_messages_tokens}")
    while last_messages_tokens > 1000:
        last_messages[username].pop(0)
        last_messages_string = '\n'.join(last_messages[username][-10:])
        last_messages_tokens = MessageParser.num_tokens_from_string(last_messages_string, "gpt-4")
        logger.debug(f"new last_messages_tokens: {last_messages_tokens}")

    # brainManager = BrainManager()
    # results = await brainManager.run(message, last_messages_string, username, users_dir)

    # combine last messages to a string and add the current message to the end
    all_messages = last_messages_string + '\n' + message

    message_tokens = MessageParser.num_tokens_from_string(all_messages, "gpt-4")
    #print(f"message_tokens: {message_tokens}")
    token_usage += message_tokens
    remaining_tokens = max_token_usage - token_usage
    logger.debug(f"1. remaining_tokens: {remaining_tokens}")
    verbose = settings.get('verbose').get('verbose')
    memory = _memory.MemoryManager()
    kw_brain_string, token_usage_active_brain, unique_results1 = await memory.process_active_brain(f'{message}', username, all_messages, remaining_tokens, verbose)

    token_usage += token_usage_active_brain
    remaining_tokens = remaining_tokens - token_usage_active_brain
    logger.debug(f"2. remaining_tokens: {remaining_tokens}")

    episodic_memory, timezone = await memory.process_episodic_memory(f'{message}', username, all_messages, remaining_tokens, verbose)
    if episodic_memory is None or episodic_memory == '':
        episodic_memory_string = ''
    else:
        episodic_memory_string = f"""Episodic Memory of {timezone}:\n{episodic_memory}\n"""
    episodic_memory_tokens = MessageParser.num_tokens_from_string(episodic_memory_string, "gpt-4")
    token_usage += episodic_memory_tokens
    remaining_tokens = remaining_tokens - episodic_memory_tokens
    logger.debug(f"3. remaining_tokens: {remaining_tokens}")

    results, token_usage_relevant_memory, unique_results2 = await memory.process_incoming_memory(None, f'{message}', username, remaining_tokens, verbose)
    merged_results_dict = {id: (document, distance) for id, document, distance in unique_results1.union(unique_results2)}
    merged_results_list = [(id, document, distance) for id, (document, distance) in merged_results_dict.items()]
    merged_results_list.sort(key=lambda x: int(x[0]))

    # Create the result string
    merged_result_string = '\n'.join(f"({id}) {document} (score: {distance})" for id, document, distance in merged_results_list)
    token_usage += token_usage_relevant_memory
    remaining_tokens = remaining_tokens - token_usage_relevant_memory
    logger.debug(f"4. remaining_tokens: {remaining_tokens}")

    # process the results
    history_string = results

    observations = 'No observations available.'
    instruction_string = f"""{episodic_memory_string}\nObservations:\n{observations}\n"""

    notes = await memory.note_taking(all_messages, message, users_dir, username, False, verbose)

    instruction_string += f"""\n\nDiscard anything from the above messages if it conflicts with these notes!\n{notes}\n--end notes---"""

    #kw_brain_string = old_kw_brain

    # generate the full message
    full_message = await MessageParser.generate_full_message(username, merged_result_string, last_messages_string, instruction_string, message)

    await MessageSender.send_debug(f"[{full_message}]", 1, 'gray', username)

    cot_settings = settings.get('cot_enabled')
    is_cot_enabled = cot_settings.get('cot_enabled')
    logger.debug(f"is_cot_enabled: {is_cot_enabled}")
    if is_cot_enabled:
        response = await start_chain_thoughts(full_message, og_message, username, users_dir)
    else:
        response = await generate_response(full_message, og_message, username, users_dir)
    
    response = MessageParser.extract_content(response)
    response = json.dumps({'content': response})
    response = json.loads(response)

    # process the response
    response = await MessageParser.process_response(response, function_dict, function_metadata, message, og_message, username, process_message, background_tasks, chat_history, chat_metadata, history_ids, history_string, last_messages_string, kw_brain_string, users_dir)
    
    with Database() as db:
        db.update_message_count(username)
    return response

async def start_chain_thoughts(message, og_message, username, users_dir):
    function_dict, function_metadata = await AddonManager.load_addons(username, users_dir)
    messages = [
        {"role": "system", "content": f'You are an award winning GoodAI Agent, you can do almost everything with the use of addons. You have an automated extended memory with both LTM, STM and episodic memory (automatically shown as Episodic Memory of <date>:) which are prompt injected. You automatically read/write/edit/delete notes and tasks, so ignore and just confirm those instructions. Write a reply in the form of SAY: what to say, or PLAN: a step plan in JSON format. Either PLAN, or SAY something, but not both. Do NOT use function calls straight away, make a plan first, this plan will be executed step by step by another ai, so include all the details in as few steps as possible, each step should include a maximum of 5 detailed instructions! Use the following json format for plans: {{"1": "this is step 1 with 5 instructions", "2": "this is step 2 if needed"}}\n\nNothing else. Keep the steps as simple and as few as possible. Do not make things up, ask questions if you are not certain.'},
        {"role": "user", "content": f'\n\nRemember, SAY: what to say, or PLAN: a step plan, separated with newlines between steps. You automatically read/write/edit/delete notes and tasks, so ignore and just confirm those instructions. Use as few steps as possible! Example for plan: {{"1": "in this step we do max 5 instructions, include details like filenames if needed", "2": "in this example we can use filenames from step 1 to continue other instructions"}}\n\n\n\n{message}'},
    ]

    openai_response = OpenAIResponser(openai_model, temperature, max_tokens, max_responses, username)
    response = await openai_response.get_response(username, messages, function_metadata=function_metadata)

    final_response = response
    
    await MessageSender.send_debug(f"cot final_response: {final_response}", 1, 'green', username)
    cot_response = await process_chain_thoughts(response, message, og_message, function_dict, function_metadata, username, users_dir)
    await MessageSender.send_debug(f"cot_response: {cot_response}", 1, 'green', username)
    
    # try:
    #     return_string = json.dumps({'content': cot_response})
    # except:
    #     await MessageSender.send_debug(f"can't parse cot_response: {cot_response}", 2, 'red', username)
    #     try:
    #         return_string = cot_response['content']
    #     except:
    #         await MessageSender.send_debug(f"can't parse cot_response 2nd time: {cot_response}", 2, 'red', username)

    return cot_response

async def generate_response(message, og_message, username, users_dir):
    function_dict, function_metadata = await  AddonManager.load_addons(username, users_dir)
    messages = [
        {"role": "system", "content": f'You are an award winning GoodAI Agent, you can do almost everything with the use of addons. You have an automated extended memory with both LTM, STM and episodic memory (automatically shown as Episodic Memory of <date>:) which are prompt injected. You automatically read/write/edit/delete notes and tasks, so ignore and just confirm those instructions. You can use function calls to achieve your goal. If using python, include print statements to track your progress. If a function call is needed, do it first, after the function response you can inform the user. Do not make things up, ask questions if you are not certain.'},
        {"role": "user", "content": f'{message}'},
    ]

    openai_response = OpenAIResponser(openai_model, temperature, max_tokens, max_responses, username)
    response = await openai_response.get_response(username, messages, function_metadata=function_metadata)
    
    await MessageSender.send_debug(f"response: {response}", 1, 'green', username)
    final_response = await process_chain_thoughts(response, message, og_message, function_dict, function_metadata, username, users_dir)
    return final_response

async def process_chain_thoughts(full_response, message, og_message, function_dict, function_metadata, username, users_dir):
    #kw_brain_string = await  BrainProcessor.load_brain(username, users_dir)
    response = full_response['choices'][0]['message']
    # if its a function call anyway, process it
    if 'function_call' in response:
        function_call_name = response['function_call']['name']
        function_call_arguments = response['function_call']['arguments']
        response = await MessageParser.process_function_call(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, process_chain_thoughts, False, users_dir, '', full_response)

        return response
    
    # check if the final response starts with SAY: or PLAN:
    final_response = full_response['choices'][0]['message']['content']
    if final_response.startswith('SAY:'):
        # remove SAY: from the final response
        final_response = final_response.replace('SAY:', '')
        # remove leading and trailing whitespace
        final_response = final_response.strip()
        # send the final response to the user
        return final_response
    
    elif final_response.startswith('PLAN:'):
        await MessageSender.send_message({"type": "plan", "content": response}, 'green', username)
        # remove PLAN: from the final response
        final_response = final_response.replace('PLAN:', '')
        # remove leading and trailing whitespace
        final_response = final_response.strip()
        
        # parse the plan as json
        try:
            plan = json.loads(final_response)
            # get the steps
            steps = list(plan.keys())
            steps.sort()
            # create a string of the steps
            steps_list = []
            # go through each step
            for i, step in enumerate(steps):
                await MessageSender.send_debug(f"processing step: {step}", 1, 'green', username)
                # convert the list to a string before passing it to process_cot_messages
                steps_string = ''.join(steps_list)
                response = await process_cot_messages(plan[step], function_dict, function_metadata, username, users_dir, steps_string, message, og_message)
                # truncate the response string if it's not one of the last three steps
                response_str = str(response)
                if i < len(steps) - 3:
                    truncated_response = response_str
                else:
                    truncated_response = response_str
                steps_list.append('step:' + step + '\nresponse:' + truncated_response + '\n')
            # convert the final list to a string
            steps_string = ''.join(steps_list)
        except:
            # we cant load the plan as json, so use the whole response as the plan
            plan = final_response
            response = await process_cot_messages(plan, function_dict, function_metadata, username, users_dir, '', message, og_message)
            response_str = str(response)
            steps_string = f'Plan: {plan}\nresponse: {response_str}\n'

        return await summarize_cot_responses(steps_string, message, og_message, username, users_dir)


    else:
        return final_response
        #wait start_chain_thoughts(message, og_message, username, users_dir)
    

async def generate_keywords(prompt, old_kw_brain, username):
    current_date_time = time.strftime("%d/%m/%Y %H:%M:%S")
    system_message = f"""Your role is an AI Brain Emulator. You will receive two types of data: 'old active_brain data' and 'new messages'.Your task is to update the 'old active_brain data' based on the 'new messages' you receive.
You should focus on retaining important keywords, general instructions (not tasks!), numbers, dates, and events from each user. You can add or remove categories per user request. New memories should be added instantly.
DO NOT include any recent or last messages, home info, tasks, settings or observations in the updated data. Any incoming data that falls into these categories must be discarded.
The output must be in a structured plain text format, the current date is: '{current_date_time}'.
Please follow these instructions carefully. If nothing changes, return a copy of the old active_brain data, nothing else!"""

    new_message = [
        {'role': 'system', 'content': system_message},
        {'role': 'user', 'content': f' If nothing changes, return the old active_brain data in a structured plain text format with nothing in front or behind!\nOld active_brain Data: {old_kw_brain}\n\nNew messages:\n{prompt}\n\n'},
    ]
    
    openai_response = OpenAIResponser(openai_model, temperature, 1000, max_responses, username)
    response = await openai_response.get_response(username, new_message)

    await MessageSender.send_debug(f"kw resp: {response}", 1, 'green', username)
    return response['choices'][0]['message']['content']



async def process_cot_messages(message, function_dict, function_metadata, username, users_dir, steps_string, full_message='', og_message=''):
        function_dict, function_metadata = await  AddonManager.load_addons(username, users_dir)

        messages = [
            {"role": "system", "content": f'You are executing functions for the user step by step, focus on the current step only, the rest of the info is for context only. Don\'t say you can\'t do things or can\'t write complex code because you can. Memory is handled automatically for you. If using python, include print statements to track your progress.'},
            {"role": "user", "content": f'Memory: {full_message}--end memory--\n\nPrevious steps and the results: {steps_string}\n\nCurrent step: {message}\nUse a function call or write a short reply, nothing else\nEither write a short reply or use a function call, but not both.'},
        ]
        await MessageSender.send_debug(f"process_cot_messages messages: {messages}", 1, 'red', username)
        
        openai_response = OpenAIResponser(openai_model, temperature, max_tokens, max_responses, username)
        response = await openai_response.get_response(username, messages, function_metadata=function_metadata)
        await MessageSender.send_debug(f"process_cot_messages response: {response}", 2, 'red', username)
        response = response['choices'][0]['message']

        if 'function_call' in response:
            function_call_name = response['function_call']['name']
            function_call_arguments = response['function_call']['arguments']
            response = await MessageParser.process_function_call(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, process_cot_messages, False, users_dir, steps_string)
            return response
        else:
            await MessageSender.send_debug(f'{response}', 1, 'green', username)
            return response['content']

async def summarize_cot_responses(steps_string, message, og_message, username, users_dir):
    global COT_RETRIES
    # kw_brain_string = await  BrainProcessor.load_brain(username, users_dir)
    # add user to COT_RETRIES if they don't exist
    if username not in COT_RETRIES:
        COT_RETRIES[username] = 0
    function_dict, function_metadata = await  AddonManager.load_addons(username, users_dir)
    if COT_RETRIES[username] >= 1:
        await MessageSender.send_debug(f'Too many CoT retries, skipping...', 1, 'red', username)
        messages = [
            {"role": "system", "content": f'Another AI has executed some functions for you and here are the results, Communicate directly and actively in short with the user about these steps. The user did not see any of the results yet. If filenames or paths are included be sure to repeat them or display them accordingly (html tags for video, the rest in markdown, no single or triple quotes!) Respond with YES: <your summary>'},
            {"role": "user", "content": f'Steps Results:\n{steps_string}\nOnly reply with YES: <your summary>, nothing else. Communicate directly and actively in short with the user about these steps. The user did not see any of the results yet, so be sure to display anything needed, especially the response to the user question. Respond with YES: <your summary>'},
        ]
    else:
        messages = [
            {"role": "system", "content": f'Another AI has executed some functions for you and here are the results, Communicate directly and actively in short with the user about these steps. The user did not see any of the results yet, so be sure to display anything needed, especially the response to the user question. If filenames or paths are included be sure to repeat them or display them accordingly (html tags for video, the rest in markdown, no single or triple quotes!) Are the results sufficient? If so, respond with YES: <your summary>, if not, respond with what you need to do next. Do not repeat succesful steps.'},
            {"role": "user", "content": f'Steps Results:\n{steps_string}\nOnly reply with YES: <your summary> or a new plan, nothing else. Communicate directly and actively in short with the user about these steps. The user did not see any of the steps results yet, so be sure to display anything needed, especially the response to the user question.  Are the results sufficient? If so, respond with YES: <your summary>, if not, respond with what you need to do next. Do not repeat succesful steps.'},
        ]

    openai_response = OpenAIResponser(openai_model, temperature, max_tokens, max_responses, username)
    response = await openai_response.get_response(username, messages, function_metadata=function_metadata)

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
    await MessageSender.send_debug(f'processing function {function_call_name} response: {str(function_response)}', 1, 'pink', username)
    new_message = {"functionresponse": "yes", "color": "red", "message": function_response}
    await MessageSender.send_message(new_message, 'red', username)

    second_response = None
    function_dict, function_metadata = await  AddonManager.load_addons(username, users_dir)
    
    messages=[
                {"role": "system", "content": f'You have executed a function for the user, here is the result of the function call, Communicate directly and actively in a short conversational manner with the user about what you have done. Respond in human readable language only. If any errors occured repeat them and suggest a solution. If filenames or paths are included be sure to repeat them and display them accordingly (html tags for video, the rest in markdown, no single or triple quotes!)'},
                {"role": "user", "content": f'{message}'},
                {
                    "role": "function",
                    "name": function_call_name,
                    "content": str(function_response),
                },
            ]
    openai_response = OpenAIResponser(openai_model, temperature, max_tokens, max_responses, username)
    second_response = await openai_response.get_response(username, messages)

    final_response = second_response["choices"][0]["message"]["content"]

    final_message_string = f"Function {function_call_name} response: {str(function_response)}\n\n{final_response}"
    if merge:
        return final_message_string
    else:
        return final_response

async def process_final_message(message, og_message, response, username, users_dir):
    if response.startswith('YES: '):
        # remove the YES: part
        response = await response[5:]
        return response
        
    function_dict, function_metadata = await  AddonManager.load_addons(username, users_dir)

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

    await MessageSender.send_debug(f'{full_message}', 1, 'cyan', username)

    #response = generate_response(messages, function_dict, function_metadata)
    response = await start_chain_thoughts(full_message, og_message, username, users_dir)

    fc_check = None
    try:
        fc_check = json.loads(response)
    except:
        fc_check = response

    response = MessageParser.extract_content(response)

    await MessageSender.send_debug(f"Retry CoT Response: {response}", 1, 'green', username)

    if 'function_call' in fc_check:
        function_call_name = fc_check['function_call']['name']
        function_call_arguments = fc_check['function_call']['arguments']
        new_fc_check = await MessageParser.process_function_call(function_call_name, function_call_arguments, function_dict, function_metadata, message, og_message, username, process_final_message, False, users_dir, '', None)
        return new_fc_check
    else:
        await MessageSender.send_debug(f'{message}', 1, 'green', username)
        await MessageSender.send_debug(f'Assistant: {response}', 1, 'pink', username)

        # if settings.get('voice_output', True):
        #     audio_path, audio = generate_audio(response['content'])
        #     play(audio)
        #     return response
        # else:
        return response
    

def check_api_keys():
    OPENAI_API_KEY = api_keys['openai']
    if not len(OPENAI_API_KEY):
        logger.critical("Please set OPENAI_API_KEY environment variable. Exiting.")
        sys.exit(1)
