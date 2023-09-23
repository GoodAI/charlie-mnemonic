import docker

description = "This addon allows you to execute python code in a non persistant terminal. Include prints to see the output."

parameters = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "The python code to be executed, you can't use input() or anything that requires user input. Include prints to see the output.",
        },
    },
    "required": ['content'],
}

def run_python_code(content, previous_content='', username=None):
    print('running python code for user', username)

    if (previous_content != ''):
        new_content = previous_content + '\n' + content
    else:
        new_content = content

    new_content = escape_string(new_content)

    try:
        client = docker.from_env()

        # Create a new container for the user if it doesn't exist
        container = None
        for c in client.containers.list(all=True):
            if c.name == username:
                container = c
                break

        if container is None:
            # Start a new container
            container = client.containers.run("python-env", name=username, detach=True, tty=True)

        # Execute the code in the container
        exec_result = container.exec_run(f'python3 -c "{new_content}"')
        output = exec_result.output.decode('utf-8')[:2000]
        # Prepare the response
        response = {
            'output': output, 
            'exit_code': exec_result.exit_code
        }

        return response

    except Exception as e:
        return {'error': str(e)}
    
def escape_string(s):
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    return s