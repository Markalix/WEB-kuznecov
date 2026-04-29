from db import create_session
from users import User


class Login:
    def __init__(self):
        self.db = create_session()
        self.user_handler = User()
        self.sessions = {}

    def authenticate(self, username: str, password: str) -> dict:
        user = self.user_handler.get_user_by_username(username)

        if not user:
            return {"success": False, "message": "Пользователь не найден"}

        if user.password != password:
            return {"success": False, "message": "Неверный пароль"}

        session_token = f"{username}_{user.id}"
        self.sessions[session_token] = user.id

        return {
            "success": True,
            "message": "Вход выполнен успешно",
            "session_token": session_token,
            "user_id": user.id,
            "username": user.username
        }

    def logout(self, session_token: str) -> dict:
        if session_token in self.sessions:
            del self.sessions[session_token]
            return {"success": True, "message": "Выход выполнен"}
        return {"success": False, "message": "Сессия не найдена"}

    def get_current_user(self, session_token: str):
        user_id = self.sessions.get(session_token)
        if user_id:
            return self.user_handler.get_user_by_id(user_id)
        return None

    def is_authenticated(self, session_token: str) -> bool:
        return session_token in self.sessions

    def close(self):
        self.db.close()
        self.user_handler.close()