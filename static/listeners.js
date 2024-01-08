// Get the textarea and count div
const message = document.getElementById("message");
const countDiv = document.getElementById("tokenCount");
var textarea = document.getElementById('message');

var lineHeight = parseFloat(getComputedStyle(textarea).lineHeight);
var viewportHeight = window.innerHeight;
var limit = Math.floor((viewportHeight * 0.7) / lineHeight); // max lines based on 70% of viewport height
var min = 1; // minimum number of lines

let pastedImageFile;

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

function playButtonHandler() {
    this.classList.remove('fa-play');
    this.classList.add('fa-spinner');
    request_audio(this).then(audioSrc => {
        var audioElement = document.createElement('audio');
        audioElement.controls = true;
        audioElement.innerHTML = `<source src="${audioSrc}" type="audio/mp3">Your browser does not support the audio element.`;
        var anchorTag = this.closest('.bubble').querySelector('a[data-tooltip="Play Audio"]');
        this.closest('.bubble').appendChild(audioElement);
        if (anchorTag) {
            anchorTag.remove();
        }
    });
}


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
    // set the .icon-container-right padding to 25
    document.querySelector('.icon-container-right').style.right = '25px';
});




// check if an image was uploaded
document.getElementById('uploadImageInput').addEventListener('change', function () {
    if (this.files.length > 0) {
        // check the size of the image, max 20MB
        if (this.files[0].size > 20000000) {
            showErrorModal('The image is too large, max 20MB!');
            // clear the file input
            this.value = '';
            return;
        }
        const file = this.files[0];
        if (!file.type.startsWith('image/')) { // if the file is not an image
            showErrorModal('Invalid file type. Please select an image file.');
            this.value = ''; // reset the input
        } else {
            handleImageFile(file);
        }
    }
});

function handleImageFile(imageFile) {
    // Check if the file is an image
    if (imageFile.type.indexOf('image') === -1) {
        // If not, reject the file and return
        showErrorMessage('Invalid file type. Please upload an image file.', true);
        return;
    }
    
    // create a new FileReader object
    let reader = new FileReader();

    reader.onload = function (event) {
        // create a new Image object
        let img = new Image();

        img.onload = function() {
            // Apply CSS constraints to get thumbnail size
            let thumbnailWidth = Math.min(100, img.width);
            let thumbnailHeight = Math.min(36, img.height);

            // Preserve aspect ratio
            if (img.width > 100 || img.height > 36) {
                let ratio = Math.min(100 / img.width, 36 / img.height);
                thumbnailWidth = img.width * ratio;
                thumbnailHeight = img.height * ratio;
            }

            console.log(`Thumbnail size: ${thumbnailWidth} x ${thumbnailHeight}`);
            document.querySelector('.icon-container-right').style.right = (thumbnailWidth + 45) + 'px';

            // Set image src to the result of FileReader
            document.getElementById('preview-image').src = event.target.result;
            // Show the image-preview
            document.getElementById('image-preview').style.display = 'block';
            // Hide the upload-image button
            document.getElementById('upload-image').style.display = 'none';
        };

        // Set image src to the result of FileReader
        img.src = event.target.result;
    };

    // Read the image file as a data URL
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
    if (document.getElementById('message').value.trim() === '') {
        return;
    }
    if (pastedImageFile) {
        let reader = new FileReader();
        reader.onload = function (event) {
            let img = new Image();
            img.onload = function() {
                // Apply CSS constraints to get thumbnail size
                let thumbnailWidth = Math.min(100, img.width);
                let thumbnailHeight = Math.min(36, img.height);

                // Preserve aspect ratio
                if (img.width > 100 || img.height > 36) {
                    let ratio = Math.min(100 / img.width, 36 / img.height);
                    thumbnailWidth = img.width * ratio;
                    thumbnailHeight = img.height * ratio;
                }

                console.log(`Thumbnail size: ${thumbnailWidth} x ${thumbnailHeight}`);
                document.querySelector('.icon-container-right').style.right = (thumbnailWidth + 45) + 'px';

                // Image sending operations
                send_image(pastedImageFile);
                document.getElementById('uploadImageInput').value = '';
                document.getElementById('preview-image').src = '';
                document.getElementById('image-preview').style.display = 'none';
                document.getElementById('upload-image').style.display = 'block';
                pastedImageFile = null;
                document.getElementById('message').value = '';
            };
            img.src = event.target.result;
        };
        reader.readAsDataURL(pastedImageFile);
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
    } catch (error) {
        console.error('Logout failed: ', error);
    }
});

document.getElementById('record').addEventListener('click', function () {
    // Initialize the default CSS box shadow
    var defaultBoxShadow = '0px 11px 35px 2px rgba(0, 0, 0, 0.20)';
    document.getElementById('message').style.boxShadow = defaultBoxShadow;

    // Check if we're currently recording
    if (mediaRecorder && mediaRecorder.state == "recording") {
        // If we are, stop the recording and reset our data
        mediaRecorder.stop();
        chunks = [];
        document.getElementById('record').innerHTML = '<i id ="recordicon" class="fa fa-microphone"></i>';
        canSend = true;
        canRecord = true;
        isRecording = false;
        isWaiting = true;
        canSendMessage();
    } else {
        // If we're not, start a new recording
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function (stream) {
                var audioContext = new (window.AudioContext || window.webkitAudioContext)();
                var source = audioContext.createMediaStreamSource(stream);
                var analyser = audioContext.createAnalyser();
                source.connect(analyser);
                var dataArray = new Uint8Array(analyser.frequencyBinCount);

                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.start();
                canSend = false;
                canRecord = true;
                isRecording = true;
                isWaiting = false;
                canSendMessage();

                // change tooltip text
                document.getElementById('record').setAttribute('data-tooltip', 'Stop recording');

                mediaRecorder.ondataavailable = function (e) {
                    chunks.push(e.data);
                }

                mediaRecorder.onstop = function (e) {
                    var blob = new Blob(chunks, { 'type': 'audio/mp3' });
                    chunks = [];

                    // Convert the blob to a File
                    var file = new File([blob], "audio.mp3", { type: "audio/mp3" });

                    send_audio(file);

                    document.getElementById('record').innerHTML = '<i id ="recordicon" class="fa fa-microphone"></i>';
                }

                // Add this function to update the glow around the message div
                function update() {
                    analyser.getByteFrequencyData(dataArray);
                    var values = 0;
                    var length = dataArray.length;
                    for (var i = 0; i < length; i++) {
                        values += (dataArray[i]);
                    }
                    var average = values / length;

                    // Lower threshold to make the red more sensitive
                    if (average < 5) {
                        document.getElementById('message').style.boxShadow = defaultBoxShadow;
                    } else {
                        // Increase the opacity of the red color as the sound level rises
                        var intensity = Math.min(1, average / 64); // Adjust normalization range for more sensitivity
                        var boxShadowColor = `rgba(255, 0, 0, ${intensity})`;
                        document.getElementById('message').style.boxShadow = `0 0 ${10 + average}px ${boxShadowColor}`;
                    }

                    if(mediaRecorder && mediaRecorder.state == "recording") {
                        requestAnimationFrame(update);
                    } else {
                        // Reset the glow around the message div
                        document.getElementById('message').style.boxShadow = defaultBoxShadow;
                        // change tooltip text
                        document.getElementById('record').setAttribute('data-tooltip', 'Start recording');
                    }
                }
                update();
            })
            .catch(function (err) {
                console.log('The following error occurred: ' + err);
                showErrorModal('Error occurred : ' + err + '.\nDid you try turning it off and on again?\nYour microphone permissions might be disabled.');
                // Reset the UI
                document.getElementById('record').innerHTML = '<i id="recordicon" class="fa fa-microphone"></i>';
                canSend = true;
                canRecord = true;
                isRecording = false;
                isWaiting = false;
                canSendMessage();
            })

        document.getElementById('record').innerHTML = '<i id="recordicon" class="fa fa-stop"></i>';
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

document.getElementById('messages').addEventListener('click', function(e) {
    if (e.target.classList.contains('debug') || e.target.parentNode.classList.contains('debug')) {
        var expandableContent = e.target.querySelector('.expandable-content') || e.target.parentNode.querySelector('.expandable-content');
        if (expandableContent) {
            if (expandableContent.style.display === 'none') {
                expandableContent.style.display = 'block';
            } else {
                expandableContent.style.display = 'none';
            }
        }
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const themeToggle = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme') || '';

    if (currentTheme) {
        document.body.classList.add(currentTheme);
    }

    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-theme');
        localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark-theme' : '');
    });
})

document.addEventListener('DOMContentLoaded', function () {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');

    tooltipElements.forEach(el => {
        el.addEventListener('mouseenter', function (e) {
            const tooltipText = this.getAttribute('data-tooltip');
            const tooltipDiv = document.createElement('div');
            tooltipDiv.className = 'dynamic-tooltip';
            tooltipDiv.textContent = tooltipText;
            document.body.appendChild(tooltipDiv);

            let rect = this.getBoundingClientRect();
            let left = rect.left + window.scrollX + (this.offsetWidth / 2) - (tooltipDiv.offsetWidth / 2);
            let top = rect.top + window.scrollY - tooltipDiv.offsetHeight - 5; // 5px above the element

            // Adjust if tooltip goes beyond the right edge of the viewport
            const rightEdge = left + tooltipDiv.offsetWidth;
            if (rightEdge > window.innerWidth) {
                left -= rightEdge - window.innerWidth;
            }

            // Adjust if tooltip goes beyond the left edge of the viewport
            if (left < 0) {
                left = 0;
            }

            // Apply the calculated position
            tooltipDiv.style.left = `${left}px`;
            tooltipDiv.style.top = `${top}px`;
            tooltipDiv.style.visibility = 'visible';
            tooltipDiv.style.opacity = '1';
        });

        el.addEventListener('mouseleave', function () {
            document.querySelectorAll('.dynamic-tooltip').forEach(tooltip => {
                tooltip.remove();
            });
        });
    });
});
