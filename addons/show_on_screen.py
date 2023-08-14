import webbrowser
import json
import tempfile
import os

description = "This addon allows you to display a string (text, html) on a screen in a specified room."

parameters = {
    "type": "object",
    "properties": {
        "room": {
            "type": "string",
            "enum": ["livingroom", "bedroom", "kitchen", "office"],
            "description": "The room where the message will be displayed.",
        },
        "message": {
            "type": "string",
            "description": "The message to be displayed.",
        },
    },
    "required": ["room", "message"],
}
    

def show_on_screen(room, message):
    # For the purpose of this demo, we will just open a new browser window with the message
    # In a real-world application, this function would interact with a device in the specified room
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
            # Write the HTML, CSS and JavaScript to the file
            message = message.replace('\n', '<br>')
            f.write(f"""
            <html>
            <head>
                <style>
                    body {{
                        background-color: #f0f0f0;
                        font-family: Arial, sans-serif;
                    }}
                </style>
            </head>
            <body>
                <h1>Message for {room}</h1>
                <div id="message"><p>{message}<p></div>
            </body>
            </html>
            """)
            temp_file_name = f.name

        # Open the file in the web browser
        webbrowser.open('file://' + os.path.realpath(temp_file_name), new=0, autoraise=True)

        return {"status": "success", "message": f"Message displayed in {room}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}