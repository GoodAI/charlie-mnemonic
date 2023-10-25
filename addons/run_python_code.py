import asyncio
import docker
from unidecode import unidecode
import os
from logs import Log

description = """This addon allows you to execute python code in a non persistant terminal, When opening files be sure to open from /data/filename.
Always include print statements to track the progress or path and name(s) of generated files.
Save any generated files in the /data/ directory with the format /data/filename.ext.
You must always display media that's been saved in the /data/ directory, using the markdown format [description](data/filename.ext) or html tags for video's (without triple quotes).
When asked to create videos, follow these rules: Create a video (make sure the code works), convert to h264 using ffmpeg subprocess, include in response as HTML tag, avoid triple quotes around HTML tag, images should always immediately be shown in your response in markdown format."""

parameters = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "The python code to be executed, Include prints to see the status and output, especially the path and name of generated files.",
        },
        "pip_packages": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The list of pip packages to be installed before executing the code."
        },
    },
    "required": ['content'],
}

async def run_python_code(content, pip_packages=[], previous_content='', username=None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_run_python_code, content, pip_packages, previous_content, username)

def sync_run_python_code(content, pip_packages=[], previous_content='', username=None):
    # convert the email to a name without special characters to name our container
    # Convert non-ASCII characters to ASCII
    name = unidecode(username)
    # replace spaces and @ with underscores
    name = name.replace(' ', '_')
    name = name.replace('@', '_')
    name = name.replace('.', '_')
    # lowercase the name
    username = name.lower()

    if (previous_content != ''):
        new_content = previous_content + '\n' + content
    else:
        new_content = content

    new_content = escape_string(new_content)

    try:
        client = docker.from_env()

        # Define the path where you want to store media on the host
        host_path = os.path.join(os.getcwd(), 'users', username, 'data')

        # Define the path inside the container where you will save media
        container_path = '/data'

        # Define the volume
        volumes = {host_path: {'bind': container_path, 'mode': 'rw'}}

        # Remove existing container with the same name
        for c in client.containers.list(all=True):
            if c.name == username:
                c.remove(force=True)

        # Start a new container with the volume
        container = client.containers.run("python-env", name=username, detach=True, tty=True, volumes=volumes)

        pip_string = ''
        # Install pip packages in the container
        for package in pip_packages:
            pip_install_result = container.exec_run(f'pip install {package}')
            if pip_install_result.exit_code != 0:
                return {'error': 'Failed to install package: ' + pip_install_result.output.decode('utf-8')}
            else:
                pip_string += f'successfully installed package: {package}\n'

        # Execute the code in the container
        exec_result = container.exec_run(f'python3 -c "{new_content}"')
        output = exec_result.output.decode('utf-8')[:2000]
        
        # Prepare the response
        response = {
            'pip': pip_string,
            'output': output, 
            'exit_code': exec_result.exit_code
        }

        # Remove the container
        container.remove(force=True)

        return response

    except Exception as e:
        return {'error': str(e)}

def escape_string(s):
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s