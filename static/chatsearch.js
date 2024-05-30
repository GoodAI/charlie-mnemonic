const debouncedChatSearch = debounce(searchChatHandler, 1000);

function searchChatHandler() {
    console.log('searching chats');
     var searchQuery = document.getElementById('searchInput').value;

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
        var tableBody = document.getElementById('memoryTableBody');
        data = JSON.parse(data);
        // put the data into the table
        tableBody.innerHTML = '';
        if (data.memories.length === 0) {
            showAlert('No memories found.', 'info');
        } else {
            data.memories.forEach((memory) => {
                var row = tableBody.insertRow();
                var shortId = memory.id.replace(/^0+/, '');
                if (shortId === '') {
                    shortId = '0';
                }
                const timestamp = memory.metadata.created_at * 1000; // Convert to milliseconds
                const date = new Date(timestamp);

                const hours = date.getHours().toString().padStart(2, '0');
                const minutes = date.getMinutes().toString().padStart(2, '0');
                const seconds = date.getSeconds().toString().padStart(2, '0');
                const day = date.getDate().toString().padStart(2, '0');
                const month = (date.getMonth() + 1).toString().padStart(2, '0'); // Months are zero-based
                const year = date.getFullYear();

                const formattedDate = `${day}/${month}/${year} - ${hours}:${minutes}:${seconds}`;
                console.log(formattedDate);
                row.innerHTML = `
                    <td>${shortId}</td>
                    <td>${memory.document}</td>
                    <td>${formattedDate}</td>\
                    <td>${memory.distance}</td>
                    <td>
                        <button class="btn btn-primary" onclick="openMemory('${memory.id}', '${memory.metadata.chat_id}')">Open</button>
                    </td>
                `;
            });
        }
     })
     .catch(error => {
        console.error('Error:', error);
        showAlert('An error occurred while searching memories.', 'danger');
     });
}

function openChatSearch() {
    // open a search modal for chats
    $('#chatSearchModal').modal('show');
}

function openMemory(memoryId, chatId) {
    // open the chat tab with the memory
    console.log('opening memory', memoryId);
    console.log('opening chat', chatId);
    setChat(chatId);
    $('#chatSearchModal').modal('hide');
}