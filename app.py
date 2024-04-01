from flask import Flask, render_template, request, session, redirect, url_for, flash, request, jsonify
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

# Define the many-to-many association between prayers and tags
prayer_tags = db.Table('prayer_tags',
    db.Column('prayer_id', db.Integer, db.ForeignKey('prayer.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True))


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
    tags = db.relationship('Tags', secondary=prayer_tags, lazy='subquery',
        backref=db.backref('prayers', lazy=True))

class Tag(db.Model):
    __tablename__ = 'Tags'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(50), nullable = False)

@app.route('/add_prayer', methods=['POST'])
def add_prayer():
    if request.method == 'POST':
        # Extract data from the form submission
        title = request.form.get('title')
        description = request.form.get('description')
        tag = request.form.get('tag')
        


        if not title or not description or not tag:
            return jsonify({'error': 'Title, description and tag are required'}), 400

        # Create new Prayer object
        new_prayer = Prayer(title=title, description=description, user_id=session['user_id'])
        
        # Add tag to the prayer
        new_tag = Tag.query.filter_by(name=tag).first()
        if not new_tag:
            new_tag = Tag(name=tag)
            db.session.add(new_tag)
            db.session.commit()
        new_prayer.tags.append(New_tag)

        # Add new prayer to database and save changes
        db.session.add(new_prayer)
        db.session.commit()
        
        return jsonify({'message': 'Prayer added successfully'}), 200

    return jsonify({'error': 'Only POST requests are allowed for this route'}), 405
    

@app.route('/prayers')
def view_prayers():
    if 'user_id' not in session:
        flash("Please log in to add a prayer", "error")
        return redirect(url_for('login'))
    
    categories = ["Thanksgiving", "Lament", "Praise", "Wisdom", "Intercession", "Confession" , "Petition", "Healing", "Protection", "Guidance", "Strength", "Unity", "Hope", "Mission"]
    user_id = session['user_id']
    user_prayers = Prayer.query.filter_by(user_id=user_id).all()
    return render_template('prayers.html', prayers = user_prayers, categories=categories)

@app.route('/mark_answered/<int:prayer_id>', methods=['POST'])
def mark_answered(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)

    # Mark the prayer as answered
    prayer.answered = True

    # Commit the changes to the database
    db.session.commit()

    return redirect(url_for('view_prayers'))

@app.route('/mark_pending/<int:prayer_id>', methods=['POST'])
def mark_pending(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)

    # Mark the prayer as answered
    prayer.answered = False

    # Commit the changes to the database
    db.session.commit()

    return redirect(url_for('view_prayers'))

@app.route('/mark_archived/<int:prayer_id>', methods=['POST'])
def mark_archived(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)

    # Mark the prayer as answered
    prayer.archived = True

    # Commit the changes to the database
    db.session.commit()

    return redirect(url_for('view_prayers'))

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

@app.route('/account_settings')
def account_settings():
    
    return render_template('account_settings.html')

@app.route('/update_account', methods=['POST'])
def update_account():
    if request.method == ['POST']:


        return redirect(url_for('account_settings'))

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
