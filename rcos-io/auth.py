from flask import (
    Blueprint, flash, g, redirect, render_template, request, session
)

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = { "id": user_id }

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')
    elif request.method == 'POST':
        email = request.form['email']
        session['user_email'] = email

        # Generate OTP
        otp = '1234567'
        session['user_otp'] = otp

        print('OTP:', otp)

        return render_template('auth/login.html')
    
@bp.route('/login/otp', methods=('POST',))
def finish_login():
    submitted_otp = request.form['otp']

    if submitted_otp == session['user_otp']:
        # Fetch user and store in session
        session['user_id'] = "abcd"
        print("logged in!")
    else:
        flash("Wrong code!")
            
    session.pop('user_otp')
    session.pop('user_email')

    return redirect('/')