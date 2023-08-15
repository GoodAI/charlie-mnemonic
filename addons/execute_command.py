description = "Execute a command and return a success or error message"
parameters = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "The command to execute",
        }
    },
    "required": ["command"],
}

def execute_command(command):
    # Execute the command
    # In a real-world scenario, the command execution logic goes here.
    # For this example, we'll just print it.
    print(f"Executing command: {command}")

    # Return a success message
    return "Command executed successfully"