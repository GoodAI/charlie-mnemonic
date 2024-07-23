const debouncedChatSearch = debounce(searchChatHandler, 300);

function searchChatHandler() {
    const searchQuery = document.getElementById('searchInput').value;
    const searchStatus = document.getElementById('searchStatus');
    const searchResults = document.getElementById('searchResults');

    if (searchQuery.trim() === '') {
        searchResults.innerHTML = '';
        searchStatus.classList.remove('loading');
        return;
    }

    // Show loading spinner
    searchStatus.classList.add('loading');

    fetch('/search_chats/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            'category': "active_brain",
            'search_query': searchQuery,
            'sort_by': 'distance',
            'sort_order': 'asc'
        })
    })
    .then(response => response.json())
    .then(data => {
        // Reset loading spinner
        searchStatus.classList.remove('loading');

        searchResults.innerHTML = '';

        if (data.memories.length === 0 && data.rewritten_memories.length === 0) {
            searchResults.innerHTML = '<p class="text-muted">No results found.</p>';
        } else {
            // Render rewritten query if available
            if (data.rewritten) {
                const rewrittenElement = document.createElement('div');
                rewrittenElement.id = 'rewrittenQuery';
                rewrittenElement.innerHTML = `<strong>Rewritten query:</strong> ${data.rewritten}`;
                searchResults.appendChild(rewrittenElement);
            }

            // Add search result text
            const searchResultText = document.createElement('div');
            searchResultText.id = 'searchResultText';
            searchResultText.innerHTML = '<strong>Results:</strong>';
            searchResults.appendChild(searchResultText);

            // Group memories by chat_id (title)
            const groupedMemories = groupMemoriesByChat(data.memories);
            
            // Render grouped memories
            Object.entries(groupedMemories).forEach(([chatTitle, messages]) => {
                const chatResultElement = createChatResultElement(chatTitle, messages);
                searchResults.appendChild(chatResultElement);
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        searchStatus.classList.remove('loading');
        searchResults.innerHTML = '<p class="text-danger">An error occurred while searching.</p>';
    });
}

function createChatResultElement(chatTitle, messages) {
    const chatElement = document.createElement('div');
    chatElement.className = 'chat-search-result';

    const titleElement = document.createElement('div');
    titleElement.className = 'chat-title collapsed';
    titleElement.textContent = chatTitle;
    titleElement.onclick = () => toggleMessageList(titleElement);
    chatElement.appendChild(titleElement);

    const messageListElement = document.createElement('div');
    messageListElement.className = 'message-list';

    messages.forEach(message => {
        const messageElement = createMessageElement(message);
        messageListElement.appendChild(messageElement);
    });

    chatElement.appendChild(messageListElement);
    return chatElement;
}

function toggleMessageList(titleElement) {
    titleElement.classList.toggle('collapsed');
    const messageList = titleElement.nextElementSibling;
    messageList.classList.toggle('show');
}

function openChatSearch() {
    $('#chatSearchModal').modal('show');
    // Clear previous search results and input
    document.getElementById('searchInput').value = '';
    document.getElementById('searchResults').innerHTML = '';
    // Reset search icon
    document.getElementById('searchStatus').classList.remove('loading');
}

function closeChatSearch() {
    $('#chatSearchModal').modal('hide');
}


function groupMemoriesByChat(memories) {
    return memories.reduce((acc, memory) => {
        const chatTitle = memory.chat_title || 'Untitled Chat';
        if (!acc[chatTitle]) {
            acc[chatTitle] = [];
        }
        acc[chatTitle].push(memory);
        return acc;
    }, {});
}


function createMessageElement(message) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message-item';

    const contentElement = document.createElement('div');
    contentElement.className = 'message-content';
    contentElement.innerHTML = highlightSearchTerms(message.document, document.getElementById('searchInput').value);
    messageElement.appendChild(contentElement);

    const metaElement = document.createElement('div');
    metaElement.className = 'message-meta';
    metaElement.innerHTML = `
        <span class="message-date">${formatDate(message.metadata.created_at)}</span>
        <span class="message-distance">Distance: ${message.distance.toFixed(3)}</span>
        <button class="btn btn-sm btn-primary float-right" onclick="openMemory('${message.metadata.uid}', '${message.metadata.chat_id}')">Open</button>
    `;
    messageElement.appendChild(metaElement);

    return messageElement;
}

function highlightSearchTerms(text, searchQuery) {
    const words = searchQuery.trim().split(/\s+/);
    let highlightedText = text;
    words.forEach(word => {
        const regex = new RegExp(word, 'gi');
        highlightedText = highlightedText.replace(regex, match => `<span class="highlight">${match}</span>`);
    });
    return highlightedText;
}

function formatDate(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

function openMemory(memoryId, chatId) {
    setChat(chatId);
    $('#chatSearchModal').modal('hide');

    setTimeout(function () {
        scrollToMessage(memoryId);
    }, 500);
}

function scrollToMessage(memoryId) {
    const messageBubble = document.querySelector(`.bubble[data-uuid="${memoryId}"]`);
    if (messageBubble) {
        const messagesContainer = document.getElementById('messages');
        messagesContainer.scrollTop = messageBubble.offsetTop - messagesContainer.offsetTop;
    } else {
        console.log('Message bubble not found:', memoryId);
    }
}