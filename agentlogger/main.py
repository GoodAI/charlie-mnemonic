from rich.panel import Panel
from rich.console import Console
from pyfiglet import figlet_format
from termcolor import colored

console = Console()

DEFAULT_TYPE_COLORS = {
    "unknown": "white",
    "system": "magenta",
    "info": "blue",
    "warning": "yellow",
    "success": "green",
    "error": "red",
    "start": "green",
    "stop": "red",
    "pause": "yellow",
    "epoch": "white",
    "summary": "cyan",
    "reasoning": "cyan",
    "action": "green",
    "prompt": "cyan",
}


def log(
    content,
    source=None,
    title="agentlogger",
    type="info",
    color="blue",
    type_colors=DEFAULT_TYPE_COLORS,
    expand=True,  # expand the panel?
    panel=True,  # display inside a bordered box panel?
    log=True,  # should log?
):
    """
    Create an event with provided metadata and saves it to the event log file

    Parameters:
    - content: Content of the event
    - source (optional): Source of the event, e.g. a function name.
        Defaults to None.
    - title (optional): Title of the event.
    - type (optional): Type of the event.
        Defaults to None.
    - type_colors (optional): Dictionary with event types as keys and colors
        Defaults to empty dictionary.
    - panel (optional): Determines if the output should be within a Panel
        Defaults to True.
    - log (optional): Determines if the output should be logged

    Returns: None
    """
    if log is not True:
        return

    title = f"({type}) {title}"

    if source is not None:
        title += ": " + source

    color = type_colors.get(type, color)

    if panel:
        print("")
        console.print(
            Panel("\n" + str(content) + "\n", title=title, style=color, expand=expand)
        )
    else:
        console.print(content, style=color)


def print_header(
    text="agentlogger",
    font="slant",
    color="yellow",
    width=console.width,
    justify="left",
):
    """
    Display a header with the provided text and color.
    """
    ascii_logo = figlet_format(text, font=font, width=width, justify=justify)
    print(colored(ascii_logo, color))


def write_to_file(
    content, source=None, type=None, filename="events.log", separator_width=80
):
    """
    Writes content to the event log file.

    Arguments:
    - content: String to be written in the log file
    - source: Source of the event, e.g. a function name or file
    - type: Type of the event
    - filename: Name of the file where the content is written

    Return: None
    """
    header = ""
    if source is not None:
        header += f"{source}"
    if type is not None:
        if header != "":
            header += ": "
        header += type
    if header != "":
        header = " " + header + " "

    bar_length = int((separator_width - len(header)) / 2)
    header = f"{'=' * int(bar_length)} {header} {'=' * int(bar_length)}"
    footer = "=" * separator_width

    with open(filename, "a") as f:
        f.write(f"{header}\n\n")
        f.write(f"{content}\n\n")
        f.write(f"{footer}\n\n")
