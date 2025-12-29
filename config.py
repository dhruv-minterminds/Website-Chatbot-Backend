import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    PORT = os.getenv("PORT", 5000)
    # Gemini AI
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Flask
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    # MongoDB
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/minterminds")

    # App
    APP_NAME = "Minterminds Chatbot"
    VERSION = "1.0.0"
