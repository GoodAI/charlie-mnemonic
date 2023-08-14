import subprocess

description = "This addon allows you to execute a python file or a piece of python code in a new terminal or subprocess. Include prints or returns to get the output, to know if it worked or not. Only use if asked explicitly by the user!"

parameters = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "The path to the python file to be executed",
        },
        "code": {
            "type": "string",
            "description": "The python code to be executed, include prints or returns to get the output, don't forget that!",
        }
    },
    "required": [],
}

def execute_python(**input):
    try:
        if 'file_path' in input:
            process = subprocess.Popen(['python', input['file_path']], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif 'code' in input:
            process = subprocess.Popen(['python', '-c', input['code']], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            return {'error': 'No valid input provided'}
        stdout, stderr = process.communicate()
        return {'output': stdout.decode('utf-8'), 'error': stderr.decode('utf-8'), 'conclusion': 'no errors usually means success, next time add more prints or returns to get the output'}
    except Exception as e:
        return {'error': str(e)}
