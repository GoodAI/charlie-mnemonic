// Get the textarea and count div
const message = document.getElementById("message");
const countDiv = document.getElementById("tokenCount");
var textarea = document.getElementById('message');

var lineHeight = parseFloat(getComputedStyle(textarea).lineHeight);
var viewportHeight = window.innerHeight;
var limit = Math.floor((viewportHeight * 0.7) / lineHeight); // max lines based on 70% of viewport height
var min = 1; // minimum number of lines

// check for session token when page loads
window.onload = function () {
    const overlay = document.getElementById('overlay_msg');
    const overlayMessage = document.getElementById('overlay-message');
    overlayMessage.textContent = "Loading...";
    overlay.style.display = 'flex';
    loadCookies();
}

// Input Handlers
textarea.oninput = function () {
    var lines = textarea.value.split('\n');
    // Remove inline styles to re-enable automatic resizing
    textarea.style.height = "";
    textarea.style.width = "";

    // Adjust the rows attribute to make the textarea grow/shrink
    textarea.rows = Math.min(Math.max(lines.length, min), limit);
};
let lastValidMessage = '';

$('#voice-input, #voice-output').change(function () {
    var settings = {
        voice_input: $('#voice-input').prop('checked'),
        voice_output: $('#voice-output').prop('checked')
    };

    // Show or hide the record button based on the voice input setting
    if (settings.voice_input) {
        $('#record').show();
    } else {
        $('#record').hide();
    }
});

$('#avatar-checkbox').change(function () {
    var settings = {
        avatar: $('#avatar-checkbox').prop('checked')
    };

    // Show or hide D-ID content based on the setting
    if (settings.avatar) {
        $('#d-id-content').show();
        document.getElementById("chat-container").style.minWidth = "50vw";
        document.getElementById("chat-container").style.maxWidth = "50vw";
    } else {
        $('#d-id-content').hide();
        document.getElementById("chat-container").style.minWidth = "80vw";
    }
});

// Event listeners
// Add an input event listener to the textarea
message.addEventListener("input", function () {
    // Encode the input text into tokens
    const tokens = GPTTokenizer_cl100k_base.encode(message.value);
    tokens_used = tokens.length;
    message_lenght = message.value.length;
    // $0.03 / 1K tokens
    cost = tokens_used * 0.03 / 1000;
    updateCounterDiv(message_lenght, tokens_used, max_message_tokens, cost);
    // limit the message length to 1000 tokens, revert to last valid input if limit is exceeded
    if (tokens_used > max_message_tokens && message.value.trim() != '') {
        canSend = false;
        canSendMessage();
    }
    else if (message.value.trim() == '') {
        canSend = false;
        canSendMessage();
    } else {
        canSend = true;
        canSendMessage();
    }
});


document.getElementById('errorModalClose').addEventListener('click', function () {
    $('#errorModal').modal('hide');
});


document.getElementById('upload-image').addEventListener('click', function () {

    const fileInput = document.getElementById('uploadImageInput');
    if (fileInput.files.length > 0) {
        //send_image(fileInput.files[0]);
    }
    else {
        // trigger the file input as if the user clicked it
        document.getElementById('uploadImageInput').click();
    }
});


let pastedImageFile; // Variable to hold the pasted/dropped image file

// check if the preview image was clicked, is so, remove it, show the upload-image button and clear the file input
document.getElementById('image-preview').addEventListener('click', function () {
    // remove the preview image
    document.getElementById('preview-image').src = '';
    // hide the preview image
    document.getElementById('image-preview').style.display = 'none';
    // show the upload-image button
    document.getElementById('upload-image').style.display = 'block';
    // clear the file input
    document.getElementById('uploadImageInput').value = '';
    // clear the pastedImageFile variable
    pastedImageFile = null;
});


// check if an image was uploaded
document.getElementById('uploadImageInput').addEventListener('change', function () {
    if (this.files.length > 0) {
        // check the size of the image, max 20MB
        if (this.files[0].size > 20000000) {
            showErrorModal('The image is too large, max 5MB!');
            // clear the file input
            this.value = '';
            return;
        }
        // set the image-preview innerhtml to the uploaded image
        document.getElementById('preview-image').src = URL.createObjectURL(this.files[0]);

        let imageWrapper = document.querySelector('.image-wrapper');
        imageWrapper.addEventListener('mouseover', function () {
            this.querySelector('.hover-text').style.display = 'block';
        });
        imageWrapper.addEventListener('mouseout', function () {
            this.querySelector('.hover-text').style.display = 'none';
        });
        // show the image-preview
        document.getElementById('image-preview').style.display = 'block';
        // hide the upload-image button
        document.getElementById('upload-image').style.display = 'none';
    }
});

function handleImageFile(imageFile) {
    // create a new FileReader object
    let reader = new FileReader();

    // set the onload function, this will be called when the image is loaded
    reader.onload = function (event) {
        // set the image-preview innerhtml to the uploaded image
        document.getElementById('preview-image').src = event.target.result;
        // show the image-preview
        document.getElementById('image-preview').style.display = 'block';
        // hide the upload-image button
        document.getElementById('upload-image').style.display = 'none';

        let imageWrapper = document.querySelector('.image-wrapper');
        imageWrapper.addEventListener('mouseover', function () {
            this.querySelector('.hover-text').style.display = 'block';
        });
        imageWrapper.addEventListener('mouseout', function () {
            this.querySelector('.hover-text').style.display = 'none';
        });
    };

    // read the image file as a data URL
    reader.readAsDataURL(imageFile);

    // Store the image file for later use
    pastedImageFile = imageFile;
}

window.addEventListener('paste', function (event) {
    // check if there's an image in the clipboard
    for (let i = 0; i < event.clipboardData.items.length; i++) {
        if (event.clipboardData.items[i].type.indexOf('image') > -1) {
            // get the image file
            let imageFile = event.clipboardData.items[i].getAsFile();
            handleImageFile(imageFile);
        }
    }
});

window.addEventListener('dragover', function (event) {
    event.preventDefault();
});

window.addEventListener('drop', function (event) {
    event.preventDefault();

    // check if there's an image in the dropped files
    if (event.dataTransfer.files.length > 0 && event.dataTransfer.files[0].type.indexOf('image') > -1) {
        // get the image file
        let imageFile = event.dataTransfer.files[0];
        handleImageFile(imageFile);
    }
});

document.getElementById('send').addEventListener('click', async function () {
    // make sure the message is not empty
    if (document.getElementById('message').value.trim() === '') {
        return;
    }
    if (pastedImageFile) {
        send_image(pastedImageFile);
        //pastedImageFile = null; // Clear the pasted image file
        document.getElementById('message').value = '';
    } else {
        sendMessageToServer();
    }
});


document.getElementById('message').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        document.getElementById('send').click();
    }
});

// function to handle the logout button click
document.getElementById('logout-button').addEventListener('click', async function (event) {
    event.preventDefault();
    try {
        await logout();
        console.log('User logged out successfully');
    } catch (error) {
        console.error('Logout failed: ', error);
    }
});


document.getElementById('record').addEventListener('click', function () {
    // Check if we're currently recording
    if (mediaRecorder && mediaRecorder.state == "recording") {
        // If we are, stop the recording and reset our data
        mediaRecorder.stop();
        chunks = [];
        document.getElementById('record').innerHTML = '<i class="fa fa-microphone"></i>';
        //document.getElementById('recordingIndicator').style.display = "none";
        canSend = true;
        canRecord = true;
        isRecording = false;
        isWaiting = true;
        canSendMessage();
    } else {
        // If we're not, start a new recording
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function (stream) {
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.start();
                canSend = false;
                canRecord = true;
                isRecording = true;
                isWaiting = false;
                canSendMessage();

                mediaRecorder.ondataavailable = function (e) {
                    chunks.push(e.data);
                }

                mediaRecorder.onstop = function (e) {
                    var blob = new Blob(chunks, { 'type': 'audio/mp3' });
                    chunks = [];

                    // Convert the blob to a File
                    var file = new File([blob], "audio.mp3", { type: "audio/mp3" });

                    send_audio(file);

                    document.getElementById('record').innerHTML = '<i class="fa fa-microphone"></i>';
                    //document.getElementById('recordingIndicator').style.display = "none";
                }
            })
            .catch(function (err) {
                console.log('The following error occurred: ' + err);
                showErrorModal('Error occurred : ' + err + '.\nDid you try turning it off and on again?\nYour microphone permissions might be disabled.');
                // Reset the UI
                document.getElementById('record').innerHTML = '<i class="fa fa-microphone"></i>';
                //document.getElementById('recordingIndicator').style.display = "none";
                canSend = true;
                canRecord = true;
                isRecording = false;
                isWaiting = false;
                canSendMessage();
            })

        document.getElementById('record').innerHTML = '<i class="fa fa-stop"></i>';
        //document.getElementById('recordingIndicator').style.display = "block";
        canSend = false;
        canRecord = false;
        isRecording = true;
        isWaiting = true;
        canSendMessage();
    }
});


// Show the register modal
document.getElementById('register-link').addEventListener('click', function (event) {
    event.preventDefault();
    loginModal.hide();
    registerModal.show();
});
// Show the login modal
document.getElementById('login-link').addEventListener('click', function (event) {
    event.preventDefault();
    registerModal.hide();
    loginModal.show();
});


// function to handle the login form submission
document.getElementById('login-form').addEventListener('submit', async function (event) {
    event.preventDefault();
    const username = document.getElementById('username-input').value.trim();
    const password = document.getElementById('password-input').value.trim();
    if (username && password) {
        try {
            await login(username, password);
            loginModal.hide();
            user_name = username;
            loadCookies();
        } catch (error) {
            console.error('Login failed: ', error.message.toString());
            var errorDiv = document.querySelector('.loginError');
            errorDiv.innerHTML = error.message.toString() || 'An error occurred';
            errorDiv.style.display = 'block';
        }
    }
});

// function to handle the register form submission
document.getElementById('register-form').addEventListener('submit', async function (event) {
    event.preventDefault();
    username = document.getElementById('register-username-input').value.trim();
    var password = document.getElementById('register-password-input').value.trim();
    var displayname = document.getElementById('register-display_name-input').value.trim();
    // check if the username is a valid email address
    if (!validateEmail(username)) {
        document.getElementById('register-error').innerText = 'Please enter a valid email address';
        return;
    }
    if (username && password && displayname) {
        try {
            await register(username, password, displayname);
            registerModal.hide();
            user_name = username;
            display_name = displayname;
            loadCookies();
        }
        catch (error) {
            console.error('Registration failed: ', error);
            // Display error message to the user
            document.getElementById('register-error').innerText = error.message;
        }
    }
});