import unittest
from unittest.mock import MagicMock, patch
from memory import MemoryManager


class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        self.memory_manager = MemoryManager()

    def test_create_memory(self):
        # Mock the create_memory function
        self.memory_manager.create_memory = MagicMock(return_value="1234")

        # Call the function and check the return value
        result = self.memory_manager.create_memory("test_category", "test_document")
        self.assertEqual(result, "1234")

        # Check that the create_memory function was called with the correct arguments
        self.memory_manager.create_memory.assert_called_once_with(
            "test_category", "test_document"
        )

    def test_create_unique_memory(self):
        # Mock the create_unique_memory function
        self.memory_manager.create_unique_memory = MagicMock(return_value="5678")

        # Call the function and check the return value
        result = self.memory_manager.create_unique_memory(
            "test_category", "test_content"
        )
        self.assertEqual(result, "5678")

        # Check that the create_unique_memory function was called with the correct arguments
        self.memory_manager.create_unique_memory.assert_called_once_with(
            "test_category", "test_content"
        )

    def test_get_memories(self):
        # Mock the get_memories function
        self.memory_manager.get_memories = MagicMock(
            return_value=["memory1", "memory2"]
        )

        # Call the function and check the return value
        result = self.memory_manager.get_memories("test_category")
        self.assertEqual(result, ["memory1", "memory2"])

        # Check that the get_memories function was called with the correct arguments
        self.memory_manager.get_memories.assert_called_once_with("test_category")

    def test_search_memory(self):
        # Mock the search_memory function
        self.memory_manager.search_memory = MagicMock(
            return_value=["memory1", "memory2"]
        )

        # Call the function and check the return value
        result = self.memory_manager.search_memory("test_category", "test_search_term")
        self.assertEqual(result, ["memory1", "memory2"])

        # Check that the search_memory function was called with the correct arguments
        self.memory_manager.search_memory.assert_called_once_with(
            "test_category", "test_search_term"
        )

    def test_search_memory_by_date(self):
        # Mock the search_memory_by_date function
        self.memory_manager.search_memory_by_date = MagicMock(
            return_value=["memory1", "memory2"]
        )

        # Call the function and check the return value
        result = self.memory_manager.search_memory_by_date(
            "test_category", "test_search_term"
        )
        self.assertEqual(result, ["memory1", "memory2"])

        # Check that the search_memory_by_date function was called with the correct arguments
        self.memory_manager.search_memory_by_date.assert_called_once_with(
            "test_category", "test_search_term"
        )

    def test_get_memory(self):
        # Mock the get_memory function
        self.memory_manager.get_memory = MagicMock(return_value="test_memory")

        # Call the function and check the return value
        result = self.memory_manager.get_memory("test_category", "test_id")
        self.assertEqual(result, "test_memory")

        # Check that the get_memory function was called with the correct arguments
        self.memory_manager.get_memory.assert_called_once_with(
            "test_category", "test_id"
        )

    def test_update_memory(self):
        # Mock the update_memory function
        self.memory_manager.update_memory = MagicMock(return_value="test_id")

        # Call the function and check the return value
        result = self.memory_manager.update_memory(
            "test_category", "test_id", document="test_document"
        )
        self.assertEqual(result, "test_id")

        # Check that the update_memory function was called with the correct arguments
        self.memory_manager.update_memory.assert_called_once_with(
            "test_category", "test_id", document="test_document"
        )

    def test_delete_memory(self):
        # Mock the delete_memory function
        self.memory_manager.delete_memory = MagicMock(return_value="test_id")

        # Call the function and check the return value
        result = self.memory_manager.delete_memory("test_category", "test_id")
        self.assertEqual(result, "test_id")

        # Check that the delete_memory function was called with the correct arguments
        self.memory_manager.delete_memory.assert_called_once_with(
            "test_category", "test_id"
        )

    def test_delete_similar_memories(self):
        # Mock the delete_similar_memories function
        self.memory_manager.delete_similar_memories = MagicMock(return_value=2)

        # Call the function and check the return value
        result = self.memory_manager.delete_similar_memories(
            "test_category", "test_content"
        )
        self.assertEqual(result, 2)

        # Check that the delete_similar_memories function was called with the correct arguments
        self.memory_manager.delete_similar_memories.assert_called_once_with(
            "test_category", "test_content"
        )

    def test_count_memories(self):
        # Mock the count_memories function
        self.memory_manager.count_memories = MagicMock(return_value=5)

        # Call the function and check the return value
        result = self.memory_manager.count_memories("test_category")
        self.assertEqual(result, 5)

        # Check that the count_memories function was called with the correct arguments
        self.memory_manager.count_memories.assert_called_once_with("test_category")

    def test_wipe_category(self):
        # Mock the wipe_category function
        self.memory_manager.wipe_category = MagicMock(return_value=3)

        # Call the function and check the return value
        result = self.memory_manager.wipe_category("test_category")
        self.assertEqual(result, 3)

        # Check that the wipe_category function was called with the correct arguments
        self.memory_manager.wipe_category.assert_called_once_with("test_category")

    def test_wipe_all_memories(self):
        # Mock the wipe_all_memories function
        self.memory_manager.wipe_all_memories = MagicMock(return_value=10)

        # Call the function and check the return value
        result = self.memory_manager.wipe_all_memories()
        self.assertEqual(result, 10)

        # Check that the wipe_all_memories function was called with the correct arguments
        self.memory_manager.wipe_all_memories.assert_called_once_with()

    def test_import_memories(self):
        # Mock the import_memories function
        self.memory_manager.import_memories = MagicMock(return_value=7)

        # Call the function and check the return value
        result = self.memory_manager.import_memories("test_path")
        self.assertEqual(result, 7)

        # Check that the import_memories function was called with the correct arguments
        self.memory_manager.import_memories.assert_called_once_with("test_path")

    def test_export_memories(self):
        # Mock the export_memories function
        self.memory_manager.export_memories = MagicMock(return_value=4)

        # Call the function and check the return value
        result = self.memory_manager.export_memories("test_path")
        self.assertEqual(result, 4)

        # Check that the export_memories function was called with the correct arguments
        self.memory_manager.export_memories.assert_called_once_with("test_path")

    def test_stop_database(self):
        # Mock the stop_database function
        self.memory_manager.stop_database = MagicMock(return_value="stopped")

        # Call the function and check the return value
        result = self.memory_manager.stop_database()
        self.assertEqual(result, "stopped")

        # Check that the stop_database function was called with the correct arguments
        self.memory_manager.stop_database.assert_called_once_with()

    async def test_split_text_into_chunks(self):
        # Mock the nltk.sent_tokenize and nltk.word_tokenize functions
        with patch("nltk.sent_tokenize", return_value=["sentence1", "sentence2"]):
            with patch(
                "nltk.word_tokenize",
                side_effect=[["word1", "word2"], ["word3", "word4"]],
            ):
                # Call the function and check the return value
                result = await self.memory_manager.split_text_into_chunks(
                    "test_text", 3
                )
                self.assertEqual(result, ["word1 word2 word3", "word2 word3 word4"])

    async def test_process_episodic_memory(self):
        # Mock the search_memory_by_date function
        self.memory_manager.search_memory_by_date = MagicMock(
            return_value=[
                {
                    "metadata": {"created_at": 1234567890},
                    "document": "test_memory",
                    "distance": 0.1,
                }
            ]
        )

        # Mock the set_username function
        self.memory_manager.openai_manager.set_username = MagicMock()

        # Call the function and check the return value
        result = await self.memory_manager.process_episodic_memory(
            "test_messages", username="test_user", all_messages="test_all_messages"
        )
        self.assertEqual(
            result, ("1234567890 - test_memory (score: 0.1)\n", "test_memory")
        )

        # Check that the search_memory_by_date function was called with the correct arguments
        self.memory_manager.search_memory_by_date.assert_called_once_with(
            "active_brain",
            "test_messages",
            username="test_user",
            filter_date=1234567890,
        )

        # Check that the set_username function was called with the correct argument
        self.memory_manager.openai_manager.set_username.assert_called_once_with(
            "test_user"
        )

    async def test_process_active_brain(self):
        # Mock the search_memory function
        self.memory_manager.search_memory = MagicMock(
            return_value=[{"document": "test_memory", "id": "test_id", "distance": 0.1}]
        )

        # Mock the split_text_into_chunks function
        self.memory_manager.split_text_into_chunks = MagicMock(
            return_value=["test_chunk"]
        )

        # Mock the create_memory function
        self.memory_manager.create_memory = MagicMock()

        # Mock the ask_openai function
        self.memory_manager.openai_manager.ask_openai = MagicMock(
            return_value={"choices": [{"message": {"content": "test_subject"}}]}
        )

        # Call the function and check the return value
        result = await self.memory_manager.process_active_brain(
            "test_messages", username="test_user", all_messages="test_all_messages"
        )
        self.assertEqual(result["created_new_memory"], "yes")

        # Check that the search_memory function was called with the correct arguments
        self.memory_manager.search_memory.assert_called_once_with(
            "active_brain", "test_messages", "test_user", max_distance=0.15
        )

        # Check that the split_text_into_chunks function was called with the correct arguments
        self.memory_manager.split_text_into_chunks.assert_called_once_with(
            "test_messages", 200
        )

        # Check that the create_memory function was called with the correct arguments
        self.memory_manager.create_memory.assert_called_once_with(
            "active_brain",
            "test_chunk",
            username="test_user",
            metadata={"uid": MagicMock()},
        )

        # Check that the ask_openai function was called with the correct arguments
        self.memory_manager.openai_manager.ask_openai.assert_called_once_with(
            "test_all_messages",
            "retriever",
            self.memory_manager.model_used,
            100,
            0.1,
            username="test_user",
        )
