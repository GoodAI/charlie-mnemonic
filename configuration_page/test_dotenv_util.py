from dataclasses import dataclass

import pytest

from configuration_page.dotenv_util import update_dotenv_contents


@dataclass
class DotenvTestData:
    original: str
    expected: str
    updates: dict
    description: str


test_cases = [
    DotenvTestData(
        original="""
OPENAI_API_KEY=original
ELEVENLABS_API_KEY=original
""",
        expected="""
OPENAI_API_KEY=new_value
ELEVENLABS_API_KEY=original
""",
        updates={"OPENAI_API_KEY": "new_value"},
        description="Update existing key",
    ),
    DotenvTestData(
        original="""
OPENAI_API_KEY=original
""",
        expected="""
OPENAI_API_KEY=original
NEW_KEY=new_value
""",
        updates={"NEW_KEY": "new_value"},
        description="Add new key",
    ),
    DotenvTestData(
        original="""
# Comment
EXISTING_KEY=existing_value
    """,
        expected="""
# Comment
EXISTING_KEY=existing_value
NEW_KEY=new_value
    """,
        updates={"NEW_KEY": "new_value"},
        description="Add new key, preserve comment",
    ),
    DotenvTestData(
        original="""
EXISTING_KEY=existing_value
# Comment
    """,
        expected="""
EXISTING_KEY=new_value
# Comment
    """,
        updates={"EXISTING_KEY": "new_value"},
        description="Update existing key, preserve trailing comment",
    ),
    DotenvTestData(
        original="""

# Leading blank line
EXISTING_KEY=existing_value
    """,
        expected="""

# Leading blank line
EXISTING_KEY=new_value
    """,
        updates={"EXISTING_KEY": "new_value"},
        description="Preserve leading blank lines and comments",
    ),
    DotenvTestData(
        original="""
EXISTING_KEY=existing_value
# Comment
# Another Comment
    """,
        expected="""
EXISTING_KEY=existing_value
# Comment
# Another Comment
NEW_KEY=new_value
    """,
        updates={"NEW_KEY": "new_value"},
        description="Add new key, preserve multiple comments",
    ),
    DotenvTestData(
        original="""
# Comment
EXISTING_KEY=existing_value
# Another Comment
    """,
        expected="""
# Comment
EXISTING_KEY=new_value
# Another Comment
    """,
        updates={"EXISTING_KEY": "new_value"},
        description="Update existing key, preserve comments before and after",
    ),
]


@pytest.mark.parametrize(
    "data", test_cases, ids=[test_case.description for test_case in test_cases]
)
def test_update_dotenv_contents(data: DotenvTestData):
    assert (
        update_dotenv_contents(data.original.strip(), data.updates)
        == data.expected.strip()
    )
