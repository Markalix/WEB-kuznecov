import sqlalchemy as sa
from datetime import datetime, timedelta
from db import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    username = sa.Column(sa.String, unique=True, nullable=False)
    email = sa.Column(sa.String, unique=True, nullable=False)
    password = sa.Column(sa.String, nullable=False)
    balance = sa.Column(sa.Integer, default=5000)
    created_at = sa.Column(sa.DateTime, default=datetime.now)


class Listing(SqlAlchemyBase):
    __tablename__ = 'listings'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.String, nullable=False)
    description = sa.Column(sa.String, nullable=False)
    price = sa.Column(sa.Integer, nullable=False)
    image_filename = sa.Column(sa.String, nullable=True)
    status = sa.Column(sa.String, default='Активно')
    created_at = sa.Column(sa.DateTime, default=datetime.now)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)


class CartItem(SqlAlchemyBase):
    __tablename__ = 'cart_items'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    listing_id = sa.Column(sa.Integer, sa.ForeignKey('listings.id'), nullable=False)
    quantity = sa.Column(sa.Integer, default=1)
    added_at = sa.Column(sa.DateTime, default=datetime.now)


class Order(SqlAlchemyBase):
    __tablename__ = 'orders'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    buyer_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    seller_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    listing_id = sa.Column(sa.Integer, sa.ForeignKey('listings.id'), nullable=False)
    title = sa.Column(sa.String, nullable=False)
    price = sa.Column(sa.Integer, nullable=False)
    delivery_address = sa.Column(sa.String, nullable=True)
    status = sa.Column(sa.String, default='Ожидает оплаты')
    created_at = sa.Column(sa.DateTime, default=datetime.now)
    delivery_date = sa.Column(sa.DateTime, nullable=True)
    delivered_at = sa.Column(sa.DateTime, nullable=True)
