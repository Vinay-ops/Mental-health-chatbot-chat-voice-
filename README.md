# 🧠 MindCare Navigator

**Safe, Voice-Enabled Multi-Language Mental Health Support**

MindCare Navigator is a full-stack Flask application designed to bridge the gap in mental health support. It provides a safe, ethical, and accessible platform for emotional guidance and resource navigation using AI, supporting English, Hindi, and Marathi.

---

## 🛠️ Technology Stack

- **Backend**: Flask (Python 3.x)
- **Database**: MongoDB (Atlas/Local) for user authentication and activity logs
- **Frontend**: HTML5, CSS3 (Glassmorphism), Bootstrap 5
- **AI Integration**: Groq (Default), Google Gemini, Ollama, Grok
- **APIs**: JWT for secure authentication, Web Speech API for Voice-to-Text & Text-to-Speech
- **Localization**: Custom client-side translation engine (JS-based)

---

## 📂 Project Structure & File Usage

### **Core Backend**
- [app.py](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/app.py): Main Flask server handling routes, AI provider logic, and JWT authentication.
- [db.py](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/db.py): MongoDB connection utility with lazy initialization and graceful fallback logic.
- [.env](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/.env): Environment variables for API keys and Database URIs.

### **Frontend Templates**
- [base.html](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/templates/base.html): Master layout containing the responsive navbar, footer, and language selector.
- [index.html](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/templates/index.html): Landing page with a modern hero section and project pillars.
- [chat.html](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/templates/chat.html): Dual-mode (Chat/Voice) interface with provider selection and real-time transcripts.
- [login.html](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/templates/login.html) & [register.html](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/templates/register.html): Secure user authentication pages.
- [about.html](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/templates/about.html): Mission details and project purpose.
- [features.html](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/templates/features.html): Technical breakdown of system capabilities.
- [contact.html](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/templates/contact.html): Emergency resources and support contact form.

### **Static Assets**
- [style.css](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/static/css/style.css): Custom CSS implementing modern Glassmorphism, animations, and responsive UI fixes.
- [chat.js](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/static/js/chat.js): Core logic for mode switching, AI API calls, speech recognition, and TTS.
- [translations.js](file:///c:/Users/Vinay Bhogal/Desktop/RMWEBSITE/static/js/translations.js): Multi-language dictionary supporting English, Hindi, and Marathi.

---

## ✨ Key Features

- **🗣️ Dual Mode Interface**: Dedicated Chat and Voice modes for diverse user preferences.
- **🌍 Multi-Language Support**: Complete UI and AI response localization for English, Hindi, and Marathi.
- **🛡️ Provider Redundancy**: Intelligent fallback system (Groq -> Gemini -> Grok -> Ollama) ensuring high availability.
- **💎 Premium UI**: High-end Glassmorphism design with fluid animations and zero-collision responsive layouts.
- **🔐 Secure Auth**: MongoDB-backed user registration and login with protected chat access.
- **🚫 Non-Diagnostic**: Strictly adheres to ethical guidelines, focusing on support without medical claims.

---

## 🚀 Getting Started

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure Environment**:
   Add your API keys (GROQ_API_KEY, GEMINI_API_KEY, etc.) to the `.env` file.
3. **Run Application**:
   ```bash
   python app.py
   ```

---

## ⚠️ Disclaimer

**MindCare Navigator does not provide medical diagnosis or therapy.** This system is designed for informational and emotional support navigation. If you are in a crisis, please contact your local emergency services immediately.
