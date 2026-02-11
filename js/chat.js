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

            // Simulate AI delay
            setTimeout(() => {
                if (typingIndicator) typingIndicator.style.display = 'none';
                const response = getAIResponse(text);
                addMessage(response, false);
            }, 1500);
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
