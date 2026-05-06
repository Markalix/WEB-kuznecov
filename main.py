from flask import Flask, request, session, redirect, url_for, render_template, jsonify
from datetime import timedelta, datetime
from db import global_init, create_session
from models import User as UserModel, Listing, CartItem, Order
import os
from werkzeug.utils import secure_filename
import threading
import time
import urllib.parse
import requests
import json

global_init("shop.db")

app = Flask(__name__)
app.secret_key = "simple-secret-key-123"

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

YANDEX_GEOCODER_API_KEY = "8013b162-6b42-4997-9691-77b7074026e0"


def geocode_address(address):
    try:
        encoded_address = urllib.parse.quote(address)
        url = f"https://geocode-maps.yandex.ru/1.x/?apikey={YANDEX_GEOCODER_API_KEY}&geocode={encoded_address}&format=json"

        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            pos = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
            lon, lat = pos.split()
            return float(lon), float(lat)
    except Exception as e:
        print(f"Ошибка геокодирования: {e}")
    return 37.6177, 55.7558


def get_static_map_image(address):
    try:
        lon, lat = geocode_address(address)
        map_url = f"https://static-maps.yandex.ru/1.x/?ll={lon},{lat}&z=15&l=map&size=400,200&pt={lon},{lat},pm2dgl"
        return map_url, lon, lat
    except Exception as e:
        print(f"Ошибка создания карты: {e}")
        return None, 37.6177, 55.7558


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app.permanent_session_lifetime = timedelta(days=7)
app.config['SESSION_PERMANENT'] = True


@app.before_request
def make_session_permanent():
    session.permanent = True


@app.context_processor
def inject_session():
    if session.get('user_id'):
        db = create_session()
        user = db.query(UserModel).filter(UserModel.id == session['user_id']).first()
        if user:
            session['balance'] = user.balance
        db.close()
    return dict(session=session)


def update_delivery_status():
    while True:
        time.sleep(60)
        try:
            db = create_session()
            now = datetime.now()

            orders_to_deliver = db.query(Order).filter(
                Order.status == 'В пути',
                Order.delivery_date <= now
            ).all()

            for order in orders_to_deliver:
                order.status = 'Доставлено'
                order.delivered_at = now

            if orders_to_deliver:
                db.commit()

            db.close()
        except Exception as e:
            print(f"Ошибка в фоновой задаче: {e}")


delivery_thread = threading.Thread(target=update_delivery_status, daemon=True)
delivery_thread.start()


@app.route('/')
def home():
    db = create_session()

    all_listings = db.query(Listing).filter(Listing.status == 'Активно').order_by(Listing.created_at.desc()).all()
    if session.get('user_id'):
        cart_items = db.query(CartItem).filter(CartItem.user_id == session['user_id']).all()
        cart_listing_ids = [item.listing_id for item in cart_items]
        all_listings = [listing for listing in all_listings if listing.id not in cart_listing_ids]

    db.close()
    return render_template('home.html', all_listings=all_listings)


@app.route('/add-to-cart/<int:listing_id>', methods=['POST'])
def add_to_cart(listing_id):
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Войдите в аккаунт'}), 401

    db = create_session()

    listing = db.query(Listing).filter(Listing.id == listing_id).first()

    if not listing:
        db.close()
        return jsonify({'success': False, 'message': 'Товар не найден'}), 404

    if listing.status != 'Активно':
        db.close()
        return jsonify({'success': False, 'message': 'Товар уже продан'}), 400

    if listing.user_id == session['user_id']:
        db.close()
        return jsonify({'success': False, 'message': 'Нельзя добавить свой товар'}), 400

    existing = db.query(CartItem).filter(
        CartItem.user_id == session['user_id'],
        CartItem.listing_id == listing_id
    ).first()

    if existing:
        existing.quantity += 1
    else:
        cart_item = CartItem(
            user_id=session['user_id'],
            listing_id=listing_id
        )
        db.add(cart_item)

    db.commit()
    db.close()

    return jsonify({'success': True, 'message': 'Товар добавлен в корзину'})


@app.route('/cart')
def cart():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    db = create_session()
    cart_items = db.query(CartItem).filter(CartItem.user_id == session['user_id']).all()

    items = []
    total = 0
    for item in cart_items:
        listing = db.query(Listing).filter(Listing.id == item.listing_id).first()
        if listing and listing.status == 'Активно':
            item_total = listing.price * item.quantity
            total += item_total
            items.append({
                'id': item.id,
                'listing_id': listing.id,
                'title': listing.title,
                'price': listing.price,
                'quantity': item.quantity,
                'total': item_total,
                'image_filename': listing.image_filename
            })
        else:
            db.delete(item)
            db.commit()

    db.close()
    return render_template('cart.html', items=items, total=total)


@app.route('/remove-from-cart/<int:cart_item_id>', methods=['POST'])
def remove_from_cart(cart_item_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    db = create_session()
    cart_item = db.query(CartItem).filter(
        CartItem.id == cart_item_id,
        CartItem.user_id == session['user_id']
    ).first()

    if cart_item:
        db.delete(cart_item)
        db.commit()

    db.close()
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    if request.method == 'GET':
        db = create_session()
        cart_items = db.query(CartItem).filter(CartItem.user_id == session['user_id']).all()

        total = 0
        for item in cart_items:
            listing = db.query(Listing).filter(Listing.id == item.listing_id).first()
            if listing and listing.status == 'Активно':
                total += listing.price * item.quantity

        db.close()
        return render_template('delivery.html', total=total)

    delivery_address = request.form.get('delivery_address')

    if not delivery_address:
        return render_template('delivery.html', error="Укажите адрес доставки")

    db = create_session()
    buyer = db.query(UserModel).filter(UserModel.id == session['user_id']).first()
    cart_items = db.query(CartItem).filter(CartItem.user_id == session['user_id']).all()

    if not cart_items:
        db.close()
        return redirect(url_for('cart'))

    total = 0
    items_to_buy = []
    error = None

    for item in cart_items:
        listing = db.query(Listing).filter(Listing.id == item.listing_id).first()
        if not listing or listing.status != 'Активно':
            error = f"Товар '{listing.title if listing else 'неизвестный'}' больше не доступен"
            break

        item_total = listing.price * item.quantity
        total += item_total
        items_to_buy.append({
            'cart_item': item,
            'listing': listing,
            'quantity': item.quantity
        })

    if error:
        for item in cart_items:
            db.delete(item)
        db.commit()
        db.close()
        return render_template('delivery.html', total=total, error=error)

    if buyer.balance < total:
        db.close()
        return render_template('delivery.html', total=total,
                               error=f'Недостаточно средств. Нужно {total} ₽, у вас {buyer.balance} ₽')

    try:
        buyer.balance -= total
        delivery_date = datetime.now() + timedelta(days=3)

        for item_data in items_to_buy:
            listing = item_data['listing']
            quantity = item_data['quantity']
            seller = db.query(UserModel).filter(UserModel.id == listing.user_id).first()

            item_total = listing.price * quantity
            seller_earn = int(item_total * 0.89)
            seller.balance += seller_earn

            listing.status = 'Продано'

            order = Order(
                buyer_id=buyer.id,
                seller_id=seller.id,
                listing_id=listing.id,
                title=listing.title,
                price=listing.price,
                delivery_address=delivery_address,
                status='В пути',
                delivery_date=delivery_date
            )
            db.add(order)

            db.delete(item_data['cart_item'])

        db.commit()

    except Exception as e:
        db.rollback()
        db.close()
        return render_template('delivery.html', total=total, error="Ошибка при оформлении заказа")

    db.close()
    return redirect(url_for('profile'))


@app.route('/get-map/<int:order_id>')
def get_map(order_id):
    if not session.get('user_id'):
        return jsonify({'error': 'Не авторизован'}), 401

    db = create_session()
    order = db.query(Order).filter(Order.id == order_id, Order.buyer_id == session['user_id']).first()
    db.close()

    if not order:
        return jsonify({'error': 'Заказ не найден'}), 404

    map_url, lon, lat = get_static_map_image(order.delivery_address)

    return jsonify({
        'map_url': map_url,
        'lon': lon,
        'lat': lat,
        'address': order.delivery_address
    })


@app.route('/topup', methods=['GET', 'POST'])
def topup():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('topup.html')

    card_number = request.form.get('card_number')
    card_holder = request.form.get('card_holder')
    expiry_date = request.form.get('expiry_date')
    cvv = request.form.get('cvv')
    amount = request.form.get('amount')

    if not card_number or not card_holder or not expiry_date or not cvv or not amount:
        return render_template('topup.html', error="Заполните все поля")

    if len(card_number) < 16:
        return render_template('topup.html', error="Неверный номер карты")

    if len(cvv) < 3:
        return render_template('topup.html', error="Неверный CVV код")

    try:
        amount = int(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return render_template('topup.html', error="Сумма должна быть положительным числом")

    db = create_session()
    user = db.query(UserModel).filter(UserModel.id == session['user_id']).first()
    user.balance += amount
    db.commit()
    db.close()

    return render_template('topup.html', message=f"Баланс успешно пополнен на {amount} ₽!")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    db = create_session()
    existing = db.query(UserModel).filter(
        (UserModel.username == username) | (UserModel.email == email)
    ).first()

    if existing:
        db.close()
        return render_template('register.html', error="Пользователь уже существует")

    new_user = UserModel(
        username=username,
        email=email,
        password=password,
        balance=5000
    )

    db.add(new_user)
    db.commit()
    db.close()

    return render_template('register.html', message="Регистрация успешна! Теперь войдите.")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if session.get('user_id'):
            return redirect(url_for('home'))
        return render_template('login.html')

    username = request.form.get('username')
    password = request.form.get('password')
    remember_me = request.form.get('remember_me') == 'on'

    db = create_session()
    user = db.query(UserModel).filter(UserModel.username == username).first()
    db.close()

    if not user or user.password != password:
        return render_template('login.html', error="Неверное имя пользователя или пароль")

    session.permanent = True
    session['user_id'] = user.id
    session['username'] = user.username
    session['email'] = user.email
    session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    session['balance'] = user.balance

    if remember_me:
        app.permanent_session_lifetime = timedelta(days=30)
    else:
        app.permanent_session_lifetime = timedelta(days=7)

    return redirect(url_for('home'))


@app.route('/profile')
def profile():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    db = create_session()
    user = db.query(UserModel).filter(UserModel.id == session['user_id']).first()

    listings = db.query(Listing).filter(Listing.user_id == session['user_id']).order_by(Listing.created_at.desc()).all()
    purchases = db.query(Order).filter(Order.buyer_id == session['user_id']).order_by(Order.created_at.desc()).all()
    sales = db.query(Order).filter(Order.seller_id == session['user_id']).order_by(Order.created_at.desc()).all()

    db.close()

    balance_formatted = round(user.balance, 2)

    return render_template('profile.html', user=user, balance=balance_formatted,
                           listings=listings, purchases=purchases, sales=sales)


@app.route('/add-listing', methods=['GET', 'POST'])
def add_listing():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('add_listing.html')

    title = request.form.get('title')
    description = request.form.get('description')
    price = request.form.get('price')
    image_file = request.files.get('image')
    image_filename = None

    if image_file and image_file.filename:
        if allowed_file(image_file.filename):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = secure_filename(image_file.filename)
            name, ext = os.path.splitext(safe_filename)
            image_filename = f"{session['user_id']}_{timestamp}_{name}{ext}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)
        else:
            return render_template('add_listing.html', error="Неподдерживаемый формат изображения")

    if not title or not description or not price:
        return render_template('add_listing.html', error="Заполните все поля")

    try:
        price = int(price)
        if price <= 0:
            raise ValueError
    except ValueError:
        return render_template('add_listing.html', error="Цена должна быть положительным числом")

    db = create_session()
    new_listing = Listing(
        title=title,
        description=description,
        price=price,
        image_filename=image_filename,
        user_id=session['user_id'],
        status='Активно'
    )

    db.add(new_listing)
    db.commit()
    db.close()

    return render_template('add_listing.html', message="Объявление успешно добавлено!")


@app.route('/delete-listing/<int:listing_id>', methods=['POST'])
def delete_listing(listing_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    db = create_session()
    listing = db.query(Listing).filter(Listing.id == listing_id, Listing.user_id == session['user_id']).first()

    if listing:
        if listing.image_filename:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], listing.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        db.delete(listing)
        db.commit()

    db.close()
    return redirect(url_for('profile'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/api/cart-count')
def api_cart_count():
    if not session.get('user_id'):
        return jsonify({'count': 0})

    db = create_session()
    count = db.query(CartItem).filter(CartItem.user_id == session['user_id']).count()
    db.close()

    return jsonify({'count': count})


if __name__ == '__main__':
    app.run(debug=True)
