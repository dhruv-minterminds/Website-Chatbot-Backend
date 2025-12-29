from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
import re
from database import get_database
from services.gemini_service import get_gemini_service

chat_bp = Blueprint("chat", __name__)

# In-memory session storage for better performance
session_store = {}


@chat_bp.route("/chat", methods=["POST"])
def chat():
    """Handle chat messages with improved session management"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        session_id = data.get("session_id")
        user_message = data.get("message")

        if not user_message:
            return jsonify({"error": "Missing message"}), 400

        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        print(
            f"💬 Chat request - Session: {session_id[:8]}..., Message: {user_message[:50]}..."
        )

        # Initialize in-memory session if not exists
        if session_id not in session_store:
            session_store[session_id] = {
                "session_id": session_id,
                "visit_id": str(uuid.uuid4()),
                "created_at": datetime.now(),
                "last_activity": datetime.now(),
                "message_count": 0,
                "engagement_score": 0,
                "conversation": [],  # Store last 10 messages in memory
                "user_captured": False,
            }
            print(f"🆕 Created new session: {session_id[:8]}...")

        # Get current session
        current_session = session_store[session_id]

        # Update session activity
        current_session["last_activity"] = datetime.now()
        current_session["message_count"] += 1
        current_session["engagement_score"] += 1

        # Add user message to in-memory conversation
        current_session["conversation"].append(
            {"role": "user", "content": user_message, "timestamp": datetime.now()}
        )

        # Keep only last 10 messages in memory
        if len(current_session["conversation"]) > 10:
            current_session["conversation"] = current_session["conversation"][-10:]

        print(
            f"📊 Session stats - Messages: {current_session['message_count']}, Engagement: {current_session['engagement_score']}"
        )

        # Get formatted history (last 5 exchanges)
        formatted_history = []
        recent_messages = current_session["conversation"][-10:]

        for msg in recent_messages:
            formatted_history.append({"role": msg["role"], "content": msg["content"]})

        # Get Gemini response WITH history
        gemini_service = get_gemini_service()
        ai_response = gemini_service.generate_response(user_message, formatted_history)

        print(
            f"🤖 AI Response - Trigger capture: {ai_response.get('trigger_capture', False)}, Category: {ai_response.get('category', 'general')}"
        )

        # Add bot response to in-memory conversation
        current_session["conversation"].append(
            {
                "role": "assistant",
                "content": ai_response["response"],
                "timestamp": datetime.now(),
            }
        )

        # Prepare response
        response_data = {
            "bot_response": ai_response["response"],
            "session_id": session_id,
            "trigger_capture": ai_response["trigger_capture"],
            "trigger_reason": ai_response.get("trigger_reason", "chat_trigger"),
            "category": ai_response["category"],
            "direct_faq_used": ai_response.get("direct_faq_used", False),
            "message_count": current_session["message_count"],
            "engagement_score": current_session["engagement_score"],
        }

        print(
            f"✅ Chat completed - Response length: {len(ai_response['response'])} chars"
        )
        return jsonify(response_data), 200

    except Exception as e:
        print(f"❌ Chat error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@chat_bp.route("/chat/clear", methods=["POST"])
def clear_chat():
    """Clear chat history for a session - both in memory and database"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        session_id = data.get("session_id")

        if not session_id:
            return jsonify({"error": "Missing session_id"}), 400

        print(f"🧹 Clearing chat for session: {session_id[:8]}...")

        # Clear in-memory session if exists
        if session_id in session_store:
            # Reset conversation but keep basic session info
            session_store[session_id]["conversation"] = []
            session_store[session_id]["message_count"] = 0
            session_store[session_id][
                "engagement_score"
            ] = 1  # Reset to 1 for new conversation
            session_store[session_id]["last_activity"] = datetime.now()

            # Optionally keep user capture info if already captured
            # This preserves the user data even after clearing chat
            if (
                "user_captured" in session_store[session_id]
                and session_store[session_id]["user_captured"]
            ):
                print(f"⚠️ Keeping user capture info for session: {session_id[:8]}...")
            else:
                session_store[session_id]["user_captured"] = False
                session_store[session_id]["user_id"] = None
                session_store[session_id]["captured_at"] = None

            print(f"✅ Cleared in-memory chat for session: {session_id[:8]}...")

        # Also clear from database if needed
        # You can add database clearing logic here if you store conversations in DB

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Chat history cleared successfully",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        print(f"❌ Clear chat error: {e}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/chat/sessions", methods=["GET"])
def list_sessions():
    """List all active sessions (for admin/debug)"""
    try:
        sessions = []
        for session_id, session_data in session_store.items():
            sessions.append(
                {
                    "session_id": session_id,
                    "message_count": session_data.get("message_count", 0),
                    "engagement_score": session_data.get("engagement_score", 0),
                    "last_activity": (
                        session_data.get("last_activity").isoformat()
                        if session_data.get("last_activity")
                        else None
                    ),
                    "conversation_count": len(session_data.get("conversation", [])),
                    "user_captured": session_data.get("user_captured", False),
                }
            )

        return (
            jsonify(
                {
                    "total_sessions": len(sessions),
                    "sessions": sessions,
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/capture", methods=["POST"])
def capture():
    """Capture user data with enhanced validation"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        session_id = data.get("session_id")
        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone", "")
        category = data.get("category", "general")
        capture_method = data.get("capture_method", "chat_trigger")
        source = data.get("source", "chatbot")

        print(
            f"📝 Capture attempt - Session: {session_id[:8]}..., Email: {email}, Category: {category}"
        )

        if not session_id or not name or not email:
            return (
                jsonify(
                    {
                        "error": "Missing required fields: session_id, name, and email are required"
                    }
                ),
                400,
            )

        # Validate email format
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return jsonify({"error": "Invalid email format"}), 400

        db = get_database()

        # Check if email already exists
        existing_user = db.users.find_one({"email": email.lower().strip()})
        if existing_user:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "This email is already registered with us.",
                        "existing_user": {
                            "name": existing_user.get("name"),
                            "registered_date": (
                                existing_user.get("created_at").isoformat()
                                if existing_user.get("created_at")
                                else None
                            ),
                        },
                    }
                ),
                400,
            )

        # Get session data if available
        session_data = session_store.get(session_id, {})

        # Save user data
        user_data = {
            "session_id": session_id,
            "visit_id": session_data.get("visit_id", str(uuid.uuid4())),
            "name": name.strip(),
            "email": email.lower().strip(),
            "phone": phone.strip() if phone else "",
            "category": category,
            "capture_method": capture_method,
            "source": source,
            "message_count": session_data.get("message_count", 0),
            "engagement_score": session_data.get("engagement_score", 0),
            "created_at": datetime.now(),
            "followup_sent": False,
            "followup_sent_at": None,
            "status": "new",
            "notes": "",
        }

        result = db.users.insert_one(user_data)
        user_id = str(result.inserted_id)

        print(f"✅ User captured successfully - ID: {user_id}, Email: {email}")

        # Update session in memory if exists
        if session_id in session_store:
            session_store[session_id]["user_captured"] = True
            session_store[session_id]["user_id"] = user_id
            session_store[session_id]["captured_at"] = datetime.now()
            session_store[session_id]["captured_category"] = category

        return (
            jsonify(
                {
                    "success": True,
                    "user_id": user_id,
                    "session_id": session_id,
                    "message": "Thank you! We will contact you soon.",
                    "next_steps": [
                        "Check your email for confirmation",
                        "Our team will reach out within 24 hours",
                        "You'll receive relevant information based on your interest",
                    ],
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        print(f"❌ Capture error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        db = get_database()
        # Test database connection
        db.command("ping")

        return (
            jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "active_sessions": len(session_store),
                    "database": "connected",
                    "version": "1.0.0",
                }
            ),
            200,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "active_sessions": len(session_store),
                }
            ),
            500,
        )


def cleanup_old_sessions(max_age_hours=24):
    """Clean up old in-memory sessions"""
    try:
        now = datetime.now()
        sessions_to_remove = []

        for session_id, session_data in session_store.items():
            last_activity = session_data.get("last_activity")
            if last_activity:
                age_hours = (now - last_activity).total_seconds() / 3600
                if age_hours > max_age_hours:
                    sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            del session_store[session_id]

        print(f"🧹 Cleaned up {len(sessions_to_remove)} old sessions")

    except Exception as e:
        print(f"❌ Session cleanup error: {e}")
