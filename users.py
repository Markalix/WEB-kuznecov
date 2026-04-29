from db import create_session
from models import User as UserModel


class User:
    def __init__(self):
        self.db = create_session()
        self.user_model = UserModel

    def register(self, username: str, email: str, password: str) -> dict:
        # Проверка существующего пользователя
        existing_user = self.db.query(self.user_model).filter(
            (self.user_model.username == username) | (self.user_model.email == email)
        ).first()

        if existing_user:
            return {"success": False, "message": "Пользователь с таким именем или email уже существует"}

        # Создание нового пользователя
        new_user = self.user_model(
            username=username,
            email=email,
            password=password
        )

        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        return {"success": True, "message": "Регистрация успешна", "user_id": new_user.id}

    def get_user_by_username(self, username: str):
        return self.db.query(self.user_model).filter(self.user_model.username == username).first()

    def get_user_by_id(self, user_id: int):
        return self.db.query(self.user_model).filter(self.user_model.id == user_id).first()

    def close(self):
        self.db.close()