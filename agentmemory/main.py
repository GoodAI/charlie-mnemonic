import datetime
import os
import time
import logs

logger = logs.Log("agentmemory", "agentmemory.log").get_logger()

os.environ["TOKENIZERS_PARALLELISM"] = "false"

from agentmemory.helpers import (
    chroma_collection_to_list,
    debug_log,
    flatten_arrays,
    get_include_types,
)


from agentmemory.client import get_client


def create_memory(
    category,
    text,
    metadata={},
    embedding=None,
    id=None,
    username=None,
    mUsername=None,
    regenerate=False,
):
    """
    Create a new memory in a collection.

    Arguments:
    category (str): Category of the collection.
    text (str): Document text.
    id (str): Unique id.
    metadata (dict): Metadata.

    Returns:
    None

    Example:
    >>> create_memory('sample_category', 'sample_text', id='sample_id', metadata={'sample_key': 'sample_value'})
    """
    # get or create the collection
    memories = get_client(username=username).get_or_create_collection(category)

    # add timestamps to metadata
    metadata["created_at"] = datetime.datetime.now().timestamp()
    metadata["updated_at"] = datetime.datetime.now().timestamp()

    # add username to metadata
    metadata["username"] = mUsername if mUsername is not None else "assistant"

    logger.debug(f"created_at: {metadata['created_at']}")
    # convert to human readable format
    formatted_date = datetime.datetime.fromtimestamp(metadata["created_at"]).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    logger.debug(f"formatted_date: {formatted_date}")

    # if no id is provided, generate one based on count of documents in collection
    if id is None:
        id = str(memories.count())
        # pad the id with zeros to make it 16 digits long
        id = id.zfill(16)

    # for each field in metadata...
    # if the field is a boolean, convert it to a string
    for key, value in metadata.items():
        if (
            isinstance(value, bool)
            or isinstance(value, dict)
            or isinstance(value, list)
        ):
            debug_log(f"WARNING: Boolean metadata field {key} converted to string")
            metadata[key] = str(value)

    text = str(text)

    # insert the document into the collection
    try:
        memories.upsert(
            ids=[str(id)],
            documents=[text],
            metadatas=[metadata],
            embeddings=[embedding] if embedding is not None else None,
        )
        debug_log(f"Created memory {id}: {text}", metadata)
        return id
    except Exception as e:
        debug_log(
            f"ERROR: Could not create memory {id}: {text}", metadata, type="error"
        )
        debug_log(f"ERROR: {e}", type="error")
        return None


def create_unique_memory(
    category, content, metadata={}, similarity=0.95, username=None
):
    """
    Creates a new memory if there aren't any that are very similar to it

    Parameters:
    - content (str): The content of the memory.
    - metadata (dict, optional): Additional metadata for the memory.
        Defaults to empty dictionary.
    - similarity (float, optional): The threshold for determining similarity.
        Defaults to DEFAULT_SIMILARY_THRESHOLD.

    Returns: None
    """

    max_distance = 1.0 - similarity

    memories = search_memory(
        category,
        min_distance=0,
        max_distance=max_distance,
        search_text=content,
        n_results=1,
        filter_metadata={"novel": "True"},
        username=username,
    )

    if len(memories) == 0:
        metadata["novel"] = "True"
        create_memory(category, content, metadata=metadata, username=username)
        return

    metadata["novel"] = "False"
    metadata["related_to"] = memories[0]["id"]
    metadata["related_document"] = memories[0]["document"]
    create_memory(category, content, metadata=metadata, username=username)
    return id


def create_alternative_memory(
    category, content, metadata={}, username=None, mUsername=None, chat_id=None
):
    """
    Creates a new alternate memory, basically a newer version of the memory
    """
    # placeholder for now
    metadata["novel"] = "True"
    create_memory(category, content, metadata=metadata, username=username)
    return id


def search_memory_by_date(
    category,
    search_text,
    n_results=100,
    filter_date=None,
    contains_text=None,
    include_embeddings=True,
    include_distances=True,
    max_distance=None,  # 0.0 - 1.0
    min_distance=None,  # 0.0 - 1.0
    novel=False,
    username=None,
):
    if filter_date is not None:
        # convert filter_date to string
        filter_date = str(filter_date)
        if isinstance(filter_date, str):
            # List of date formats
            logger.debug(f"filter_date: {filter_date}")
            date_formats = [
                "%Y-%m-%d",
                "%d/%m/%Y %H:%M:%S",
                "%m/%d/%Y",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%d-%m-%Y %H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ]

            has_time = False  # Flag to track if the date format contains time

            # Try parsing the date with each format
            for date_format in date_formats:
                try:
                    filter_date = datetime.datetime.strptime(filter_date, date_format)
                    if (
                        "%H:%M:%S" in date_format
                        and filter_date.time() != datetime.time(0, 0)
                    ):  # Check if the date format contains time and it is not 00:00
                        has_time = True
                    break
                except ValueError:
                    continue

            # Calculate the timestamps for the start and end of filter_date
            start_of_date = datetime.datetime(
                filter_date.year,
                filter_date.month,
                filter_date.day,
                filter_date.hour,
                filter_date.minute,
                filter_date.second,
            )
            logger.debug(f"start_of_date: {start_of_date}")
            if (
                has_time
            ):  # If the date format contains time and it is not 00:00, add an hour
                end_of_date = start_of_date + datetime.timedelta(hours=1)
                logger.debug(f"end_of_date: {end_of_date}")
            else:  # Otherwise, add a day
                end_of_date = start_of_date + datetime.timedelta(days=1)
                logger.debug(f"end_of_date: {end_of_date}")
            start_timestamp = start_of_date.timestamp() - 0.000001
            end_timestamp = end_of_date.timestamp() + 0.000001
            logger.debug(f"start_timestamp: {start_timestamp}")
            logger.debug(f"end_timestamp: {end_timestamp}")

            # filter_metadata = {'created_at': {'$gte': start_timestamp}}
            # filter_metadata = {'created_at': {'$lte': end_timestamp}}
            filter_metadata = {
                "$and": [
                    {"created_at": {"$gt": start_timestamp}},
                    {"created_at": {"$lt": end_timestamp}},
                ]
            }
        else:
            logger.error(f"filter_date must be a string")
            return ValueError("filter_date must be a string")
        logger.debug(f"filter_metadata: {filter_metadata}")

    return search_memory(
        category=category,
        search_text=search_text,
        n_results=n_results,
        filter_metadata=filter_metadata,
        contains_text=contains_text,
        include_embeddings=include_embeddings,
        include_distances=include_distances,
        max_distance=max_distance,
        min_distance=min_distance,
        novel=novel,
        username=username,
    )


def get_memory_by_date(
    category,
    filter_date=None,
    username=None,
):
    if filter_date is not None:
        # convert filter_date to string
        filter_date = str(filter_date)
        if isinstance(filter_date, str):
            # List of date formats
            date_formats = [
                "%Y-%m-%d",
                "%d/%m/%Y %H:%M:%S",
                "%m/%d/%Y",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%d-%m-%Y %H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ]

            has_time = False  # Flag to track if the date format contains time

            # Try parsing the date with each format
            for date_format in date_formats:
                try:
                    filter_date = datetime.datetime.strptime(filter_date, date_format)
                    if (
                        "%H:%M:%S" in date_format
                        and filter_date.time() != datetime.time(0, 0)
                    ):  # Check if the date format contains time
                        has_time = True
                    break
                except ValueError:
                    continue

            # Calculate the timestamps for the start and end of filter_date
            start_of_date = datetime.datetime(
                filter_date.year,
                filter_date.month,
                filter_date.day,
                filter_date.hour,
                filter_date.minute,
                filter_date.second,
            )
            logger.debug(f"start_of_date: {start_of_date}")
            if has_time:  # If the date format contains time, add an hour
                end_of_date = start_of_date + datetime.timedelta(hours=1)
                logger.debug(f"end_of_date: {end_of_date}")
            else:  # Otherwise, add a day
                end_of_date = start_of_date + datetime.timedelta(days=1)
                logger.debug(f"end_of_date: {end_of_date}")
            start_timestamp = start_of_date.timestamp()
            end_timestamp = end_of_date.timestamp()
            logger.debug(f"start_timestamp: {start_timestamp}")
            logger.debug(f"end_timestamp: {end_timestamp}")

            memories = get_client(username=username).get_or_create_collection(category)
            for memory in memories:
                pass
            results = memories.get(
                where={
                    "$and": [
                        {"created_at": {"$gt": start_timestamp}},
                        {"created_at": {"$lt": end_timestamp}},
                    ]
                }
            )
            query = flatten_arrays(results)
            # convert the query response to list and return
            result_list = chroma_collection_to_list(query)
            return result_list


def search_memory(
    category,
    search_text,
    n_results=50,
    filter_metadata=None,
    contains_text=None,
    include_embeddings=True,
    include_distances=True,
    max_distance=None,  # 0.0 - 1.0
    min_distance=None,  # 0.0 - 1.0
    novel=False,
    username=None,
):
    """
    Cearch a collection with given query texts.

    Arguments:
    category (str): Category of the collection.
    search_text (str): Text to be searched.
    n_results (int): Number of results to be returned.
    filter_metadata (dict): Metadata for filtering the results.
    contains_text (str): Text that must be contained in the documents.
    include_embeddings (bool): Whether to include embeddings in the results.
    include_distances (bool): Whether to include distances in the results.
    max_distance (float): Only include memories with this distance threshold maximum.
        0.1 = most memories will be exluded, 1.0 = no memories will be excluded
    min_distance (float): Only include memories that are at least this distance
        0.0 = No memories will be excluded, 0.9 = most memories will be excluded
    novel (bool): Only include memories that are marked as novel

    Returns:
    list: List of search results.

    Example:
    >>> search_memory('sample_category', 'search_text', n_results=2, filter_metadata={'sample_key': 'sample_value'}, contains_text='sample', include_embeddings=True, include_distances=True)
    [{'metadata': '...', 'document': '...', 'id': '...'}, {'metadata': '...', 'document': '...', 'id': '...'}]
    """

    # check if contains_text is provided and format it for the query
    if contains_text is not None:
        contains_text = {"$contains": contains_text}

    # get or create the collection
    memories = get_client(username=username).get_or_create_collection(category)

    if (memories.count()) == 0:
        return []

    # min n_results to prevent searching for more elements than are available
    n_results = min(n_results, memories.count())

    # get the types to include
    include_types = get_include_types(include_embeddings, include_distances)

    # filter_metadata is a dictionary of metadata to filter by
    if filter_metadata is not None and len(filter_metadata.keys()) > 1:
        # map each key:value in filter_metadata to an object shaped like { "key": { "$eq": "value" } }
        filter_metadata = [
            {key: {"$eq": value}} for key, value in filter_metadata.items()
        ]

        filter_metadata = {"$and": filter_metadata}

    if novel:
        if filter_metadata is None:
            filter_metadata = {}
        filter_metadata["novel"] = "True"

    # perform the query and get the response
    query = memories.query(
        query_texts=[search_text],
        where=filter_metadata,
        where_document=contains_text,
        n_results=n_results,
        include=include_types,
    )

    # if isinstance(query, list):
    query = flatten_arrays(query)

    # convert the query response to list and return
    result_list = chroma_collection_to_list(query)

    if min_distance is not None and min_distance > 0:
        result_list = [res for res in result_list if res["distance"] >= min_distance]

    if max_distance is not None and max_distance < 2.0:
        result_list = [res for res in result_list if res["distance"] <= max_distance]

    debug_log(f"Searched memory: {search_text}", result_list)

    return result_list


def get_memory(category, id, include_embeddings=True, username=None):
    """
    Retrieve a specific memory from a given category based on its ID.

    Arguments:
        category (str): The category of the memory.
        id (str/int): The ID of the memory.
        include_embeddings (bool, optional): Whether to include the embeddings. Defaults to True.

    Returns:
        dict: The retrieved memory.

    Example:
        >>> get_memory("books", "1")
    """

    # Get or create the collection for the given category
    memories = get_client(username=username).get_or_create_collection(category)

    # Get the types to include based on the function parameters
    include_types = get_include_types(include_embeddings, False)

    memory = memories.get(ids=[id], limit=1, include=include_types)

    memory = chroma_collection_to_list(memory)

    debug_log(f"Got memory {id} from category {category}", memory)

    if len(memory) == 0:
        debug_log(
            f"WARNING: Tried to get memory {id} from category {category} but it does not exist",
            type="warning",
        )
        return None

    # Return the first (and only) memory in the list
    return memory[0]


def get_memories(
    category,
    sort_order="desc",
    contains_text=None,
    filter_metadata=None,
    n_results=20,
    include_embeddings=True,
    novel=False,
    username=None,
    start_from=None,
):
    """
    Retrieve a list of memories from a given category, sorted by ID, with optional filtering.

    Arguments:
        category (str): The category of the memories.
        sort_order (str, optional): The sorting order of the memories. Can be 'asc' or 'desc'. Defaults to 'desc'.
        filter_metadata (dict, optional): Filter to apply on metadata. Defaults to None.
        n_results (int, optional): The number of results to return. Defaults to 20.
        include_embeddings (bool, optional): Whether to include the embeddings. Defaults to True.
        novel (bool, optional): Whether to only include memories that are marked as novel. Defaults to False.

    Returns:
        list: List of retrieved memories.

    Example:
        >>> get_memories("books", sort_order="asc", n_results=10)
    """

    # Get or create the collection for the given category
    memories = get_client(username=username).get_or_create_collection(category)

    # min n_results to prevent searching for more elements than are available
    n_results = min(n_results, memories.count())

    # Get the types to include based on the function parameters
    include_types = get_include_types(include_embeddings, False)

    where_document = None

    if contains_text is not None:
        where_document = {"$contains": contains_text}

    # filter_metadata is a dictionary of metadata to filter by
    if filter_metadata is not None and len(filter_metadata.keys()) > 1:
        # map each key:value in filter_metadata to an object shaped like { "key": { "$eq": "value" } }
        filter_metadata = [
            {key: {"$eq": value}} for key, value in filter_metadata.items()
        ]

        filter_metadata = {"$and": filter_metadata}

    if novel:
        if filter_metadata is None:
            filter_metadata = {}
        filter_metadata["novel"] = "True"

    # Retrieve all memories that meet the given metadata filter
    memories = memories.get(
        where=filter_metadata, where_document=where_document, include=include_types
    )

    if not isinstance(memories, list):
        # Convert the collection to list format
        memories = chroma_collection_to_list(memories)

    # Sort memories by ID. If sort_order is 'desc', then the reverse parameter will be True, and memories will be sorted in descending order.
    memories.sort(key=lambda x: x["id"], reverse=sort_order == "desc")

    # Only keep the top n_results memories
    memories = memories[:n_results]

    debug_log(f"Got memories from category {category}", memories)

    return memories


def get_last_message(category, chat_id, username=None, message_uuid=None):
    """
    Retrieve the second to last message from a given category or the message before the message with the given UUID.

    Arguments:
        category (str): The category of the memories.
        chat_id (str): The chat_id of the chat.
        username (str, optional): The username for client authentication. Defaults to None.
        message_uuid (str, optional): The UUID of the message to find the preceding message of. Defaults to None.

    Returns:
        dict: The retrieved memory.

    Example:
        >>> get_last_message("books", "1")
        >>> get_last_message("books", "1", message_uuid="some-uuid")
    """

    # Get or create the collection for the given category
    memories = get_client(username=username).get_or_create_collection(category)

    # Get the types to include based on the function parameters
    include_types = get_include_types(True, False)

    # Retrieve all memories that meet the given metadata filter
    memories = memories.get(where={"chat_id": chat_id}, include=include_types)

    if not isinstance(memories, list):
        # Convert the collection to list format
        memories = chroma_collection_to_list(memories)

    # Sort memories by ID. Sorting in descending order to make it easier to access the second to last message.
    memories.sort(key=lambda x: x["metadata"]["created_at"], reverse=False)

    debug_log(f"Got previous last message from category {category}", memories)

    if message_uuid:
        # Iterate over memories to find the one with the given UUID and return the message before it
        for i, memory in enumerate(memories):
            if memory.get("metadata").get("uid") == message_uuid and i > 0:
                return memories[i - 1]["document"]
        return (
            {}
        )  # Return an empty dict if the UUID is not found or is the first message
    elif len(memories) > 1:
        # Access the second to last message if there are enough memories, otherwise return an empty dict
        return memories[1]["document"]
    else:
        return {}  # Return an empty dict if there's only one or no messages


def update_memory(
    category, id, text=None, metadata=None, embedding=None, username=None
):
    """
    Update a memory with new text and/or metadata.

    Arguments:
        category (str): The category of the memory.
        id (str/int): The ID of the memory.
        text (str, optional): The new text of the memory. Defaults to None.
        metadata (dict, optional): The new metadata of the memory. Defaults to None.

    Returns:
        None

    Raises:
        Exception: If neither text nor metadata is provided.

    Example:
        >>> update_memory("books", "1", text="New text", metadata={"author": "New author"})
    """

    # Get or create the collection for the given category
    memories = get_client(username=username).get_or_create_collection(category)

    # If neither text nor metadata is provided, raise an exception
    if metadata is None and text is None:
        raise Exception("No text or metadata provided")
    if metadata is not None:
        # for each key value in metadata -- if the type is boolean, convert it to string
        for key, value in metadata.items():
            if (
                isinstance(value, bool)
                or isinstance(value, dict)
                or isinstance(value, list)
            ):
                debug_log(f"WARNING: Boolean metadata field {key} converted to string")
                metadata[key] = str(value)
    else:
        metadata = {}

    metadata["updated_at"] = datetime.datetime.now().timestamp()

    documents = [text] if text is not None else None
    metadatas = [metadata] if metadata is not None else None
    embeddings = [embedding] if embedding is not None else None
    # Update the memory with the new text and/or metadata
    memories.update(
        ids=[str(id)], documents=documents, metadatas=metadatas, embeddings=embeddings
    )

    debug_log(
        f"Updated memory {id} in category {category}",
        {"documents": documents, "metadatas": metadatas},
    )


def delete_memory(category, id, username=None):
    """
    Delete a memory by ID.

    Arguments:
        category (str): The category of the memory.
        id (str/int): The ID of the memory.

    Returns:
        None

    Example:
        >>> delete_memory("books", "1")
    """
    # Get or create the collection for the given category
    memories = get_client(username=username).get_or_create_collection(category)

    if not memory_exists(category, id, username=username):
        debug_log(
            f"WARNING: Tried could not delete memory {id} in category {category}",
            type="warning",
        )
        return
    # Delete the memory
    memories.delete(ids=[str(id)])

    debug_log(f"Deleted memory {id} in category {category}")


def delete_memories(category, document=None, metadata=None, username=None):
    """
    Delete all memories in the category either by document, or by metadata, or by both.

    Arguments:
        category (str): The category of the memories.
        document (str, optional): The text of the memories to delete. Defaults to None.
        metadata (dict, optional): The metadata of the memories to delete. Defaults to None.

    Returns:
        bool: True if memories are deleted, False otherwise.

    Example:
        >>> delete_memories("books", document="Foundation", metadata={"author": "Isaac Asimov"})
    """

    # Get or create the collection for the given category
    memories = get_client(username=username).get_or_create_collection(category)

    # Create a query to match either the document or the metadata
    if document is not None:
        memories.delete(where_document={"$contains": document})
    if metadata is not None:
        memories.delete(where=metadata)

    debug_log(f"Deleted memories from category {category}")

    return True


def delete_similar_memories(
    category, content, similarity_threshold=0.95, username=None
):
    """
    Search for memories that are similar to the item that contains the content and removes it.

    Parameters:
    - content (str): The content to search for.
    - similarity_threshold (float, optional): The threshold for determining similarity. Defaults to DEFAULT_SIMILARY_THRESHOLD.

    Returns: bool - True if the memory item is found and removed, False otherwise.
    """

    memories = search_memory(category, content, username=username)
    memories_to_delete = []

    # find similar memories
    if len(memories) > 0:
        for memory in memories:
            goal_similarity = 1.0 - memory["distance"]
            if goal_similarity > similarity_threshold:
                memories_to_delete.append(memory["id"])
            else:
                # responses are sorted by similarity, so ignore the rest
                break

    if len(memories_to_delete) > 0:
        debug_log(
            f"Deleting similar memories to {content} in category {category}",
            memories_to_delete,
        )
        for memory in memories_to_delete:
            delete_memory(category, memory, username=username)
    debug_log(
        f"WARNING: Tried to delete similar memories to {content} in category {category} but none were found",
        type="warning",
    )
    return len(memories_to_delete) > 0


def memory_exists(category, id, includes_metadata=None, username=None):
    """
    Check if a memory with a specific ID exists in a given category.

    Arguments:
        category (str): The category of the memory.
        id (str/int): The ID of the memory.
        includes_metadata (dict, optional): Metadata that the memory should include. Defaults to None.

    Returns:
        bool: True if the memory exists, False otherwise.

    Example:
        >>> memory_exists("books", "1")
    """

    # Get or create the collection for the given category
    memories = get_client(username=username).get_or_create_collection(category)

    # Check if there's a memory with the given ID and metadata
    memory = memories.get(ids=[str(id)], where=includes_metadata, limit=1)

    exists = len(memory["ids"]) > 0

    debug_log(
        f"Checking if memory {id} exists in category {category}. Exists: {exists}"
    )

    # Return True if at least one memory was found, False otherwise
    return exists


def count_memories(category, novel=False, username=None):
    """
    Count the number of memories in a given category.

    Arguments:
        category (str): The category of the memories.

    Returns:
        int: The number of memories.

    Example:
        >>> count_memories("books")
    """

    # Get or create the collection for the given category
    memories = get_client(username=username).get_or_create_collection(category)

    if novel:
        memories = memories.get(where={"novel": "True"})

    debug_log(f"Counted memories in {category}: {memories.count()}")

    # Return the count of memories
    return memories.count()


def wipe_category(category, username=None):
    """
    Delete an entire category of memories.

    Arguments:
        category (str): The category to delete.

    Example:
        >>> wipe_category("books")
    """

    collection = None

    try:
        collection = get_client(username=username).get_collection(
            category
        )  # Check if the category exists
    except Exception:
        debug_log(
            f"WARNING: Tried to wipe category {category} but it does not exist",
            type="warning",
        )

    if collection is not None:
        # Delete the entire category
        get_client(username=username).delete_collection(category)


def wipe_all_memories(username=None):
    """
    Delete all memories across all categories.

    Example:
        >>> wipe_all_memories()
    """
    client = get_client(username=username)
    collections = client.list_collections()

    # Iterate over all collections
    for collection in collections:
        client.delete_collection(collection.name)

    debug_log("Wiped all memories", type="system")


def stop_database(username=None):
    """
    Stop the database.

    Example:
        >>> stop_database()
    """
    client = get_client(username=username)
    client.reset()
