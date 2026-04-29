from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from datetime import timedelta, datetime
from db import global_init
from users import User
from login import Login

global_init("shop.db")

app = Flask(__name__)
app.secret_key = "simple-secret-key-123"
app.permanent_session_lifetime = timedelta(days=7)
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


@app.before_request
def make_session_permanent():
    session.permanent = True
    if 'user_id' in session:
        session.modified = True


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
            return redirect(url_for('profile'))
        return render_template('login.html')
    username = request.form.get('username')
    password = request.form.get('password')
    remember_me = request.form.get('remember_me') == 'on'
    login_manager = Login()
    result = login_manager.authenticate(username, password)
    login_manager.close()

    if result['success']:
        session.permanent = True
        session['session_token'] = result['session_token']
        session['username'] = result['username']
        session['user_id'] = result['user_id']
        session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if remember_me:
            app.permanent_session_lifetime = timedelta(days=30)
        else:
            app.permanent_session_lifetime = timedelta(days=7)
        return redirect(url_for('home'))
    else:
        return render_template('login.html', error=result['message'])


@app.route('/profile')
def profile():
    if not session.get('user_id'):
        print('redirect')
        return redirect(url_for('login'))
    session_token = session.get('session_token')
    login_manager = Login()
    user = login_manager.get_current_user(session_token)
    login_manager.close()
    if user:
        return render_template('profile.html', user=user)
    else:
        session.clear()
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session_token = session.get('session_token')
    if session_token:
        login_manager = Login()
        login_manager.logout(session_token)
        login_manager.close()

    session.clear()
    return redirect(url_for('home'))


@app.route('/check-session')
def check_session():
    return {
        'session': dict(session),
        'has_user_id': 'user_id' in session,
        'username': session.get('username')
    }


# @app.route('/session-info')
# def session_info():
#     if not session.get('user_id'):
#         return redirect(url_for('login'))
#     info = {
#         'session_id': session.get('session_token'),
#         'user_id': session.get('user_id'),
#         'username': session.get('username'),
#         'login_time': session.get('login_time'),
#         'is_permanent': session.permanent,
#         'session_lifetime_days': app.permanent_session_lifetime.days
#     }
#     return render_template('session_info.html', info=info)


if __name__ == '__main__':
    app.run(debug=True)