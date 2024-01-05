var currentActiveTab = 1;
var categoryValues;

var tempFullChunk = '';
// populate the settings menu
function populateSettingsMenu(settings) {
    var settingsMenu = document.getElementById("SidenavAddons");

    // Clear the settings menu
    while (settingsMenu.firstChild) {
        settingsMenu.firstChild.remove();
    }

    var tabs = ['Addons', 'Data', 'General Settings', 'Recent Messages', 'User Data', 'Memory Configuration'];
    var tabNav = createTabNav(tabs);
    settingsMenu.appendChild(tabNav);

    settingsMenu.appendChild(createAddonsTabContent(settings.addons, 'tab1'));
    settingsMenu.appendChild(createDataTabContent(settings.audio, 'tab2'));
    settingsMenu.appendChild(createGeneralSettingsTabContent(settings, 'tab3'));
    settingsMenu.appendChild(createRecentMessagesTabContent('tab4'));
    settingsMenu.appendChild(createUserDataTabContent('tab5'));
    settingsMenu.appendChild(createMemoryTabContent('tab6'));

    var maxRange = settings.memory.max_tokens;
    var minRange = settings.memory.min_tokens;
    max_message_tokens = settings.memory.input;
    updateCounterDiv(0, 0, max_message_tokens, 0);

    var slider = document.getElementById('slider');

    var startValues = [settings.memory.functions, settings.memory.ltm1, settings.memory.ltm2, settings.memory.episodic, settings.memory.recent, settings.memory.notes, settings.memory.input, settings.memory.output];

    for (var i = 1; i < startValues.length; i++) {
        startValues[i] += startValues[i - 1];
    }
    
    noUiSlider.create(slider, {
        start: startValues,
        connect: true,
        range: {
            'min': 0,
            'max': maxRange
        },
        step: 100,
    });

    slider.noUiSlider.on('update', function(values) {
        var values = values.map(Number).map(Math.round);
        categoryValues = values.map(function(value, index, array) {
            return index === 0 ? value : value - array[index - 1];
        });

        document.getElementById('value-functions').innerHTML = ((categoryValues[0]/maxRange)*100).toFixed(2) + '% (' + categoryValues[0] + ')';
        document.getElementById('value-ltm1').innerHTML = ((categoryValues[1]/maxRange)*100).toFixed(2) + '% (' + categoryValues[1] + ')';
        document.getElementById('value-ltm2').innerHTML = ((categoryValues[2]/maxRange)*100).toFixed(2) + '% (' + categoryValues[2] + ')';
        document.getElementById('value-episodicmemory').innerHTML = ((categoryValues[3]/maxRange)*100).toFixed(2) + '% (' + categoryValues[3] + ')';
        document.getElementById('value-recentmessages').innerHTML = ((categoryValues[4]/maxRange)*100).toFixed(2) + '% (' + categoryValues[4] + ')';
        document.getElementById('value-notes').innerHTML = ((categoryValues[5]/maxRange)*100).toFixed(2) + '% (' + categoryValues[5] + ')';
        document.getElementById('value-input').innerHTML = ((categoryValues[6]/maxRange)*100).toFixed(2) + '% (' + categoryValues[6] + ')';
        document.getElementById('value-output').innerHTML = ((categoryValues[7]/maxRange)*100).toFixed(2) + '% (' + categoryValues[7] + ')';
    });

    slider.noUiSlider.on('slide', function(values, handle) {
        var values = values.map(Number).map(Math.round);

        // Check the first handle
        if (handle === 0 && values[0] !== minRange) {
            slider.noUiSlider.setHandle(0, minRange);
        }
        // last handle can't be moved
        if (handle === 7) {
            slider.noUiSlider.setHandle(7, maxRange);
        }
        // make sure input and output category values are at least 500
        if (handle === 6 && values[6] < values[5] + minRange) {
            slider.noUiSlider.setHandle(6, values[5] + minRange);
        }
        if (handle === 6 && values[7] < values[6] + minRange) {
            slider.noUiSlider.setHandle(6, values[7] - minRange);
        }
        if (handle === 5 && values[6] < values[5] + minRange) {
            slider.noUiSlider.setHandle(5, values[6] - minRange);
        }
    });

    var categories = document.getElementsByClassName('category');
    for (var i = 0; i < categories.length; i++) {
        categories[i].style.pointerEvents = "none";
    }

    switchTab(currentActiveTab); // make the first tab active by default
};

function createTabNav(tabs) {
    var tabNav = document.createElement('ul');
    tabNav.className = 'nav nav-tabs';

    tabs.forEach((tab, index) => {
        var tabLink = document.createElement('a');
        tabLink.href = '#';
        tabLink.textContent = tab;
        tabLink.onclick = function (e) {
            e.preventDefault();
            switchTab(index + 1);
        };
        
        var listItem = document.createElement('li');
        listItem.className = 'nav-item';
        listItem.appendChild(tabLink);
        tabNav.appendChild(listItem);
    });

    return tabNav;
}

function switchTab(tabNumber) {
    var tabs = document.querySelectorAll('.tab-content');
    var tabLinks = document.querySelectorAll('.nav-item a');
    for (var i = 0; i < tabs.length; i++) {
        tabs[i].classList.remove('active');
        tabLinks[i].classList.remove('active');
    }
    var activeTab = document.getElementById('tab' + tabNumber);
    activeTab.classList.add('active');
    tabLinks[tabNumber - 1].classList.add('active');
    currentActiveTab = tabNumber; // update the current active tab
}

function createAddonsTabContent(addons, tabId) {
    var tabContent = document.createElement('div');
    tabContent.id = tabId;
    tabContent.className = 'tab-content';

    var h3 = document.createElement('h3');
    h3.textContent = 'Addons';
    tabContent.appendChild(h3);

    var addon_descriptions = [
        {
          name: 'get_current_weather',
          description: 'Get the current weather in a location'
        },
        {
          name: 'get_search_results',
          description: 'Get 5 search results from google or youtube'
        },
        {
            name: 'run_python_code',
            description: 'Run python code'
        },
        {
            name: 'visit_website',
            description: 'Visit a website'
        }
      ];

    for (let addon in addons) {
        if (addons.hasOwnProperty(addon)) {
            var status = addons[addon] ? '<i class="fas fa-check-square"></i>' : '<i class="fas fa-square-full"></i>';
            var menuItem = document.createElement('a');
            menuItem.href = "#";
            menuItem.innerHTML = addon + ": " + status + "<br/>" + addon_descriptions.find(x => x.name === addon).description;
            menuItem.onclick = (function (addon) {
                return function (e) {
                    e.preventDefault();
                    edit_status('addons', addon, !addons[addon]);
                };
            })(addon);
            tabContent.appendChild(menuItem);
        }
    }

    return tabContent;
}

function createDataTabContent(audio, tabId) {
    var tabContent = document.createElement('div');
    tabContent.id = tabId;
    tabContent.className = 'tab-content';

    var h3 = document.createElement('h3');
    h3.textContent = 'Audio';
    tabContent.appendChild(h3);

    for (let audioItem in audio) {
        if (audio.hasOwnProperty(audioItem)) {
            var menuItem = document.createElement('a');
            menuItem.href = "#";
            var status = audio[audioItem] ? '<i class="fas fa-check-square"></i>' : '<i class="fas fa-square-full"></i>';
            menuItem.innerHTML = audioItem + ": " + status;
            menuItem.onclick = (function (audioItem) {
                return function (e) {
                    e.preventDefault();
                    edit_status('audio', audioItem, !audio[audioItem]);
                };
            })(audioItem);
            tabContent.appendChild(menuItem);
        }
    }

    return tabContent;
}

function createGeneralSettingsTabContent(settings, tabId) {
    var tabContent = document.createElement('div');
    tabContent.id = tabId;
    tabContent.className = 'tab-content';

    // Populate avatar settings
    var h3 = document.createElement('h3');
    h3.textContent = 'Avatar';
    tabContent.appendChild(h3);

    var avatarItem = document.createElement('a');
    avatarItem.href = "#";
    var status = settings.avatar.avatar ? '<i class="fas fa-check-square"></i>' : '<i class="fas fa-square-full"></i>';
    avatarItem.innerHTML = 'Enable avatar: ' + status;
    avatarItem.onclick = function (e) {
        e.preventDefault();
        edit_status('avatar', 'avatar', !settings.avatar.avatar);
    };
    tabContent.appendChild(avatarItem);

    // Populate language settings
    h3 = document.createElement('h3');
    h3.textContent = 'Language';
    tabContent.appendChild(h3);

    var languageItem = document.createElement('select');
    languageItem.id = 'language';
    languageItem.name = 'language';
    var option1 = document.createElement('option');
    option1.value = 'en';
    option1.text = 'English';
    var option2 = document.createElement('option');
    option2.value = 'af';
    option2.text = 'Afrikaans';
    languageItem.appendChild(option1);
    languageItem.appendChild(option2);
    languageItem.value = settings.language.language;
    languageItem.onchange = function (e) {
        edit_status('language', 'language', e.target.value);
    }
    tabContent.appendChild(languageItem);

    // Populate Display Name settings
    h3 = document.createElement('h3');
    h3.textContent = 'Display Name';
    tabContent.appendChild(h3);

    var displayNameItem = document.createElement('textarea');
    displayNameItem.id = 'display_name';
    displayNameItem.name = 'display_name';
    displayNameItem.value = settings.display_name;
    displayNameItem.onchange = function (e) {
        edit_status('db', 'display_name', e.target.value);
    }
    tabContent.appendChild(displayNameItem);

    // Other settings
    h3 = document.createElement('h3');
    h3.textContent = 'Other settings';
    tabContent.appendChild(h3);

    // Populate verbose settings
    var verboseItem = document.createElement('a');
    verboseItem.href = "#";
    var status = settings.verbose.verbose ? '<i class="fas fa-check-square"></i>' : '<i class="fas fa-square-full"></i>';
    verboseItem.innerHTML = 'See Memory Retrieval: ' + status;
    verboseItem.onclick = function (e) {
        e.preventDefault();
        edit_status('verbose', 'verbose', !settings.verbose.verbose);
    }
    tabContent.appendChild(verboseItem);

    // Populate chain of thought settings
    var cotItem = document.createElement('a');
    cotItem.href = "#";
    var status = settings.cot_enabled.cot_enabled ? '<i class="fas fa-check-square"></i>' : '<i class="fas fa-square-full"></i>';
    cotItem.innerHTML = 'Chain of thought (experimental): ' + status;
    cotItem.onclick = function (e) {
        e.preventDefault();
        edit_status('cot_enabled', 'cot_enabled', !settings.cot_enabled.cot_enabled);
    }
    tabContent.appendChild(cotItem);

    return tabContent;
}


function createRecentMessagesTabContent(tabId) {
    var tabContent = document.createElement('div');
    tabContent.id = tabId;
    tabContent.className = 'tab-content';

    var h3 = document.createElement('h3');
    h3.textContent = 'Recent Message';
    tabContent.appendChild(h3);

    var clearMsgBtn = document.createElement('button');
    clearMsgBtn.id = 'clearMsgBtn';
    clearMsgBtn.textContent = 'Clear recent messages';
    tabContent.appendChild(clearMsgBtn);
    
    clearMsgBtn.addEventListener('click', delete_recent_messages);

    return tabContent;
}

function createUserDataTabContent(tabId) {
    var tabContent = document.createElement('div');
    tabContent.id = tabId;
    tabContent.className = 'tab-content';

    var h3 = document.createElement('h3');
    h3.textContent = 'User Data';
    tabContent.appendChild(h3);

    var saveDataBtn = document.createElement('button');
    saveDataBtn.id = 'saveDataBtn';
    saveDataBtn.textContent = 'Save Data';
    tabContent.appendChild(saveDataBtn);

    var deleteDataBtn = document.createElement('button');
    deleteDataBtn.id = 'deleteDataBtn';
    deleteDataBtn.textContent = 'Delete Data';
    tabContent.appendChild(deleteDataBtn);

    var uploadDataInput = document.createElement('input');
    uploadDataInput.type = 'file';
    uploadDataInput.id = 'uploadDataInput';
    tabContent.appendChild(uploadDataInput);

    var uploadDataBtn = document.createElement('button');
    uploadDataBtn.id = 'uploadDataBtn';
    uploadDataBtn.textContent = 'Upload Data';
    tabContent.appendChild(uploadDataBtn);

    
    saveDataBtn.addEventListener('click', save_user_data);
    deleteDataBtn.addEventListener('click', delete_user_data);
    uploadDataBtn.addEventListener('click', function () {
        const fileInput = document.getElementById('uploadDataInput');
        if (fileInput.files.length > 0) {
            upload_user_data(fileInput.files[0]);
        }
    });

    return tabContent;
}

function createMemoryTabContent(tabId) {
    var tabContent = document.createElement('div');
    tabContent.id = tabId;
    tabContent.className = 'tab-content';

    var h3 = document.createElement('h3');
    h3.textContent = 'Memory Configuration';
    tabContent.appendChild(h3);

    var container = document.createElement('div');
    container.id = 'container';

    var slider = document.createElement('div');
    slider.id = 'slider';
    container.appendChild(slider);

    var values = document.createElement('div');
    values.id = 'values';

    var categories = ['Functions', 'LTM 1', 'LTM 2', 'Episodic Memory', 'Recent Messages', 'Notes', 'Input', 'Output'];
    categories.forEach(cat => {
        var p = document.createElement('p');
        p.className = 'category';
        p.innerHTML = `${cat}: <span id="value-${cat.toLowerCase().replace(' ', '')}"></span>`;
        values.appendChild(p);
    });

    container.appendChild(values);
    tabContent.appendChild(container);

    // button to load default memory configuration
    var resetButton = document.createElement('button');
    resetButton.textContent = 'Reset to Default';
    resetButton.onclick = function () {
        var defaultValues = [500, 1500, 2500, 2800, 3500, 4500, 5500, 6500];
        slider.noUiSlider.set(defaultValues);
    };
    tabContent.appendChild(resetButton);

    var saveButton = document.createElement('button');
    saveButton.textContent = 'Save Memory Configuration';
    saveButton.onclick = saveMemoryConfiguration;
    tabContent.appendChild(saveButton);

    return tabContent;
}

function saveMemoryConfiguration() {
    const overlay = document.getElementById('overlay_msg');
    const overlayMessage = document.getElementById('overlay-message');
    overlayMessage.textContent = "Updating Settings...";
    overlay.style.display = 'flex';
    var memorySettings = {
        functions: categoryValues[0],
        ltm1: categoryValues[1],
        ltm2: categoryValues[2],
        episodic: categoryValues[3],
        recent: categoryValues[4],
        notes: categoryValues[5],
        input: categoryValues[6],
        output: categoryValues[7]
    };
    max_message_tokens = categoryValues[6];
    updateCounterDiv(0, 0, max_message_tokens, 0);

    fetch(API_URL + '/update_settings/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            category: 'memory',
            setting: memorySettings,
            username: user_name
        }),
        credentials: 'include'
    })
        .then(response => response.json())
        .then(data => {
            setSettings(data);
            overlay.style.display = 'none';
        })
        .catch(console.error);
}

function edit_status(category, setting, value) {
    const overlay = document.getElementById('overlay_msg');
    const overlayMessage = document.getElementById('overlay-message');
    overlayMessage.textContent = "Updating Settings...";
    overlay.style.display = 'flex';

    fetch(API_URL + '/update_settings/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ category: category, setting: setting, value: value, username: user_name }),
        credentials: 'include'
    })
        .then(response => response.json())
        .then(data => {
            overlayMessage.textContent = "Settings Updated";
            setSettings(data);
            overlay.style.display = 'none';
        })
        .catch(console.error);
};

function playButtonHandler() {
    var playIcon = this.querySelector('.play-button');
    playIcon.classList.remove('fa-play');
    playIcon.classList.add('fa-spinner');
    var messageBubble = this.parentElement.querySelector('p');
    var clonedButton = playIcon.cloneNode(true);
    messageBubble.appendChild(clonedButton);
    request_audio(clonedButton).then(audioSrc => {
        var audioElement = document.createElement('audio');
        audioElement.controls = true;
        audioElement.innerHTML = `<source src="${audioSrc}" type="audio/mp3">Your browser does not support the audio element.`;
        this.closest('.bubble').appendChild(audioElement);
        this.remove();
    });
}

function setSettings(newSettings) {
    // import the settings and populate the settings menu
    const overlay = document.getElementById('overlay_msg');
    const overlayMessage = document.getElementById('overlay-message');
    overlay.style.display = 'none';
    if (newSettings) {
        // if no display name is set, use the username
        if (newSettings.display_name == null || newSettings.display_name == '') {
            newSettings.display_name = user_name;
        }
        // Update the username in the widget
        display_name = newSettings.display_name;
        document.getElementById('username').innerHTML = 'Display Name: <a href="/profile" target="_blank">' + display_name + '</a>';
        settings = newSettings;
        populateSettingsMenu(settings);
        if (newSettings.audio.voice_input) {
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(function (stream) {
                    $('#record').show();
                })
                .catch(function (err) {
                    edit_status('audio', 'voice_input', false);
                    $('#record').hide();
                    if (err.name === 'NotAllowedError') {
                        showErrorModal('Permission to access microphone was denied. Please allow access to the microphone and try again.');
                    } else if (err.name === 'NotFoundError') {
                        showErrorModal('No microphone was found. Ensure that a microphone is installed and that microphone settings are configured correctly.');
                    } else {
                        showErrorModal('Error occurred : ' + err.name);
                    }
                });

        } else {
            $('#record').hide();
        }

        var playButtonCode = '<div class="play-button-wrapper"><a href="#" data-tooltip="Play Audio"><i class="fas fa-play play-button"></i></a></div>';

        if (newSettings.audio.voice_output) {
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(function (stream) {
                    $('#record').show();
        
                    // Add play button to all existing chat bubbles of bot messages
                    var allMessages = document.querySelectorAll('.message.bot .bubble');
                    allMessages.forEach(function(message) {
                        if (!message.querySelector('.play-button')) {
                            message.innerHTML += playButtonCode;
                            var playButton = message.querySelector('.play-button');
                            playButton.addEventListener('click', playButtonHandler);
                        }
                    });
                })
                .catch(function (err) {
                    edit_status('audio', 'voice_output', false);
                    $('#record').hide();
                    // Error handling code...
                });
        
        } else {
            $('#record').hide();
        
            // Remove play button from all existing chat bubbles of bot messages
            var allPlayButtonWrappers = document.querySelectorAll('.message.bot .bubble .play-button-wrapper');
            allPlayButtonWrappers.forEach(function(wrapper) {
                wrapper.remove();
            });
            // Remove audio elements from all existing chat bubbles of bot messages
            var allAudioElements = document.querySelectorAll('.message.bot .bubble audio');
            allAudioElements.forEach(function(audio) {
                audio.remove();
            });
        }

        if (newSettings.avatar.avatar) {
            $('#d-id-content').show();
            document.getElementById("chat-container").style.minWidth = "50vw";
            document.getElementById("chat-container").style.maxWidth = "50vw";
        }
        else {
            $('#d-id-content').hide();
            document.getElementById("chat-container").style.minWidth = "80vw";
        }
        if (newSettings.usage != "" && newSettings.usage != null) {
            handleUsage(newSettings);
        }
        if (newSettings.daily_usage != "" && newSettings.daily_usage != null) {
            handleDailyUsage(newSettings);
        }
    }
};
function showErrorMessage(message, instant) {
    var timestamp = new Date().toLocaleTimeString();
    var content = message;
    var tempchild = document.getElementById('messages').lastChild;
    if (tempchild && tempchild.querySelector) {
        var spinner = tempchild.querySelector('.spinner');
        if (spinner != null) {
            spinner.remove();
            document.getElementById('messages').lastChild.remove();
        }
    }

    var lastMessage = document.querySelector('.last-message');
    if (lastMessage) {
        lastMessage.classList.remove('last-message');
    }

    var chatMessage = document.createElement('div');
    if (instant) {
        chatMessage.innerHTML = `
            <div class="message warning">
                <span class="timestamp">${timestamp}</span>
                <div class="bubble">
                    ${message}
                </div>
            </div>
        `;
    } else {
        chatMessage.innerHTML = `
            <div class="message error">
                <span class="timestamp">${timestamp}</span>
                <div class="bubble">
                    <div class="expandable" onclick="this.classList.toggle('expanded')">
                        <div class="title">Error:<div class="arrow"></div></div>
                        ${message}
                    </div>
                </div>
            </div>
        `;
    }
    document.getElementById('messages').appendChild(chatMessage);

    // enable the send  and record button again
    canSend = true;
    canRecord = true;
    isWaiting = false;
    isRecording = false;
    canSendMessage();
    document.getElementById('message').placeholder = 'Type a message...';
    // Auto-scroll to the bottom of the chat
    document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
};

function try_reconnect(socket, username) {
    // try to reconnect to the socket
    if (socket.readyState == WebSocket.CLOSED) {
        console.log('socket closed, trying to reconnect');
        var connectionStatusElement = document.getElementById('connectionStatus');
        connectionStatusElement.textContent = 'Reconnecting...';
        connectionStatusElement.style.color = 'orange';
        get_settings(username);
    }
};

function handleDebugMessage(msg) {
    let debugNumber = msg.debug;
    let color = msg.color ? msg.color : 'white';
    let message = msg.message.replace(/\n/g, '<br>');

    let debugContentElementId = `debugContent${debugNumber}`;
    let objDiv = document.getElementById(debugContentElementId);

    let isNearBottom = objDiv.scrollHeight - objDiv.clientHeight - objDiv.scrollTop <= 50;

    let debugMessage = document.createElement('p');
    debugMessage.style.color = color;
    debugMessage.innerHTML = message;
    objDiv.appendChild(debugMessage);

    if (isNearBottom) {
        objDiv.scrollTop = objDiv.scrollHeight;
    }
}

function handleUsage(msg) {
    // update the userStats with the new usage
    var userStats = document.getElementById('userStats');
    userStats.innerHTML = '';
    userStats.innerHTML += '<p>Lifetime: Tokens: ' + msg.usage.total_tokens + ', cost: $' + msg.usage.total_cost + '</p>';

}

function handleDailyUsage(msg) {
    // update the userStats with the new usage
    var dailyLimit = document.getElementById('dailyLimit');
    dailyLimit.innerHTML = '';
    dailyLimit.innerHTML += '<p>Daily limit: $' + msg.daily_usage.daily_cost.toFixed(5) + '/$' + daily_limit + '</p>';

}


function handlePlanMessage(msg) {
    var content = msg.content && msg.content.content;
    var timestamp = new Date().toLocaleTimeString();
    tempchild = document.getElementById('messages').lastChild;
    if (tempchild) {
        if (tempchild.querySelector('.spinner') != null) {
            tempchild.querySelector('.spinner').remove();
            document.getElementById('messages').lastChild.remove();
        }
    }

    var args = content ? content.replace(/\r?\n/g, '<br>') : '';

    var lastMessage = document.querySelector('.last-message');
    if (lastMessage) {
        lastMessage.classList.remove('last-message');
    }

    var chatMessage = document.createElement('div');
    chatMessage.innerHTML = `
        <div class="message plan">
            <span class="timestamp">${timestamp}</span>
            <div class="bubble">
                <div class="expandable" onclick="this.classList.toggle('expanded')">
                    <div class="title">PLAN:<div class="arrow"></div></div>
                    ${args}
                </div>
            </div>
        </div>
    `;
    document.getElementById('messages').appendChild(chatMessage);

    var botMessage = '<div class="message bot last-message"><span class="timestamp">' + timestamp + '</span><div class="bubble"><div class="spinner"></div></div></div>';
    var botMessageElement = document.createElement('div');
    botMessageElement.innerHTML = botMessage;
    document.getElementById('messages').appendChild(botMessageElement);

    document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
    content = '';
    tempReceived = '';
    tempFormatted = '';
}

function handleFunctionCall(msg) {
    var timestamp = new Date().toLocaleTimeString();
    var addon = msg.message.function;
    var args = parseComplexJson(msg.message.arguments); // Assuming parseComplexJson is a function you have defined

    var callDetails = {
        "Function": addon,
        "Arguments": args
    };

    // Call updateOrCreateDebugBubble to handle the display
    updateOrCreateDebugBubble("Function Call", timestamp, callDetails);
}

function handleFunctionResponse(msg) {
    var timestamp = new Date().toLocaleTimeString();
    var content = { "Response": msg.message }; // Wrap the response in an object

    // Call updateOrCreateDebugBubble to handle the display
    updateOrCreateDebugBubble("Function Response", timestamp, content);
}

function handleErrorMessage(msg) {
    var timestamp = new Date().toLocaleTimeString();
    var content = msg;
    var tempchild = document.getElementById('messages').lastChild;
    if (tempchild && tempchild.querySelector) {
        var spinner = tempchild.querySelector('.spinner');
        if (spinner != null) {
            spinner.remove();
            document.getElementById('messages').lastChild.remove();
        }
    }
    var args = content.error ? content.error.replace(/\r?\n/g, '<br>') : '';

    var lastMessage = document.querySelector('.last-message');
    if (lastMessage) {
        lastMessage.classList.remove('last-message');
    }

    var chatMessage = `
        <div class="message error">
            <span class="timestamp">${timestamp}</span>
            <div class="bubble">
                <div class="expandable" onclick="this.classList.toggle('expanded')">
                    <div class="title">Error:<div class="arrow"></div></div>
                    ${args}
                </div>
            </div>
        </div>
    `;

    var chatMessageElement = document.createElement('div');
    chatMessageElement.innerHTML = chatMessage;
    document.getElementById('messages').appendChild(chatMessageElement);
}

function handleTabDescription(msg) {
    // update the corresponding button with the tab description
    var tabId = msg.tab_id;
    // trim to the first 5 words only
    var tabDescription = msg.tab_description.split(' ').slice(0, 5).join(' ');
    if (msg.tab_description.split(' ').length > 5) {
        tabDescription += '...';
    }
    var tabButton = document.getElementById('chat-tab-' + tabId);
    if (tabButton) {
        tabButton.textContent = tabDescription;
    }
    // add the typewriter class to the tab button
    tabButton.classList.add('typewriter-text');
    // force the browser to reflow the element
    tabButton.offsetWidth;
}

async function handleStopMessage(msg) {
    var lastMessage = document.querySelector('.last-message .bubble');
    if (lastMessage) {
        // Remove the typing indicator
        removeTypingIndicator();

        // Appending the new chunk to the existing content of the last message
        lastMessage.innerHTML = formatTempReceived(tempFullChunk);
    }

    // Function to remove the typing indicator
    function removeTypingIndicator() {
        var typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    if (settings.audio.voice_output) {
        var playButtonCode = '<div class="play-button-wrapper"><a href="#" data-tooltip="Play Audio"><i class="fas fa-play play-button"></i></a></div>';
        var lastMessage = document.querySelector('.last-message .bubble');
        if (lastMessage) {
            lastMessage.innerHTML += playButtonCode;
        }
        var playButtons = document.querySelectorAll('.play-button');
        var playButton = playButtons[playButtons.length - 1];
        playButton.addEventListener('click', async function () {
            this.classList.remove('fa-play');
            this.classList.add('fa-spinner');
            var audioSrc = await request_audio(this);
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
    
    tempFullChunk = '';
    resetState();
}

function handleChunkMessage(msg) {
    // check if the last message is a chunk message or a debug message

    var timestamp = new Date().toLocaleTimeString();
    var chunkContent = msg.chunk_message;
    tempFullChunk += chunkContent;

    // remove the spinner from the last message
    var tempchild = document.getElementById('messages').lastChild;
    if (tempchild && tempchild.querySelector) {
        var spinner = tempchild.querySelector('.spinner');
        if (spinner != null) {
            spinner.remove();
            document.getElementById('messages').lastChild.remove();
        }
    }

    var lastMessage = document.querySelector('.last-message .bubble');
    if (lastMessage) {
        // Appending the new chunk to the existing content of the last message
        var tempcontent = tempFullChunk;
        lastMessage.innerHTML = parseAndFormatMessage(tempcontent, true);

    } else {
        // If there is no last message, create a new message element for the chunk
        var chatMessage = `
            <div class="message bot last-message">
                <span class="timestamp">${timestamp}</span>
                <div class="bubble">${chunkContent + createTypingIndicator()}</div>
            </div>
        `;

        var chatMessageElement = document.createElement('div');
        chatMessageElement.innerHTML = chatMessage;
        document.getElementById('messages').appendChild(chatMessageElement);
    }
    //resetState();
    function createTypingIndicator() {
        return '<div class="typing-indicator"><div class="dot"></div></div>';
    }
    // Auto-scroll to the bottom of the chat
    document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
}


function handleRateLimit(msg) {
    const toastContainer = document.querySelector('.toast-container');
    const timestamp = new Date().toLocaleTimeString();
    const button = '<button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>';
    let toastType, toastMessage;

    if (msg.content.warning) {
        toastType = 'Rate Limit Warning';
        toastMessage = msg.content.warning;
    } else if (msg.content.error) {
        toastType = 'Rate Limit Error';
        toastMessage = msg.content.error;
    } else {
        toastType = 'Rate Limit Info';
        toastMessage = msg.content.message;
    }

    const toastEl = document.createElement('div');
    toastEl.classList.add('toast');
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.innerHTML = `
        <div class="toast-header">
            ${toastType}
            <small>${timestamp}</small>
            ${button}
        </div>
        <div class="toast-body">
            ${toastMessage}
        </div>
    `;

    const myToast = new bootstrap.Toast(toastEl, { delay: 10000 });
    toastContainer.appendChild(toastEl);
    myToast.show();
}  

function handleRelations(msg) {
    var tempchild = document.getElementById('messages').lastChild;
    if (tempchild && tempchild.querySelector) {
        var spinner = tempchild.querySelector('.spinner');
        if (spinner != null) {
            spinner.remove();
            document.getElementById('messages').lastChild.remove();
        }
    }
    var timestamp = new Date().toLocaleTimeString();
    updateOrCreateDebugBubble("thinking...", timestamp, msg);
}

function handleNoteTaking(msg) {
    var timestamp = new Date().toLocaleTimeString();
    var tempchild = document.getElementById('messages').lastChild;
    if (tempchild && tempchild.querySelector) {
        var spinner = tempchild.querySelector('.spinner');
        if (spinner != null) {
            spinner.remove();
            document.getElementById('messages').lastChild.remove();
        }
    }
    updateOrCreateDebugBubble("exploring notes...", timestamp, msg);
}

function updateOrCreateDebugBubble(message, timestamp, msg) {
    var messagesContainer = document.getElementById('messages');
    var lastMessageWrapper = messagesContainer.lastElementChild;
    var lastMessage = lastMessageWrapper ? lastMessageWrapper.firstElementChild : null;
    var isLastDebug = lastMessage && lastMessage.classList.contains('debug');

    console.log(msg);

    var formattedMsgContent = '';
    for (var key in msg) {
        if (msg.hasOwnProperty(key)) {
            // Selectively display keys
            if (["input", "created_new_memory", "active_brain", "error", "Function", "Arguments", "Response"].includes(key)) {
                formattedMsgContent += `<b>${key}:</b> `;

                if (key === 'active_brain' && typeof msg[key] === 'object') {
                    // Summarize the contents of active_brain
                    formattedMsgContent += 'Query Categories: ' + Object.keys(msg[key]).length + '<br/>';
                } else {
                    // Format other keys normally
                    formattedMsgContent += `${formatContent(msg[key])}<br/>`;
                }
            }
            
        console.log("Formatted content for key", key, formattedMsgContent);
        }
    }
    var expandableContent = `<div class="expandable-content" style="display: none;">${formattedMsgContent}</div>`;

    if (isLastDebug) {
        // Update existing debug bubble
        let typewriterText = lastMessage.querySelector('.typewriter-text');
        if (typewriterText) {
            typewriterText.textContent = message;
            typewriterText.classList.remove('typewriter-text'); // Remove class
            void typewriterText.offsetWidth; // Trigger reflow
            typewriterText.classList.add('typewriter-text'); // Add class back
        }
        var expandableContentElement = lastMessageWrapper.querySelector('.expandable-content');
        if (expandableContentElement) {
            expandableContentElement.innerHTML += formattedMsgContent; // Append new data
        } else {
            lastMessageWrapper.innerHTML += expandableContent;
        }
    } else {
        // Create new debug bubble
        let botMessage = `
            <div class="message debug">
                <span class="timestamp">${timestamp}</span>
                <div class="bubble">
                    <div class="typewriter-container">
                        <div class="loading-icon"></div>
                        <div class="typewriter-text">${message}</div>
                    </div>
                </div>
            </div>`;
        let botMessageWrapper = document.createElement('div');
        botMessageWrapper.innerHTML = botMessage + expandableContent;
        messagesContainer.appendChild(botMessageWrapper);
    }
}

function formatContent(value) {
    if (typeof value === 'object') {
        if (Array.isArray(value)) {
            // Format array elements
            return value.map(item => formatContent(item)).join('<br/>');
        } else {
            // Format object properties
            let formattedObjContent = '';
            for (let key in value) {
                if (value.hasOwnProperty(key)) {
                    formattedObjContent += `<b>${key}:</b> ${formatContent(value[key])}<br/>`;
                }
            }
            return formattedObjContent;
        }
    } else {
        // Format non-object values (string, number, boolean)
        return value.toString();
    }
}

function formatSubContent(subKey, subContent) {
    var result = `<b>${subKey}:</b> `;
    if (Array.isArray(subContent)) {
        result += subContent.map(item => formatContent(item)).join('<br/>');
    } else if (typeof subContent === 'object') {
        result += JSON.stringify(subContent, null, 2).replace(/\n/g, '<br/>');
    } else {
        result += subContent;
    }
    return result + '<br/>';
}

async function get_chat_tabs(username) {
    try {
        const response = await fetch(API_URL + '/get_chat_tabs/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 'username': username }),
            credentials: 'include'
        });

        const full_data = await handleError(response);
        active_tab_data = full_data.active_tab_data;
        tabs_data = full_data.tab_data;

        if (active_tab_data.chat_id != null) {
            chat_id = active_tab_data.chat_id;
        }
        else {
            addChatTab();
            get_chat_tabs(username);
        }

        populateChatTabs(tabs_data);
        

    } catch (error) {
        console.error('Failed to send message: ', error);
        showErrorMessage('Failed to send message: ' + error);
    }
}


async function setChat(id) {
    chat_id = id;

    // Update active state for chat tabs
    var chatTabs = document.getElementById('chat-tabs-container');
    var tabs = chatTabs.getElementsByClassName('chat-tab');
    for (var i = 0; i < tabs.length; i++) {
        tabs[i].classList.remove('active');
    }
    // set the active tab
    var targetTab = document.getElementById('chat-tab-' + id);
    targetTab.classList.add('active');
    swap_tab();
    await get_recent_messages(user_name, chat_id);
    if (settings != null) {
        setSettings(settings);
    }
}

// Random UUID generator
// The purpose of this function is to conform to the standard UUID format (8-4-4-4-12), 
// where the 13th character (represented by ‘y’) is always 8, 9, A, or B.
const uuid = () => {
	return `CLANGxxx-xxxx-xxxx-yxxx-${Date.now().toString(16)}`.replace(
		/[xy]/g,
		function(c) {
			var r = (Math.random() * 16) | 0,
				v = c == "x" ? r : (r & 0x3) | 0x8;
			return v.toString(16);
		}
	);
};

function addChatTab(id) {
    if (id == undefined) {
        id = uuid();
    }
    chat_id = id;
    var chatTabs = document.getElementById('chat-tabs-container');
    var newTab = document.createElement('button');
    newTab.className = 'chat-tab';
    newTab.innerText = 'New Chat';
    newTab.id = 'chat-tab-' + id;
    newTab.onclick = function() {
        setChat(id);
    };
    chatTabs.appendChild(newTab);
    setChat(id);
}

function deleteChatTab() {
    var chatTabs = document.getElementById('chat-tabs-container');
    var targetTab = document.getElementById('chat-tab-' + chat_id);
    if (!targetTab) {
        return; // Exit if the target tab is not found
    }

    var newActiveTab = targetTab.nextElementSibling || targetTab.previousElementSibling;
    
    // Remove the target tab
    chatTabs.removeChild(targetTab);

    // Send the delete request
    fetch(API_URL + '/delete_chat_tab/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 'username': user_name, 'chat_id': chat_id }),
        credentials: 'include'
    })
        .then(response => response.json())
        .then(data => {
            // Select new active tab
            if (newActiveTab) {
                var newActiveTabId = newActiveTab.id.replace('chat-tab-', '');
                setChat(newActiveTabId);
            } else {
                addChatTab();
            }
        })
        .catch(console.error);
}


async function get_recent_messages(username, chat_id) {
    try {
        const response = await fetch(API_URL + '/get_recent_messages/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 'username': username, 'chat_id': chat_id }),
            credentials: 'include'
        });

        const full_data = await handleError(response);

        let data = full_data.recent_messages;
        let messages = [];

        // Merge messages by UUID and process them
        let currentUUID = null;
        let currentMessage = '';
        let currentUser = '';
        let currentTimestamp = null;

        data.forEach(message => {
            const uuid = message.metadata.uid;
            const text = message.document;
            const user = message.metadata.username;
            const timestamp = message.metadata.updated_at;

            // Check for UUID continuity
            if (uuid === currentUUID) {
                currentMessage += '\n' + text;
            } else {
                if (currentUUID !== null) {
                    messages.push({ text: currentMessage, user: currentUser, timestamp: currentTimestamp });
                }
                currentUUID = uuid;
                currentMessage = text;
                currentUser = user;
                currentTimestamp = timestamp;
            }
        });

        // Add the last message if it exists
        if (currentUUID !== null) {
            messages.push({ text: currentMessage, user: currentUser, timestamp: currentTimestamp });
        }

        // Process and display the messages
        messages.forEach(message => {
            addCustomMessage(message.text, message.user === 'user' ? 'user' : 'bot', false, true, message.timestamp);
        });

    } catch (error) {
        console.error('Failed to get messages: ', error);
        showErrorMessage('Failed to get messages: ' + error);
    }
}


function get_settings(username) {
    var timestamp = new Date().toLocaleTimeString();
    prefix = production ? 'wss://' : 'ws://';
    var socket = new WebSocket(prefix + document.domain + ':' + location.port + '/ws/' + username);

    var reconnectInterval = null;

    socket.onclose = function () {
        // Update the connection status in the widget
        var connectionStatusElement = document.getElementById('connectionStatus');
        connectionStatusElement.textContent = 'Disconnected';
        connectionStatusElement.style.color = 'red';
        // wait 2 seconds
        setTimeout(function () {
            // try to reconnect
            try_reconnect(socket, username);
        }, 2000);
    };

    socket.onopen = function () {
        // Update the connection status in the widget
        var connectionStatusElement = document.getElementById('connectionStatus');
        connectionStatusElement.textContent = 'Connected';
        connectionStatusElement.style.color = 'green';
    };

    socket.onerror = function () {
        // Update the connection status in the widget
        var connectionStatusElement = document.getElementById('connectionStatus');
        connectionStatusElement.textContent = 'Error';
        connectionStatusElement.style.color = 'orange';
    };

    socket.addEventListener('message', function (event) {
        // TODO: proper parsing for all of the next messages
        let msg = JSON.parse(event.data);

        if (msg.debug) {
            handleDebugMessage(msg);
        }
        else if (msg.functionresponse) {
            handleFunctionResponse(msg);
        }
        else if (msg.type) {
            if (msg.type == 'plan') {
                handlePlanMessage(msg);
            }
            else if (msg.type == 'note_taking') {
                handleNoteTaking(msg.content);
            }
            else if (msg.type == 'relations') {
                handleRelations(msg.content);
            }
            else if (msg.type == 'rate_limit') {
                handleRateLimit(msg);
            }
        }
        else if (msg.usage) {
            handleUsage(msg);
        }
        else if (msg.daily_usage) {
            handleDailyUsage(msg);
        }
        else if (msg.functioncall) {
            handleFunctionCall(msg);
        }
        else if (msg.error) {
            handleErrorMessage(msg);
        }
        else if (msg.chunk_message) {
            handleChunkMessage(msg);
        }
        else if (msg.stop_message) {
            handleStopMessage(msg);
        }
        else if (msg.tab_description) {
            handleTabDescription(msg);
        }


        if (msg.debug1 !== undefined) {
            var debug1 = msg.debug1.replace(/\n/g, '<br>');
            var color1 = msg.color ? msg.color : 'white';
            var objDiv = document.getElementById('debugContent1');
            var isNearBottom = objDiv.scrollHeight - objDiv.clientHeight - objDiv.scrollTop <= 50;
            document.getElementById('debugContent1').innerHTML += '<p style="color:' + color1 + ';">' + debug1 + '</p>';
            if (isNearBottom) {
                objDiv.scrollTop = objDiv.scrollHeight;
            }
        }
        if (msg.debug2 !== undefined) {
            var debug2 = msg.debug2.replace(/\n/g, '<br>');
            var color2 = msg.color ? msg.color : 'white';
            var objDiv = document.getElementById('debugContent2');
            var isNearBottom = objDiv.scrollHeight - objDiv.clientHeight - objDiv.scrollTop <= 50;
            document.getElementById('debugContent2').innerHTML += '<p style="color:' + color2 + ';">' + debug2 + '</p>';
            if (isNearBottom) {
                objDiv.scrollTop = objDiv.scrollHeight;
            }
        }
    });

    // get the settings from the server
    fetch(API_URL + '/load_settings/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: user_name }),
        credentials: 'include'
    })
        .then(handleError)
        .then(data => {
            setSettings(data);
        })
        .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
        });

};

function showErrorModal(errorMessage) {
    var errorModal = document.getElementById('errorModal');
    var errorModalBody = document.getElementById('errorModal-body');
    errorModalBody.innerHTML = errorMessage;
    $('#errorModal').modal('show');
}

async function handleError(response) {
    if (!response.ok) {
        let errorMessage = '';
        const overlay = document.getElementById('overlay_msg');
        const overlayMessage = document.getElementById('overlay-message');
        overlayMessage.textContent = "Error!";
        overlay.style.display = 'none';
        switch (response.status) {
            case 400:
                const data = await response.json();
                errorMessage = data.detail;
                showErrorModal(errorMessage);
                throw new Error(`400: Bad Request - ${errorMessage}`);
            case 401:
                deleteCookies();
                // show the login modal
                $('#login-modal').modal('show');
                errorMessage = "Invalid session data. Please login again."
                var errorDiv = document.querySelector('.loginError');
                errorDiv.innerHTML = errorMessage;
                errorDiv.style.display = 'block';
                errorMessage = '';
                throw new Error('401: Unauthorized');
            case 500:
                showErrorMessage('500: Server Error');
                throw new Error('500: Server Error');
            case 503:
                showErrorMessage('503: Service Unavailable');
                throw new Error('503: Service Unavailable');
            case 504:
                showErrorMessage('504: Gateway Timeout: The server is taking too long to respond. Please try again later.');
                throw new Error('504: Gateway Timeout: The server is taking too long to respond. Please try again later.');
            default:
                showErrorMessage('An error occurred. Please try again later. (Error ' + response.status + ')');
                throw new Error('Network response was not ok: ' + response.status);
        }
    }
    return await response.json();
};

function externalMessage(msg) {
    addExternalMessage(msg);
};

async function parseMessage(msg) {
    if (typeof msg === 'string') {
        try {
            msg = JSON.parse(msg);
        } catch (e) {
            console.error('Error parsing JSON: ', e);
        }
    }
    return msg;
}

function removeSpinner() {
    var lastMessage = document.querySelector('.last-message');
    if (lastMessage) {
        lastMessage.classList.remove('last-message');
        if (lastMessage.querySelector('.spinner') != null) {
            lastMessage.querySelector('.spinner').remove();
            document.getElementById('messages').lastChild.remove();
        }
    }
}

function formatTempReceived(tempReceived) {
    var tempFormatted = tempReceived;
    var count = (tempReceived.match(/(`\s*`\s*`)|(```)/g) || []).length;
    tempReceived = tempReceived.replace(/(`\s*`\s*`)/g, '```');
    if (count > 0) {
        if (count % 2 == 0) {
            tempFormatted = marked(tempReceived);
        } else {
            tempReceived = tempReceived.replace('<div class="typing-indicator"><div class="dot"><\/div><\/div>', '');
            tempFormatted = tempReceived + '\n```';
            tempFormatted = marked(tempFormatted);
        }
    } else {
        tempFormatted = marked(tempReceived);
    }
    return tempFormatted;
}

async function handleAvatar(settings, tempReceived) {
    if (settings.avatar.avatar) {
        var textToSay = tempReceived.replace(/\n/g, "");
        var videoDuration = 0;
        var videoPromise;
        await import('./d-id/streaming-client-api.js').then(
            did => { videoPromise = did.generateVideoStream(textToSay); });

        videoDuration = await videoPromise;
        if (videoDuration > 0) {
            var numCredits = Math.ceil(videoDuration / 15.0);
            var cost = 18.0 * numCredits / 120.0;
            console.log("video stream will start soon. duration: " + videoDuration + "; d-id credits: " + numCredits + "; cost: " + cost);
            await new Promise(resolve => setTimeout(resolve, 3000));
        }
    }
}

async function handleAudio(settings, timestamp, tempFormatted, msg) {
    if (settings.audio.voice_output) {
        var chatMessage = '<br><div class="message bot last-message"><span class="timestamp">' + timestamp + '</span><div class="bubble">' + tempFormatted + '<i class="fa fa-play play-button" aria-hidden="true"></i></div>';
        document.getElementById('messages').innerHTML += chatMessage;

        var playButtons = document.querySelectorAll('.play-button');
        var playButton = playButtons[playButtons.length - 1];
        var playButtons = document.querySelectorAll('.play-button');
        var playButton = playButtons[playButtons.length - 1];
        playButton.addEventListener('click', async function () {
            this.classList.remove('fa-play');
            this.classList.add('fa-spinner');
            var audioSrc = await request_audio(this);
            var audioElement = document.createElement('audio');
            audioElement.controls = true;
            audioElement.innerHTML = `<source src="${audioSrc}" type="audio/mp3">Your browser does not support the audio element.`;
            
            var anchorTag = this.closest('.bubble').querySelector('a[data-tooltip="Play Audio"]');
            this.closest('.bubble').appendChild(audioElement);
            if (anchorTag) {
                anchorTag.remove();
            }
        });
    } else {
        var chatMessage = '<div class="message bot last-message"><span class="timestamp">' + timestamp + '</span><div class="bubble">' + tempFormatted + '</div>';
        document.getElementById('messages').innerHTML += chatMessage;
    }
}

function resetState() {
    tempReceived = '';
    tempFormatted = '';
    var lastMessage = document.querySelector('.last-message');
    if (lastMessage) {
        document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
    }
    content = '';
    canSend = true;
    canRecord = true;
    isWaiting = false;
    isRecording = false;
    canSendMessage();
    document.getElementById('message').placeholder = 'Type a message...';
}

async function onResponse(msg) {
    var timestamp = new Date().toLocaleTimeString();
    msg = await parseMessage(msg);
    removeSpinner();
    tempReceived += msg.content;
    tempFormatted = formatTempReceived(tempReceived);
    await handleAvatar(settings, tempReceived);
    await handleAudio(settings, timestamp, tempFormatted, msg);
    resetState();

    if (msg && msg.end && msg.end === 'true') {
        resetState();
    }
};