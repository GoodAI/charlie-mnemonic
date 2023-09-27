import datetime
import unittest
from agentmemory import search_memory_by_date, get_memory_by_date

class TestMemory(unittest.TestCase):
    def test_search_memory_by_date(self):
        # Test searching for episodic messages on a specific date
        category = "active_brain"
        new_messages = 'Bob'
        username = "Bob"
        filter_date = "2023-09-27 00:00:32"
        results_string, results_string2 = "", ""
        print(f'searching for episodic messages on a specific date: {filter_date} in category: {category} for user: {username} and message: {new_messages}')
        episodic_messages = search_memory_by_date(category, new_messages, username=username, filter_date=filter_date)
        episodic_messages_get = get_memory_by_date(category, username=username, filter_date=filter_date)
        print(f'episodic_messages: {len(episodic_messages)}')
        print(f'episodic_messages_get: {len(episodic_messages_get)}')
        #self.assertEqual(episodic_messages, [])
        for memory in episodic_messages:
            #transform date from 1695434677.402186 to human readable format
            date = memory['metadata']['created_at']
            formatted_date = datetime.datetime.fromtimestamp(date).strftime('%Y-%m-%d %H:%M:%S')
            #print(f"{formatted_date} - {memory['document']} (score: {memory['distance']})")
            results_string += f"{formatted_date} - {memory['document']} (score: {memory['distance']})\n"
        print(f"results_string:\n{results_string}")
        for memory in episodic_messages_get:
            #transform date from 1695434677.402186 to human readable format
            date = memory['metadata']['created_at']
            formatted_date = datetime.datetime.fromtimestamp(date).strftime('%Y-%m-%d %H:%M:%S')
            #print(f"{formatted_date} - {memory['document']}")
            results_string2 += f"{formatted_date} - {memory['document']}\n"
        print(f"results_string2:\n{results_string2}")
        #return results_string

if __name__ == '__main__':
    unittest.main()