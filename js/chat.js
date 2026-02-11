document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');

    let isRecording = false;

    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(sender === 'user' ? 'message-user' : 'message-ai');
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function handleSend() {
        const text = userInput.value.trim();
        if (text) {
            addMessage(text, 'user');
            userInput.value = '';
            
            // Simulate AI response
            setTimeout(() => {
                const aiResponse = "Thank you for sharing that. I'm here to support you. Would you like to explore some stress-relief techniques or find local resources?";
                addMessage(aiResponse, 'ai');
            }, 1000);
        }
    }

    sendBtn.addEventListener('click', handleSend);

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSend();
        }
    });

    micBtn.addEventListener('click', () => {
        isRecording = !isRecording;
        if (isRecording) {
            micBtn.style.backgroundColor = '#ffcdd2';
            micBtn.style.color = '#d32f2f';
            userInput.placeholder = "Listening...";
            
            // Simulate voice-to-text after 2 seconds
            setTimeout(() => {
                if (isRecording) {
                    userInput.value = "I've been feeling a bit stressed lately.";
                    stopRecording();
                }
            }, 2000);
        } else {
            stopRecording();
        }
    });

    function stopRecording() {
        isRecording = false;
        micBtn.style.backgroundColor = '';
        micBtn.style.color = '';
        userInput.placeholder = "Type your message here...";
    }

    // Check for voice mode in URL
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('mode') === 'voice') {
        setTimeout(() => {
            micBtn.click();
        }, 500);
    }
});
