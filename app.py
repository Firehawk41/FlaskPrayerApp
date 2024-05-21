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
from wtforms import SelectField, StringField, IntegerField, SelectMultipleField, BooleanField, widgets, PasswordField
from wtforms.validators import DataRequired, Email, Length, InputRequired, NumberRange, EqualTo
from pytz import common_timezones, timezone
from flask_wtf import FlaskForm
import logging

# Load environment variables from .env file
load_dotenv()

# Access environment variables
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
login_manager = LoginManager(app)
csrf = CSRFProtect(app)

# Configure logging
app.logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)


# Get current UTC time
current_utc_time = datetime.now(dt_timezone.utc)

db = SQLAlchemy(app)

# Define possible prayer tags
prayer_categories = ["Thanksgiving", "Lament", "Praise", "Wisdom", "Intercession", "Confession" , "Petition", "Healing", "Protection", "Guidance", "Strength", "Unity", "Hope", "Mission"]
days_of_week=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
DEFAULT_PER_PAGE = 15

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class AccountSettingsForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired(), Length(max=100)])
    lastname = StringField('Last Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    password1 = PasswordField('Password', validators=[DataRequired(), Length(min=3, max=20)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password1', message='Passwords must match')])
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

@app.route('/add_or_edit_prayer/<int:prayer_id>', methods=['GET', 'POST'])
@login_required
def add_or_edit_prayer(prayer_id=0):
    # Check if editing an existing prayer or adding a new one
    if prayer_id != 0:
        # Retrieve the prayer from the database
        app.logger.info(f'Retrieving prayer to edit. Prayer ID: {prayer_id}')
        prayer = Prayer.query.get_or_404(prayer_id)
        tag_name = prayer.tag.name
        form = AddPrayerForm(obj=prayer)

        if request.method == "GET":
            tag_index = next((i for i, name in enumerate(prayer_categories) if name == tag_name), None)
            form.tag.data = tag_index

        # Prevent users from editing others' prayers
        if prayer.user.id != current_user.id:
            flash("You cannot edit another user's prayer.", "error")
            app.logger.warning(f'Attempted to edit another user\'s prayer. User ID: {current_user.id}, Prayer ID: {prayer_id}')
            return redirect(home)
    else:
        prayer = None
        form = AddPrayerForm()
        app.logger.info('Adding new prayer.')

        # Set all reminder_days as selected by default
        for field_name in ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']:
            getattr(form, field_name).data = True

    if form.validate_on_submit():
        # Extract data from the form
        title = form.title.data
        description = form.description.data
        tag_name = dict(form.tag.choices).get(form.tag.data)
        tag_id = get_or_create_tag_id(tag_name)
        sharable = True if form.sharable.data == 'True' else False

        # Create or update the prayer object
        if prayer_id != 0:
            app.logger.info(f'Editing existing prayer. Prayer ID: {prayer_id}')
            prayer.title = title
            prayer.description = description
            prayer.tag_id = tag_id
            prayer.sharable = sharable
            for field_name in ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']:
                setattr(prayer, field_name, getattr(form, field_name).data)
        else:
            app.logger.info('Creating new prayer.')
            prayer = Prayer(user_id=current_user.id, title=title, description=description, tag_id=tag_id, 
                            sunday=form.sunday.data, monday=form.monday.data, tuesday=form.tuesday.data, 
                            wednesday=form.wednesday.data, thursday=form.thursday.data, friday=form.friday.data, 
                            saturday=form.saturday.data, sharable=sharable)
            db.session.add(prayer)

        # Commit changes to the database
        try:
            db.session.commit()
            app.logger.info('Prayer saved successfully.')
            flash('Prayer added successfully.' if prayer_id == 0 else 'Prayer edited successfully.', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            app.logger.error(f'Failed to save prayer. Error: {str(e)}')
            flash('An error occurred while saving the prayer.  Please try again later.', 'error')

    return render_template('add_or_edit_prayer.html', form=form, edit_mode=bool(prayer_id!=0), prayer=prayer)

def get_or_create_tag_id(tag_name):
    # Add tag to the prayer
    
    existing_tag = Tag.query.filter_by(name=tag_name).first()
    if not existing_tag:
        # If the tag doesn't exist, create a new one
        app.logger.info(f'Creating new tag: {tag_name}')
        new_tag = Tag(name=tag_name)
        db.session.add(new_tag)
        db.session.commit()
        app.logger.info('Tag added successfully.')
        return new_tag.id
    else:
        app.logger.info(f'Getting tag: {tag_name}')
        return existing_tag.id

@app.route('/prayers')
@login_required
def view_prayers():
    
    # Retrieve all user's prayers
    user_id = current_user.id
    user_prayers_query = Prayer.query.filter_by(user_id=user_id)
    app.logger.info('Retrieving user\'s tags.')

    # Paginate prayers
    page = request.args.get('page', 1, type=int)
    paginated_prayers = user_prayers_query.paginate(page=page, per_page=DEFAULT_PER_PAGE, error_out=False)

    return render_template('prayers.html', prayers = paginated_prayers, categories=prayer_categories, page_name='view_prayers', page=page)


@app.route('/mark_answered/<int:prayer_id>', methods=['POST'])
@login_required
def mark_answered(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)
    app.logger.info(f'Retrieved prayer from database. Prayer ID: {prayer_id}.')

    # Prevent editing of other users' prayers
    if prayer.user.id != current_user.id:
        flash("You cannot edit another user's prayer.", "error")
        app.logger.warning(f'Attempted to edit another user\'s prayer. User ID: {current_user.id}, Prayer ID: {prayer_id}')
        return redirect('view_prayers')
    
    # Mark the prayer as answered
    prayer.answered = True

    # Set the answered date
    prayer.answered_at = current_utc_time

    # Commit the changes to the database
    db.session.commit()
    app.logger.info(f'Prayer marked as prayed.')

    return redirect(url_for('view_prayers'))


@app.route('/mark_pending/<int:prayer_id>', methods=['POST'])
@login_required
def mark_pending(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)
    app.logger.info(f'Retrieved prayer from database. Prayer ID: {prayer_id}.')

    # Prevent editing of other users' prayers
    if prayer.user.id != current_user.id:
        app.logger.warning(f'Attempted to edit another user\'s prayer. User ID: {current_user.id}, Prayer ID: {prayer_id}')
        flash("You cannot edit another user's prayer.", "error")
        return redirect('view_prayers')

    # Mark the prayer as answered
    prayer.answered = False

    # Commit the changes to the database
    db.session.commit()
    app.logger.info(f'Prayer marked as pending.')

    return redirect(url_for('view_prayers'))


@app.route('/mark_archived/<int:prayer_id>', methods=['POST'])
@login_required
def mark_archived(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)
    app.logger.info(f'Retrieved prayer from database. Prayer ID: {prayer_id}.')

    # Prevent editing of other users' prayers
    if prayer.user.id != current_user.id:
        app.logger.warning(f'Attempted to edit another user\'s prayer. User ID: {current_user.id}, Prayer ID: {prayer_id}')
        flash("You cannot edit another user's prayer.", "error")
        return redirect('view_prayers')
    
    # Mark the prayer as answered
    prayer.archived = True

    # Commit the changes to the database
    db.session.commit()
    app.logger.info(f'Prayer marked as archived.')

    return redirect(url_for('view_prayers'))


@app.route('/mark_prayed/<int:prayer_id>', methods=['POST'])
@login_required
def mark_prayed(prayer_id):
    # Get the prayer from the database
    prayer = Prayer.query.get_or_404(prayer_id)
    app.logger.info(f'Retrieved prayer from database. Prayer ID: {prayer_id}.')
    
    # Mark the prayer as prayed
    prayer_history = PrayerHistory(prayer_id=prayer.id, user_id=current_user.id)

    # Commit the changes to the database
    db.session.add(prayer_history)
    db.session.commit()
    app.logger.info(f'Prayer marked as prayed.')

    return redirect(url_for('home'))


@app.route('/delete_prayer/<int:prayer_id>', methods=['POST'])
@login_required
def delete_prayer(prayer_id):
    prayer = Prayer.query.get_or_404(prayer_id)
    app.logger.info(f'Retrieved prayer from database. Prayer ID: {prayer_id}.')
    
    # Prevent editing of other users' prayers
    if prayer.user.id != current_user.id:
        flash("You cannot edit another user's prayer.", "error")
        app.logger.warning(f'Attempted to edit another user\'s prayer. User ID: {current_user.id}, Prayer ID: {prayer_id}')
        return redirect('view_prayers')
    
    db.session.delete(prayer)
    db.session.commit()
    app.logger.info('Prayer successfully deleted.')
    flash('Prayer deleted.')

    return redirect(url_for('home'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    # Render your login page template
    return redirect(url_for('login'))

@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()

    if form.validate_on_submit():

        email = form.email.data
        password = form.password.data

        # Check if the email exists in the database
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            app.logger.info('Login successful.')
            return redirect(url_for('home'))
        else:
            # Authentication failed
            flash('Invalid email or password', 'error')
            app.logger.warning('Login unsuccessful.')
    
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    app.logger.info('User logged out.')
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
        app.logger.info(f'Successfully updated settings for user ID: {current_user.id}.')

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

    app.logger.debug("Constructing query with parameters: {}, {}".format(attribute_name, seven_days_ago))


    # Set the query
    all_prayers_query = Prayer.query.distinct() \
        .join(User, Prayer.user_id == User.id) \
        .join(FriendRequest, and_(User.id == FriendRequest.sender_id, FriendRequest.status == 'Accepted')) \
        .filter(and_(or_(Prayer.answered ==False, Prayer.answered_at >= seven_days_ago), getattr(Prayer, attribute_name).is_(True),
            or_(User.id == current_user.id, and_(FriendRequest.receiver_id == current_user.id, Prayer.sharable == True)))) \
        .order_by(case((Prayer.user_id == current_user.id, 0), else_= Prayer.user_id), Prayer.id)

    app.logger.debug("Fetched {} prayers from the database".format(all_prayers_query.count()))

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

    form = AccountSettingsForm(timezone='America/Chicago',thankfulness_length=7)


    if form.validate_on_submit():
        firstname = form.firstname.data.strip()
        lastname = form.lastname.data.strip()
        email = form.email.data.strip()
        password1 = form.password1.data
        
        # Check if the email already exists in the database
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            # Email already exists, handle accordingly
            flash('An account already exists with this email address.', 'error')
            app.logger.info("User attempted to create account with email already in the database.")
            return render_template('signup.html', form=form)

        # Has the password before storing it in the database
        hashed_password = bcrypt.hashpw(password1.encode('utf-8'), bcrypt.gensalt())

        new_user = User(firstname=firstname,lastname=lastname, email=email,password=hashed_password, timezone=form.timezone.data, 
                        thankfulness_length = form.thankfulness_length.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Sign-up successful!', 'success')
        app.logger.info(f"User created successfully. User ID: {new_user.id}.")
        login_user(new_user)

        return redirect(url_for('home'))
    
    return render_template('signup.html', form=form)

@app.route('/friends', methods=['POST','GET'])
@login_required
def friends():

    if request.method == 'POST':
        email = request.form.get('email').strip()

        existing_user = User.query.filter_by(email=email).first()
        if not existing_user:
            # if the user doesn't exist, handle accordingly
            flash('This account does not exist.', 'error')
            app.logger.info("User {} attempted to add a friend that doesn't exist.".format(current_user.id))
            return redirect(url_for('friends'))
        
        if existing_user == current_user:
            flash('You cannot send a friend request to yourself.', 'error')
            app.logger.info("User {} attempted to add him or herself as a friend.".format(current_user.id))
            return redirect(url_for('friends'))
        
        friendship_exists = FriendRequest.are_friends(current_user.id, existing_user.id)
        if friendship_exists:
            flash('You are already friends with this user.', 'error')
            app.logger.info("User {} attempted to add user {} as a friend but they already were friends.".format(current_user.id,existing_user.id))
            return redirect(url_for('friends'))

        friend_request = FriendRequest(sender_id=current_user.id, receiver_id=existing_user.id)

        db.session.add(friend_request)
        db.session.commit()

        flash('Friend request sent successfully.', 'success')
        app.logger.info("User {} successfully sent a friend request to {}.".format(current_user.id,existing_user.id))
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
    app.logger.info("User {} accepted a friend request from {}.".format(receiver_id,sender_id))
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
    app.logger.info("User {} declined a friend request from {}.".format(request.receiver_id,request.sender_id))
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
    app.logger.info("User {} deleted a friend request to {}.".format(request.receiver_id,request.sender_id))
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
