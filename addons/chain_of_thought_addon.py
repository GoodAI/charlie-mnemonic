import os
import json
import asyncio
from typing import List, Dict, Any
import tiktoken
import re
from colorama import Fore, Style, init

import llmcalls
from config import api_keys, default_params
from memory import MemoryManager
from utils import MessageSender, SettingsManager, AddonManager
import utils
import memory as _memory

SHOW_DEBUG_PRINTS = False

# Initialize colorama
init(autoreset=True)

description = """
This addon implements a chain of thought process for executing complex tasks. It generates a plan, executes it step by step, and can use other enabled addons to complete the task.
Use this addon to break down complex tasks into actionable steps and execute them systematically. From research to code writing, this addon can help you complete a wide range of tasks.
Use as many details as possible in the initial input to get the best results, because the chain of thought process does not see the user's recent messages or context.
"""

parameters = {
    "type": "object",
    "properties": {
        "input": {
            "type": "string",
            "description": "The initial input or task description",
        },
        "max_loops": {
            "type": "integer",
            "description": "The maximum number of loops to execute",
            "default": 5,
        },
    },
    "required": ["input"],
}


def debug_print(message, color=Fore.WHITE):
    if SHOW_DEBUG_PRINTS:
        print(f"{color}{message}{Style.RESET_ALL}")


def extract_json_from_text(text):
    decoder = json.JSONDecoder()
    pos = 0
    last_json = None
    while pos < len(text):
        try:
            obj, index = decoder.raw_decode(text, pos)
            last_json = obj
            pos = index
        except json.JSONDecodeError:
            pos += 1
    if last_json is not None:
        return last_json
    else:
        raise ValueError("No valid JSON object found in the text.")


def extract_file_paths(execution_output):
    """
    Extract file paths from the code within <execute_code> tags in the assistant's response.
    Looks for file write operations in the code.
    """
    file_paths = set()
    # Extract code within <execute_code> tags
    code_pattern = r"<execute_code>(.*?)</execute_code>"
    code_matches = re.findall(code_pattern, execution_output, re.DOTALL)

    for code in code_matches:
        # Find file write operations
        # Look for patterns like open('file_path', 'w') or open("file_path", 'w')
        open_pattern = r"open\((?:'|\")(.+?)(?:'|\")\s*,\s*['\"]w['\"]\)"
        open_matches = re.findall(open_pattern, code)
        for file_path in open_matches:
            file_paths.add(file_path)

    return file_paths


async def chain_of_thought_addon(
    input: str,
    max_loops: int = 5,
    username: str = None,
    chat_id: str = None,
):
    settings_data = await SettingsManager.load_settings("users", username)
    model = settings_data.get("active_model", {}).get("active_model", "gpt-4o")

    # Set temperature to reduce creativity
    default_params["temperature"] = 0.2

    responder = llmcalls.get_responder(
        api_keys["openai"] if model.startswith("gpt") else api_keys["anthropic"],
        model,
        default_params,
    )

    # Load enabled addons
    _, function_m_data = await AddonManager.load_addons(username, "users")

    # Exclude 'chain_of_thought_addon' from function_metadata
    function_metadata = [
        func
        for func in function_m_data
        if func.get("function", {}).get("name") != "chain_of_thought_addon"
    ]
    debug_print(f"Starting CoT process for input: {input}", Fore.CYAN)
    debug_print(f"Using model: {model}", Fore.CYAN)

    # # fetch the previous 10 messages from the chat
    # memory = _memory.MemoryManager()
    # recent_messages = await memory.get_most_recent_messages(
    #     "active_brain", username, chat_id=chat_id, n_results=10
    # )

    # # we only need the document field, lets extract it and format it nicely as a string
    # recent_messages = [message["document"] for message in recent_messages]

    # # properly format the recent messages
    # formatted_messages = "\n".join(recent_messages)

    # debug_print(f"Recent messages: {recent_messages}", Fore.CYAN)

    # Generate the pipeline
    debug_print("Generating pipeline", Fore.YELLOW)
    pipeline_messages = [
        {
            "role": "system",
            "content": """You are a task planner. Given an input task, create a detailed plan with steps to complete the task.
Each step should be concise and actionable. Format your response as a JSON array of strings, where each string is a step in the plan.
You have addons and tools at your disposal, so only plan steps you can actually execute using these tools. If part of the plan is to write to a file, mention to use Python to write files. Be sure to add paths to files. Always work in the /data/ directory. If a file needs to be edited you should do this in 2 steps, read the file first, then edit.
Use as few steps as possible, preferably less than 10, but separate each task or tool usage into a new step. For example, generating images and writing code should be 2 steps. It is important to put no additional text or comments before or after the JSON! Only output the JSON array.
For example: ["Step 1: Plan Project", "Step 2: Write base code to app.py with python", "Step 3: Generate image", "Step 4: Verify images are generated", "Step 5: Make images transparent with Python", "Step 6: Replace code with new images, use python to write to file app.py", "Step 7: Verify the code has no placeholder code or ommisions", "Step 8: Review steps and present to user, include code and files/paths to files if needed"]""",
        },
        {
            "role": "user",
            "content": f"Create a detailed plan for the following task: {input}\n\nRemember to use as few steps as possible, preferably less than 10,  include filepaths, data or info, and separate each task or tool usage into a new step. For example, generating images and writing code should be 2 steps. It is important to put no additional text or comments before or after the JSON! Only output the JSON array.",
        },
    ]

    pipeline_response = ""
    async for resp in responder.get_response(
        username,
        pipeline_messages,
        stream=False,
        function_metadata=function_metadata,
        chat_id=chat_id,
    ):
        pipeline_response += resp if resp else ""

    try:
        # Remove any text before and after the JSON array
        pipeline_response = pipeline_response.strip()
        pipeline_response = re.search(r"\[.*\]", pipeline_response, re.DOTALL).group()

        pipeline = json.loads(pipeline_response)
        if not isinstance(pipeline, list):
            raise ValueError("Pipeline is not a list")
    except Exception as e:
        debug_print(
            f"Error parsing pipeline. Exception: {e}\nRaw response: {pipeline_response}",
            Fore.RED,
        )
        pipeline = [
            "Research topic",
            "Analyze findings",
            "Generate image",
            "Create PDF report",
            "Review and finalize",
        ]

    debug_print(f"Generated plan: {json.dumps(pipeline, indent=2)}", Fore.GREEN)

    result = []
    context = ""
    total_steps = len(pipeline)
    file_paths = set()  # Set to store file paths

    # Initialize tiktoken encoder
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

    for step_index, step in enumerate(pipeline, start=1):
        debug_print(f"Executing step {step_index}/{total_steps}: {step}", Fore.MAGENTA)

        # Send the current step to the frontend
        await MessageSender.send_message(
            {
                "type": "cot_step",
                "content": {
                    "step_number": step_index,
                    "total_steps": total_steps,
                    "step_description": step,
                },
                "chat_id": chat_id,
            },
            "blue",
            username,
        )

        # Adjust function metadata based on the current step to prevent misuse
        current_function_metadata = function_metadata.copy()
        if "generate_image" in [func["function"]["name"] for func in function_metadata]:
            if "image" not in str(step).lower() and "graphic" not in str(step).lower():
                current_function_metadata = [
                    func
                    for func in function_metadata
                    if func["function"]["name"] != "generate_image"
                ]

        # Build the context with previous steps and file contents
        debug_print("Building context for current step", Fore.YELLOW)
        max_context_tokens = (
            settings_data.get("memory", {}).get("input", 4096) - 500
        )  # Reserve tokens for prompts and responses
        print(f"DEBUG: Max context tokens: {max_context_tokens}")
        context_pieces = []

        # Include previous steps and their results
        for prev_result in result[
            -10:
        ]:  # Limit to last 10 steps to manage context size
            # Todo: Count tokens in context_pieces and truncate/summarize if necessary
            step_desc = prev_result.get("step_description", "")
            execution_output = prev_result.get("execution_output", "")
            context_pieces.append(f"{step_desc}: {execution_output}")

        # # Include relevant file contents
        # charlie_mnemonic_user_dir = os.path.join(os.getcwd(), "users")
        # full_path = os.path.join(charlie_mnemonic_user_dir, username, "data")
        # # detect if we are in a docker container or not
        # if os.path.exists("/.dockerenv"):
        #     file_paths = {
        #         os.path.join(
        #             "/app", "users", username, "data", os.path.basename(file_path)
        #         )
        #         for file_path in file_paths
        #     }
        # else:
        #     file_paths = {
        #         os.path.join(full_path, os.path.basename(file_path))
        #         for file_path in file_paths
        #     }

        # # Include relevant file contents
        # for file_path in file_paths:
        #     try:
        #         with open(file_path, "r", encoding="utf-8") as f:
        #             content = f.read()
        #         context_pieces.append(f"File '{file_path}':\n{content}")
        #     except Exception as e:
        #         debug_print(f"Error reading file '{file_path}': {e}", Fore.RED)

        # Combine context pieces
        combined_context = "\n".join(context_pieces)
        tokens = enc.encode(combined_context)

        if len(tokens) > max_context_tokens:
            debug_print("Context exceeds token limit. Truncating...", Fore.YELLOW)
            tokens = tokens[-max_context_tokens:]
            combined_context = enc.decode(tokens)

        debug_print(f"Context built. Token count: {len(tokens)}", Fore.GREEN)

        # Step 1: Execute the step
        debug_print("Executing step", Fore.YELLOW)
        execution_messages = [
            {
                "role": "system",
                "content": f"""You are executing a step in a chain of thought process. Follow the instructions carefully and provide a detailed response.

**Important Instructions:**

- Only focus on executing the current step.
- **Do not use any addons or functions unless explicitly required for the current step.**
- If the step is to make folders or write code, be it python, html, css or any other file, then you must use python to write the code to a file.
- If you write to a file, be sure to replace the whole file content with the new content, without omissions or placeholders.
- **When writing or updating code files, always include the full code without using ommisions or placeholders or ellipses like '// ... (previous code) ...'. Ensure that the code is complete and can be run on its own.**
- If your current step involves writing code or creating files, provide the exact code or file content.
- **Do not generate images or use the 'generate_image' function unless the step specifically instructs you to do so.**

When you need to execute Python code, please format your response as follows:

1. If you need to install any pip packages, list them between `<pip_install>` tags, with each package on a new line or separated by commas.
2. Enclose the Python code to be executed between `<execute_code>` tags.
3. The user does not see the code execution. So do not mention "as you can see" or something similar. Code is executed in a secure environment, so you can safely run it without any restrictions.
4. Do not say anything else after the code; you will first be presented with the output of the code execution, and then you can continue with the conversation.
5. If you need to save any file, save it in the `/data` directory.
6. Generated images or other media files should be displayed using markdown or HTML tags.
7. Remember to always include the full edited code without using ommisions or placeholders, else the file will be corrupted and miss important parts.

Only use the `<execute_code>` tags when you need to execute Python code as part of the current step.
""",
            },
            {
                "role": "user",
                "content": f"Task: {input}\nContext so far:\n{combined_context}\n\nThe above is for context only, it is important to focus on the current step ({step_index}/{total_steps}): {step}\nPlease execute the current step as specified, and provide the result according to the instructions, if you need to write code, full code without ommisions or placeholders",
            },
        ]

        step_execution_output = ""
        try:
            async for resp in responder.get_response(
                username,
                execution_messages,
                stream=True,
                function_metadata=current_function_metadata,
                chat_id=chat_id,
            ):
                step_execution_output += resp if resp else ""
        except Exception as e:
            debug_print(f"Exception during step execution: {e}", Fore.RED)
            step_execution_output = f"An error occurred during step execution: {e}"

        debug_print(f"Step execution output:\n{step_execution_output}", Fore.CYAN)
        # send the step execution output to the frontend
        await MessageSender.send_message(
            {
                "type": "cot_step_output",
                "content": {
                    "step_number": step_index,
                    "total_steps": total_steps,
                    "step_output": step_execution_output,
                },
                "chat_id": chat_id,
            },
            "blue",
            username,
        )

        # Extract file paths from the code within <execute_code> tags
        # new_file_paths = extract_file_paths(step_execution_output)
        # file_paths.update(new_file_paths)
        # debug_print(f"Updated file paths: {file_paths}", Fore.GREEN)

        # Update context
        context += f"\n{step}: {step_execution_output.strip()}"

        # Step 2: Generate the JSON result based on the execution output
        debug_print("Generating JSON result", Fore.YELLOW)
        json_messages = [
            {
                "role": "system",
                "content": f"""Based on the execution output, generate the result in the required JSON format.

**Important Instructions:**

- **Only output the JSON object** as your response.
- **Do not include** any explanations, notes, or additional text.
- **Do not include** any content outside the JSON.

Format your response as a JSON object with the following structure:
{{
    "step_result": "Provide a concise summary of the execution output",
    "next_action": "CONTINUE", "FINISH_EARLY", or "COMPLETE",
    "confidence": "High" or "Medium" or "Low",
    "addons_used": ["List of addons used during execution"] // If none, use an empty list
}}

**Guidelines for 'next_action':**
- Use 'COMPLETE' only if you are on the final step of the plan (Step {step_index} of {total_steps}) and you are satisfied that the task is fully completed.
- Use 'FINISH_EARLY' if you believe the task has been fully completed before reaching the final step.
- Use 'CONTINUE' if you are not on the final step, or if more steps are needed.

Remember: **Your entire response should be the JSON object only.**""",
            },
            {
                "role": "user",
                "content": f"Based on the execution output:\n{step_execution_output.strip()}\n\nPlease generate the JSON result as per the instructions.",
            },
        ]

        # Debug print the user message
        for message in json_messages:
            if message["role"] == "user":
                debug_print(f"JSON generation message: {message['content']}", Fore.CYAN)

        step_result_json = ""
        try:
            async for resp in responder.get_response(
                username,
                json_messages,
                stream=True,
                function_metadata=current_function_metadata,
                chat_id=chat_id,
            ):
                step_result_json += resp if resp else ""

            parsed_result = extract_json_from_text(step_result_json)
            # Add the execution output and step description to the parsed result
            parsed_result["execution_output"] = step_execution_output.strip()
            parsed_result["step_description"] = step
            result.append(parsed_result)

            debug_print(
                f"Step result JSON: {json.dumps(parsed_result, indent=2)}", Fore.GREEN
            )

            next_action = parsed_result.get("next_action", "CONTINUE")

            if next_action == "COMPLETE" and step_index == total_steps:
                debug_print("Task completed. Breaking loop.", Fore.GREEN)
                break
            elif next_action == "FINISH_EARLY":
                debug_print(
                    f"Assistant chose to finish early at step {step_index}.",
                    Fore.YELLOW,
                )
                break
            elif next_action == "COMPLETE":
                debug_print(
                    f"Assistant attempted to complete early at step {step_index}. Forcing 'next_action' to 'CONTINUE'.",
                    Fore.YELLOW,
                )
                parsed_result["next_action"] = "CONTINUE"
                # Continue to the next step
        except Exception as e:
            debug_print(
                f"Error parsing step result JSON. Exception: {e}\nRaw output:\n{step_result_json}",
                Fore.RED,
            )
            # Include the execution output in the fallback result
            result.append(
                {
                    "step_result": step_execution_output.strip(),
                    "next_action": "CONTINUE",
                    "confidence": "Low",
                    "addons_used": [],
                    "execution_output": step_execution_output.strip(),
                    "step_description": step,
                }
            )

    # Format the final result
    final_result = {"task": input, "steps_executed": len(result), "results": result}

    # Send the final result to the user
    await MessageSender.send_message(
        {
            "content": f"Chain of Thought Process Results:\n{json.dumps(final_result, indent=2)}",
            "chat_id": chat_id,
        },
        "blue",
        username,
    )

    debug_print(
        f"Chain of Thought Process completed. Final result:\n{json.dumps(final_result, indent=2)}",
        Fore.GREEN,
    )

    return final_result
