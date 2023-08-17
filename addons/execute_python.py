import subprocess
import tempfile
import os

description = "This addon allows you to execute a python file or a piece of python code in a new terminal or subprocess. Include prints or returns to get the output, to know if it worked or not. Only use if asked explicitly by the user!"

parameters = {
    "type": "object",
    "properties": {
        "use_file": {
            "type": "boolean",
            "default": False,
            "description": "Use file (True) or code (False)?",
        },
        "arg": {
            "type": "string",
            "description": "The path to the file or the python code to be executed, include prints or returns to get the output, write all code on 1 line. This is a temporary terminal, so you can't use input() or anything that requires user input. It does also not remember functions andvariables, so you can't them from previous executions.",
        }
    },
    "required": ['use_file', 'arg'],
}

def execute_python(use_file, arg):
    try:
        if use_file == True:
            process = subprocess.Popen(['python', arg], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            # Write the code to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as temp:
                temp.write(arg)
                temp_name = temp.name
            # Execute the temporary file
            process = subprocess.Popen(['python', temp_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Wait for the subprocess to finish
            stdout, stderr = process.communicate()
            # Delete the temporary file
            os.remove(temp_name)
        return {'output': stdout.decode('utf-8'), 'error': stderr.decode('utf-8'), 'conclusion': 'no errors usually means success, next time add more prints or returns to get the output'}
    except Exception as e:
        return {'error': str(e)}