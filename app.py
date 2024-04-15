from flask import  Flask, render_template,  session, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import os
import bcrypt

# Load environment variables from .env file
load_dotenv()

# Access environment variables
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')

# Get currecnt UTC time
current_utc_time = datetime.now(timezone.utc)

db = SQLAlchemy(app)

# Define possible prayer tags
prayer_categories = ["Thanksgiving", "Lament", "Praise", "Wisdom", "Intercession", "Confession" , "Petition", "Healing", "Protection", "Guidance", "Strength", "Unity", "Hope", "Mission"]


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
    answered_at = db.Column(db.DateTime)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)

    user = db.relationship('User', backref=db.backref('prayers', lazy=True))
    tag =  db.relationship('Tag', backref=db.backref('prayers', lazy=True))
    
    def move_to_schedule(self):
        # Calculate the date 1 days from now
        next_pray_date = current_utc_time + timedelta(days=1)
        self.next_pray_date = next_pray_date
        db.session.commit()

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(50), nullable = False, unique=True)

class PrayerHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prayer_id = db.Column(db.Integer, db.ForeignKey('prayer.id'), nullable=False)
    date_prayed = db.Column(db.DateTime, default=current_utc_time)

    prayer = db.relationship('Prayer', backref=db.backref('history'))

@app.before_request
def check_login():
    print("Endpoint: " + str(request.endpoint))
    print("Logged in: " + str(session.get('logged_in',False)))
    if not session.get('logged_in') and request.endpoint != 'login' and request.endpoint != 'signup':
        return redirect(url_for('login'))

@app.route('/add_prayer', methods=['POST'])
def add_prayer():
    if request.method == 'POST':
        # Extract data from the form submission
        title = request.form.get('title')
        description = request.form.get('description')
        tag_name = request.form.get('tag')
        
        print(title)
        print(description)
        print(tag_name)

        if not title or not description or not tag_name:
            return jsonify({'error': 'Title, description and tag are required'}), 400


        
        # Add tag to the prayer
        existing_tag = Tag.query.filter_by(name=tag_name).first()
        if not existing_tag:
            # If the tag doesn't exist, create a new one
            new_tag = Tag(name=tag_name)
            db.session.add(new_tag)
            db.session.commit()
        else:
            new_tag = existing_tag

        # Create new Prayer object
        new_prayer = Prayer(title=title, description=description, user_id=session['user_id'], tag=new_tag)

        # Add new prayer to database and save changes
        db.session.add(new_prayer)
        db.session.commit()
        
        return jsonify({'message': 'Prayer added successfully'}), 200

    return jsonify({'error': 'Only POST requests are allowed for this route'}), 405
    
@app.route('/edit_prayer/<int:prayer_id>', methods=['GET', 'POST'])
def edit_prayer(prayer_id):
    # Retrieve the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)
    tag_name = request.form.get('tag')

    if request.method == 'POST':
        # Update prayer details based on form submission
        prayer.title = request.form['title']
        prayer.description = request.form['description']

        # Add tag to the prayer
        existing_tag = Tag.query.filter_by(name=tag_name).first()
        if not existing_tag:
            new_tag = Tag(name=tag_name)
            db.session.add(new_tag)
            db.session.commit()
        else:
            new_tag = existing_tag

        prayer.tag = new_tag

        if request.form['status'] == "answered":
            prayer.answered = True
        else:
            prayer.answered = False
        #prayer.answered = request.form['answered']

        # Commit changes to the database
        db.session.commit()

        flash('Prayer updated successfully', 'success')
        return redirect(url_for('view_prayers'))
    
    # Render the edit prayer form
    return render_template('edit_prayer.html', prayer=prayer, categories=prayer_categories)

@app.route('/prayers')
def view_prayers():
    if 'user_id' not in session:
        flash("Please log in to add a prayer", "error")
        return redirect(url_for('login'))
    
    categories = ["Thanksgiving", "Lament", "Praise", "Wisdom", "Intercession", "Confession" , "Petition", "Healing", "Protection", "Guidance", "Strength", "Unity", "Hope", "Mission"]
    user_id = session['user_id']
    user_prayers = Prayer.query.filter_by(user_id=user_id).all()
    return render_template('prayers.html', prayers = user_prayers, categories=prayer_categories)

@app.route('/mark_answered/<int:prayer_id>', methods=['POST'])
def mark_answered(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)

    # Mark the prayer as answered
    prayer.answered = True

    # Set the answered date
    prayer.answered_at = current_utc_time

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

@app.route('/mark_prayed/<int:prayer_id>', methods=['POST'])
def mark_prayed(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)

    # Mark the prayer as prayed
    prayer_history = PrayerHistory(prayer_id=prayer.id, date_prayed=current_utc_time)
    db.session.add(prayer_history)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/delete_prayer/<int:prayer_id>', methods=['POST'])
def delete_prayer(prayer_id):
    prayer = Prayer.query.get_or_404(prayer_id)
    db.session.delete(prayer)
    db.session.commit()
    flash('Item deleted.')
    return redirect(url_for('index'))


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

        user_id = session['user_id']
        user_prayers = Prayer.query.filter_by(user_id=user_id).all()

        # Create empty lists
        filtered_prayers = []
        prayed_today_prayers = []

        # Filter the prayers to display as daily prayers
        for prayer in user_prayers:
            # Set as boolean values
            within_seven_days = False
            prayed_today = False

            # Check whether a prayer has been answered more than 7 days ago
            if prayer.answered_at:
                answered_at = prayer.answered_at.replace(tzinfo=timezone.utc)
                time_difference = current_utc_time - answered_at
                within_seven_days = time_difference <= timedelta(days=7)

            # Check whether a prayer has been prayed today
            if prayer.history:
                    last_prayed_date = PrayerHistory.query.filter_by(prayer_id=prayer.id).order_by(PrayerHistory.date_prayed.desc()).first().date_prayed.date()
                    prayed_today = last_prayed_date == current_utc_time.date()

            # Add prayers to either the prayed today list or the filtered list
            if prayed_today:
                prayed_today_prayers.append(prayer)        
            elif not prayer.archived and (not prayer.answered or within_seven_days):
                filtered_prayers.append(prayer)

        return render_template('index.html', firstname=firstname, lastname=lastname, filtered_prayers = filtered_prayers, prayed_today_prayers=prayed_today_prayers)
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
        flash('Sign-up successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
