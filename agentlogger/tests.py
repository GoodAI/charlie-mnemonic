import os
from agentlogger import (
    log,
    print_header,
    write_to_file,
)  # replace 'your_module' with the actual module name


def test_log():
    log("Test message", type="info")
    log("Test message", type="error")
    log("Test message", type="unknown")
    log("Test message", type="random")  # this will test the fallback color
    log("Test message", source="test_source")
    log("Test message", panel=False)
    log("Test message", log=False)  # this should do nothing


def test_print_header():
    print_header("Test header", font="slant", color="blue")
    print_header("Test header", font="doom", color="red")
    print_header("Test header", font="banner", color="green")


def test_write_to_file():
    filename = "test_events.log"
    write_to_file(
        "Test log content", source="test_source", type="info", filename=filename
    )

    # assert that the file now exists
    assert os.path.exists(filename)

    # remove the file to clean up
    os.remove(filename)
    assert not os.path.exists(filename)


def test_write_to_file_no_type_no_source():
    filename = "test_events.log"
    write_to_file("Test log content", type="log", filename=filename)

    # assert that the file now exists
    assert os.path.exists(filename)

    # read and print contents of filename
    with open(filename, "r") as f:
        print()
        print(f.read())

    write_to_file(
        "More log content",
        source="tests.py",
        type="test_write_to_file_no_type_no_source",
        filename=filename,
    )

    with open(filename, "r") as f:
        print()
        print(f.read())

    # remove the file to clean up
    os.remove(filename)
    assert not os.path.exists(filename)
