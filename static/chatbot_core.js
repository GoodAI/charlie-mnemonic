function addUserMessage(message) {
    var messageR = parseAndFormatMessage(message, false, false);
    var timestamp = new Date().toLocaleTimeString();
    var lastMessage = document.querySelector('.last-message');
    if (lastMessage) {
        lastMessage.classList.remove('last-message');
    }

    var chatMessage = document.createElement('div');
    chatMessage.innerHTML = '<div class="message user last-message"><span class="timestamp">' + timestamp + '</span><div class="bubble">' + messageR + '</div></div>';
    document.getElementById('messages').appendChild(chatMessage.firstChild);

    var lastMessage2 = document.querySelector('.last-message');
    if (lastMessage2) {
        lastMessage2.classList.remove('last-message');
    }

    // create a bot message div with a loading spinner
    var botMessage = document.createElement('div');
    botMessage.innerHTML = '<div class="message bot last-message"><span class="timestamp">' + timestamp + '</span><div class="bubble"><div class="spinner"></div></div></div>';
    document.getElementById('messages').appendChild(botMessage.firstChild);

    var messagesContainer = document.getElementById('messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // remove input text
    document.getElementById('message').value = '';
    var textarea = document.getElementById('message');
    textarea.rows = 1;
    // reset token count
    document.getElementById('tokenCount').textContent = 'Characters: 0, tokens: 0/' + max_message_tokens.toString() + ', cost: $0.0000';
    // change placeholder text
    document.getElementById('message').placeholder = 'Please wait for the response...';

    // disable the send button
    canSend = false;
    canRecord = false;
    isRecording = false;
    isWaiting = true;
    canSendMessage();
}

function parseAndFormatMessage(message, addIndicator = false, replaceNewLines = false) {
    // Replace multiple backticks with triple backticks
    message = message.replace(/(`\s*`\s*`)/g, '```');
    
    // Count the number of triple backticks
    var count = (message.match(/```/g) || []).length;

    // If the count is odd, add an extra set of backticks to close the last code block
    if (count % 2 !== 0) {
        message += '\n```';
    }
    
    // Apply Markdown formatting
    message = marked(message);

    // If outside of code block, add the typing indicator and replace newline characters
    if (count % 2 === 0 && addIndicator) {
        if (!replaceNewLines) {
            message = message.replace(/\n/g, "");
        }
        else {
            message = message.replace(/\n/g, "<br>");
        }
        message += '<span class="typing-indicator"><span class="dot"></span></span>';
    }

    return `<div class="markdown">${message}</div>`;
}

function addCustomMessage(message, user, showLoading = false, replaceNewLines = false, timestamp = null, scroll = false, addButtons = false, uuid = null) {
    var messageReplaced = parseAndFormatMessage(message, false, replaceNewLines);

    if (messageReplaced.endsWith('<br>')) {
        messageReplaced = messageReplaced.slice(0, -4);
    }
    if (timestamp == null) {
        timestamp = new Date().toLocaleTimeString();
    } else {
        var date = new Date(timestamp * 1000);
        timestamp = date.toLocaleTimeString();
    }

    var lastMessage = document.querySelector('.last-message');
    if (lastMessage) {
        lastMessage.classList.remove('last-message');
    }
    var uuidAttribute = uuid ? ' data-uuid="' + uuid + '"' : '';
    
    var chatMessage = document.createElement('div');
    chatMessage.innerHTML = '<div class="message ' + user + ' last-message"><span class="timestamp">' + timestamp + '</span><div class="bubble"' + uuidAttribute + '>' + messageReplaced + '</div></div>';
    
    if (addButtons && user === 'bot') {
        // add bottom buttons to the bubble
        var buttons = document.createElement('div');
        buttons.className = 'bottom-buttons-container';
        addBottomButtons(buttons);
        chatMessage.firstChild.querySelector('.bubble').appendChild(buttons);
    }

    var messagesContainer = document.getElementById('messages');
    messagesContainer.appendChild(chatMessage);

    if (showLoading) {
        // remove the last message class from the last user message
        var lastMessage2 = document.querySelector('.last-message');
        if (lastMessage2) {
            lastMessage2.classList.remove('last-message');
        }
        var botMessage = document.createElement('div');
        botMessage.innerHTML = '<div class="message bot last-message"><span class="timestamp">' + timestamp + '</span><div class="bubble"><div class="spinner"></div></div></div>';
        messagesContainer.appendChild(botMessage);
    }

    if (isUserAtBottom(messagesContainer) || scroll) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        hideNewMessageIndicator();
    } else {
        showNewMessageIndicator();
    }
}

function isUserAtBottom(container) {
    const threshold = 50;
    return container.scrollHeight - container.scrollTop - container.clientHeight <= threshold;
}

function showNewMessageIndicator() {
    var indicator = document.getElementById('new-message-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'new-message-indicator';
        indicator.innerHTML = '<button onclick="scrollToBottom()">New Messages ↓</button>';
        document.body.appendChild(indicator);
    }
    indicator.style.display = 'block';
}

function hideNewMessageIndicator() {
    var indicator = document.getElementById('new-message-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

function scrollToBottom() {
    var messagesContainer = document.getElementById('messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    hideNewMessageIndicator();
}


function addExternalMessage(message) {
    var escaped_message = escapeHTML(message);
    var messageFormatted = escaped_message.replace(/\n/g, "<br>");
    var timestamp = new Date().toLocaleTimeString();
    var lastMessage = document.querySelector('.last-message');
    if (lastMessage) {
        lastMessage.classList.remove('last-message');
    }
    var chatMessage = '<div class="message external last-message"><span class="timestamp">' + timestamp + '</span><div class="bubble">' + messageFormatted + '</div></div>';
    document.getElementById('messages').innerHTML += chatMessage;
    var lastMessage2 = document.querySelector('.last-message');
    if (lastMessage2) {
        lastMessage2.classList.remove('last-message');
    }

    // create a bot message div with a loading spinner
    var botMessage = '<div class="message bot last-message"><span class="timestamp">' + timestamp + '</span><div class="bubble"><div class="spinner"></div></div></div>';
    var element = document.createElement('div');
    element.innerHTML = botMessage;
    document.getElementById('messages').innerHTML += botMessage;
    var messagesContainer = document.getElementById('messages');
    if (isUserAtBottom(messagesContainer)) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        hideNewMessageIndicator();
    } else {
        showNewMessageIndicator();
    }
    // remove input text
    document.getElementById('message').value = '';
    document.getElementById('message').placeholder = 'Please wait for the response...';

    // disable the send button
    canSend = false;
    canSendMessage();
}

async function sendMessageToServer(message) {
    if (message === undefined) {
        message = document.getElementById('message').value;
    }
    canRecord = false;
    canSend = false;
    isWaiting = true;
    isRecording = false;
    canSendMessage();
    addUserMessage(message);
    try {
        const response = await fetch(API_URL + '/message/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 'prompt': message, 'username': user_name, 'display_name': display_name[0], 'chat_id': chat_id }),
            credentials: 'include'
        });

        const data = await handleError(response);
        //await onResponse(data);

    } catch (error) {
        console.error('Failed to send message: ', error);
        showErrorMessage('Failed to send message: ' + error);
    }
}

async function regenerateResponse(div) {
    // extract the uuid from the div
    var uuid = div.parentNode.getAttribute('data-uuid');
    canRecord = false;
    canSend = false;
    isWaiting = true;
    isRecording = false;
    canSendMessage();
    try {
        const response = await fetch(API_URL + '/regenerate_response/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 'uuid': uuid, 'username': user_name, 'chat_id': chat_id}),
            credentials: 'include'
        });

        const data = await response.json();
        addCustomMessage(data.content, 'bot');

    } catch (error) {
        console.error('Failed to regenerate response: ', error);
        showErrorMessage('Failed to regenerate response: ' + error);
    }
}

async function request_audio(button) {
    var bubbleContainer = button.closest('.bubble');

    var clonedBubbleContainer = bubbleContainer.cloneNode(true);

    var codeBlocks = clonedBubbleContainer.querySelectorAll('code[class^="language-"]');
    codeBlocks.forEach(function(block) {
        block.parentNode.removeChild(block);
    });

    const message = clonedBubbleContainer.innerText;

    try {
        const response = await fetch(API_URL + '/generate_audio/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 'prompt': message, 'username': user_name }),
            credentials: 'include'
        });

        const data = await response.blob();
        var audioSrc = URL.createObjectURL(data);
        return audioSrc;

    } catch (error) {
        await handleError(error);
        console.error('Failed to send message: ', error);
    }
}


async function save_user_data() {
    try {
        const overlay = document.getElementById('overlay_msg');
        const overlayMessage = document.getElementById('overlay-message');
        overlayMessage.textContent = "Downloading Data...";
        overlay.style.display = 'flex';

        const response = await fetch(API_URL + '/save_data/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 'username': user_name }),
            credentials: 'include'
        });
        const data = await response.blob();
        var downloadUrl = URL.createObjectURL(data);
        var a = document.createElement("a");
        document.body.appendChild(a);
        a.style = "display: none";
        a.href = downloadUrl;
        // get the filename from the Content-Disposition header
        var contentDisposition = response.headers.get('Content-Disposition');
        var filename = contentDisposition.split('filename=')[1].replace(/"/g, '');
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        overlayMessage.textContent = "Download started...";

        // Hide the overlay after a delay to let the user see the message
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 2000);

    } catch (error) {
        await handleError(error);
        console.error('Failed to save data: ', error);

        // Hide the overlay in case of error
        overlay.style.display = 'none';
    }
}

async function delete_user_data() {
    try {
        const overlay = document.getElementById('overlay_msg');
        const overlayMessage = document.getElementById('overlay-message');
        overlayMessage.textContent = "Deleting Data...";
        overlay.style.display = 'flex';

        const response = await fetch(API_URL + '/delete_data/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 'username': user_name }),
            credentials: 'include'
        });

        const data = await response.json();
        overlayMessage.textContent = data.message;

        // Hide the overlay after a delay to let the user see the message
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 2000);
        get_settings(user_name);
        get_chat_tabs(user_name);

    } catch (error) {
        await handleError(error);
        console.error('Failed to delete data: ', error);

        // Hide the overlay in case of error
        overlay.style.display = 'none';
    }
}

async function upload_user_data(file) {
    
    const overlay = document.getElementById('overlay_msg');
    const overlayMessage = document.getElementById('overlay-message');
    overlayMessage.textContent = "Uploading Data...";
    overlay.style.display = 'flex';

    const formData = new FormData();
    formData.append('username', user_name);
    formData.append('data_file', file);
    try {
        const response = await fetch(API_URL + '/upload_data/', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        if (response.ok) {
            const data = await response.json();
            overlayMessage.textContent = data.message;
        } 
        else
        {
            await handleError(response);
        }
        // Hide the overlay after a delay to let the user see the message
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 2000);
        get_settings(user_name);
    } catch (error) {
        console.log('Failed to upload data: ', error);
        await handleError(response);
        // Hide the overlay in case of error
        overlay.style.display = 'none';
    }
}

async function delete_recent_messages() {
    try {
        const overlay = document.getElementById('overlay_msg');
        const overlayMessage = document.getElementById('overlay-message');
        overlayMessage.textContent = "Deleting Messages...";
        overlay.style.display = 'flex';

        const response = await fetch(API_URL + '/delete_recent_messages/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 'username': user_name }),
            credentials: 'include'
        });

        const data = await response.json();
        overlayMessage.textContent = data.message;

        // Hide the overlay after a delay to let the user see the message
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 200);
        // clear the messages
        document.getElementById('messages').innerHTML = '';

    } catch (error) {
        await handleError(error);
        console.error('Failed to delete messages: ', error);

        // Hide the overlay in case of error
        overlay.style.display = 'none';
    }
}

async function swap_tab() {
    try {
        const overlay = document.getElementById('overlay_msg');
        const overlayMessage = document.getElementById('overlay-message');
        overlayMessage.textContent = "Changing Tab...";
        overlay.style.display = 'flex';

        // Hide the overlay after a delay to let the user see the message
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 200);
        // clear the messages
        document.getElementById('messages').innerHTML = '';

    } catch (error) {
        await handleError(error);
        console.error('Failed to delete messages: ', error);

        // Hide the overlay in case of error
        overlay.style.display = 'none';
    }
}

function stopStream() {
    // send a message to the server to stop the stream to /stop_streaming/
    fetch(API_URL + '/stop_streaming/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 'username': user_name }),
        credentials: 'include'
    })
        .then(response => response.json())
        .then(data => {
            console.log(data);
        })
        .catch(console.error);
}

async function send_image(image_file, prompt) {
    try {
        var message = document.getElementById('message').value;
        // put image and prompt into a string
        // if prompt is not empty, set the message to prompt
        if (prompt) {
            message = prompt;
        }
        // convert the image to base64
        var reader = new FileReader();
        reader.readAsDataURL(image_file);
        reader.onloadend = function () {
            var base64data = reader.result;
            var fullmessage = '![image](' + base64data + ' "image")<p>' + message + '</p>';
            fullmessage = marked(fullmessage);
            addCustomMessage(fullmessage, 'user', true);
        }

        var messagesContainer = document.getElementById('messages');
        if (isUserAtBottom(messagesContainer)) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            hideNewMessageIndicator();
        } else {
            showNewMessageIndicator();
        }

        canRecord = false;
        canSend = false;
        isWaiting = true;
        isRecording = false;
        canSendMessage();

        const formData = new FormData();
        formData.append('username', user_name);
        formData.append('image_file', image_file);
        formData.append('prompt', message);
        formData.append('chat_id', chat_id);

        const response = await fetch(API_URL + '/message_with_image/', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        const data = await response.json();
        //addCustomMessage(data.content, 'bot');
        //await onResponse(data);

    } catch (error) {
        await handleError(error);
        console.error('Failed to upload image: ', error);

        // Hide the overlay in case of error
        overlay.style.display = 'none';
    }
}

async function send_files(files, prompt) {
    try {
        var message = document.getElementById('message').value;
        // if prompt is not empty, set the message to prompt
        if (prompt) {
            message = prompt;
        }

        var fullmessage = '';
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (file.type.startsWith('image/')) {
                // convert the image to base64
                var base64data = await getBase64(file);
                fullmessage += '![' + file.name + '](' + base64data + ' "' + file.name + '")<p>' + message + '</p>';
            } else {
                fullmessage += '[' + file.name + '](' + file.name + ')<p>' + message + '</p>';
            }
        }
        fullmessage = marked(fullmessage);
        addCustomMessage(fullmessage, 'user', true);

        var messagesContainer = document.getElementById('messages');
        if (isUserAtBottom(messagesContainer)) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            hideNewMessageIndicator();
        } else {
            showNewMessageIndicator();
        }

        canRecord = false;
        canSend = false;
        isWaiting = true;
        isRecording = false;
        canSendMessage();

        const formData = new FormData();
        formData.append('username', user_name);
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        formData.append('prompt', message);
        formData.append('chat_id', chat_id);

        const response = await fetch(API_URL + '/message_with_files/', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        const data = await response.json();

    } catch (error) {
        await handleError(error);
        console.error('Failed to upload files: ', error);
        overlay.style.display = 'none';
    }
}

function getBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
    });
}

function send_audio(file) {
    // Create a FormData object
    var formData = new FormData();

    // Add the file to the form data
    formData.append("audio_file", file);

    // Send the form data using fetch
    fetch(API_URL + "/message_audio/", {
        method: "POST",
        body: formData,
        credentials: 'include'
    })
        .then(response => response.json())
        .then(data => {
            // send the transcription to the server as user message
            // make sure the message is not empty
            if (data.transcription.trim() === '') {
                showErrorMessage('Too low volume or no voice detected!', true);
                return;
            }
            // todo: add option toggle to send immediatly or send to text box first
            const fileInput = document.getElementById('uploadFileInput');
            if (fileInput.files.length > 0) {
                send_files(fileInput.files, data.transcription);
                document.getElementById('uploadFileInput').value = '';
                document.getElementById('preview-files').innerHTML = '';
                document.getElementById('files-preview').style.display = 'none';
                document.getElementById('upload-file').style.display = 'block';
                pastedFiles = [];
                document.getElementById('message').value = '';
            } else {
                console.log('Sending audio transcription to server: ' + data.transcription);
                sendMessageToServer(data.transcription);
            }
        })
        .catch(console.error);
}



// Show the username modal
var loginModal = new bootstrap.Modal(document.getElementById('login-modal'), {
    backdrop: 'static',
    keyboard: false
});
var registerModal = new bootstrap.Modal(document.getElementById('register-modal'), {
    backdrop: 'static',
    keyboard: false
});
registerModal.hide();
loginModal.hide();

// function to login a user
async function login(username, password) {
    const response = await fetch(API_URL + '/login/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: username, password: password }),
        credentials: 'include'
    });

    if (!response.ok) {
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
            const responseBody = await response.json();
            errorMessage = responseBody.detail || errorMessage;
        } catch (e) {
            console.error('Failed to parse error response as JSON: ', e);
        }
        throw new Error(errorMessage);
    }
    else {
        // set the session token
        session_token = getCookie('session_token');
    }
}

// function to login a user
async function handleCredentialResponse(input) {
    const response = await fetch(API_URL + '/google-login/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ credentials: input.credential }),
        credentials: 'include'
    });

    if (!response.ok) {
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
            const responseBody = await response.json();
            errorMessage = responseBody.detail || errorMessage;
        } catch (e) {
            console.error('Failed to parse error response as JSON: ', e);
        }
        throw new Error(errorMessage);
    }
    else {
        // set the session token
        session_token = getCookie('session_token');
        loginModal.hide();
        user_name = username;
        loadCookies();
    }
}


// function to register a user
async function register(username, password, displayname) {
    const response = await fetch(API_URL + '/register/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: username, password: password, display_name: displayname }),
        credentials: 'include'
    });

    if (!response.ok) {
        const errorDetail = await response.json();
        throw new Error(`Registration failed: ${errorDetail.detail}`);
    }
}


function validateEmail(email) {
    // https://stackoverflow.com/a/46181/112731
    var re = /\S+@\S+\.\S+/;
    return re.test(email);
}

// function to delete a cookie
function deleteCookie(name) {
    var domain = window.location.hostname;
    document.cookie = name + '=; Domain=' + domain + '; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
}

// function to logout a user
async function logout() {
    const response = await fetch(API_URL + '/logout/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: getCookie('username'), session_token: getCookie('session_token') }),
        credentials: 'include'
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    else {
        // delete the session token and username
        deleteCookie('session_token');
        deleteCookie('username');
        // reload the page
        location.reload();
    }
}



// function to get a cookie by name
function getCookie(name) {
    var cookieArr = document.cookie.split("; ");
    for (var i = 0; i < cookieArr.length; i++) {
        var cookiePair = cookieArr[i].split("=");
        if (cookiePair[0] === name) {
            if (name == 'username') {
                // remove possible double quotes from around the username
                cookiePair[1] = cookiePair[1].replace(/"/g, '');
            }
            return decodeURIComponent(cookiePair[1]);
        }
    }
    return null;
}

async function loadCookies() {
    var sessionToken = getCookie('session_token');
    const overlay = document.getElementById('overlay_msg');
    const overlayMessage = document.getElementById('overlay-message');
    if (sessionToken) {
        // session token exists, no need to login
        user_name = getCookie('username');
        // remove possible double quotes from around the username
        user_name = user_name.replace(/"/g, '');
        overlayMessage.textContent = "Logging in...";
        overlay.style.display = 'flex';
        loginModal.hide();
        get_settings(user_name);
        await get_chat_tabs(user_name);
        await get_recent_messages(user_name, chat_id);

    } else {
        // no session token, show the login modal
        loginModal.show();
        overlay.style.display = 'none';
    }
}

// function to delete session and username cookies
function deleteCookies() {
    deleteCookie('session_token');
    deleteCookie('username');
}




async function big_red_abort_button() {
    try {
        const response = await fetch(API_URL + '/abort_button/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 'username': user_name }),
            credentials: 'include'
        });

        const data = await response.json();

    } catch (error) {
        await handleError(error);
        console.error('Failed to abort: ', error);
    }
}

// document.getElementById('abort').addEventListener('click', function() {
//     if (!abortClicked) {
//         this.innerHTML = 'Are you sure? This will shut down the whole server! A manual server reboot is required after this! Click again to confirm.';
//         abortClicked = true;
//     } else {
//         big_red_abort_button();
//     }
// });

function toggleStopButton(showStop) {
    const stopButton = document.getElementById('stop');
    const sendButton = document.getElementById('send');
    const recordButton = document.getElementById('record');
    const uploadButton = document.getElementById('upload-file');

    if (showStop) {

        stopButton.style.display = 'block';
        sendButton.style.display = 'none';
        recordButton.style.display = 'none';
        uploadButton.style.display = 'none';
    } else {
        stopButton.style.display = 'none';
        sendButton.style.display = 'block';
        recordButton.style.display = 'block';
        uploadButton.style.display = 'block';
    }
}

function canSendMessage() {
    record_button = document.getElementById('record');
    const message = document.getElementById("message");

    if (message.value.trim() == '') {
        document.getElementById('send').disabled = true;
        canSend = false;
    }
    if (record_button) {
        record_button.disabled = false;
    }
    if (canSend && !isWaiting && !isRecording) {
        document.getElementById('send').disabled = false;
        if (record_button) {
            record_button.disabled = false;
        }
    }
    if (!canSend) {
        document.getElementById('send').disabled = true;
    }
    if (isWaiting) {
        document.getElementById('send').disabled = true;
        if (record_button) {
            record_button.disabled = true;
        }
    }
    toggleStopButton(isWaiting);
}

canSendMessage();

function populateChatTabs(tabs_data) {
    // sort the tabs by created_at row, most recent first
    tabs_data.sort((a, b) => (a.created_at < b.created_at) ? 1 : -1);
    // Get the chat tabs container
    var chatTabs = document.getElementById('chat-tabs-container');
    // Remove the loader
    var loader = document.querySelector('.loader');
    if (loader) {
        loader.remove();
    }
    // Clear the current tabs
    while (chatTabs.firstChild) {
        chatTabs.removeChild(chatTabs.firstChild);
    }

    // Iterate over the tabs_data array
    for (let i = 0; i < tabs_data.length; i++) {
        // Create a new button for each tab
        var newTab = document.createElement('button');
        newTab.className = 'chat-tab';
        newTab.id = 'chat-tab-' + tabs_data[i].tab_id;
        // trim to the first 5 words only and add ... if there are more
        newTab.innerText = tabs_data[i].chat_name.split(' ').slice(0, 5).join(' ');
        if (tabs_data[i].chat_name.split(' ').length > 5) {
            newTab.innerText += '...';
        }
        
        // Set the onclick function to the setChat function with the chat id as parameter
        newTab.onclick = function() {
            setChat(tabs_data[i].chat_id);
        };

        // If the tab is active, add the 'active' class to the button
        if (tabs_data[i].is_active) {
            newTab.classList.add('active');
        }
        var dots = document.createElement('div');
        dots.className = 'chat-tab-dots';
        dots.innerHTML = '&nbsp;&#x22EE;&nbsp;';
        dots.onclick = function(event) {
            event.stopPropagation();
            showDropdown(this, tabs_data[i].chat_id);
        };

        newTab.appendChild(dots);

        // Append the new tab to the chat tabs container
        chatTabs.appendChild(newTab);
        
    }
    
    setupDropdownMenus();
}

function showDropdown(dotElement, chatId) {
    // Close any already open dropdowns
    closeAllDropdowns();

    var dropdownMenu = document.createElement('div');
    dropdownMenu.className = 'dropdown-menu';
    dropdownMenu.innerHTML = `<ul>
        <li onclick="shareChat('${chatId}')"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" width="15" height="15" style="fill: var(--chat-tab-dots-color);"><!--!Font Awesome Free 6.5.1 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.--><path d="M246.6 9.4c-12.5-12.5-32.8-12.5-45.3 0l-128 128c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L192 109.3V320c0 17.7 14.3 32 32 32s32-14.3 32-32V109.3l73.4 73.4c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3l-128-128zM64 352c0-17.7-14.3-32-32-32s-32 14.3-32 32v64c0 53 43 96 96 96H352c53 0 96-43 96-96V352c0-17.7-14.3-32-32-32s-32 14.3-32 32v64c0 17.7-14.3 32-32 32H96c-17.7 0-32-14.3-32-32V352z"/></svg> Share</li>
        <li onClick="editTabDescription('${chatId}')"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" width="15" height="15" style="fill: var(--chat-tab-dots-color);"><!--!Font Awesome Free 6.5.1 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.--><path d="M471.6 21.7c-21.9-21.9-57.3-21.9-79.2 0L362.3 51.7l97.9 97.9 30.1-30.1c21.9-21.9 21.9-57.3 0-79.2L471.6 21.7zm-299.2 220c-6.1 6.1-10.8 13.6-13.5 21.9l-29.6 88.8c-2.9 8.6-.6 18.1 5.8 24.6s15.9 8.7 24.6 5.8l88.8-29.6c8.2-2.7 15.7-7.4 21.9-13.5L437.7 172.3 339.7 74.3 172.4 241.7zM96 64C43 64 0 107 0 160V416c0 53 43 96 96 96H352c53 0 96-43 96-96V320c0-17.7-14.3-32-32-32s-32 14.3-32 32v96c0 17.7-14.3 32-32 32H96c-17.7 0-32-14.3-32-32V160c0-17.7 14.3-32 32-32h96c17.7 0 32-14.3 32-32s-14.3-32-32-32H96z"/></svg> Rename</li>
        <li onclick="deleteChatTab('${chatId}')"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" height="15" style="fill: var(--chat-tab-dots-color);"><!--!Font Awesome Free 6.5.1 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.--><path d="M135.2 17.7L128 32H32C14.3 32 0 46.3 0 64S14.3 96 32 96H416c17.7 0 32-14.3 32-32s-14.3-32-32-32H320l-7.2-14.3C307.4 6.8 296.3 0 284.2 0H163.8c-12.1 0-23.2 6.8-28.6 17.7zM416 128H32L53.2 467c1.6 25.3 22.6 45 47.9 45H346.9c25.3 0 46.3-19.7 47.9-45L416 128z"/></svg> Delete</li>
        </ul>`;

    document.body.appendChild(dropdownMenu);

    // Position the dropdown menu
    var rect = dotElement.getBoundingClientRect();
    dropdownMenu.style.position = 'absolute';
    dropdownMenu.style.left = `${rect.left}px`;
    dropdownMenu.style.top = `${rect.bottom}px`;
    dropdownMenu.style.display = 'block';
}

function closeAllDropdowns() {
    var dropdowns = document.querySelectorAll('.dropdown-menu');
    dropdowns.forEach(function(dropdown) {
        dropdown.remove();
    });
}

// Ensure that clicking anywhere on the window closes the dropdown
window.onclick = closeAllDropdowns;

function setupDropdownMenus() {
    window.addEventListener('click', function() {
        var dropdowns = document.querySelectorAll('.dropdown-menu');
        dropdowns.forEach(function(dropdown) {
            dropdown.style.display = 'none';
        });
    });
}