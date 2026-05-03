from db import create_session
from users import User


class Login:
    def __init__(self):
        self.db = create_session()
        self.user_handler = User()

    def authenticate(self, username: str, password: str) -> dict:
        user = self.user_handler.get_user_by_username(username)

        if not user:
            return {"success": False, "message": "Пользователь не найден"}

        if user.password != password:
            return {"success": False, "message": "Неверный пароль"}

        return {
            "success": True,
            "message": "Вход выполнен успешно",
            "user_id": user.id,
            "username": user.username,
            "email": user.email
        }

    def get_user_by_id(self, user_id: int):
        return self.user_handler.get_user_by_id(user_id)

    def close(self):
        self.db.close()
        self.user_handler.close()