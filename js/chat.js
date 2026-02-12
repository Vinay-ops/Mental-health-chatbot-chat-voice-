document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');
    const typingIndicator = document.getElementById('typing-indicator');
    const recordingRing = document.getElementById('recording-ring');
    const quickActions = document.getElementById('quick-actions');

    // AI Response Logic
    function getAIResponse(message) {
        const msg = message.toLowerCase();
        if (msg.includes('hello') || msg.includes('hi')) return "Hello! I'm here to support you. How are you feeling today?";
        if (msg.includes('stressed') || msg.includes('stress')) return "I'm sorry you're feeling stressed. Would you like to try a quick breathing exercise or find some local support resources?";
        if (msg.includes('resources')) return "I can help with that. Are you looking for local clinics, hotlines, or online support groups?";
        if (msg.includes('breathing')) return "Let's try the 4-7-8 technique: Inhale for 4s, hold for 7s, exhale for 8s. Shall we start?";
        if (msg.includes('help') || msg.includes('support')) return "I'm here for you. If this is an emergency, please visit our Contact page for immediate helpline numbers.";
        return "I hear you. Could you tell me a bit more about that? I'm here to listen and help navigate your options.";
    }

    const providerSelect = document.getElementById('provider-select');
    function getSelectedProvider() {
        const p = localStorage.getItem('provider') || '';
        if (providerSelect) providerSelect.value = p;
        return p || null;
    }
    if (providerSelect) {
        providerSelect.addEventListener('change', () => {
            localStorage.setItem('provider', providerSelect.value || '');
        });
        const initP = localStorage.getItem('provider') || '';
        providerSelect.value = initP;
    }

    async function fetchAIResponse(message) {
        try {
            const provider = getSelectedProvider();
            const token = localStorage.getItem('authToken');
            const backendBase = 'http://127.0.0.1:8002';
            const res = await fetch(`${backendBase}/api/chat`, {
                method: 'POST',
                headers: Object.assign(
                    { 'Content-Type': 'application/json' },
                    token ? { 'Authorization': `Bearer ${token}` } : {}
                ),
                body: JSON.stringify({ message, provider })
            });
            if (!res.ok) throw new Error('Network response was not ok');
            const data = await res.json();
            return data.reply || getAIResponse(message);
        } catch (e) {
            return getAIResponse(message);
        }
    }

    const synth = window.speechSynthesis;
    function speak(text) {
        try {
            if (!synth) return;
            const utter = new SpeechSynthesisUtterance(text);
            utter.rate = 1;
            utter.pitch = 1;
            synth.speak(utter);
        } catch {}
    }
    function addMessage(text, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'message-user' : 'message-ai');
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function handleSend() {
        const text = userInput.value.trim();
        if (text) {
            addMessage(text, true);
            userInput.value = '';
            
            // Hide quick actions after first message
            if (quickActions) quickActions.style.display = 'none';

            // Show typing indicator
            if (typingIndicator) {
                typingIndicator.style.display = 'block';
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            fetchAIResponse(text).then((response) => {
                if (typingIndicator) typingIndicator.style.display = 'none';
                addMessage(response, false);
                speak(response);
            });
        }
    }

    // Quick Action Click
    if (quickActions) {
        quickActions.addEventListener('click', (e) => {
            if (e.target.classList.contains('action-chip')) {
                userInput.value = e.target.textContent;
                handleSend();
            }
        });
    }

    sendBtn.addEventListener('click', handleSend);

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
    });

    // Voice Input Simulation
    let isRecording = false;
    micBtn.addEventListener('click', () => {
        isRecording = !isRecording;
        if (isRecording) {
            micBtn.classList.add('active');
            if (recordingRing) recordingRing.style.display = 'block';
            userInput.placeholder = "Listening...";
            
            // Simulate voice recognition after 3 seconds
            setTimeout(() => {
                if (isRecording) {
                    isRecording = false;
                    micBtn.classList.remove('active');
                    if (recordingRing) recordingRing.style.display = 'none';
                    userInput.placeholder = "Type your message here...";
                    userInput.value = "I'm feeling a bit anxious today";
                    handleSend();
                }
            }, 3000);
        } else {
            micBtn.classList.remove('active');
            if (recordingRing) recordingRing.style.display = 'none';
            userInput.placeholder = "Type your message here...";
        }
    });

    // Check for voice mode in URL
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('mode') === 'voice') {
        setTimeout(() => {
            micBtn.click();
        }, 500);
    }
});
