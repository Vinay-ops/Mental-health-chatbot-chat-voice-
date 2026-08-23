# Route blueprints
from backend.routes.auth import auth_bp
from backend.routes.chat import chat_bp
from backend.routes.psychologist import psychologist_bp
from backend.routes.community import community_bp

__all__ = ["auth_bp", "chat_bp", "psychologist_bp", "community_bp"]
