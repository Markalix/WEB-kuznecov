from flask import Flask, request, jsonify, session as flask_session
from db import global_init
from users import User
from login import Login

global_init("shop.db")

app = Flask(__name__)
app.secret_key = "simple-secret-key-123"


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    user_manager = User()

    result = user_manager.register(
        username=data.get('username'),
        email=data.get('email'),
        password=data.get('password')
    )

    user_manager.close()
    return jsonify(result)


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    login_manager = Login()

    result = login_manager.authenticate(
        username=data.get('username'),
        password=data.get('password')
    )

    login_manager.close()

    if result['success']:
        flask_session['session_token'] = result['session_token']

    return jsonify(result)


@app.route('/profile', methods=['GET'])
def profile():
    session_token = flask_session.get('session_token')
    if not session_token:
        return jsonify({"error": "Не авторизован"}), 401

    login_manager = Login()
    user = login_manager.get_current_user(session_token)
    login_manager.close()

    if user:
        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email
        })

    return jsonify({"error": "Сессия недействительна"}), 401


@app.route('/logout', methods=['POST'])
def logout():
    session_token = flask_session.get('session_token')
    if session_token:
        login_manager = Login()
        result = login_manager.logout(session_token)
        login_manager.close()
        flask_session.pop('session_token', None)
        return jsonify(result)

    return jsonify({"success": False, "message": "Нет активной сессии"})


@app.route('/check-auth', methods=['GET'])
def check_auth():
    session_token = flask_session.get('session_token')
    if session_token:
        login_manager = Login()
        is_auth = login_manager.is_authenticated(session_token)
        login_manager.close()
        return jsonify({"authenticated": is_auth})
    return jsonify({"authenticated": False})


if __name__ == '__main__':
    app.run(debug=True)
