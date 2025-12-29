from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Import updated services
from services.knowledge_base_service import get_knowledge_service
from services.gemini_service import get_gemini_service
from routes.chat_routes import chat_bp

# Load environment variables
load_dotenv()


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Initialize rate limiter with simple in-memory storage
    limiter = Limiter(
        get_remote_address,  # Use IP address for rate limiting
        app=app,
        default_limits=["50 per hour"],  # Default limit for all endpoints
        storage_uri="memory://",  # Simple in-memory storage (no Redis needed)
        strategy="fixed-window",
        headers_enabled=True,
    )

    # Initialize knowledge base
    try:
        kb_service = get_knowledge_service()
        stats = kb_service.get_stats()
        print("✅ Knowledge base initialized successfully")
        print(f"📊 Loaded {stats['total_files']} files with {stats['total_faqs']} FAQs")

        # Print category breakdown
        for category, subcats in stats["categories"].items():
            for subcat, data in subcats.items():
                print(
                    f"  • {category}/{subcat}: {data['file_count']} files, {data['faq_count']} FAQs"
                )

    except Exception as e:
        print(f"❌ Failed to initialize knowledge base: {e}")
        return None

    # Initialize Gemini AI
    try:
        gemini_service = get_gemini_service()
        print("✅ Gemini AI initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Gemini AI: {e}")
        return None

    # Register blueprints
    # Apply rate limiting to all routes in chat blueprint
    # You can customize limits for specific endpoints if needed

    app.register_blueprint(chat_bp, url_prefix="/api")

    # Add health check endpoint (no rate limiting)
    @app.route("/api/health", methods=["GET"])
    @limiter.exempt  # Health check is exempt from rate limiting
    def health_check():
        return jsonify(
            {
                "status": "healthy",
                "knowledge_base": {
                    "total_files": stats["total_files"],
                    "total_faqs": stats["total_faqs"],
                },
                "rate_limiting": "enabled",
                "default_limit": "100 requests per hour",
            }
        )

    # Error handler for rate limit exceeded
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return (
            jsonify(
                {
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "limit": str(e.description),
                }
            ),
            429,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    if app:
        print("🚀 Starting Minterminds Chatbot API...")
        print("📡 Running on: http://localhost:5000")
        print("🔒 Rate limiting enabled: 50 requests per hour per IP")
        app.run(debug=True, port=5000, host="0.0.0.0")
    else:
        print("❌ Failed to start application")
