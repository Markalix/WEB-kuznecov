import sqlalchemy as sa
from datetime import datetime
from db import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    username = sa.Column(sa.String, unique=True, nullable=False)
    email = sa.Column(sa.String, unique=True, nullable=False)
    password = sa.Column(sa.String, nullable=False)
    created_at = sa.Column(sa.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<User {self.username}>"
