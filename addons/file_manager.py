import os
import json
import PyPDF2

description = "An addon that allows you to open, read, edit and save text-based files. Or read directories (list files and subfolders) It can also create new folders and files. Deleting files is only possible after the user agreed twice. Editing a file will require you to read it first, then edit."


parameters = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The action to be performed: open, read, edit, save, create, delete, Editing a file will require you to read it first, then edit. Addons need to have the same name as the function name!",
            "enum": ["open", "read", "edit", "save", "create", "delete"]
        },
        "file_path": {
            "type": "string",
            "description": "The path to the file or directory, if the action is read, directories will return a list of files and subdirectories"
        },
        "content": {
            "type": "string",
            "description": "The content to be written to the file, only necessary for 'create', 'edit' and 'save' actions"
        },
        "confirm_delete": {
            "type": "boolean",
            "description": "Confirmation for deleting files, only necessary for 'delete' action, ask twice for confirmation, first time is always without confirmation"
        }
    },
    "required": ["action", "file_path"],
}




def file_manager(action, file_path, content=None, confirm_delete=False):
    # Check if the file_path starts with a / remove the /
    if file_path.startswith("/"):
        file_path = file_path[1:]
    if action == "open":
        with open(file_path, 'r', encoding='utf-8') as f:
            return f'the content of {file_path} is:\n---STARTFILE---\n{f.read()[:7000]}\n---ENDOFFILE---\n\n'
    elif action == "read":
        if os.path.isfile(file_path):
            # check if its a text based file
            if not os.path.splitext(file_path)[1] in ['.pdf', '.docx', '.txt', '.py', '.json', '.md', '.html', '.css', '.js', '.xml', '.csv', '.tsv', '.log', '.bat', '.sh', '.c', '.cpp', '.h', '.hpp', '.java', '.php', '.pl', '.rb', '.go', '.rs', '.sql', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.cnf', '.env', '.envrc', '.gitignore', '.gitattributes', '.gitmodules', '.gitconfig', '.gitkeep', '.git', '.gitlab-ci.yml', '.gitignore_global', '.gitconfig', '.gitattributes', '.gitkeep', '.gitmodules', '.gitignore_global', '.gitconfig', '.gitattributes', '.gitkeep', '.gitmodules', '.gitignore_global', '.gitconfig', '.gitattributes', '.gitkeep', '.gitmodules', '.gitignore_global', '.gitconfig', '.gitattributes', '.gitkeep', '.gitmodules', '.gitignore_global', '.gitconfig', '.gitattributes', '.gitkeep', '.gitmodules', '.gitignore_global', '.gitconfig', '.gitattributes', '.gitkeep', '.gitmodules', '.gitignore_global', '.gitconfig', '.gitattributes', '.gitkeep', '.gitmodules', '.gitignore_global', '.gitconfig', '.gitattributes', '.gitkeep', '.gitmodules', '.gitignore_global', '.gitconfig', '.gitattributes', '.gitkeep', '.gitmodules', '.gitignore_global', '.gitconfig', '.gitattributes', '.gitkeep', '.gitmodules', '.gitignore_global']:
                return "The file is not a text based file"
            # check if its a pdf
            if os.path.splitext(file_path)[1] == '.pdf':
                # convert pdf to text
                with open(file_path, "rb") as f:
                    pdfreader=PyPDF2.PdfReader(f)
                    text = ""
                    for page in pdfreader.pages:
                        text += page.extract_text()
                return f'the content of {file_path} is:\n---STARTFILE---\n{text[:7000]}\n---ENDOFFILE---\n\n'
            # check if its a docx
            if os.path.splitext(file_path)[1] == '.docx':
                # convert docx to text
                from docx import Document
                doc = Document(file_path)
                fullText = []
                for para in doc.paragraphs:
                    fullText.append(para.text)
                return f'the content of {file_path} is:\n---STARTFILE---\n{fullText[:7000]}\n---ENDOFFILE---\n\n'
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f'the content of {file_path} is:\n---STARTFILE---\n{f.read()[:7000]}\n---ENDOFFILE---\n\n'
        elif os.path.isdir(file_path):
            output = ""
            count = 0
            limit = 20
            ignore_dirs = ['.git', 'objects', '__pycache__']
            for root, dirs, files in os.walk(file_path):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                level = root.replace(file_path, '').count(os.sep)
                indent = ' ' * 4 * (level)
                output += '{}{}/\n'.format(indent, os.path.basename(root))
                count += 1
                if count >= limit:
                    break
                subindent = ' ' * 4 * (level + 1)
                for f in files:
                    output += '{}{}\n'.format(subindent, f)
                    count += 1
                    if count >= limit:
                        break
            return output
        else:
            return "The path does not exist"
    elif action == "edit" or action == "save":
        if content is None:
            return "No content provided to write to the file"
        with open(file_path, 'w') as f:
            f.write(content)
        return f"File {file_path} edited/saved successfully with content:\n---STARTFILE---\n{content}\n---ENDOFFILE---\n\n"
    elif action == "create":
        # If the file_path has an extension, assume it's a file
        if os.path.splitext(file_path)[1]:
            # Get the directory name from the file_path
            directory = os.path.dirname(file_path)

            # If the directory does not exist, create it
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                dir_message = f"Directory: {directory} created successfully.\n"
            else:
                dir_message = ""

            # Now, create the file
            with open(file_path, 'w') as f:
                if content is not None:
                    f.write(content)
            return f"{dir_message}File: {file_path} created successfully with content:\n---STARTFILE---\n{content}\n---ENDOFFILE---\n\n"
        else:  # Assume it's a directory
            os.makedirs(file_path, exist_ok=True)
            return f"Directory: {file_path} created successfully with no content."
    elif action == "delete":
        if confirm_delete:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)
            else:
                return "The path does not exist"
            return f"File/directory: {file_path} deleted successfully"
        else:
            return "Confirmation for delete not provided"
    else:
        return "Invalid action"
