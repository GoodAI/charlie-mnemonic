function addUserMessage(message) {
    var escaped_message = escapeHTML(message);
    var messageFormatted = formatTempReceived(escaped_message);
    var messageR = messageFormatted.replace(/\n/g, "<br>");
    if (messageR.endsWith('<br>')) {
        messageR = messageR.slice(0, -4);
    }
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

    document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
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

function addCustomMessage(message, user, showLoading = false, replaceNewLines = false) {
    //var escaped_message = escapeHTML(message);
    messageFormatted = formatTempReceived(message);
    if (replaceNewLines) {
        var messageReplaced = messageFormatted.replace(/\n/g, "<br>");
    }
    else {
        var messageReplaced = messageFormatted.replace(/\n/g, "");
    }
    if (messageReplaced.endsWith('<br>')) {
        messageReplaced = messageReplaced.slice(0, -4);
    }
    var timestamp = new Date().toLocaleTimeString();
    var lastMessage = document.querySelector('.last-message');
    if (lastMessage) {
        lastMessage.classList.remove('last-message');
    }

    var chatMessage = document.createElement('div');
    chatMessage.innerHTML = '<div class="message ' + user + ' last-message"><span class="timestamp">' + timestamp + '</span><div class="bubble">' + messageReplaced + '</div></div>';
    document.getElementById('messages').appendChild(chatMessage);

    var lastMessage2 = document.querySelector('.last-message');
    if (lastMessage2) {
        lastMessage2.classList.remove('last-message');
    }

    if (showLoading) {
        // create a bot message div with a loading spinner
        var botMessage = document.createElement('div');
        botMessage.innerHTML = '<div class="message bot last-message"><span class="timestamp">' + timestamp + '</span><div class="bubble"><div class="spinner"></div></div></div>';
        document.getElementById('messages').appendChild(botMessage);
    }
    // scroll to the bottom of the chat
    document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
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
    document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
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
            body: JSON.stringify({ 'prompt': message, 'username': user_name, 'display_name': display_name[0] }),
            credentials: 'include'
        });

        const data = await handleError(response);
        await onResponse(data);

    } catch (error) {
        console.error('Failed to send message: ', error);
        showErrorMessage('Failed to send message: ' + error);
    }
}

async function request_audio(message) {
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
        console.log(data.message);
        overlayMessage.textContent = data.message;

        // Hide the overlay after a delay to let the user see the message
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 2000);
        get_settings(user_name);

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
            console.log(data.message);
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
        console.log(data.message);
        overlayMessage.textContent = data.message;

        // Hide the overlay after a delay to let the user see the message
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 2000);
        // clear the messages
        document.getElementById('messages').innerHTML = '';

    } catch (error) {
        await handleError(error);
        console.error('Failed to delete messages: ', error);

        // Hide the overlay in case of error
        overlay.style.display = 'none';
    }
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
            // ![The San Juan Mountains are beautiful!](/assets/images/san-juan-mountains.jpg "San Juan Mountains")
            var fullmessage = '![image](' + base64data + ' "image")<p>' + message + '</p>';
            fullmessage = marked(fullmessage);
            addCustomMessage(fullmessage, 'user', true);
        }

        document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;

        canRecord = false;
        canSend = false;
        isWaiting = true;
        isRecording = false;
        canSendMessage();

        const formData = new FormData();
        formData.append('username', user_name);
        formData.append('image_file', image_file);
        formData.append('prompt', message);

        const response = await fetch(API_URL + '/message_with_image/', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        console.log(response);
        const data = await response.json();
        console.log(data.content);
        //addCustomMessage(data.content, 'bot');
        await onResponse(data);

    } catch (error) {
        await handleError(error);
        console.error('Failed to upload image: ', error);

        // Hide the overlay in case of error
        overlay.style.display = 'none';
    }
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
            console.log('received transcription: ' + data.transcription);
            // send the transcription to the server as user message
            // make sure the message is not empty
            if (data.transcription.trim() === '') {
                showErrorMessage('Too low volume or no voice detected!');
                return;
            }
            // todo: add option toggle to send immediatly or send to text box first
            const fileInput = document.getElementById('uploadImageInput');
            if (fileInput.files.length > 0) {
                send_image(fileInput.files[0], data.transcription);
                // clear the file input
                //fileInput.value = '';
                // clear the image preview
                //document.getElementById('image-preview').innerHTML = '';
                // clear the message input
                document.getElementById('message').value = '';
            } else {
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
        console.log('setting session token');
        session_token = getCookie('session_token');
        console.log('session token: ' + session_token);
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

function loadCookies() {
    var sessionToken = getCookie('session_token');
    const overlay = document.getElementById('overlay_msg');
    const overlayMessage = document.getElementById('overlay-message');
    if (sessionToken) {
        // session token exists, no need to login
        user_name = getCookie('username');
        // remove possible double quotes from around the username
        user_name = user_name.replace(/"/g, '');
        console.log('session token found, logging in as ' + user_name);
        overlayMessage.textContent = "Logging in...";
        overlay.style.display = 'flex';
        loginModal.hide();
        get_settings(user_name);
        get_recent_messages(user_name);

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
        console.log(data.message);

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
}

canSendMessage();