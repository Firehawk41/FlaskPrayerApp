from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import datetime, timezone
import os
import bcrypt

# Load environment variables from .env file
load_dotenv()

# Access environment variables
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
print(os.environ.get('SECRET_KEY'))
print(os.environ.get('SQLALCHEMY_DATABASE_URI'))

# Get currecnt UTC time
current_utc_time = datetime.now(timezone.utc)

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique = True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

class Prayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100),nullable=False)
    description = db.Column(db.Text, nullable=False)
    answered = db.Column(db.Boolean, default=False)
    archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=current_utc_time)
    last_modified = db.Column(db.DateTime, default=current_utc_time, onupdate=current_utc_time)

    user = db.relationship('User', backref=db.backref('prayers', lazy=True))

@app.route('/add_prayer', methods=['GET','POST'])
def add_prayer():
    if request.method == 'POST':
        title = request.form.get('title').strip()
        description = request.form.get('description').strip()
        user_id = session['user_id']

        new_prayer = Prayer(title=title, description=description, user_id=user_id)
        db.session.add(new_prayer)
        db.session.commit()
        flash('Prayer added successfully', 'success')
        return redirect(url_for('index'))
    else:
    
        if 'user_id' not in session:
            flash("Please log in to add a prayer", "error")
            return redirect(url_for('login'))
    
    return render_template('add_prayer.html')
    

@app.route('/prayers')
def view_prayers():
    if 'user_id' not in session:
        flash("Please log in to add a prayer", "error")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_prayers = Prayer.query.filter_by(user_id=user_id).all()
    return render_template('prayers.html', prayers = user_prayers)

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    # Check if the email exists in the database
    user = User.query.filter_by(email=email).first()
    if user:
        # Verify the password
        if user.password and bcrypt.checkpw(password.encode('utf-8'), user.password):
            # Authentication successful
            session['logged_in'] = True
            session['user_id'] = user.id
            session['firstname'] = user.firstname
            session['lastname'] = user.lastname
            print('success')
            flash('Login successful', 'success')
            return redirect(url_for('index'))
    
    # Authentication failed
    flash('Invalid email or password', 'error')
    print('fail')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('firstname', None)
    session.pop('lastname', None)
    return redirect(url_for('index'))

@app.route('/', methods=['GET'])
def index():
    if 'logged_in' in session and session['logged_in']:
        firstname = session.get('firstname')
        lastname = session.get('lastname')
        return render_template('index.html', firstname=firstname, lastname=lastname)
    else:
        return render_template('login.html')
    
    

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        firstname = request.form.get('firstname').strip()
        lastname = request.form.get('lastname').strip()
        email = request.form.get('email').strip()
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        
        # Check if the email already exists in the database
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            # Email already exists, handle accordingly
            return render_template('signup.html', error='Email already exists')

        if password1 != password2:
            return render_template('signup.html', error='Passwords do not match')

        # Has the password before storing it in the database
        hashed_password = bcrypt.hashpw(password1.encode('utf-8'), bcrypt.gensalt())

        new_user = User(firstname=firstname,lastname=lastname, email=email,password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return 'Sign-up successful!'
    
    return render_template('signup.html')



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
