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

function copyToClipboard(event) {    
    if (!event.target) {
        return;
    }
    // Find the closest .bubble ancestor
    var bubbleDiv = event.target.closest('.bubble');
    if (!bubbleDiv) {
        console.warn('Failed to find the .bubble parent element.');
        return;
    }
    

    // Clone the bubble content
    var contentToCopy = bubbleDiv.cloneNode(true);

    // Remove the bottom buttons container
    var bottomButtons = contentToCopy.querySelector('.bottom-buttons-container');
    if (bottomButtons) {
        bottomButtons.remove();
    }

    // Function to get text content, preserving line breaks
    function getTextContent(element) {
        let text = '';
        for (let node of element.childNodes) {
            if (node.nodeType === Node.TEXT_NODE) {
                text += node.textContent;
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                if (node.nodeName === 'BR' || node.nodeName === 'P' || node.nodeName === 'DIV') {
                    text += '\n';
                }
                text += getTextContent(node);
            }
        }
        return text;
    }

    // Get the text content
    var textToCopy = getTextContent(contentToCopy).trim();

    // Use the Clipboard API to copy the text
    navigator.clipboard.writeText(textToCopy).then(function() {
        console.log('Copying to clipboard was successful!');
        showCopyFeedback();
    }, function(err) {
        console.error('Could not copy text: ', err);
    });
}

function showCopyFeedback() {
    var overlay = document.getElementById('overlay');
    if (overlay) {
        overlay.textContent = 'Copied to clipboard';
        overlay.classList.add('active');
        setTimeout(function () {
            overlay.classList.remove('active');
        }, 2000);
    } else {
        console.error('Overlay element not found');
    }
}

// Use event delegation
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('copy-button')) {
        copyToClipboard(event);
    }
});

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

function closeConf() {
    // close googleAuthModal
    $('#googleConfModal').modal('hide');

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

function debounce(func, delay) {
    let timeoutId;
    return function () {
        const context = this;
        const args = arguments;
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(context, args), delay);
    };
}

function set_chat_padding(width) {
    const messages = document.getElementById("messages");
    messages.style.padding = `20px ${width}vw`;
    // save the padding in local storage
    localStorage.setItem("chatPadding", width);
}

function scrollToBottom(force = false) {
    const messagesContainer = document.getElementById('messages');
    if (force || isUserAtBottom(messagesContainer)) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        hideNewMessageIndicator();
    } else {
        showNewMessageIndicator();
    }
}

function setupScrollObserver() {
    const messagesContainer = document.getElementById('messages');
    const observer = new MutationObserver((mutations) => {
        let shouldScroll = false;
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                shouldScroll = true;
            } else if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                shouldScroll = true;
            }
        });
        if (shouldScroll) {
            scrollToBottom();
        }
    });

    observer.observe(messagesContainer, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['style']
    });
}

function showNotification(message, type = 'info') {
    const notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }

    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.role = 'alert';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    document.getElementById('notification-container').appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}