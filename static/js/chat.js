document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const chatModeBtn = document.getElementById('mode-chat-btn');
    const voiceModeBtn = document.getElementById('mode-voice-btn');
    const chatModeView = document.getElementById('chat-mode-view');
    const voiceModeView = document.getElementById('voice-mode-view');
    const chatInputArea = document.getElementById('chat-input-area');
    const quickActions = document.getElementById('quick-actions');
    
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const providerSelect = document.getElementById('provider-select');
    const typingIndicator = document.getElementById('typing-indicator');
    
    const voiceMicBtn = document.querySelector('.main-mic-btn');
    const voiceStatusText = document.getElementById('voice-status-text');
    const voiceTranscript = document.getElementById('voice-transcript');
    const voiceAiReply = document.getElementById('voice-ai-reply');
    const voiceAiReplyBox = document.getElementById('voice-ai-reply-box');
    const recordingVisualizer = document.querySelector('.recording-visualizer');

    // --- State ---
    let currentMode = 'chat'; // 'chat' or 'voice'
    let isRecording = false;
    const synth = window.speechSynthesis;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;

    // --- Initialization ---
    if (providerSelect) {
        providerSelect.value = localStorage.getItem('provider') || 'groq';
        providerSelect.addEventListener('change', () => {
            localStorage.setItem('provider', providerSelect.value);
        });
    }

    // --- Helper for Dynamic Translations ---
    function t(key) {
        const lang = localStorage.getItem('selectedLanguage') || 'en';
        return (translations[lang] && translations[lang][key]) || key;
    }

    // --- Mode Switching ---
    function switchMode(mode) {
        currentMode = mode;
        if (mode === 'chat') {
            chatModeBtn.classList.replace('btn-outline-primary', 'btn-primary');
            voiceModeBtn.classList.replace('btn-primary', 'btn-outline-primary');
            chatModeView.style.setProperty('display', 'flex', 'important');
            voiceModeView.style.setProperty('display', 'none', 'important');
            chatInputArea.style.display = 'block';
            quickActions.style.display = 'flex';
            stopRecording();
        } else {
            voiceModeBtn.classList.replace('btn-outline-primary', 'btn-primary');
            chatModeBtn.classList.replace('btn-primary', 'btn-outline-primary');
            voiceModeView.style.setProperty('display', 'flex', 'important');
            chatModeView.style.setProperty('display', 'none', 'important');
            chatInputArea.style.display = 'none';
            quickActions.style.display = 'none';
            
            // Reset voice view text
            voiceStatusText.textContent = t('voice_click_to_start');
            voiceTranscript.textContent = "...";
            voiceAiReplyBox.style.display = 'none';
        }
    }

    chatModeBtn.addEventListener('click', () => switchMode('chat'));
    voiceModeBtn.addEventListener('click', () => switchMode('voice'));

    // --- AI Communication ---
    async function fetchAIResponse(message) {
        try {
            const provider = providerSelect ? providerSelect.value : 'groq';
            const lang = localStorage.getItem('selectedLanguage') || 'en';
            const token = localStorage.getItem('authToken');
            
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({ message, provider, lang })
            });
            
            if (!res.ok) throw new Error('API Error');
            const data = await res.json();
            return data.reply;
        } catch (e) {
            console.error('Chat Error:', e);
            // We could localize this error too, but it's a fallback
            return "I'm having trouble connecting to my knowledge base right now. Please check your internet or try again in a moment.";
        }
    }

    // --- Chat Mode Logic ---
    function addChatMessage(text, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        if (isUser) {
            messageDiv.classList.add('message-user');
            messageDiv.textContent = text;
        } else {
            messageDiv.classList.add('message-ai');
            messageDiv.innerHTML = `
                <div class="d-flex align-items-start gap-3">
                    <div class="ai-icon-container"><i class="bi bi-robot"></i></div>
                    <div class="message-content">${text}</div>
                </div>
            `;
        }
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function handleChatSend() {
        const text = userInput.value.trim();
        if (!text) return;

        addChatMessage(text, true);
        userInput.value = '';
        typingIndicator.style.display = 'block';

        const response = await fetchAIResponse(text);
        typingIndicator.style.display = 'none';
        addChatMessage(response, false);
        
        speak(response); 
    }

    sendBtn.addEventListener('click', handleChatSend);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleChatSend();
    });

    if (quickActions) {
        quickActions.addEventListener('click', (e) => {
            if (e.target.classList.contains('action-chip')) {
                userInput.value = e.target.textContent;
                handleChatSend();
            }
        });
    }

    // --- Voice Mode Logic ---
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;

        recognition.onstart = () => {
            isRecording = true;
            recordingVisualizer.classList.add('is-recording');
            voiceStatusText.textContent = t('chat_listening');
            voiceTranscript.textContent = "...";
            voiceAiReplyBox.style.display = 'none';
            synth.cancel();
        };

        recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(result => result[0])
                .map(result => result.transcript)
                .join('');
            voiceTranscript.textContent = transcript;
            
            if (event.results[0].isFinal) {
                stopRecording();
                handleVoiceInput(transcript);
            }
        };

        recognition.onerror = (e) => {
            console.error('Speech Error:', e);
            stopRecording();
            voiceStatusText.textContent = "Error occurred";
        };

        recognition.onend = () => {
            stopRecording();
        };
    }

    function stopRecording() {
        if (isRecording) {
            recognition.stop();
            isRecording = false;
            recordingVisualizer.classList.remove('is-recording');
            voiceStatusText.textContent = t('voice_click_to_start');
        }
    }

    voiceMicBtn.addEventListener('click', () => {
        if (!recognition) {
            alert("Speech recognition is not supported in this browser.");
            return;
        }
        if (isRecording) {
            stopRecording();
        } else {
            const currentLang = localStorage.getItem('selectedLanguage') || 'en';
            const langMap = { 'en': 'en-US', 'hi': 'hi-IN', 'mr': 'mr-IN' };
            recognition.lang = langMap[currentLang] || 'en-US';
            recognition.start();
        }
    });

    async function handleVoiceInput(text) {
        if (!text) return;
        
        voiceStatusText.textContent = "...";
        typingIndicator.style.display = 'block';
        
        const response = await fetchAIResponse(text);
        
        typingIndicator.style.display = 'none';
        voiceStatusText.textContent = ""; 
        voiceAiReply.textContent = response;
        voiceAiReplyBox.style.display = 'block';
        
        speak(response);
    }

    function speak(text) {
        if (!synth || !text) return;
        
        // Stop any current speaking
        synth.cancel();

        const utter = new SpeechSynthesisUtterance(text);
        const currentLang = localStorage.getItem('selectedLanguage') || 'en';
        
        // Map our language codes to TTS locales
        const langMap = {
            'en': 'en-US',
            'hi': 'hi-IN',
            'mr': 'hi-IN' // Marathi often works better with Hindi TTS if Marathi isn't available
        };
        
        utter.lang = langMap[currentLang] || 'en-US';
        
        // Try to find a native-sounding voice
        const voices = synth.getVoices();
        const preferredVoice = voices.find(v => v.lang.startsWith(utter.lang) && v.name.includes('Google'));
        if (preferredVoice) utter.voice = preferredVoice;

        utter.rate = 1.0;
        utter.pitch = 1.0;
        
        utter.onend = () => {
            if (currentMode === 'voice') {
                voiceStatusText.textContent = "Click to start speaking";
            }
        };
        
        synth.speak(utter);
    }

    // --- URL Mode Handling ---
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('mode') === 'voice') {
        switchMode('voice');
    }
});