from db import create_session
from models import User as UserModel


class User:
    def __init__(self):
        self.db = create_session()

    def register(self, username: str, email: str, password: str):
        existing_user = self.db.query(UserModel).filter(
            (UserModel.username == username) | (UserModel.email == email)
        ).first()
        if existing_user:
            return {"success": False, "message": "Пользователь с таким именем или email уже существует"}
        new_user = UserModel(
            username=username,
            email=email,
            password=password
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        return {"success": True, "message": "Регистрация успешна", "user_id": new_user.id}

    def get_user_by_username(self, username: str):
        return self.db.query(UserModel).filter(UserModel.username == username).first()

    def get_user_by_id(self, user_id: int):
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()

    def close(self):
        self.db.close()
