from flask import  Flask, render_template, session, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy, pagination
from dotenv import load_dotenv
from datetime import datetime, timezone as dt_timezone, timedelta
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
import os
from bcrypt import checkpw
import bcrypt
from sqlalchemy import and_, not_, or_, case, func, text, union
from flask_wtf.csrf import CSRFProtect
from wtforms import SelectField, StringField, IntegerField, SelectMultipleField, BooleanField, widgets
from wtforms.validators import DataRequired, Email, Length, InputRequired, NumberRange
from pytz import common_timezones, timezone
from flask_wtf import FlaskForm

# Load environment variables from .env file
load_dotenv()

# Access environment variables
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
login_manager = LoginManager(app)
csrf = CSRFProtect(app)

# Get current UTC time
current_utc_time = datetime.now(dt_timezone.utc)

db = SQLAlchemy(app)

# Define possible prayer tags
prayer_categories = ["Thanksgiving", "Lament", "Praise", "Wisdom", "Intercession", "Confession" , "Petition", "Healing", "Protection", "Guidance", "Strength", "Unity", "Hope", "Mission"]
days_of_week=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
DEFAULT_PER_PAGE = 5

class AccountSettingsForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    lastname = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    timezone = SelectField('Timezone', choices=[(tz, tz) for tz in common_timezones], validators=[Length(max=100)])
    thankfulness_length = IntegerField('Number of days to remember an answered prayer', validators=[DataRequired(), NumberRange(min=0, max=99)])

class AddPrayerForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired()])
    description = StringField('Description', validators=[InputRequired(), Length(max=256)])
    tag = SelectField('Tag', coerce=int, validators=[InputRequired()], choices=[(i, category) for i, category in enumerate(prayer_categories)])
    sunday = BooleanField('Sunday')
    monday = BooleanField('Monday')
    tuesday = BooleanField('Tuesday')
    wednesday = BooleanField('Wednesday')
    thursday = BooleanField('Thursday')
    friday = BooleanField('Friday')
    saturday = BooleanField('Saturday')
    sharable = SelectField('Share with friends?', choices=[('False', 'Private'), ('True', 'Sharable')])



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique = True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    timezone = db.Column(db.String(64), nullable=False, default='America/Chicago')
    thankfulness_length = db.Column(db.Integer, nullable=False,default=7)

    history = db.relationship('PrayerHistory', back_populates='user')

    def get_id(self):
        return str(self.id)

    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password)

class Prayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100),nullable=False)
    description = db.Column(db.String(256), nullable=False)
    answered = db.Column(db.Boolean, default=False)
    archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=current_utc_time)
    last_modified = db.Column(db.DateTime, default=current_utc_time, onupdate=current_utc_time)
    answered_at = db.Column(db.DateTime)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)
    sunday = db.Column(db.Boolean, default=True)
    monday = db.Column(db.Boolean, default=True)
    tuesday = db.Column(db.Boolean, default=True)
    wednesday = db.Column(db.Boolean, default=True)
    thursday = db.Column(db.Boolean, default=True)
    friday = db.Column(db.Boolean, default=True)
    saturday = db.Column(db.Boolean, default=True)
    sharable = db.Column(db.Boolean, default=False)
    

    user = db.relationship('User', backref=db.backref('prayers', lazy=True))
    tag =  db.relationship('Tag', backref=db.backref('prayers', lazy=True))

    history = db.relationship('PrayerHistory', back_populates='prayer', cascade='all, delete-orphan')

    answered_prayer = db.relationship('AnsweredPrayer', back_populates='original_prayer', uselist = False, cascade='all, delete-orphan')

    
    def move_to_schedule(self):
        # Calculate the date 1 days from now
        next_pray_date = current_utc_time + timedelta(days=1)
        self.next_pray_date = next_pray_date
        db.session.commit()

class AnsweredPrayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_prayer_id = db.Column(db.Integer, db.ForeignKey('prayer.id'),nullable = False)
    content = db.Column(db.Text,nullable = False)
    created_at = db.Column(db.DateTime, default=current_utc_time)


    original_prayer = db.relationship('Prayer', back_populates='answered_prayer')

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(50), nullable = False, unique=True)

class PrayerHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prayer_id = db.Column(db.Integer, db.ForeignKey('prayer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_prayed = db.Column(db.DateTime, default=current_utc_time)

    prayer = db.relationship('Prayer', back_populates='history')
    user = db.relationship('User', back_populates='history')

class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.Enum('Pending', 'Accepted', 'Declined'), default='Pending', nullable=False)
    sent_at = db.Column(db.DateTime, default=current_utc_time)
    updated_at = db.Column(db.DateTime, onupdate=current_utc_time)

    # Define relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_friend_requests')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_friend_requests')

    # Function to check whether a friendship exists
    @staticmethod
    def are_friends(user1_id, user2_id):
        friend_request = FriendRequest.query.filter((FriendRequest.sender_id ==user1_id) & (FriendRequest.receiver_id == user2_id) & (FriendRequest.status == 'Accepted')).first()

        return friend_request is not None


@login_manager.user_loader
def load_user(user_id):
    #return User.query.get(int(user_id))
    return db.session.get(User,int(user_id))

    

@app.route('/add_prayer', methods=['POST', 'GET'])
@login_required
def add_prayer():

    form = AddPrayerForm()

    # Set all reminder_days as selected by default
    for field_name in ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']:
        getattr(form, field_name).data = True

    if form.validate_on_submit():
        # Extract data from the validating form
        title = form.title.data
        description = form.description.data
        tag_name = form.tag.label.text
        sharable = True if form.sharable.data == 'True' else False
        tag_id = get_or_create_tag_id(tag_name)
        
        # Add new Prayer object and commit changes
        new_prayer = Prayer(user_id=current_user.id, title=title, description=description, tag_id=tag_id,sunday=form.sunday.data, monday=form.monday.data, 
                            tuesday=form.tuesday.data, wednesday=form.wednesday.data,thursday=form.thursday.data,friday=form.friday.data,saturday=form.saturday.data,
                            sharable = sharable)
        db.session.add(new_prayer)
        db.session.commit()

        # Flash success notification and redirect home
        flash('Prayer added successfully.', 'success')
        return redirect(url_for('home'))
    
    return render_template('add_prayer.html', form=form, page_name='add_prayer')

def get_or_create_tag_id(tag_name):
    # Add tag to the prayer
    existing_tag = Tag.query.filter_by(name=tag_name).first()
    if not existing_tag:
        # If the tag doesn't exist, create a new one
        new_tag = Tag(name=tag_name)
        db.session.add(new_tag)
        db.session.commit()
        return new_tag.id
    else:
        return existing_tag.id

@app.route('/edit_prayer/<int:prayer_id>', methods=['GET', 'POST'])
@login_required
def edit_prayer(prayer_id):
    
    form = AddPrayerForm()

    # Retrieve the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)
    tag_name = request.form.get('tag')

    if prayer.user.id != current_user.id:
        flash("You cannot edit another user's prayer.", "error")
        return redirect(home)
    
    # Find the index of the tag name in the list of choices
    tag_index = next((i for i, name in enumerate(prayer_categories) if name == prayer.tag.name), None)

    print("current prayer name: " + str(prayer.tag.name))
    print("tag data: " + str(form.tag.data))
    form.title.data = prayer.title
    form.description.data = prayer.description
    
    
    form.tag.data = tag_index
    form.sharable.text = 'Sharable' if prayer.sharable == True else 'Private'


    # Set all reminder_days as selected by default
    for field_name in ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']:
        getattr(form, field_name).data = getattr(prayer, field_name)

    if form.validate_on_submit():
        # Extract data from the validating form
        title = form.title.data
        description = form.description.data
        tag_name = form.tag.label.text
        sharable = True if form.sharable.data == 'True' else False
        tag_id = get_or_create_tag_id(tag_name)
        
        # Add new Prayer object and commit changes
        new_prayer = Prayer(user_id=current_user.id, title=title, description=description, tag_id=tag_id,sunday=form.sunday.data, monday=form.monday.data, 
                            tuesday=form.tuesday.data, wednesday=form.wednesday.data,thursday=form.thursday.data,friday=form.friday.data,saturday=form.saturday.data,
                            sharable = sharable)
        db.session.add(new_prayer)
        db.session.commit()

        # Flash success notification and redirect home
        flash('Prayer editted successfully.', 'success')
        return redirect(url_for('home'))
    
    return render_template('add_prayer.html', form=form, page_name='edit_prayer')

    prev_url = request.args.get('prev_url', '/')

    # Retrieve the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)
    tag_name = request.form.get('tag')

    if prayer.user.id != current_user.id:
        flash("You cannot edit another user's prayer.", "error")
        return redirect(prev_url)

    if request.method == 'POST':
        # Update prayer details based on form submission
        prayer.title = request.form['title']
        prayer.description = request.form['description']

        # Update reminder days to prayer
        reminder_days = request.form.getlist('reminderDays')
        prayer.reminder = ",".join(reminder_days)

        # Add tag to the prayer
        existing_tag = Tag.query.filter_by(name=tag_name).first()
        if not existing_tag:
            new_tag = Tag(name=tag_name)
            db.session.add(new_tag)
            db.session.commit()
        else:
            new_tag = existing_tag

        prayer.tag = new_tag

        # Update the prayer status
        if request.form['status'] == "answered":
            prayer.answered = True
        else:
            prayer.answered = False

        # Update the sharing
        if request.form['sharable'] == "shared":
            prayer.sharable = True
        else:
            prayer.sharable = False


        # Commit changes to the database
        db.session.commit()

        flash('Prayer updated successfully', 'success')
        return redirect(prev_url)
    
    # Render the edit prayer form
    return render_template('edit_prayer.html', prayer=prayer, categories=prayer_categories, days_of_week=days_of_week)

@app.route('/prayers')
@login_required
def view_prayers():
    
    # Retrieve all user's prayers
    user_id = current_user.id
    user_prayers_query = Prayer.query.filter_by(user_id=user_id)




    # Paginate prayers
    page = request.args.get('page', 1, type=int)
    paginated_prayers = user_prayers_query.paginate(page=page, per_page=DEFAULT_PER_PAGE, error_out=False)

    return render_template('prayers.html', prayers = paginated_prayers, categories=prayer_categories, page_name='view_prayers', page=page)


@app.route('/mark_answered/<int:prayer_id>', methods=['POST'])
@login_required
def mark_answered(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)
    print('Found prayer')
    # Prevent editing of other users' prayers
    if prayer.user.id != current_user.id:
        flash("You cannot edit another user's prayer.", "error")
        return redirect('view_prayers')
    
    # Mark the prayer as answered
    prayer.answered = True

    # Set the answered date
    prayer.answered_at = current_utc_time

    # Commit the changes to the database
    db.session.commit()

    return redirect(url_for('view_prayers'))


@app.route('/mark_pending/<int:prayer_id>', methods=['POST'])
@login_required
def mark_pending(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)

    # Prevent editing of other users' prayers
    if prayer.user.id != current_user.id:
        flash("You cannot edit another user's prayer.", "error")
        return redirect('view_prayers')

    # Mark the prayer as answered
    prayer.answered = False

    # Commit the changes to the database
    db.session.commit()

    return redirect(url_for('view_prayers'))


@app.route('/mark_archived/<int:prayer_id>', methods=['POST'])
@login_required
def mark_archived(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)

    # Prevent editing of other users' prayers
    if prayer.user.id != current_user.id:
        flash("You cannot edit another user's prayer.", "error")
        return redirect('view_prayers')
    
    # Mark the prayer as answered
    prayer.archived = True

    # Commit the changes to the database
    db.session.commit()

    return redirect(url_for('view_prayers'))


@app.route('/mark_prayed/<int:prayer_id>', methods=['POST'])
@login_required
def mark_prayed(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)
    print('Found prayer: ' + str(prayer.title) + ".")
    
    # Mark the prayer as prayed
    prayer_history = PrayerHistory(prayer_id=prayer.id, user_id=current_user.id)

    print("Created new prayer_history: " + str(prayer_history.id) + ".")

    db.session.add(prayer_history)
    db.session.commit()

    return redirect(url_for('home'))


@app.route('/delete_prayer/<int:prayer_id>', methods=['POST'])
@login_required
def delete_prayer(prayer_id):
    prayer = Prayer.query.get_or_404(prayer_id)
    
    # Prevent editing of other users' prayers
    if prayer.user.id != current_user.id:
        flash("You cannot edit another user's prayer.", "error")
        return redirect('view_prayers')
    
    db.session.delete(prayer)
    db.session.commit()

    flash('Item deleted.')

    return redirect(url_for('home'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    # Render your login page template
    return render_template('login.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        # Check if the email exists in the database
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            print('login success')

            return redirect(url_for('home'))
        else:
            # Authentication failed
            flash('Invalid email or password', 'error')
            print('fail')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/account_settings', methods=['POST', 'GET'])
@login_required
def account_settings():

    # Instantiate the form
    form = AccountSettingsForm()

    # Populate the form fields with the current user's data
    form.firstname.data = current_user.firstname
    form.lastname.data = current_user.lastname
    form.email.data = current_user.email
    form.timezone.data = current_user.timezone
    form.thankfulness_length.data = current_user.thankfulness_length

    if form.validate_on_submit():
        # Update the current user's data with the form data
        current_user.firstname = form.firstname.data
        current_user.lastname = form.lastname.data
        current_user.email = form.email.data
        current_user.timezone = form.timezone.data
        current_user.thankfulness_length = form.thankfulness_length.data

        # Commit changes to the database
        db.session.commit()

        # Flash success message
        flash('Account settings updated successfully.', 'success')

        # Redirect back to the account settings page
        return redirect(url_for('account_settings'))
    
    # Render the template with the form
    return render_template('account_settings.html', form=form)


@app.route('/update_account', methods=['POST'])
@login_required
def update_account():
    if request.method == ['POST']:


        return redirect(url_for('account_settings'))

@app.route('/home', methods=['GET'])
@login_required
def home():
    # Get the current user's information
    firstname = current_user.firstname
    lastname = current_user.lastname

    # Calculates the date seven days ago
    seven_days_ago = current_utc_time - timedelta(days=7)

    # Get the current day in lower case
    today = datetime.now().weekday()

    # Define a dictionary mapping integers to day attributes
    day_attributes = {
        0: 'sunday',
        1: 'monday',
        2: 'tuesday',
        3: 'wednesday',
        4: 'thursday',
        5: 'friday',
        6: 'saturday'
    }

    # Construct the attribute name dynamically using the dictionary
    attribute_name = day_attributes.get(today)
    print(getattr(Prayer, attribute_name))
    # Set the query
    all_prayers_query = Prayer.query.distinct() \
        .join(User, Prayer.user_id == User.id) \
        .join(FriendRequest, and_(User.id == FriendRequest.sender_id, FriendRequest.status == 'Accepted')) \
        .filter(and_(or_(Prayer.answered ==False, Prayer.answered_at >= seven_days_ago), getattr(Prayer, attribute_name).is_(True),
            or_(User.id == current_user.id, and_(Prayer.sharable == True, User.id != current_user.id)))) \
        .order_by(case((Prayer.user_id == current_user.id, 0), else_= Prayer.user_id), Prayer.id)

    # Get the user's timezone
    user_timezone = timezone(current_user.timezone)

    # Get today's date in the user's timezone
    today_user_timezone = datetime.now(user_timezone).date()

    # Check if each prayer in the history was prayed today
    prayed_today_prayers = []
    for prayer in all_prayers_query.all():
        if prayer.history:
            # Convert the timestamp in the prayer history to the user's timezone
            prayed_at_user_timezone = prayer.history[-1].date_prayed.astimezone(user_timezone).date()
            if prayed_at_user_timezone == today_user_timezone:
                prayed_today_prayers.append(prayer)

    # Paginate the query
    page = request.args.get('page', 1, type=int)
    paginated_query = all_prayers_query.paginate(page=page, per_page=DEFAULT_PER_PAGE, error_out=True)

    return render_template('home.html', firstname=firstname, lastname=lastname, prayers=paginated_query, user_id = current_user.id, prayed_today_prayers=prayed_today_prayers, page_name='home')
    

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

@app.route('/friends', methods=['POST','GET'])
@login_required
def friends():

    if request.method == 'POST':
        email = request.form.get('email').strip()

        existing_user = User.query.filter_by(email=email).first()
        if not existing_user:
            # if the user doesn't exist, handle accordingly
            flash('This account does not exist.', 'error')
            return redirect(url_for('friends'))
        
        if existing_user == current_user:
            flash('You cannot send a friend request to yourself.', 'error')
            return redirect(url_for('friends'))
        
        friendship_exists = FriendRequest.are_friends(current_user.id, existing_user.id)
        if friendship_exists:
            flash('You are already friends with this user.', 'error')
            return redirect(url_for('friends'))

        friend_request = FriendRequest(sender_id=current_user.id, receiver_id=existing_user.id)

        db.session.add(friend_request)
        db.session.commit()

        flash('Friend request sent successfully.', 'success')
        return redirect(url_for('friends'))
    
    friend_list = FriendRequest.query.filter_by(sender_id=current_user.id, status='Accepted').all()

    request_in_list = FriendRequest.query.filter_by(receiver_id=current_user.id, status='Pending').all()

    request_out_list = FriendRequest.query.filter_by(sender_id=current_user.id, status='Pending').all()

    tables = [
        {'heading': 'Friends', 'rows': friend_list, 'checkbox-name': 'selectedFriends'},
        {'heading': 'Incoming Requests', 'rows': request_in_list, 'checkbox_name': 'selectedRequest'},
        {'heading': 'Outgoing Requests', 'rows': request_out_list, 'checkbox_name': 'selectedRequest'}
    ]

    return render_template('friends.html', tables=tables)

@app.route('/accept_friend_request/<int:request_id>', methods=['POST'])
@login_required
def accept_friend_request(request_id):
    # Get the request from the database
    request = FriendRequest.query.get_or_404(request_id)
    sender_id = request.sender_id
    receiver_id = request.receiver_id

    # Mark the request as accepted
    request.status = 'Accepted'

    # Add reciprical friendship
    reciprical_friendship = FriendRequest(sender_id=receiver_id, receiver_id=sender_id,status='Accepted')
    db.session.add(reciprical_friendship)

    # Commit the changes to the database
    db.session.commit()

    return redirect(url_for('friends'))

@app.route('/decline_friend_request/<int:request_id>', methods=['POST'])
@login_required
def decline_friend_request(request_id):
    # Get the request from the database
    request = FriendRequest.query.get_or_404(request_id)


    # Mark the request as declinded
    request.status = 'Declined'

    # Commit the changes to the database
    db.session.commit()

    return redirect(url_for('friends'))

@app.route('/cancel_or_unfriend/<int:request_id>', methods=['POST'])
@login_required
def cancel_or_unfriend(request_id):
    # Get the request from the database
    request = FriendRequest.query.get_or_404(request_id)


    # Delete the friend request
    db.session.delete(request)

    # Commit the changes to the database
    db.session.commit()

    return redirect(url_for('friends'))

@app.route('/friends_prayers',methods=['POST', 'GET'])
@login_required
def friends_prayers():
    # Join Prayer, User and FriendRequest tables
    friends_prayers_query = db.session.query(Prayer) \
        .join(User, Prayer.user_id == User.id) \
        .join(FriendRequest, and_(User.id == FriendRequest.sender_id, FriendRequest.status == 'Accepted')) \
        .filter(Prayer.sharable == True).filter(not_(User.id == current_user.id))

    # Paginate prayers
    page = request.args.get('page', 1, type=int)
    paginated_prayers = friends_prayers_query.paginate(page=page, per_page=DEFAULT_PER_PAGE, error_out=False)

    return render_template('friends_prayers.html', prayers=paginated_prayers, page_name='friends_prayers')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
