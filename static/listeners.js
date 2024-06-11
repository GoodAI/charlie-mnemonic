// Get the textarea and count div
const message = document.getElementById("message");
const countDiv = document.getElementById("tokenCount");
var textarea = document.getElementById('message');

var lineHeight = parseFloat(getComputedStyle(textarea).lineHeight);
var viewportHeight = window.innerHeight;
var limit = Math.floor((viewportHeight * 0.7) / lineHeight); // max lines based on 70% of viewport height
var min = 1; // minimum number of lines

let pastedImageFile;
let pastedFiles = [];
let isGeneratingAudio = false;

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

function playButtonHandler(element) {
    if (!element) return;
    element.classList.remove('fa-play');
    element.classList.add('fa-spinner');

    if (isGeneratingAudio) {
        return;
    }
    isGeneratingAudio = true;

    // remove the event listener to prevent multiple clicks
    element.removeEventListener('click', playButtonHandler);

    // force the browser to reflow the DOM
    element.offsetWidth;

    // make sure the message has no more than 4096 characters
    var bubbleContainer = element.closest('.bubble');

    var clonedBubbleContainer = bubbleContainer.cloneNode(true);

    var codeBlocks = clonedBubbleContainer.querySelectorAll('code[class^="language-"]');
    codeBlocks.forEach(function(block) {
        block.parentNode.removeChild(block);
    });

    const message = clonedBubbleContainer.innerText;

    if (message.length > 4096) {
        console.error('Message too long');
        showErrorModal('The message you are trying to generate audio for is too long. The openAI API has a limit of 4096 characters.');
        isGeneratingAudio = false;
        // reset the play button
        element.classList.remove('fa-spinner');
        element.classList.add('fa-play');
        // force the browser to reflow the DOM
        element.offsetWidth;
        return;
    }

    request_audio(element).then(audioSrc => {
        var audioElement = document.createElement('audio');
        audioElement.controls = true;
        audioElement.innerHTML = `<source src="${audioSrc}" type="audio/mp3">Your browser does not support the audio element.`;
        var anchorTag = element.closest('.bubble').querySelector('a[data-tooltip="Play Audio"]');
        element.closest('.bubble').appendChild(audioElement);
        isGeneratingAudio = false;
        if (anchorTag) {
            anchorTag.remove();
        }
    }).catch(error => {
        console.error("Error processing audio: ", error);
        isGeneratingAudio = false;
    });
}

// Event listeners
// Add an input event listener to the textarea
message.addEventListener("input", function () {
    // Encode the input text into tokens
    const tokens = GPTTokenizer_cl100k_base.encode(message.value);
    tokens_used = tokens.length;
    message_lenght = message.value.length;
    // $0.01 / 1K tokens
    cost = tokens_used * 0.00001;
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


document.getElementById('upload-file').addEventListener('click', function () {
     document.getElementById('uploadFileInput').click();
});

function handleFiles(files) {
    // Check if the total size of all files is less than 200MB
    let totalSize = 0;
    for (let i = 0; i < files.length; i++) {
        totalSize += files[i].size;
    }
    if (totalSize > 200000000) {
        showErrorModal('The total size of the files is too large, max 200MB!');
        return;
    }

    let textFiles = [];
    let nonTextFiles = [];
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.type.startsWith('text/') || file.name.match(/\.(txt|html|css|js|cs)$/i)) {
            textFiles.push(file);
        } else {
            nonTextFiles.push(file);
        }
    }
    if (textFiles.length > 0) {
        showTextFileModal(textFiles);
    }
    if (nonTextFiles.length > 0) {
        for (let i = 0; i < nonTextFiles.length; i++) {
            const file = nonTextFiles[i];
            pastedFiles.push(file);
            createFilePreview(file, pastedFiles.length - 1);
        }
        // Show the file-preview
        document.getElementById('files-preview').style.display = 'flex';
        document.getElementById('files-preview').style.justifyContent = 'center';
    }
}

function createFilePreview(file, index) {
    let preview = document.createElement('div');
    preview.className = 'file-preview';

    if (file.type.startsWith('image/')) {
        let reader = new FileReader();
        reader.onload = function (event) {
            let img = new Image();
            img.onload = function () {
                let thumbnailWidth = Math.min(100, img.width);
                let thumbnailHeight = Math.min(36, img.height);

                if (img.width > 100 || img.height > 36) {
                    let ratio = Math.min(100 / img.width, 36 / img.height);
                    thumbnailWidth = img.width * ratio;
                    thumbnailHeight = img.height * ratio;
                }

                preview.innerHTML = `<img src="${event.target.result}" alt="${file.name}" width="${thumbnailWidth}" height="${thumbnailHeight}">`;
                addDeleteIcon(preview, file, index);
            };
            img.src = event.target.result;
        };
        reader.readAsDataURL(file);
    } else if (file.type.startsWith('video/')) {
        preview.innerHTML = `<i class="fas fa-file-video"></i><span>${file.name}</span>`;
        addDeleteIcon(preview, file, index);
    } else if (file.type.startsWith('text/')) {
        preview.innerHTML = `<i class="fas fa-file-alt"></i><span>${file.name}</span>`;
        addDeleteIcon(preview, file, index);
    } else if (file.type.startsWith('audio/')) {
        preview.innerHTML = `<i class="fas fa-file-audio"></i><span>${file.name}</span>`;
        addDeleteIcon(preview, file, index);
    } else if (file.type.startsWith('application/pdf')) {
        preview.innerHTML = `<i class="fas fa-file-pdf"></i><span>${file.name}</span>`;
        addDeleteIcon(preview, file, index);
    } else {
        preview.innerHTML = `<i class="fas fa-file"></i><span>${file.name}</span>`;
        addDeleteIcon(preview, file, index);
    }

    document.getElementById('preview-files').appendChild(preview);
}

function addDeleteIcon(preview, file, index) {
    let deleteIcon = document.createElement('i');
    deleteIcon.className = 'fas fa-times-circle file-delete-icon';
    deleteIcon.setAttribute('title', 'Delete');
    deleteIcon.addEventListener('click', function () {
        if (index >= 0 && index < pastedFiles.length) {
            pastedFiles.splice(index, 1);
            preview.remove();

            // Update the indices of the remaining files
            let previews = document.querySelectorAll('.file-preview');
            previews.forEach((preview, i) => {
                let deleteIcon = preview.querySelector('.file-delete-icon');
                deleteIcon.removeEventListener('click', deleteIcon.onclick);
                addDeleteIcon(preview, pastedFiles[i], i);
            });

            if (pastedFiles.length === 0) {
                document.getElementById('files-preview').style.display = 'none';
            } else {
                document.getElementById('files-preview').style.display = 'flex';
            }
        } else {
            console.log('Invalid file index');
        }
    });
    preview.appendChild(deleteIcon);
}

// check if files were uploaded
document.getElementById('uploadFileInput').addEventListener('change', function () {
    if (this.files.length > 0) {
        handleFiles(this.files);
    }
});

window.addEventListener('paste', function (event) {
    // check if there are files in the clipboard
    if (event.clipboardData.files.length > 0) {
        handleFiles(event.clipboardData.files);
    }
});

window.addEventListener('dragover', function (event) {
    event.preventDefault();
});

window.addEventListener('drop', function (event) {
    event.preventDefault();

    // check if there are files in the dropped data
    if (event.dataTransfer.files.length > 0) {
        handleFiles(event.dataTransfer.files);
    }
});

document.getElementById('send').addEventListener('click', async function () {
    if (document.getElementById('message').value.trim() === '') {
        return;
    }
    if (pastedFiles.length > 0) {
        send_files(pastedFiles, document.getElementById('message').value);
        document.getElementById('uploadFileInput').value = '';
        document.getElementById('preview-files').innerHTML = '';
        document.getElementById('files-preview').style.display = 'none';
        document.getElementById('upload-file').style.display = 'block';
        pastedFiles = [];
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
        var messageDebug = e.target.closest('.message.debug');
        if (expandableContent && messageDebug) {
            if (expandableContent.style.display === 'none') {
                expandableContent.style.display = 'block';
                messageDebug.classList.add('active');
            } else {
                expandableContent.style.display = 'none';
                messageDebug.classList.remove('active');
            }
        }
    }
});


document.getElementById('messages').addEventListener('scroll', function() {
    var messagesContainer = this;
    if (isUserAtBottom(messagesContainer)) {
        hideNewMessageIndicator();
    }
});

function applyTooltips(selector) {
    const tooltipElements = document.querySelectorAll(selector);

    tooltipElements.forEach(el => {
        el.addEventListener('mouseenter', showTooltip);
        el.addEventListener('mouseleave', hideTooltip);
    });

    function showTooltip(e) {
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
        tooltipDiv.style.position = 'absolute'; // Ensure tooltip is positioned absolutely
        tooltipDiv.style.opacity = '1';
    }

    function hideTooltip() {
        document.querySelectorAll('.dynamic-tooltip').forEach(tooltip => {
            tooltip.remove();
        });
    }
}


document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme') || '';
    const tabsState = localStorage.getItem("tabsState");
    const sendMailButton = document.getElementById('send-email');
    const cancelEmailButton = document.getElementById('cancel-email');
    const hiddenIdField = document.getElementById('emailId');

    if (currentTheme) {
        document.body.classList.add(currentTheme);
    }

    sendMailButton.addEventListener('click', function() {
        sendMail(hiddenIdField.value);
    });

    cancelEmailButton.addEventListener('click', function() {
        $('#googleConfModal').modal('hide');
    });

    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-theme');
        localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark-theme' : '');
    });
    // Hacky way, this still shows the animation when the page loads
    if (tabsState === "open") {
        openTabs();
    } else if (tabsState === "closed") {
        closeTabs();
    }

    // Event delegation for copy button
    document.body.addEventListener('click', function(e) {
        if (e.target && e.target.className.includes('copy-button')) {
            var div = e.target.closest('.bubble');
            copyToClipboard(div);
        }
    });

    // Event delegation for regenerate button
    document.body.addEventListener('click', function(e) {
        if (e.target && e.target.className.includes('regenerate-button')) {
            var div = e.target.closest('.bubble');
            regenerateResponse(div);
        }
    });
    applyTooltips('[data-tooltip]');

});

function toggleTabs() {
    const toggle = document.getElementById("toggle-chat-tabs");
    toggle.style.transition = "left 0.3s";
    const sideNav = document.getElementById("sideNav");
    const chatContainer = document.getElementById("chat-container");
    chatContainer.style.transition = "max-width 0.3s, min-width 0.3s";

    if (sideNav.classList.contains("open")) {
        closeTabs();
    } else {
        openTabs();
    }
}
function showTextFileModal(files) {
    let modalHtml = `
        <div class="modal fade" id="textFileModal">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Text Files</h5>
                        <button type="button" class="close" data-dismiss="modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p>Choose an option for each text file:</p>
                        <ul id="textFileList"></ul>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    let modalElement = document.createElement('div');
    modalElement.innerHTML = modalHtml;
    document.body.appendChild(modalElement);

    let modal = document.getElementById('textFileModal');
    let textFileList = document.getElementById('textFileList');

    let processedFilesCount = 0;  // Counter for processed files

    files.forEach((file, index) => {
        let listItem = document.createElement('li');
        listItem.innerHTML = `
            <span>${file.name}</span>
            <button class="includeTextBtn" data-index="${index}">Include in Input</button>
            <button class="uploadTextBtn" data-index="${index}">Upload as File</button>
        `;
        textFileList.appendChild(listItem);
    });

    let checkCloseModal = function () {
        if (processedFilesCount >= files.length) {
            $(modal).modal('hide');
        }
    };

    let closeModal = function () {
        $(modal).modal('hide');
    };

    $('.close, .btn-secondary').on('click', closeModal);

    $(modal).on('hidden.bs.modal', function () {
        $('.close, .btn-secondary').off('click', closeModal);
        modalElement.remove();
    });

    $(modal).modal('show');

    $('.includeTextBtn').on('click', function () {
        let index = $(this).data('index');
        let file = files[index];
        let reader = new FileReader();
        reader.onload = function (event) {
            let inputText = `${file.name}\n\n${event.target.result}`;
            document.getElementById('message').value += inputText;
            // Trigger the input event on the message textarea
            message.dispatchEvent(new Event('input'));
        };
        reader.readAsText(file);
        $(this).prop('disabled', true);
        $(this).siblings('.uploadTextBtn').prop('disabled', true);
        processedFilesCount++;
        checkCloseModal();
    });

    $('.uploadTextBtn').on('click', function () {
        let index = $(this).data('index');
        let file = files[index];
        pastedFiles.push(file);
        createFilePreview(file, pastedFiles.length - 1);
        document.getElementById('files-preview').style.display = 'flex';
        document.getElementById('files-preview').style.justifyContent = 'center';
        $(this).prop('disabled', true);
        $(this).siblings('.includeTextBtn').prop('disabled', true);
        processedFilesCount++;
        checkCloseModal();
    });
}
