var currentActiveTab = 1;
var categoryValues;

var tempFullChunk = '';

var showDebug = false;

const modelMaxTokens = {
    'gpt-4o': 4096,
    'gpt-4o-mini': 16384,
    'gpt-4-turbo': 4096,
    'o1-mini': 65536,
    'o1-preview': 32768,
    'claude-3-5-sonnet-20240620': 8192,
    'claude-3-opus-20240229': 4096
};

// populate the settings menu
function populateSettingsMenu(settings) {
    var settingsMenu = document.getElementById("SidenavAddons");

    // Clear the settings menu
    while (settingsMenu.firstChild) {
        settingsMenu.firstChild.remove();
    }

    var tabs = [
        { name: 'General', icon: 'fas fa-cog' },
        { name: 'Chat', icon: 'fas fa-comments' },
        { name: 'Addons', icon: 'fas fa-puzzle-piece' },
        { name: 'Audio', icon: 'fas fa-volume-up' },
        { name: 'User Data', icon: 'fas fa-user' },
        { name: 'Memory', icon: 'fas fa-memory' }
    ];
    var tabNav = createTabNav(tabs);
    settingsMenu.appendChild(tabNav);

    settingsMenu.appendChild(createGeneralSettingsTabContent(settings, 'tab1'));
    settingsMenu.appendChild(createChatSettingsTabContent(settings, 'tab2'));
    settingsMenu.appendChild(createAddonsTabContent(settings.addons, 'tab3'));
    settingsMenu.appendChild(createAudioTabContent(settings.audio, 'tab4', settings.available_models));
    settingsMenu.appendChild(createUserDataTabContent('tab5'));
    settingsMenu.appendChild(createMemoryTabContent('tab6'));

    var maxRange = settings.memory.max_tokens;
    var minRange = settings.memory.min_tokens;
    max_message_tokens = settings.memory.input;
    updateCounterDiv(0, 0, max_message_tokens, 0);

    var slider = document.getElementById('slider');

    var startValues = [
        settings.memory.functions,
        settings.memory.functions + settings.memory.ltm1,
        settings.memory.functions + settings.memory.ltm1 + settings.memory.ltm2,
        settings.memory.functions + settings.memory.ltm1 + settings.memory.ltm2 + settings.memory.episodic,
        settings.memory.functions + settings.memory.ltm1 + settings.memory.ltm2 + settings.memory.episodic + settings.memory.recent,
        settings.memory.functions + settings.memory.ltm1 + settings.memory.ltm2 + settings.memory.episodic + settings.memory.recent + settings.memory.notes,
        settings.memory.functions + settings.memory.ltm1 + settings.memory.ltm2 + settings.memory.episodic + settings.memory.recent + settings.memory.notes + settings.memory.input,
        maxRange
    ];

    // Convert the start values to percentages
    var startPercentages = startValues.map(value => value / maxRange);

    if (slider && slider.noUiSlider) {
        slider.noUiSlider.set(startPercentages);
    }

    var categories = document.getElementsByClassName('category');
    for (var i = 0; i < categories.length; i++) {
        categories[i].style.pointerEvents = "none";
    }

    switchTab(currentActiveTab); // make the first tab active by default
}

function createTabNav(tabs) {
    var tabNav = document.createElement('ul');
    tabNav.className = 'nav nav-tabs';

    tabs.forEach((tab, index) => {
        var tabLink = document.createElement('a');
        tabLink.href = '#';
        tabLink.innerHTML = `<i class="${tab.icon}"></i> ${tab.name}`;
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
    h3.innerHTML = '<i class="fas fa-puzzle-piece"></i> Addons';
    tabContent.appendChild(h3);
    // todo: don't hardcode the addon descriptions
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
            description: 'Run python code (dockerized)'
        },
        {
            name: 'visit_website',
            description: 'Visit a website (simple requests only)'
        },
        {
            name: 'generate_image',
            description: 'Generate an image with Dalle 3'
        },
        {
            name: 'get_image_descriptions',
            description: 'Get descriptions of uploaded images using OpenAI GPT-4o'
        },
        {
            name: 'calendar_addon',
            description: 'Google Calendar integration to add/edit/delete events'
        },
        {
            name: 'gmail_addon',
            description: 'Gmail Integration to read/write/delete emails'
        },
        {
            name: 'google_search',
            description: 'Search the web with Google (needs API key) or DuckDuckGo as a fallback'
        },
        {
            name: 'chain_of_thought_addon',
            description: 'This addon implements a chain of thought process for executing complex tasks. It generates a plan, executes it step by step, and can use other enabled addons to complete the task.'
        },
        {
            name: 'search_visual_history',
            description: 'Search in your visual history (Charlie Recall) for screenshots and their descriptions. The results are semantic similar results.'
        }
    ];

    for (let addon in addons) {
        if (addons.hasOwnProperty(addon)) {
            var status = addons[addon] ? '<i class="fas fa-check-square"></i>' : '<i class="fas fa-square-full"></i>';
            var menuItem = document.createElement('a');
            menuItem.href = "#";
            var addonDescription = addon_descriptions.find(x => x.name === addon) || { description: 'No description available' };
            menuItem.innerHTML = addon + ": " + status + "<br/>" + addonDescription.description;
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

function createAudioTabContent(audio, tabId, availableModels) {
    var tabContent = document.createElement('div');
    tabContent.id = tabId;
    tabContent.className = 'tab-content';

    var h3 = document.createElement('h3');
    h3.innerHTML = '<i class="fas fa-volume-up"></i> Audio';
    tabContent.appendChild(h3);

    const hasOpenAIModel = availableModels.some(model => model.includes('gpt'));

    if (!hasOpenAIModel) {
        // Display message when no OpenAI API key is available
        var messageDiv = document.createElement('div');
        messageDiv.className = 'audio-settings-message';
        messageDiv.textContent = 'An OpenAI API key is required for Text-to-Speech and Speech-to-Text functions.';
        tabContent.appendChild(messageDiv);
    } else {
        // Create checkboxes for audio settings when OpenAI API key is available
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
    }

    return tabContent;
}

function createGeneralSettingsTabContent(settings, tabId) {
    var tabContent = document.createElement('div');
    tabContent.id = tabId;
    tabContent.className = 'tab-content'

    // Populate language settings
    h3 = document.createElement('h3');
    h3.innerHTML = '<i class="fas fa-language"></i> Language';
    tabContent.appendChild(h3);

    var languageItem = document.createElement('select');
    languageItem.id = 'language';
    languageItem.name = 'language';
    var option1 = document.createElement('option');
    option1.value = 'en';
    option1.text = 'English';
    languageItem.appendChild(option1);
    languageItem.value = settings.language.language;
    languageItem.onchange = function (e) {
        edit_status('language', 'language', e.target.value);
    }
    tabContent.appendChild(languageItem);

    // Populate Display Name settings
    h3 = document.createElement('h3');
    h3.innerHTML = '<i class="fas fa-user"></i> Display Name';
    tabContent.appendChild(h3);

    var displayNameItem = document.createElement('textarea');
    displayNameItem.id = 'display_name';
    displayNameItem.name = 'display_name';
    displayNameItem.value = settings.display_name;
    displayNameItem.onchange = function (e) {
        edit_status('db', 'display_name', e.target.value);
    }
    tabContent.appendChild(displayNameItem);

    // Populate timezone settings
    h3 = document.createElement('h3');
    h3.innerHTML = '<i class="fas fa-globe"></i> Timezone';
    tabContent.appendChild(h3);

    var timezoneItem = document.createElement('select');
    timezoneItem.id = 'timezone';
    timezoneItem.name = 'timezone';
    var timezones = [
        'Auto',
        'UTC-12',
        'UTC-11',
        'UTC-10',
        'UTC-9',
        'UTC-8',
        'UTC-7',
        'UTC-6',
        'UTC-5',
        'UTC-4',
        'UTC-3',
        'UTC-2',
        'UTC-1',
        'UTC',
        'UTC+1',
        'UTC+2',
        'UTC+3',
        'UTC+4',
        'UTC+5',
        'UTC+6',
        'UTC+7',
        'UTC+8',
        'UTC+9',
        'UTC+10',
        'UTC+11',
        'UTC+12',
    ];
    timezones.forEach(function (timezone) {
        var option = document.createElement('option');
        option.value = timezone;
        option.text = timezone;
        timezoneItem.appendChild(option);
    });

    // Detect user's timezone if settings.timezone.timezone is set to "auto"
    if (settings.timezone && settings.timezone.timezone === 'auto') {
        var userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        var utcOffset = new Date().getTimezoneOffset() / -60;
        var utcOffsetString = 'UTC' + (utcOffset >= 0 ? '+' : '') + utcOffset;
        timezoneItem.value = utcOffsetString;
    } else {
        timezoneItem.value = settings.timezone ? settings.timezone.timezone : 'UTC';
    }

    timezoneItem.onchange = function (e) {
        if (e.target.value === 'Auto') {
            var userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            var utcOffset = new Date().getTimezoneOffset() / -60;
            var utcOffsetString = 'UTC' + (utcOffset >= 0 ? '+' : '') + utcOffset;
            edit_status('timezone', 'timezone', utcOffsetString);
        } else {
            edit_status('timezone', 'timezone', e.target.value);
        }
    }
    tabContent.appendChild(timezoneItem);

    // add slider for chat Spacing
    h3 = document.createElement('h3');
    h3.innerHTML = '<i class="fas fa-arrows-alt-h"></i> Chat Spacing';
    tabContent.appendChild(h3);

    var chatPaddingItem = document.createElement('input');
    chatPaddingItem.type = 'range';
    chatPaddingItem.min = 5;
    chatPaddingItem.max = 25;
    chatPaddingItem.step = 1;
    // get the current chat padding from local storage
    var chatPadding = localStorage.getItem('chatPadding') || 10;
    chatPaddingItem.value = chatPadding;
    chatPaddingItem.oninput = function (e) {
        set_chat_padding(e.target.value);
    }
    tabContent.appendChild(chatPaddingItem);

    return tabContent;
}

function createChatSettingsTabContent(settings, tabId) {
    var tabContent = document.createElement('div');
    tabContent.id = tabId;
    tabContent.className = 'tab-content';

    // Populate System Prompt settings
    var h3 = document.createElement('h3');
    h3.innerHTML = '<i class="fas fa-cogs"></i> System Prompt';
    tabContent.appendChild(h3);

    var systemPromptContainer = document.createElement('div');
    systemPromptContainer.id = 'system-prompt-container';

    var systemPromptSwitch = document.createElement('div');
    systemPromptSwitch.className = 'form-check form-switch';
    var systemPromptSwitchInput = document.createElement('input');
    systemPromptSwitchInput.className = 'form-check-input';
    systemPromptSwitchInput.type = 'checkbox';
    systemPromptSwitchInput.id = 'system-prompt-switch';
    systemPromptSwitch.appendChild(systemPromptSwitchInput);
    var systemPromptSwitchLabel = document.createElement('label');
    systemPromptSwitchLabel.className = 'form-check-label';
    systemPromptSwitchLabel.htmlFor = 'system-prompt-switch';
    systemPromptSwitchLabel.textContent = 'Enable System Prompt';
    systemPromptSwitch.appendChild(systemPromptSwitchLabel);
    systemPromptContainer.appendChild(systemPromptSwitch);

    var systemPromptDropdown = document.createElement('select');
    systemPromptDropdown.id = 'system-prompt-dropdown';
    systemPromptDropdown.className = 'form-select';
    var option1 = document.createElement('option');
    option1.value = 'None';
    option1.text = 'None';
    systemPromptDropdown.appendChild(option1);
    var option2 = document.createElement('option');
    option2.value = 'stoic';
    option2.text = 'Stoic';
    systemPromptDropdown.appendChild(option2);
    var option3 = document.createElement('option');
    option3.value = 'custom';
    option3.text = 'Custom';
    systemPromptDropdown.appendChild(option3);
    systemPromptContainer.appendChild(systemPromptDropdown);

    var systemPromptTextarea = document.createElement('textarea');
    systemPromptTextarea.id = 'system-prompt-textarea';
    systemPromptTextarea.className = 'form-control';
    systemPromptTextarea.rows = 4;
    systemPromptTextarea.maxLength = 1000;
    systemPromptTextarea.style.display = 'none';
    systemPromptContainer.appendChild(systemPromptTextarea);

    tabContent.appendChild(systemPromptContainer);

    // Set initial values based on settings
    if (settings.system_prompt && settings.system_prompt.system_prompt !== 'None') {
        systemPromptSwitchInput.checked = true;
        systemPromptDropdown.value = settings.system_prompt.system_prompt;
        if (settings.system_prompt.system_prompt === 'custom') {
            systemPromptTextarea.value = settings.system_prompt.custom_prompt;
            systemPromptTextarea.style.display = 'block';
        }
    }

    // Event listeners
    systemPromptSwitchInput.onchange = function () {
        if (this.checked) {
            systemPromptDropdown.disabled = false;
            if (systemPromptDropdown.value === 'custom') {
                systemPromptTextarea.style.display = 'block';
            }
        } else {
            systemPromptDropdown.disabled = true;
            systemPromptTextarea.style.display = 'none';
            edit_status('system_prompt', 'system_prompt', 'None');
        }
    };

    systemPromptDropdown.onchange = function () {
        if (this.value === 'custom') {
            systemPromptTextarea.style.display = 'block';
        } else {
            systemPromptTextarea.style.display = 'none';
            edit_status('system_prompt', 'system_prompt', this.value);
        }
    };

    systemPromptTextarea.onchange = function () {
        if (this.value.trim() !== '') {
            edit_status('system_prompt', 'system_prompt', this.value);
        }
    };

    // Other settings
    h3 = document.createElement('h3');
    h3.innerHTML = '<i class="fas fa-sliders-h"></i> Other settings';
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

    // Populate chat model choice settings
    h3 = document.createElement('h3');
    h3.innerHTML = '<i class="fas fa-robot"></i> Chat Model';
    tabContent.appendChild(h3);
    var chatModelItem = document.createElement('select');
    chatModelItem.id = 'chatModel';
    chatModelItem.name = 'chatModel';
    
    if (settings.available_models) {
        settings.available_models.forEach(function (chatModel) {
            var option = document.createElement('option');
            option.value = chatModel;
            option.text = `${chatModel} (Max ${modelMaxTokens[chatModel]} tokens)`;
            chatModelItem.appendChild(option);
        });
    }
    
    chatModelItem.value = settings.active_model.active_model;
    chatModelItem.onchange = function (e) {
        updateModelAndTokens(e.target.value);
    }

    tabContent.appendChild(chatModelItem);

    return tabContent;
}
 
 function updateModelAndTokens(newModel) {
    if (newModel === settings.active_model.active_model) {
        return; // No change, exit early
    }

    const newModelMaxTokens = modelMaxTokens[newModel];
    const currentSettings = settings.memory;
    const currentOutput = currentSettings.output;

    // Set the new output to the minimum of the new model's max tokens and the current max_tokens
    const newOutput = Math.min(newModelMaxTokens, currentSettings.max_tokens);

    // Calculate the scaling factor for non-output tokens
    const nonOutputTokens = currentSettings.max_tokens - currentOutput;
    const remainingTokens = currentSettings.max_tokens - newOutput;
    const scalingFactor = remainingTokens / nonOutputTokens;

    // Calculate new values while maintaining proportions for non-output tokens
    let newSettings = {
        functions: Math.round(currentSettings.functions * scalingFactor),
        ltm1: Math.round(currentSettings.ltm1 * scalingFactor),
        ltm2: Math.round(currentSettings.ltm2 * scalingFactor),
        episodic: Math.round(currentSettings.episodic * scalingFactor),
        recent: Math.round(currentSettings.recent * scalingFactor),
        notes: Math.round(currentSettings.notes * scalingFactor),
        input: Math.round(currentSettings.input * scalingFactor),
        output: newOutput,
        max_tokens: currentSettings.max_tokens, // Keep the original max_tokens
        min_tokens: currentSettings.min_tokens
    };

    // Ensure the sum of all values (except max_tokens and min_tokens) equals the original max_tokens
    let totalTokens = Object.values(newSettings).reduce((sum, value) => sum + value, 0) - newSettings.max_tokens - newSettings.min_tokens;
    
    if (totalTokens !== currentSettings.max_tokens) {
        const difference = currentSettings.max_tokens - totalTokens;
        newSettings.input += difference; // Adjust the input to make up the difference
    }

    // Ensure no value is negative
    for (let key in newSettings) {
        if (key !== 'max_tokens' && key !== 'min_tokens') {
            newSettings[key] = Math.max(0, newSettings[key]);
        }
    }

    // Update the settings
    settings.memory = newSettings;

    // Update the slider
    updateMemorySlider(newSettings);

    // Save the new configuration
    saveMemoryConfiguration(newSettings);

    // Update the model in settings
    settings.active_model.active_model = newModel;
    edit_status('active_model', 'active_model', newModel);

    // Show notification
    showNotification(`Model changed to ${newModel}. Memory configuration adjusted accordingly.`, 'info');
}

function updateMemorySlider(memorySettings) {
    const slider = document.getElementById('slider');
    if (slider && slider.noUiSlider) {
        const maxTokens = memorySettings.max_tokens;
        const values = [
            memorySettings.functions / maxTokens,
            (memorySettings.functions + memorySettings.ltm1) / maxTokens,
            (memorySettings.functions + memorySettings.ltm1 + memorySettings.ltm2) / maxTokens,
            (memorySettings.functions + memorySettings.ltm1 + memorySettings.ltm2 + memorySettings.episodic) / maxTokens,
            (memorySettings.functions + memorySettings.ltm1 + memorySettings.ltm2 + memorySettings.episodic + memorySettings.recent) / maxTokens,
            (memorySettings.functions + memorySettings.ltm1 + memorySettings.ltm2 + memorySettings.episodic + memorySettings.recent + memorySettings.notes) / maxTokens,
            (memorySettings.functions + memorySettings.ltm1 + memorySettings.ltm2 + memorySettings.episodic + memorySettings.recent + memorySettings.notes + memorySettings.input) / maxTokens,
            1
        ];
        
        // Set the slider values without triggering the 'update' event
        slider.noUiSlider.set(values, false);
    }

    // Update the displayed values
    updateDisplayedValuesM(memorySettings);
}

function updateDisplayedValuesM(memorySettings) {
    var maxTokens = memorySettings.max_tokens;
    var categories = ['Functions', 'LTM 1', 'LTM 2', 'Episodic Memory', 'Recent Messages', 'Notes', 'Input', 'Output'];
    var values = [
        memorySettings.functions,
        memorySettings.ltm1,
        memorySettings.ltm2,
        memorySettings.episodic,
        memorySettings.recent,
        memorySettings.notes,
        memorySettings.input,
        memorySettings.output
    ];

    categories.forEach((cat, index) => {
        var spanId = `value-${cat.toLowerCase().replace(' ', '')}`;
        var span = document.getElementById(spanId);
        if (span) {
            var percentage = (values[index] / maxTokens) * 100;
            span.textContent = `${percentage.toFixed(2)}% (${values[index]})`;
        }
    });
}

function saveMemoryConfiguration(memorySettings) {
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
        updateDisplayedValuesM(data.memory);
    })
    .catch(console.error);
}

function createUserDataTabContent(tabId) {
    var tabContent = document.createElement('div');
    tabContent.id = tabId;
    tabContent.className = 'tab-content';

    var h3 = document.createElement('h3');
    h3.innerHTML = '<i class="fas fa-user-cog"></i> User Data';
    tabContent.appendChild(h3);

    var saveDataBtn = document.createElement('button');
    saveDataBtn.id = 'saveDataBtn';
    saveDataBtn.innerHTML = '<i class="fas fa-save"></i> Save Data';
    tabContent.appendChild(saveDataBtn);

    var deleteDataBtn = document.createElement('button');
    deleteDataBtn.id = 'deleteDataBtn';
    deleteDataBtn.innerHTML = '<i class="fas fa-trash-alt"></i> Delete Data';
    tabContent.appendChild(deleteDataBtn);

    var uploadDataInput = document.createElement('input');
    uploadDataInput.type = 'file';
    uploadDataInput.id = 'uploadDataInput';
    tabContent.appendChild(uploadDataInput);

    var uploadDataBtn = document.createElement('button');
    uploadDataBtn.id = 'uploadDataBtn';
    uploadDataBtn.innerHTML = '<i class="fas fa-upload"></i> Upload Data';
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
    h3.innerHTML = '<i class="fas fa-memory"></i> Memory Configuration';
    tabContent.appendChild(h3);

    var maxTokensLabel = document.createElement('label');
    maxTokensLabel.textContent = 'Max Total Tokens: ';
    tabContent.appendChild(maxTokensLabel);

    var maxTokensDropdown = document.createElement('select');
    maxTokensDropdown.id = 'max-tokens-dropdown';
    var presetValues = [8000, 16000, 32000, 64000, 128000];
    presetValues.forEach(value => {
        var option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        maxTokensDropdown.appendChild(option);
    });
    maxTokensDropdown.value = settings.memory.max_tokens;
    tabContent.appendChild(maxTokensDropdown);

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
        var span = document.createElement('span');
        span.id = `value-${cat.toLowerCase().replace(' ', '')}`;
        p.innerHTML = `${cat}: `;
        p.appendChild(span);
        values.appendChild(p);
    });

    container.appendChild(values);
    tabContent.appendChild(container);

    var resetButton = document.createElement('button');
    resetButton.innerHTML = '<i class="fas fa-undo"></i> Reset to Default';
    resetButton.onclick = function () {
        var maxTokens = parseInt("128000");
        maxTokensDropdown.value = maxTokens;
        var defaultValues = [0.050, 0.070, 0.090, 0.110, 0.130, 0.150, 0.970, 1.000];
        slider.noUiSlider.set(defaultValues);
    };
    tabContent.appendChild(resetButton);

    var saveButton = document.createElement('button');
    saveButton.innerHTML = '<i class="fas fa-save"></i> Save Memory Configuration';
    saveButton.onclick = saveMemoryConfigurationSlider;
    tabContent.appendChild(saveButton);

    noUiSlider.create(slider, {
        start: [0.050, 0.070, 0.090, 0.110, 0.130, 0.150, 0.970, 1.000],
        connect: true,
        range: {
            'min': 0.000,
            'max': 1.000
        },
        format: {
            to: (v) => parseFloat(v).toFixed(4),
            from: (v) => parseFloat(v).toFixed(4)
        }
    });

    var updateDisplayedValues = function () {
        var maxTokens = parseInt(maxTokensDropdown.value);
        var values = slider.noUiSlider.get();
        var values = values.map(Number);
        categoryValues = values.map(function (value, index, array) {
            return index === 0 ? value * 100 : (value - array[index - 1]) * 100;
        });
        var percentages = categoryValues.map(value => value / 100);
        var tokenValues = percentages.map(percentage => Math.round(percentage * maxTokens));

        categories.forEach((cat, index) => {
            var spanId = `value-${cat.toLowerCase().replace(' ', '')}`;
            var span = document.getElementById(spanId);
            if (span) {
                span.textContent = `${(percentages[index] * 100).toFixed(3)}% (${tokenValues[index]})`;
            }
        });
    };

    slider.noUiSlider.on('update', updateDisplayedValues);
    maxTokensDropdown.addEventListener('change', updateDisplayedValues);

    updateDisplayedValues();

    return tabContent;
}

function saveMemoryConfigurationSlider() {
    const overlay = document.getElementById('overlay_msg');
    const overlayMessage = document.getElementById('overlay-message');
    overlayMessage.textContent = "Updating Settings...";
    overlay.style.display = 'flex';

    var maxTokensDropdown = document.getElementById('max-tokens-dropdown');
    var maxTokens = parseInt(maxTokensDropdown.value);

    var values = slider.noUiSlider.get();
    var tokenValues = values.map(value => Math.round(value * maxTokens));

    var memorySettings = {
        functions: tokenValues[0],
        ltm1: tokenValues[1] - tokenValues[0],
        ltm2: tokenValues[2] - tokenValues[1],
        episodic: tokenValues[3] - tokenValues[2],
        recent: tokenValues[4] - tokenValues[3],
        notes: tokenValues[5] - tokenValues[4],
        input: tokenValues[6] - tokenValues[5],
        output: maxTokens - tokenValues[6],
        max_tokens: maxTokens
    };
    max_message_tokens = memorySettings.input;
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

    let requestBody;
    if (typeof value === 'object') {
        requestBody = JSON.stringify({ category: category, setting: setting, value: JSON.stringify(value), username: user_name });
    } else {
        requestBody = JSON.stringify({ category: category, setting: setting, value: value, username: user_name });
    }

    fetch(API_URL + '/update_settings/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: requestBody,
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

function updateModelDropdown(availableModels, currentModel) {
    const chatModelItem = document.getElementById('chatModel');
    if (!chatModelItem) {
        console.warn("Chat model dropdown not found in the DOM");
        return;
    }

    chatModelItem.innerHTML = ''; // Clear existing options

    availableModels.forEach(function (chatModel) {
        var option = document.createElement('option');
        option.value = chatModel;
        option.text = `${chatModel} (Max ${modelMaxTokens[chatModel]} tokens)`;
        chatModelItem.appendChild(option);
    });

    // Set the current model without triggering the onchange event
    if (availableModels.includes(currentModel)) {
        chatModelItem.value = currentModel;
    } else if (availableModels.length > 0) {
        chatModelItem.value = availableModels[0];
    }
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

        // Update the memory settings
        if (newSettings.memory) {
            settings.memory = newSettings.memory;
            updateMemorySlider(newSettings.memory);
        }

        populateSettingsMenu(settings);
        handleAudioSettings(newSettings);

        if (newSettings.usage != "" && newSettings.usage != null) {
            handleUsage(newSettings);
        }
        if (newSettings.daily_usage != "" && newSettings.daily_usage != null) {
            handleDailyUsage(newSettings);
        }

        // Store available models
        if (newSettings.available_models && Array.isArray(newSettings.available_models)) {
            settings.available_models = newSettings.available_models;
        }

        // Update the system prompt settings
        if (newSettings.system_prompt) {
            var systemPromptSwitch = document.getElementById('system-prompt-switch');
            var systemPromptDropdown = document.getElementById('system-prompt-dropdown');
            var systemPromptTextarea = document.getElementById('system-prompt-textarea');

            if (systemPromptSwitch && systemPromptDropdown && systemPromptTextarea) {
                if (newSettings.system_prompt.system_prompt === 'None') {
                    systemPromptSwitch.checked = false;
                    systemPromptDropdown.disabled = true;
                    systemPromptTextarea.style.display = 'none';
                } else {
                    systemPromptSwitch.checked = true;
                    systemPromptDropdown.disabled = false;

                    if (newSettings.system_prompt.system_prompt === 'stoic') {
                        systemPromptDropdown.value = 'stoic';
                        systemPromptTextarea.style.display = 'none';
                    } else {
                        systemPromptDropdown.value = 'custom';
                        systemPromptTextarea.value = newSettings.system_prompt.system_prompt;
                        systemPromptTextarea.style.display = 'block';
                    }
                }
            }
        }
        // Check if the timezone setting is not defined or set to "auto"
        if (!newSettings.timezone || newSettings.timezone.timezone.toLowerCase() === 'auto') {
            // Detect the user's timezone
            var userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            var utcOffset = new Date().getTimezoneOffset() / -60;
            var utcOffsetString = 'UTC' + (utcOffset >= 0 ? '+' : '') + utcOffset;

            // Update the timezone setting
            newSettings.timezone = {
                timezone: utcOffsetString
            };

            // Save the updated settings
            edit_status('timezone', 'timezone', utcOffsetString);
        }
    }
    // check if there is a google auth uri in the settings
    if (settings.auth_uri) {
        // if there is, show the google auth modal
        showGoogleAuthModal(settings.auth_uri);
    }
    applyTooltips('[data-tooltip]');
}

function showGoogleAuthModal(auth_uri) {
    var googleAuthModal = document.getElementById('googleAuthModal');
    var googleAuthLink = document.getElementById('googleAuthLink');
    googleAuthLink.href = auth_uri;
    $(googleAuthModal).modal('show');
}

function handleAudioSettings(newSettings) {
    const hasOpenAIModel = newSettings.available_models.some(model => model.includes('gpt'));

    // Handle voice input settings
    if (newSettings.audio.voice_input && hasOpenAIModel) {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function (stream) {
                $('#record').show();
            })
            .catch(function (err) {
                edit_status('audio', 'voice_input', false);
                $('#record').hide();
                handleMicrophoneErrors(err);
            });
    } else {
        $('#record').hide();
    }

    // Handle voice output settings
    if (newSettings.audio.voice_output && hasOpenAIModel) {
        addPlayButtonsToMessages();
    } else {
        removePlayButtonsAndAudioFromMessages();
    }
}

function handleMicrophoneErrors(err) {
    if (err.name === 'NotAllowedError') {
        showErrorModal('Permission to access microphone was denied. Please allow access to the microphone and try again.');
    } else if (err.name === 'NotFoundError') {
        showErrorModal('No microphone was found. Ensure that a microphone is installed and that microphone settings are configured correctly.');
    } else {
        showErrorModal('Error occurred : ' + err.name);
    }
}

function addPlayButtonsToMessages() {
    var playButtonCode = '<div class="play-button-wrapper"><a href="#" data-tooltip="Play Audio"><i class="fas fa-play play-button"></i></a></div>';
    // Add play buttons to all messages' bottom buttons
    var messages = document.querySelectorAll('.message');
    for (var i = 0; i < messages.length; i++) {
        var message = messages[i];
        var bottomButtons = message.querySelector('.bottom-buttons-container');
        // check if the message already has a play button
        if (bottomButtons && !bottomButtons.querySelector('.play-button-wrapper')) {
            bottomButtons.insertAdjacentHTML('afterbegin', playButtonCode);
        }
    }

    // Add event listeners to the play buttons
    var playButtons = document.querySelectorAll('.play-button');
    playButtons.forEach(playButton => {
        playButton.addEventListener('click', event => {
            playButtonHandler(event.target); // `event.target` is the clicked playButton
        });
    });
}

function removePlayButtonsAndAudioFromMessages() {
    // Remove play buttons from all messages' bottom buttons
    var playButtons = document.querySelectorAll('.play-button-wrapper');
    for (var i = 0; i < playButtons.length; i++) {
        playButtons[i].remove();
    }

    // Remove audio elements from all messages
    var audioElements = document.querySelectorAll('audio');
    for (var i = 0; i < audioElements.length; i++) {
        audioElements[i].remove();
    }
}


function showMessage(message, type, instant) {
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
            <div class="message ${type}">
                <span class="timestamp">${timestamp}</span>
                <div class="bubble">
                    ${message}
                </div>
            </div>
        `;
    } else {
        if (type === 'error') {
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
        } else {
            chatMessage.innerHTML = `
                <div class="message ${type}">
                    <span class="timestamp">${timestamp}</span>
                    <div class="bubble">
                        ${message}
                    </div>
                </div>
            `;
        }
    }
    document.getElementById('messages').appendChild(chatMessage);

    // enable the send and record button again
    canSend = true;
    canRecord = true;
    isWaiting = false;
    isRecording = false;
    canSendMessage();
    document.getElementById('message').placeholder = 'Type a message...';
    // Auto-scroll to the bottom of the chat
    setTimeout(() => scrollToBottom(), 10);
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

    let debugMessage = document.createElement('p');
    debugMessage.style.color = color;
    debugMessage.innerHTML = message;
    objDiv.appendChild(debugMessage);

    setTimeout(() => scrollToBottom(), 10);
}

function handleUsage(msg) {
    // update the userStats with the new usage
    var userStats = document.getElementById('userStats');
    userStats.innerHTML = '';
    userStats.innerHTML += '<p>Lifetime: Tokens: ' + msg.usage.total_tokens + ', cost: $' + msg.usage.total_cost + '</p>';

}

function handleAudioCost(msg) {
    // update the userStats with the new usage
    var userStats = document.getElementById('userStats');
    userStats.innerHTML = '';
    // add the audio cost to the total cost
    var totalCost = parseFloat(msg.audio_cost.total_cost) + parseFloat(msg.audio_cost.audio_cost);
    userStats.innerHTML += '<p>Lifetime: Tokens: ' + msg.audio_cost.total_tokens + ', cost: $' + totalCost.toFixed(5) + '</p>';

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
    setTimeout(() => scrollToBottom(), 10);
    content = '';
    tempReceived = '';
    tempFormatted = '';
}

function handleFunctionCall(msg) {
    const timestamp = new Date().toLocaleTimeString();
    const addon = msg.message.function;
    try {
        const argsStr = typeof msg.message.arguments === 'string' ? msg.message.arguments : JSON.stringify(msg.message.arguments);
        const args = parseComplexJson(argsStr);

        const callDetails = {
            "Function": addon,
            "Arguments": args
        };

        updateOrCreateDebugBubble("Function Call", timestamp, callDetails);
    } catch (error) {
        console.error('Error parsing JSON:', error);
    }
}

function handleFunctionResponse(msg) {
    const timestamp = new Date().toLocaleTimeString();
    const content = { "Response": msg.message };

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
    // add the chat-tab-dots class to the tab button
    var dots = document.createElement('div');
    dots.className = 'chat-tab-dots';
    dots.innerHTML = '&nbsp;&#x22EE;&nbsp;';
    dots.onclick = function (event) {
        event.stopPropagation();
        showDropdown(this, tabId);
    };

    // Append the dots to the new tab
    tabButton.appendChild(dots);
}

async function handleCancelMessage(msg) {
    var target_chat_id = msg.chat_id;
    // check if the current active tab is the same as the target chat id
    var chatTabs = document.getElementById('chat-tabs-container');
    var activeTab = chatTabs.querySelector('.active');
    var current_chat_id = activeTab.id.replace('chat-tab-', '');
    if (current_chat_id != target_chat_id) {
        // if not, do nothing
        resetState();
        return;
    }
    var lastMessage = document.querySelector('.last-message .bubble');
    if (lastMessage) {
        // Remove the typing indicator
        removeTypingIndicator();

        // Appending the new chunk to the existing content of the last message
        lastMessage.innerHTML = parseAndFormatMessage(tempFullChunk);
    }

    // Function to remove the typing indicator
    function removeTypingIndicator() {
        var typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    tempFullChunk = '';
    resetState();
}

function addBottomButtons(div, model) {
    var buttonsContainer = document.createElement('div');
    buttonsContainer.className = 'bottom-buttons-container';
    
    // check if the settings exist
    if (!settings) {
        return;
    }

    const hasOpenAIModel = settings.available_models.some(model => model.includes('gpt'));

    // Check the settings to see if we need to add the audio play button
    if (settings.audio.voice_output && hasOpenAIModel) {
        var playButtonWrapper = document.createElement('div');
        playButtonWrapper.className = 'play-button-wrapper';
        var playButtonLink = document.createElement('a');
        playButtonLink.href = '#';
        playButtonLink.setAttribute('data-tooltip', 'Play Audio');
        var playButton = document.createElement('i');
        playButton.className = 'fas fa-play play-button';
        playButton.title = 'Play';
        playButton.onclick = function () {
            playButtonHandler(playButton);
        };

        playButtonLink.appendChild(playButton);
        playButtonWrapper.appendChild(playButtonLink);
        buttonsContainer.appendChild(playButtonWrapper);
    }

    if (showDebug === true) {
        console.log(settings);
    }

    // Create a copy button with the same structure and styling as the play button
    var copyButtonWrapper = document.createElement('div');
    copyButtonWrapper.className = 'copy-button-wrapper';
    var copyButtonLink = document.createElement('a');
    copyButtonLink.href = '#';
    copyButtonLink.setAttribute('data-tooltip', 'Copy to clipboard');
    var copyButton = document.createElement('i');
    copyButton.className = 'fas fa-copy copy-button';
    copyButton.title = 'Copy';
    copyButton.onclick = function () {
        copyToClipboard(div);
    };

    copyButtonLink.appendChild(copyButton);
    copyButtonWrapper.appendChild(copyButtonLink);

    // Create a model indicator button
    var modelButtonWrapper = document.createElement('div');
    modelButtonWrapper.className = 'model-button-wrapper';
    var modelButtonLink = document.createElement('a');
    modelButtonLink.href = '#';
    var modelTooltip = model ? model : 'Unknown Model';
    modelButtonLink.setAttribute('data-tooltip', modelTooltip);
    var modelButton = document.createElement('i');
    
    if (model) {
        // Set icon based on the model
        if (model.toLowerCase().includes('gpt')) {
            modelButton.className = 'fas fa-robot model-button';
        } else if (model.toLowerCase().includes('claude')) {
            modelButton.className = 'fas fa-brain model-button';
        } else {
            modelButton.className = 'fas fa-microchip model-button';
        }
    } else {
        modelButton.className = 'fas fa-question model-button';
    }

    modelButtonLink.appendChild(modelButton);
    modelButtonWrapper.appendChild(modelButtonLink);

    // // Create a regenerate button with the same structure and styling as the play button
    // var regenerateButtonWrapper = document.createElement('div');
    // regenerateButtonWrapper.className = 'regen-button-wrapper';
    // var regenerateButtonLink = document.createElement('a');
    // regenerateButtonLink.href = '#';
    // regenerateButtonLink.setAttribute('data-tooltip', 'Regenerate');
    // var regenerateButton = document.createElement('i');
    // regenerateButton.className = 'fas fa-redo-alt regen-button';
    // regenerateButton.title = 'Regenerate';
    // regenerateButton.onclick = function() {
    //     regenerateResponse(div);
    // };

    // regenerateButtonLink.appendChild(regenerateButton);
    // regenerateButtonWrapper.appendChild(regenerateButtonLink);

    // Append the button wrappers to the container
    buttonsContainer.appendChild(copyButtonWrapper);
    buttonsContainer.appendChild(modelButtonWrapper);
    // buttonsContainer.appendChild(regenerateButtonWrapper);

    // Append the buttons container to the div
    div.appendChild(buttonsContainer);
}

function handleStopMessage(msg) {
    resetDebugBubble();
    var target_chat_id = msg.chat_id;
    var chatTabs = document.getElementById('chat-tabs-container');
    var activeTab = chatTabs.querySelector('.active');
    var current_chat_id = activeTab.id.replace('chat-tab-', '');
    
    if (current_chat_id != target_chat_id) {
        resetState();
        return;
    }

    if (currentMessageBubble) {
        const bubbleContent = currentMessageBubble.querySelector('.bubble');
        bubbleContent.innerHTML = parseAndFormatMessage(tempFullChunk);
        highlightCodeBlocks(bubbleContent);
        addBottomButtons(bubbleContent, msg.model);
    }

    // Remove any remaining spinners
    const spinners = document.querySelectorAll('.spinner');
    spinners.forEach(spinner => {
        const messageDiv = spinner.closest('.message');
        if (messageDiv) {
            messageDiv.remove();
        }
    });

    tempFullChunk = '';
    currentMessageBubble = null;
    applyTooltips('[data-tooltip]');
    resetState();
    setTimeout(() => scrollToBottom(), 50);
}

let codeBlockOpen = false;
let executeCodeOpen = false;
let currentLanguage = '';

function addMessageBubble(content, type = 'bot', model = '') {
    const timestamp = new Date().toLocaleTimeString();
    const messagesContainer = document.getElementById('messages');
    
    // Remove any existing spinner
    const existingSpinner = messagesContainer.querySelector('.message.bot:last-child .spinner');
    if (existingSpinner) {
        existingSpinner.closest('.message').remove();
    }

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = `message ${type}`;
    bubbleDiv.innerHTML = `
        <span class="timestamp">${timestamp}</span>
        <div class="bubble">
            ${content}
        </div>
    `;

    messagesContainer.appendChild(bubbleDiv);
    
    if (type === 'bot') {
        addBottomButtons(bubbleDiv.querySelector('.bubble'), model);
    }

    setTimeout(() => scrollToBottom(), 10);
    return bubbleDiv;
}

let currentMessageBubble = null;

function handleChunkMessage(msg) {
    const target_chat_id = msg.chat_id;
    const chatTabs = document.getElementById('chat-tabs-container');
    const activeTab = chatTabs.querySelector('.active');
    const current_chat_id = activeTab.id.replace('chat-tab-', '');

    if (current_chat_id !== target_chat_id) {
        return;
    }

    const chunkContent = msg.chunk_message;
    tempFullChunk += chunkContent;

    if (!currentMessageBubble) {
        currentMessageBubble = addMessageBubble('', 'bot');
    }

    const bubbleContent = currentMessageBubble.querySelector('.bubble');
    bubbleContent.innerHTML = parseAndFormatStreamingMessage(tempFullChunk);
    highlightCodeBlocks(bubbleContent);
}

function handleCoTStep(msg) {
    const { step_number, total_steps, step_description } = msg.content;
    const timestamp = new Date().toLocaleTimeString();
    const content = `
        <div class="message cot-step">
            <span class="timestamp">${timestamp}</span>
            <div class="bubble">
                <div class="cot-header" onclick="toggleCoTExpand(this)">
                    <div class="cot-title">Step ${step_number}/${total_steps} - ${escapeHtml(step_description)}</div>
                    <button class="toggle-expand">
                        <i class="fas fa-chevron-down"></i>
                    </button>
                </div>
                <div class="expandable-content" style="display: none;">
                    <div class="cot-step-output">
                        <h4>Step Output</h4>
                        <pre class="step-output-content"></pre>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.getElementById('messages').insertAdjacentHTML('beforeend', content);
}

function handleCoTStepOutput(msg) {
    const { step_number, total_steps, step_output } = msg.content;
    const lastCoTStep = document.querySelector('.message.cot-step:last-child');
    if (lastCoTStep) {
        const outputContent = lastCoTStep.querySelector('.step-output-content');
        if (outputContent) {
            outputContent.textContent = step_output; // Use textContent to prevent HTML execution
        }
    }
}

function toggleCoTExpand(header) {
    const bubble = header.closest('.bubble');
    const expandableContent = bubble.querySelector('.expandable-content');
    const icon = header.querySelector('i');
    
    if (expandableContent.style.display === 'none') {
        expandableContent.style.display = 'block';
        icon.classList.replace('fa-chevron-down', 'fa-chevron-up');
    } else {
        expandableContent.style.display = 'none';
        icon.classList.replace('fa-chevron-up', 'fa-chevron-down');
    }
}

function parseAndFormatStreamingMessage(content) {
    let formattedContent = content;

    // Handle <execute_code> tags
    formattedContent = formattedContent.replace(/<execute_code>/g, (match) => {
        executeCodeOpen = true;
        currentLanguage = 'python';
        return '<pre><code class="language-python">';
    });

    formattedContent = formattedContent.replace(/<\/execute_code>/g, (match) => {
        executeCodeOpen = false;
        currentLanguage = '';
        return '</code></pre>';
    });

    // Handle regular code blocks
    formattedContent = formattedContent.replace(/```(\w+)?/g, (match, language) => {
        if (codeBlockOpen) {
            codeBlockOpen = false;
            currentLanguage = '';
            return '</code></pre>';
        } else {
            codeBlockOpen = true;
            currentLanguage = language || '';
            const languageClass = language ? `language-${language}` : '';
            return `<pre><code class="${languageClass}">`;
        }
    });

    // Handle inline code
    formattedContent = formattedContent.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Apply Markdown formatting
    formattedContent = marked(formattedContent);

    // Add typing indicator if we're in the middle of a code block
    if (codeBlockOpen || executeCodeOpen) {
        formattedContent += '<span class="typing-code-indicator">...</span>';
    } else {
        formattedContent += createTypingIndicator();
    }

    return formattedContent;
}

function highlightCodeBlocks(element) {
    element.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
        // Force a re-highlight after a short delay
        setTimeout(() => hljs.highlightElement(block), 100);
    });
}

function createNewChatMessage(timestamp, content) {
    const chatMessageElement = document.createElement('div');
    chatMessageElement.innerHTML = `
        <div class="message bot last-message">
            <span class="timestamp">${timestamp}</span>
            <div class="bubble">${content}</div>
        </div>
    `;
    return chatMessageElement;
}

function createTypingIndicator() {
    return '<div class="typing-indicator"><div class="dot"></div></div>';
}

function parseAndFormatMessage(content, isStreaming = false) {
    let formattedContent = content;

    // Handle <execute_code> tags
    formattedContent = formattedContent.replace(/<execute_code>([\s\S]*?)<\/execute_code>/g, (match, code) => {
        return '```python\n' + code.trim() + '\n```';
    });

    // Extract code blocks and replace with placeholders
    let codeBlocks = [];
    formattedContent = formattedContent.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, language, code) => {
        let id = codeBlocks.length;
        codeBlocks.push({ language, code });
        return `\n<CODE_BLOCK_${id}>\n`;
    });

    // Apply Markdown formatting
    formattedContent = marked(formattedContent);

    // Restore code blocks with syntax highlighting
    formattedContent = formattedContent.replace(/<CODE_BLOCK_(\d+)>/g, (match, id) => {
        let { language, code } = codeBlocks[id];
        const languageClass = language ? `language-${language}` : '';
        return `<div class="language">${language || 'code'}</div>
                <button class="copy-btn" onclick="copyCodeToClipboard(this)">Copy</button>
                <pre><code class="${languageClass}">${escape_Html(code.trim())}</code></pre>`;
    });
    // apply syntax highlighting to the code blocks
    formattedContent = applyHighlighting(formattedContent);

    // Handle inline code
    formattedContent = formattedContent.replace(/<code>([^<]+)<\/code>/g, (match, code) => {
        return `<code>${escape_Html(code)}</code>`;
    });

    if (isStreaming) {
        formattedContent += createTypingIndicator();
    }

    return formattedContent;
}

function applyHighlighting(content) {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = content;
    tempDiv.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
    return tempDiv.innerHTML;
}

function escape_Html(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
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

let lastDebugBubble = null;

function updateOrCreateDebugBubble(message, timestamp, msg) {
    var messagesContainer = document.getElementById('messages');
    var formattedMsgContent = formatDebugContent(msg);

    if (lastDebugBubble) {
        // Update existing debug bubble
        let typewriterText = lastDebugBubble.querySelector('.typewriter-text');
        if (typewriterText) {
            typewriterText.textContent = message;
        }
        var expandableContentElement = lastDebugBubble.querySelector('.expandable-content');
        if (expandableContentElement) {
            expandableContentElement.innerHTML += formattedMsgContent;
        }
    } else {
        // Create new debug bubble
        let debugMessage = `
            <div class="message debug">
                <span class="timestamp">${timestamp}</span>
                <div class="bubble">
                    <div class="debug-header">
                        <div class="typewriter-container">
                            <div class="loading-icon"></div>
                            <div class="typewriter-text">${escapeHtml(message)}</div>
                        </div>
                        <button class="toggle-expand" onclick="toggleDebugExpand(this)">
                            <i class="fas fa-chevron-down"></i>
                        </button>
                    </div>
                    <div class="expandable-content">${formattedMsgContent}</div>
                </div>
            </div>`;
        let debugMessageWrapper = document.createElement('div');
        debugMessageWrapper.innerHTML = debugMessage;
        lastDebugBubble = debugMessageWrapper.firstElementChild;
        messagesContainer.appendChild(lastDebugBubble);
        setTimeout(() => scrollToBottom(), 10);
    }
}

function formatDebugContent(msg) {
    let formattedContent = '<div class="debug-content">';
    const categories = {
        'Memory': ['input', 'created_new_memory', 'active_brain', 'results_list_before_token_check', 'results_list_after_token_check', 'result_string', 'token_count'],
        'Notes': ['actions', 'content', 'message', 'timestamp', 'final_message', 'note_taking_query', 'files_content_string'],
        'Function Call': ['Function', 'Arguments'],
        'Function Response': ['Response']
    };

    for (let category in categories) {
        let categoryContent = '';
        for (let key of categories[category]) {
            if (msg.hasOwnProperty(key)) {
                if (showDebug === true) {
                    console.log('key:', key, 'value:', msg[key]);
                }
                categoryContent += `
                    <div class="debug-item">
                        <span class="debug-key">${escapeHtml(key)}:</span>
                        <span class="debug-value">${formatValue(msg[key])}</span>
                    </div>`;
            }
        }
        if (categoryContent) {
            formattedContent += `
                <div class="debug-category">
                    <div class="debug-category-header" onclick="toggleCategory(this)">
                        <i class="fas fa-chevron-right"></i> ${category}
                    </div>
                    <div class="debug-category-content" style="display: none;">
                        ${categoryContent}
                    </div>
                </div>`;
        }
    }
    formattedContent += '</div>';
    return formattedContent;
}

function formatValue(value) {
    if (typeof value === 'object') {
        return `<pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
    } else {
        return escapeHtml(value.toString());
    }
}

function toggleDebugExpand(button) {
    const bubble = button.closest('.bubble');
    bubble.classList.toggle('expanded');
    button.querySelector('i').classList.toggle('fa-chevron-down');
    button.querySelector('i').classList.toggle('fa-chevron-up');
}

function toggleCategory(header) {
    const content = header.nextElementSibling;
    const icon = header.querySelector('i');
    if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.classList.replace('fa-chevron-right', 'fa-chevron-down');
    } else {
        content.style.display = 'none';
        icon.classList.replace('fa-chevron-down', 'fa-chevron-right');
    }
}

function resetDebugBubble() {
    if (lastDebugBubble) {
        const loadingIcon = lastDebugBubble.querySelector('.loading-icon');
        if (loadingIcon) {
            loadingIcon.remove();
        }
    }
    lastDebugBubble = null;
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
                    formattedObjContent += `<b>${escapeHtml(key)}:</b> ${formatContent(value[key])}<br/>`;
                }
            }
            return formattedObjContent;
        }
    } else {
        // Format non-object values (string, number, boolean)
        return escapeHtml(value.toString());
    }
}

function formatSubContent(subKey, subContent) {
    var result = `<b>${escapeHtml(subKey)}:</b> `;
    if (Array.isArray(subContent)) {
        result += subContent.map(item => formatContent(item)).join('<br/>');
    } else if (typeof subContent === 'object') {
        result += escapeHtml(JSON.stringify(subContent, null, 2)).replace(/\n/g, '<br/>');
    } else {
        result += escapeHtml(subContent);
    }
    return result + '<br/>';
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
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
            addChatTab(chat_id);
            get_chat_tabs(username);
        }

        populateChatTabs(tabs_data);


    } catch (error) {
        console.error('Failed to send message: ', error);
        showMessage('Failed to send message: ' + error, "error", false);
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
        function (c) {
            var r = (Math.random() * 16) | 0,
                v = c == "x" ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        }
    );
};

function addChatTab(id) {
    if (id === undefined) {
        id = uuid();
    }
    chat_id = id;
    var chatTabs = document.getElementById('chat-tabs-container');
    var newTab = document.createElement('button');
    newTab.className = 'chat-tab';
    newTab.innerText = 'New Chat';
    newTab.id = 'chat-tab-' + id;

    // Create the three-dot icon
    var dots = document.createElement('div');
    dots.className = 'chat-tab-dots';
    dots.innerHTML = '&nbsp;&#x22EE;&nbsp;';
    dots.onclick = function (event) {
        event.stopPropagation();
        showDropdown(this, id);
    };

    // Append the dots to the new tab
    newTab.appendChild(dots);

    // Set the onclick function for the new tab
    newTab.onclick = function () {
        setChat(id);
    };

    // Prepend the new tab to ensure it's added at the beginning
    chatTabs.prepend(newTab);

    // Set the newly added chat as the active chat
    setChat(id);
}

function shareChat(chat_id) {
    var chatContent = document.getElementById('messages').innerHTML;

    // Create the modal elements
    var backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    var modalContent = document.createElement('div');
    modalContent.className = 'share-modal-content';

    // Set the inner HTML of the modal content
    modalContent.innerHTML = `<h3>This function is a WIP, your shared conversation would look like this (only active tab is currently displayed):</h3>${chatContent}`;

    // Append the modal content to the backdrop and then the backdrop to the modal container
    backdrop.appendChild(modalContent);
    document.getElementById('share-modal-container').appendChild(backdrop);

    // Show the modal
    backdrop.style.display = 'block';

    // Close the modal when clicking on the backdrop
    backdrop.addEventListener('click', function (event) {
        if (event.target === backdrop) {
            backdrop.style.display = 'none';
            backdrop.remove();
        }
    });
}



function editTabDescription(chat_id) {
    var tabButton = document.getElementById('chat-tab-' + chat_id);
    var tabDescription = tabButton.textContent;
    // rempve the ' ⋮ ' from the text
    tabDescription = tabDescription.split(' ⋮ ')[0];
    var newDescription = prompt('Enter a new description for the chat tab:', tabDescription);
    if (newDescription != null) {
        // trim to the first 5 words only
        newDescription = newDescription.split(' ').slice(0, 5).join(' ');
        if (newDescription.split(' ').length > 5) {
            newDescription += '...';
        }
        tabButton.textContent = newDescription;
        tabButton.classList.add('typewriter-text');
        // force the browser to reflow the element
        tabButton.offsetWidth;
        tabButton.classList.add('typewriter-text');
        // send the new description to the server
        fetch(API_URL + '/update_chat_tab_description/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 'username': user_name, 'chat_id': chat_id, 'description': newDescription }),
            credentials: 'include'
        })
            .then(response => response.json())
            .then(data => {
                // add the tab dots menu
                var dots = document.createElement('div');
                dots.className = 'chat-tab-dots';
                dots.innerHTML = '&nbsp;&#x22EE;&nbsp;';
                dots.onclick = function (event) {
                    event.stopPropagation();
                    showDropdown(this, chat_id);
                };

                tabButton.appendChild(dots);
            })
            .catch(console.error);
    }
}


function deleteChatTab(chat_id) {
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
        let currentModel = '';

        data.forEach(message => {
            const uuid = message.metadata.uid;
            const text = message.document;
            const user = message.metadata.username;
            const timestamp = message.metadata.updated_at;
            const message_model = message.metadata.model;

            // Check for UUID continuity
            if (uuid === currentUUID) {
                currentMessage += '\n' + text;
            } else {
                if (currentUUID !== null) {
                    messages.push({ text: currentMessage, user: currentUser, timestamp: currentTimestamp, uuid: currentUUID, model: currentModel });
                }
                currentUUID = uuid;
                currentMessage = text;
                currentUser = user;
                currentTimestamp = timestamp;
                currentModel = message_model;
            }
        });

        // Add the last message if it exists
        if (currentUUID !== null) {
            messages.push({ text: currentMessage, user: currentUser, timestamp: currentTimestamp, uuid: currentUUID, model: currentModel });
        }

        // Process and display the messages
        messages.forEach(message => {
            addCustomMessage(message.text, message.user === 'user' ? 'user' : 'bot', false, true, message.timestamp, true, true, message.uuid, message.model);
        });
        // call the tooltip function
        applyTooltips('[data-tooltip]');
    } catch (error) {
        console.error('Failed to get messages: ', error);
        showMessage('Failed to get messages: ' + error, "error", false);
    }
}

function get_settings(username) {
    var timestamp = new Date().toLocaleTimeString();
    prefix = production ? 'wss://' : 'ws://';
    var socket;
    var reconnectInterval = null;
    var pingInterval = null;

    function initializeSocket() {
        socket = new WebSocket(prefix + document.domain + ':' + location.port + '/ws/' + username);

        socket.onclose = function () {
            // Update the connection status in the widget
            var connectionStatusElement = document.getElementById('connectionStatus');
            connectionStatusElement.textContent = 'Disconnected';
            connectionStatusElement.style.color = 'red';
            // Attempt to reconnect every 2 seconds
            if (!reconnectInterval) {
                reconnectInterval = setInterval(function () {
                    initializeSocket();
                }, 2000);
            }
            // Clear ping interval if the connection is closed
            if (pingInterval) {
                clearInterval(pingInterval);
                pingInterval = null;
            }
        };

        socket.onopen = function () {
            // Update the connection status in the widget
            var connectionStatusElement = document.getElementById('connectionStatus');
            connectionStatusElement.textContent = 'Connected';
            connectionStatusElement.style.color = 'green';
            // Clear the reconnection interval if it's running
            if (reconnectInterval) {
                clearInterval(reconnectInterval);
                reconnectInterval = null;
            }
            // Set a ping interval to keep the connection alive
            if (!pingInterval) {
                pingInterval = setInterval(function () {
                    socket.send(JSON.stringify({ type: 'ping' }));
                }, 5000);
            }
        };

        socket.onerror = function () {
            // Update the connection status in the widget
            var connectionStatusElement = document.getElementById('connectionStatus');
            connectionStatusElement.textContent = 'Error';
            connectionStatusElement.style.color = 'orange';
        };

        socket.addEventListener('message', function (event) {
            let msg;
            try {
                msg = JSON.parse(event.data);
            } catch (e) {
                console.error("Failed to parse message as JSON:", event.data);
                return;
            }

            if (msg.type === 'pong') {
                return;
            }

            if (msg.debug) {
                handleDebugMessage(msg);
            }
            else if (msg.functionresponse) {
                handleFunctionResponse(msg);
            }
            else if (msg.type) {
                switch (msg.type) {
                    case 'plan':
                        handlePlanMessage(msg);
                        break;
                    case 'note_taking':
                        handleNoteTaking(msg.content);
                        break;
                    case 'relations':
                        handleRelations(msg.content);
                        break;
                    case 'rate_limit':
                        handleRateLimit(msg);
                        break;
                    case 'confirm_email':
                        handleConfirmMail(msg);
                        break;
                    case 'cot_step':
                        handleCoTStep(msg);
                        break;
                    case 'cot_step_output':
                        handleCoTStepOutput(msg);
                        break;
                }
            }
            else if (msg.action == 'confirm_email') {
                handleConfirmMail(msg);
            }
            else if (msg.usage) {
                handleUsage(msg);
            }
            else if (msg.audio_cost) {
                handleAudioCost(msg);
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
            else if (msg.cancel_message) {
                handleCancelMessage(msg);
            }
            else if (msg.tab_description) {
                handleTabDescription(msg);
            }
            else if (msg.auth) {
                handleAuthMessage(msg);
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
    }

    // Initial call to initialize the socket connection
    initializeSocket();

    // Get the settings from the server
    fetch(API_URL + '/load_settings/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 'username': username }),
        credentials: 'include'
    })
        .then(handleError)
        .then(data => {
            setSettings(data);
        })
        .catch(error => {
            console.error('There has been a problem with your fetch operation:', error);
        });
}


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
                showMessage('500: Server Error', "error", false);
                throw new Error('500: Server Error');
            case 503:
                showMessage('503: Service Unavailable', "error", false);
                throw new Error('503: Service Unavailable');
            case 504:
                showMessage('504: Gateway Timeout: The server is taking too long to respond. Please try again later.', "error", false);
                throw new Error('504: Gateway Timeout: The server is taking too long to respond. Please try again later.');
            default:
                showMessage('An error occurred. Please try again later. (Error ' + response.status + ')', "error", false);
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
            tempFormatted = renderMarkdown(tempReceived);
        } else {
            tempReceived = tempReceived.replace('<div class="typing-indicator"><div class="dot"><\/div><\/div>', '');
            tempFormatted = tempReceived + '\n```';
            tempFormatted = renderMarkdown(tempFormatted);
        }
    } else {
        tempFormatted = renderMarkdown(tempReceived);
    }
    return tempFormatted;
}

function resetState() {
    tempReceived = '';
    tempFormatted = '';
    var lastMessage = document.querySelector('.last-message');
    if (lastMessage) {
        setTimeout(() => scrollToBottom(), 10);
    }
    content = '';
    canSend = true;
    canRecord = true;
    isWaiting = false;
    isRecording = false;
    canSendMessage();
    document.getElementById('message').placeholder = 'Type a message...';
}

const msg = {
    "action": "send_message",
    "content": {
        "message": "Hello",
        "chat_id": "1234"
    }
};
// Function to handle the confirmation email
function handleConfirmMail(msg) {
    showConfirmationWindow(msg.content);
}

let currentEmailIndex = 0;
let emails = [];

// Function to show the confirmation window
function showConfirmationWindow(msgArray) {
    // Store the array of emails
    emails = msgArray;

    // Reset the current email index
    currentEmailIndex = 0;

    // Show the first email
    showEmail(currentEmailIndex);

    // Show the modal
    $('#googleConfModal').modal('show');
}

// Function to display an email based on index
function showEmail(index) {
    if (index < 0 || index >= emails.length) {
        return;
    }

    const msg = emails[index];

    // Set the confirmation message
    document.getElementById('confirm-message').textContent = 'Are you sure you want to send this email?';

    // Format and set the email details
    const emailDetails = `
        <b>To:</b> ${msg.to}<br>
        <b>Subject:</b> ${msg.subject}<br>
        <b>Body:</b> ${msg.body.replace(/\r?\n/g, '<br>')}<br>
        <b>Attachments:</b> ${msg.attachments && msg.attachments.length > 0 ? msg.attachments.join(', ') : 'None'}
    `;
    document.getElementById('email-details').innerHTML = emailDetails;
    document.getElementById('emailId').value = msg.draft_id;

    // Enable/disable navigation buttons
    document.getElementById('prev-email').disabled = index === 0;
    document.getElementById('next-email').disabled = index === emails.length - 1;
}

// Function to show the previous email
function showPreviousEmail() {
    if (currentEmailIndex > 0) {
        currentEmailIndex--;
        showEmail(currentEmailIndex);
    }
}

// Function to show the next email
function showNextEmail() {
    if (currentEmailIndex < emails.length - 1) {
        currentEmailIndex++;
        showEmail(currentEmailIndex);
    }
}

// Function to send the current email
async function sendCurrentEmail() {
    if (currentEmailIndex < 0 || currentEmailIndex >= emails.length) {
        return;
    }

    const msg = emails[currentEmailIndex];
    if (showDebug === true) {
        console.log('Sending email:', msg);
    }
    await sendMail(msg.draft_id);

    // Remove the sent email from the list
    emails.splice(currentEmailIndex, 1);

    // Adjust the current index if necessary
    if (currentEmailIndex >= emails.length) {
        currentEmailIndex = emails.length - 1;
    }

    // Show the next email or close the modal if no emails are left
    if (emails.length > 0) {
        showEmail(currentEmailIndex);
    } else {
        $('#googleConfModal').modal('hide');
    }
}

function sendMail(id) {
    return new Promise((resolve, reject) => {
        fetch(API_URL + '/send_email/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 'username': user_name, 'draft_id': id }),
            credentials: 'include'
        })
            .then(handleError)
            .then(data => {
                if (showDebug === true) {
                    console.log('Email sent:', data);
                }
                showMessage('Email sent successfully!', "success", true);
                resolve(data);
            })
            .catch(error => {
                console.error('Failed to send email:', error);
                showMessage('Failed to send email: ' + error, "error", true);
                reject(error);
            });
    });
}