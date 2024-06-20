const debouncedChatSearch = debounce(searchChatHandler, 1000);
function searchChatHandler() {
    console.log('searching chats');
    var searchQuery = document.getElementById('searchInput').value;

    if (searchQuery.trim() === '') {
        return;
    }

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
        .then(response => response.text())
        .then(data => {
            data = JSON.parse(data);

            var memoryTableBody = document.getElementById('memoryTableBody');
            var rewrittenMemoryTableBody = document.getElementById('rewrittenMemoryTableBody');
            var memoriesSection = document.getElementById('memoriesSection');
            var rewrittenMemoriesSection = document.getElementById('rewrittenMemoriesSection');

            memoryTableBody.innerHTML = '';
            rewrittenMemoryTableBody.innerHTML = '';
            memoriesSection.style.display = 'none';
            rewrittenMemoriesSection.style.display = 'none';

            if (data.memories.length === 0 && data.rewritten_memories.length === 0) {
                showAlert('No memories found.', 'info');
            } else {
                if (data.memories.length > 0) {
                    memoriesSection.style.display = 'block';
                    data.memories.forEach(memory => {
                        var row = memoryTableBody.insertRow();
                        var shortId = memory.id.replace(/^0+/, '') || '0';
                        var formattedDate = formatDate(memory.metadata.created_at);

                        row.innerHTML = `
                        <td>${shortId}</td>
                        <td>${memory.document}</td>
                        <td>${formattedDate}</td>
                        <td>${memory.distance.toFixed(3)}</td>
                        <td>
                            <button class="btn btn-primary" onclick="openMemory('${memory.metadata.uid}', '${memory.metadata.chat_id}')">Open</button>
                        </td>
                    `;
                    });
                }
                if (data.rewritten_memories.length > 0) {
                    rewrittenMemoriesSection.style.display = 'block';
                    data.rewritten_memories.forEach(alt_memory => {
                        var row = rewrittenMemoryTableBody.insertRow();
                        var shortId = alt_memory.id.replace(/^0+/, '') || '0';
                        var formattedDate = formatDate(alt_memory.metadata.created_at);

                        row.innerHTML = `
                        <td>${shortId}</td>
                        <td>${alt_memory.document}</td>
                        <td>${formattedDate}</td>
                        <td>${alt_memory.distance.toFixed(3)}</td>
                        <td>
                            <button class="btn btn-primary" onclick="openMemory('${alt_memory.metadata.uid}', '${alt_memory.metadata.chat_id}')">Open</button>
                        </td>
                    `;
                    });
                }
                document.getElementById('rewrittenQuery').innerHTML = data.rewritten;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('An error occurred while searching memories.', 'danger');
        });
}

function formatDate(timestamp) {
    const date = new Date(timestamp * 1000); // Convert to milliseconds
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0'); // Months are zero-based
    const year = date.getFullYear();

    return `${day}/${month}/${year} - ${hours}:${minutes}:${seconds}`;
}


function openChatSearch() {
    // open a search modal for chats
    $('#chatSearchModal').modal('show');
}

function closeChatSearch() {
    // close the chat search modal
    $('#chatSearchModal').modal('hide');
}

function openMemory(memoryId, chatId) {
    // Open the chat tab with the memory
    console.log('opening memory', memoryId);
    console.log('opening chat', chatId);
    setChat(chatId);
    $('#chatSearchModal').modal('hide');

    // Wait for the chat tab to be active, then scroll to the message
    setTimeout(function () {
        scrollToMessage(memoryId);
    }, 500);
}

function scrollToMessage(memoryId) {
    // Find the message bubble with the given data-uuid
    var messageBubble = document.querySelector('.bubble[data-uuid="' + memoryId + '"]');

    // Check if the message bubble exists
    if (messageBubble) {
        // Scroll the messages container to the message bubble's position
        var messagesContainer = document.getElementById('messages');
        messagesContainer.scrollTop = messageBubble.offsetTop - messagesContainer.offsetTop;
    } else {
        console.log('Message bubble not found:', memoryId);
    }
}