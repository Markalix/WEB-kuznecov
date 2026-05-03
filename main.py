from flask import Flask, request, session, redirect, url_for, render_template
from datetime import timedelta, datetime
from db import global_init
from users import User
from login import Login

global_init("shop.db")

app = Flask(__name__)
app.secret_key = ""

app.permanent_session_lifetime = timedelta(days=7)
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


@app.before_request
def make_session_permanent():
    session.permanent = True


@app.context_processor
def inject_session():
    return dict(session=session)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    user_manager = User()
    result = user_manager.register(username, email, password)
    user_manager.close()

    if result['success']:
        return render_template('register.html', message=result['message'])
    else:
        return render_template('register.html', error=result['message'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if session.get('user_id'):
            return redirect(url_for('home'))
        return render_template('login.html')

    username = request.form.get('username')
    password = request.form.get('password')
    remember_me = request.form.get('remember_me') == 'on'

    login_manager = Login()
    result = login_manager.authenticate(username, password)
    login_manager.close()

    if result['success']:
        session.permanent = True
        session['user_id'] = result['user_id']
        session['username'] = result['username']
        session['email'] = result['email']
        session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if remember_me:
            app.permanent_session_lifetime = timedelta(days=30)
        else:
            app.permanent_session_lifetime = timedelta(days=7)

        print(f"Пользователь {username} вошел в систему")
        print(f"Данные сессии: user_id={session['user_id']}, username={session['username']}")

        return redirect(url_for('home'))
    else:
        return render_template('login.html', error=result['message'])


@app.route('/profile')
def profile():
    if not session.get('user_id'):
        print("Нет user_id в сессии, перенаправляем на вход")
        return redirect(url_for('login'))

    print(f"Данные сессии в profile: user_id={session.get('user_id')}, username={session.get('username')}")
    login_manager = Login()
    user = login_manager.get_user_by_id(session['user_id'])
    login_manager.close()

    if user:
        return render_template('profile.html', user=user)
    else:
        print("Пользователь не найден в БД, очищаем сессию")
        session.clear()
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    print("Пользователь вышел из системы")
    return redirect(url_for('home'))


@app.route('/check-session')
def check_session():
    return {
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'email': session.get('email'),
        'login_time': session.get('login_time'),
        'is_authenticated': 'user_id' in session
    }


@app.route('/session-info')
def session_info():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    info = {
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'email': session.get('email'),
        'login_time': session.get('login_time'),
        'is_permanent': session.permanent,
        'session_lifetime_days': app.permanent_session_lifetime.days
    }
    return render_template('session_info.html', info=info)


if __name__ == '__main__':
    app.run(debug=True)