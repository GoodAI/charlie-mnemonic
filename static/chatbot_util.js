// parse a json with json5
function parseComplexJson(jsonStr) {
    try {
        return JSON5.parse(jsonStr);
    } catch (error) {
        console.error('Error parsing JSON5:', error);
        return null;
    }
};

function escapeHTML(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
};

// copy the code to the clipboard
function copyCodeToClipboard(btn) {
    var code = btn.nextElementSibling.innerText;
    var textarea = document.createElement('textarea');
    textarea.textContent = code;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    var overlay = document.getElementById('overlay');
    overlay.textContent = 'Code copied to clipboard';
    overlay.classList.add('active');
    setTimeout(function () {
        overlay.classList.remove('active');
    }, 1000);
};

function copyToClipboard(btn) {
    // Ensure the button is correctly passed and exists in the DOM
    if (!btn || !btn.closest) {
        console.error('copyToClipboard was called with an invalid element or the element is not in the DOM');
        return;
    }

    // Navigate up to the parent '.bubble' div
    var bubbleDiv = btn.closest('.bubble');
    if (!bubbleDiv) {
        console.error('Failed to find the .bubble parent element.');
        return;
    }

    // Find the '.markdown' div within the '.bubble' div
    var markdownDiv = bubbleDiv.querySelector('.markdown');
    if (!markdownDiv) {
        console.error('Failed to find the .markdown element within the bubble.');
        return;
    }

    // Get the text content you want to copy
    var textToCopy = markdownDiv.innerText;

    var textarea = document.createElement('textarea');
    textarea.textContent = textToCopy;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);

    // Display overlay message
    var overlay = document.getElementById('overlay');
    if (overlay) {
        overlay.textContent = 'Message copied to clipboard';
        overlay.classList.add('active');
        setTimeout(function () {
            overlay.classList.remove('active');
        }, 1000);
    } else {
        console.error('Overlay element not found');
    }
}



var renderer = new marked.Renderer();

renderer.image = function (href, title, text) {
    return `<a href="${href}" data-lightbox="${text}" data-title="${title}"><img src="${href}" width="250px" alt="${text}"></a>`;
};

renderer.link = function (href, title, text) {
    return `<a target="_blank" href="${href}" title="${title}">${text}</a>`;
};

marked.setOptions({
    highlight: function (code, lang) {
        return '<div class="language">' + (lang || 'code') + '</div>' +
            '<button class="copy-btn" onclick="copyToClipboard(this)">Copy</button>' +
            '<pre><code>' + hljs.highlightAuto(code, [lang]).value + '</code></pre>';
    },
    renderer: renderer,
});


function setupCollapsible() {
    var coll = document.getElementsByClassName("collapsible");

    for (var i = 0; i < coll.length; i++) {
        var old_element = coll[i];
        var new_element = old_element.cloneNode(true);
        old_element.parentNode.replaceChild(new_element, old_element);

        new_element.addEventListener("click", function () {
            this.classList.toggle("active");
            var content = this.nextElementSibling;
            if (content.style.display === "block") {
                content.style.display = "none";
            } else {
                content.style.display = "block";
            }
        });
    }
}

// function to open the debug navigation
function openDebugNav() {
    document.getElementById("debugNav").style.width = "60%";
    document.getElementById("debugNav").style.height = "100vh";
    document.getElementById("debugNav").style.display = "block";
    document.addEventListener('click', closeDebugNavOnClickOutside);
}

// function to close the debug navigation
function closeDebugNav() {
    document.getElementById("debugNav").style.width = "0";
    document.getElementById("debugNav").style.height = "0";
    document.getElementById("debugNav").style.display = "none";
    document.removeEventListener('click', closeDebugNavOnClickOutside);
}

// function to close the debug navigation when click happens outside of it
function closeDebugNavOnClickOutside(event) {
    var debugNav = document.getElementById("debugNav");
    if (!debugNav.contains(event.target)) {
        closeDebugNav();
    }
}

// function to open the memory explorer page
// todo: use a modal instead of a new tab
function showMemoryExplorer() {
    var url = "/memory_explorer/active_brain";
    window.open(url, '_blank');
}

function insertPresetText(text) {
    var messageInput = document.getElementById('message');
    messageInput.value += text;
    document.getElementById('send').click();
}

function openNav() {
    // open settings modal
    $('#settingsModal').modal('show');
}

function closeNav() {
    // close settings modal
    $('#settingsModal').modal('hide');
}

function closeAuth() {
    // close googleAuthModal
    $('#googleAuthModal').modal('hide');
}

function openTabs() {
    const toggle = document.getElementById("toggle-chat-tabs");
    toggle.classList.remove("closed");
    toggle.classList.add("open");

    document.getElementById("sideNav").classList.add("open");
    const container = document.getElementById("chat-container");
    container.classList.add("open");
    toggle.setAttribute("data-tooltip", "Hide Chat tabs");

    localStorage.setItem("tabsState", "open");

    setTimeout(() => {
        toggle.style.transition = "none";
        container.style.transition = "none";
    }, 500);
}

function closeTabs() {
    const toggle = document.getElementById("toggle-chat-tabs");
    toggle.classList.remove("open");
    toggle.classList.add("closed");
    toggle.setAttribute("data-tooltip", "Show Chat tabs");

    document.getElementById("sideNav").classList.remove("open");
    const container = document.getElementById("chat-container");
    container.classList.remove("open");
    
    localStorage.setItem("tabsState", "closed");

    setTimeout(() => {
        toggle.style.transition = "none";
        container.style.transition = "none";
    }, 500);
}


function updateCounterDiv(message_length, tokens_used, max_message_tokens, cost) {
    const countDiv = document.getElementById("tokenCount");
    let tokensColor = tokens_used > max_message_tokens ? "<span style='color: red;'>" : "<span>";
    
    countDiv.innerHTML = `Characters: ${message_length}, tokens: ${tokensColor}${tokens_used}</span>/${max_message_tokens}, cost: $${cost.toFixed(4)}`;
}



function formatTime(seconds) {
    const pad = (num) => (num < 10 ? '0' : '') + num;
    const minutes = Math.floor(seconds / 60);
    seconds = seconds % 60;
    return `${pad(minutes)}:${pad(seconds)}`;
}

function getUuidFromMessage(messageElement) {
    return messageElement.dataset.uuid;
}

function showTextFileModal(file, fileContent) {
    // Create the modal HTML
    let modalHtml = `
        <div class="modal" id="textFileModal">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Text File: ${file.name}</h5>
                        <button type="button" class="close" data-dismiss="modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p>Choose an option for the text file:</p>
                        <button id="includeTextBtn">Include in Input</button>
                        <button id="uploadTextBtn">Upload as File</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Append the modal to the body
    document.body.innerHTML += modalHtml;

    // Get references to the modal and buttons
    let modal = document.getElementById('textFileModal');
    let includeTextBtn = document.getElementById('includeTextBtn');
    let uploadTextBtn = document.getElementById('uploadTextBtn');

    // Show the modal
    $(modal).modal('show');

    // Handle the "Include in Input" button click
    includeTextBtn.onclick = function () {
        let inputText = `${file.name}\n\n${fileContent}`;
        document.getElementById('message').value += inputText;
        $(modal).modal('hide');
    };

    // Handle the "Upload as File" button click
    uploadTextBtn.onclick = function () {
        // Add the file to the pastedFiles array
        pastedFiles.push(new File([fileContent], file.name));
        $(modal).modal('hide');
        // Create a preview element for non-image files
        let preview = document.createElement('div');
        preview.className = 'file-preview';
        preview.innerHTML = `<i class="fas fa-file"></i><span>${file.name}</span>`;
        document.getElementById('preview-files').appendChild(preview);
        // Add delete icon and tooltip
        let deleteIcon = document.createElement('i');
        deleteIcon.className = 'fas fa-times-circle file-delete-icon';
        deleteIcon.setAttribute('data-index', i);
        deleteIcon.setAttribute('title', 'Delete');
        preview.appendChild(deleteIcon);
    };

    // Remove the modal from the DOM when hidden
    $(modal).on('hidden.bs.modal', function () {
        modal.remove();
    });
}