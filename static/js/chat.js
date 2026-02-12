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
    const sentimentBadge = document.getElementById('sentiment-badge');
    const historyToggle = document.getElementById('history-toggle');
    const sessionsList = document.getElementById('sessions-list');
    const historyLoading = document.getElementById('history-loading');
    const historyEmpty = document.getElementById('history-empty');
    const newChatBtn = document.getElementById('new-chat-btn');
    const sidebarNewChat = document.getElementById('sidebar-new-chat');

    // --- State ---
    let currentMode = 'chat'; // 'chat' or 'voice'
    let isRecording = false;
    let sessionId = localStorage.getItem('chat_session_id') || null;
    const synth = window.speechSynthesis;
    const SpeechRecognition = window.Recognition || window.webkitSpeechRecognition;
    let recognition = null;

    // --- Initialization ---
    async function initSession() {
        if (!sessionId) {
            await startNewChat();
        }
        loadSessions();
    }

    async function startNewChat() {
        try {
            const res = await fetch('/api/new_chat', { method: 'POST' });
            const data = await res.json();
            sessionId = data.session_id;
            localStorage.setItem('chat_session_id', sessionId);
            // Clear UI
            chatMessages.innerHTML = `
                <div class="message message-ai fade-in-up">
                    <div class="d-flex align-items-start gap-3">
                        <div class="ai-icon-container"><i class="bi bi-robot"></i></div>
                        <div class="message-content" data-t="chat_welcome">${t('chat_welcome')}</div>
                    </div>
                </div>
            `;
            voiceTranscript.textContent = "...";
            voiceAiReplyBox.style.display = 'none';
            updateSentimentUI('neutral');
            loadSessions();
        } catch (e) {
            console.error('Error starting new chat:', e);
        }
    }

    async function loadSessions() {
        const token = localStorage.getItem('authToken');
        if (!token || !sessionsList) return;

        historyLoading.style.display = 'block';
        historyEmpty.style.display = 'none';
        sessionsList.innerHTML = '';

        try {
            const res = await fetch('/api/sessions', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const sessions = await res.json();
            historyLoading.style.display = 'none';

            if (sessions.length === 0) {
                historyEmpty.style.display = 'block';
                return;
            }

            sessions.forEach(sid => {
                const item = document.createElement('div');
                item.className = `history-item ${sid === sessionId ? 'active' : ''}`;
                item.innerHTML = `
                    <div class="history-date">Session ID</div>
                    <div class="history-preview text-truncate">${sid.substring(0, 24)}...</div>
                `;
                item.addEventListener('click', () => {
                    loadHistory(sid);
                    // Close offcanvas
                    const bsOffcanvas = bootstrap.Offcanvas.getInstance(document.getElementById('historySidebar'));
                    if (bsOffcanvas) bsOffcanvas.hide();
                });
                sessionsList.appendChild(item);
            });
        } catch (e) {
            console.error('Error loading sessions:', e);
            historyLoading.style.display = 'none';
        }
    }

    async function loadHistory(sid) {
        const token = localStorage.getItem('authToken');
        if (!token) return;

        sessionId = sid;
        localStorage.setItem('chat_session_id', sessionId);
        chatMessages.innerHTML = ''; // Clear current
        typingIndicator.style.display = 'block';

        try {
            const res = await fetch(`/api/history/${sid}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const history = await res.json();
            typingIndicator.style.display = 'none';

            if (history.length === 0) {
                chatMessages.innerHTML = `<div class="text-center py-4 text-muted small">No messages in this session</div>`;
            } else {
                history.forEach(log => {
                    addChatMessage(log.content, log.role === 'user');
                });
            }
            loadSessions(); // Refresh active state
        } catch (e) {
            console.error('Error loading history:', e);
            typingIndicator.style.display = 'none';
        }
    }

    newChatBtn?.addEventListener('click', startNewChat);
    sidebarNewChat?.addEventListener('click', startNewChat);

    initSession();
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
            chatModeBtn.classList.add('active');
            voiceModeBtn.classList.remove('active');
            chatModeView.style.setProperty('display', 'flex', 'important');
            voiceModeView.style.setProperty('display', 'none', 'important');
            chatInputArea.style.display = 'block';
            quickActions.style.display = 'flex';
            stopRecording();
        } else {
            voiceModeBtn.classList.add('active');
            chatModeBtn.classList.remove('active');
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
                body: JSON.stringify({ message, provider, lang, session_id: sessionId })
            });
            
            if (!res.ok) throw new Error('API Error');
            const data = await res.json();
            
            // Save session ID for memory
            if (data.session_id) {
                sessionId = data.session_id;
                localStorage.setItem('chat_session_id', sessionId);
            }
            
            // Update Sentiment UI
            if (data.sentiment) {
                updateSentimentUI(data.sentiment);
            }
            
            return data.reply;
        } catch (e) {
            console.error('Chat Error:', e);
            return t('chat_error_fallback');
        }
    }

    function updateSentimentUI(sentiment) {
        if (!sentimentBadge) return;
        
        const iconMap = {
            happy: 'bi-emoji-laughing',
            sad: 'bi-emoji-frown',
            anxious: 'bi-emoji-expressionless',
            angry: 'bi-emoji-angry',
            calm: 'bi-emoji-heart',
            neutral: 'bi-emoji-smile'
        };
        
        const colorMap = {
            happy: 'bg-soft-green text-success',
            sad: 'bg-soft-blue text-primary',
            anxious: 'bg-soft-purple text-dark',
            angry: 'bg-danger-subtle text-danger',
            calm: 'bg-info-subtle text-info',
            neutral: 'bg-soft-blue text-primary'
        };
        
        // Add pop animation
        sentimentBadge.style.animation = 'none';
        sentimentBadge.offsetHeight; // trigger reflow
        sentimentBadge.style.animation = 'pulse 0.5s ease-out';
        
        const icon = sentimentBadge.querySelector('i');
        const text = sentimentBadge.querySelector('span');
        
        icon.className = `bi ${iconMap[sentiment] || iconMap.neutral} me-1`;
        text.textContent = t(`mood_${sentiment}`);
        sentimentBadge.className = `badge ${colorMap[sentiment] || colorMap.neutral} rounded-pill px-3 py-2 transition-all`;
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
        
        // speak(response); // Voice disabled in Chat mode as requested
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
    let voices = [];
    function loadVoices() {
        voices = synth.getVoices();
    }
    loadVoices();
    if (synth.onvoiceschanged !== undefined) {
        synth.onvoiceschanged = loadVoices;
    }

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
        
        // Stop any current speaking before starting to listen
        if (synth.speaking) {
            synth.cancel();
        }

        if (isRecording) {
            stopRecording();
        } else {
            const currentLang = localStorage.getItem('selectedLanguage') || 'en';
            const langMap = { 'en': 'en-US', 'hi': 'hi-IN', 'mr': 'mr-IN' };
            recognition.lang = langMap[currentLang] || 'en-US';
            try {
                recognition.start();
            } catch (e) {
                console.error("Recognition already started or error:", e);
                stopRecording();
            }
        }
    });

    async function handleVoiceInput(text) {
        if (!text) return;
        
        // Add to background chat history for continuity
        addChatMessage(text, true);
        
        voiceStatusText.textContent = "...";
        typingIndicator.style.display = 'block';
        
        const response = await fetchAIResponse(text);
        
        typingIndicator.style.display = 'none';
        voiceStatusText.textContent = ""; 
        voiceAiReply.textContent = response;
        voiceAiReplyBox.style.display = 'block';
        
        // Add response to background chat history
        addChatMessage(response, false);
        
        speak(response);
    }

    function speak(text) {
        if (!synth || !text) return;
        
        // Stop any current speaking
        synth.cancel();

        // Create a new utterance
        const utter = new SpeechSynthesisUtterance(text);
        const currentLang = localStorage.getItem('selectedLanguage') || 'en';
        
        const langMap = {
            'en': 'en-US',
            'hi': 'hi-IN',
            'mr': 'hi-IN' 
        };
        
        const targetLang = langMap[currentLang] || 'en-US';
        utter.lang = targetLang;
        
        // Try to find the best voice
        if (voices.length === 0) loadVoices();
        
        // Find voice for specific language
        let voice = voices.find(v => v.lang === targetLang || v.lang.replace('_', '-') === targetLang);
        
        // Preference: Google or Natural sounding voices
        const premiumVoice = voices.find(v => (v.lang === targetLang || v.lang.replace('_', '-') === targetLang) && 
                                              (v.name.includes('Google') || v.name.includes('Natural')));
        
        if (premiumVoice) voice = premiumVoice;
        if (voice) utter.voice = voice;

        utter.rate = 1.0;
        utter.pitch = 1.0;
        utter.volume = 1.0;
        
        utter.onend = () => {
            if (currentMode === 'voice') {
                voiceStatusText.textContent = t('voice_click_to_start');
            }
        };

        // Crucial fix for Chrome: call speak after a tiny delay
        setTimeout(() => {
            synth.speak(utter);
        }, 50);
    }

    // --- URL Mode Handling ---
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('mode') === 'voice') {
        switchMode('voice');
    }
});