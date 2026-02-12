from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- Routes ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# --- API Endpoints ---

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.json
    user_message = data.get('message', '').lower()
    
    # Simple AI response logic (moved from JS to Python)
    response = ""
    if 'hello' in user_message or 'hi' in user_message:
        response = "Hello! I'm here to support you. How are you feeling today?"
    elif 'stressed' in user_message or 'stress' in user_message:
        response = "I'm sorry you're feeling stressed. Would you like to try a quick breathing exercise or find some local support resources?"
    elif 'resources' in user_message:
        response = "I can help with that. Are you looking for local clinics, hotlines, or online support groups?"
    elif 'breathing' in user_message:
        response = "Let's try the 4-7-8 technique: Inhale for 4s, hold for 7s, exhale for 8s. Shall we start?"
    elif 'help' in user_message or 'support' in user_message:
        response = "I'm here for you. If this is an emergency, please visit our Contact page for immediate helpline numbers."
    else:
        response = "I hear you. Could you tell me a bit more about that? I'm here to listen and help navigate your options."
        
    return jsonify({"reply": response}) # Match 'reply' key from chat.js fetch logic

if __name__ == '__main__':
    app.run(debug=True, port=8002) # Match port 8002 from chat.js fetch logic
