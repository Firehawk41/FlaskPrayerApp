from flask import  Flask, render_template, session, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy, pagination
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
import os
from bcrypt import checkpw
import bcrypt
from sqlalchemy import and_, not_, or_, case, func, text, union
from flask_wtf.csrf import CSRFProtect

# Load environment variables from .env file
load_dotenv()

# Access environment variables
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
login_manager = LoginManager(app)
csrf = CSRFProtect(app)

# Get currecnt UTC time
current_utc_time = datetime.now(timezone.utc)

db = SQLAlchemy(app)

# Define possible prayer tags
prayer_categories = ["Thanksgiving", "Lament", "Praise", "Wisdom", "Intercession", "Confession" , "Petition", "Healing", "Protection", "Guidance", "Strength", "Unity", "Hope", "Mission"]
days_of_week=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
DEFAULT_PER_PAGE = 5

# Function to paginate a list of prayers
def paginate_list(items, page, per_page=DEFAULT_PER_PAGE):
    total_items = len(items)
    print("Total items: " + str(total_items) + ".")

    start_index = (page - 1) * per_page
    end_index = min(start_index + per_page, total_items)

    if start_index >= total_items:
        return []

    return items[start_index:end_index]

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique = True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

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
    description = db.Column(db.Text, nullable=False)
    answered = db.Column(db.Boolean, default=False)
    archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=current_utc_time)
    last_modified = db.Column(db.DateTime, default=current_utc_time, onupdate=current_utc_time)
    answered_at = db.Column(db.DateTime)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)
    reminder = db.Column(db.String(60),default=("Sunday,Monday,Tuesday,Wednesday,Thursday,Friday,Saturday"))
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

        # Add reminder days to prayer
        reminder_days = request.form.getlist('reminderDays')
        reminder_days_str = ",".join(reminder_days)

        # Add tag to the prayer
        existing_tag = Tag.query.filter_by(name=tag_name).first()
        if not existing_tag:
            # If the tag doesn't exist, create a new one
            new_tag = Tag(name=tag_name)
            db.session.add(new_tag)
            db.session.commit()
        else:
            new_tag = existing_tag

        # Add sharable status
        sharable = False
        sharable_str = request.form.get('sharable', 'False')
        print("Share status is: " + str(sharable_str) + ".")
        if sharable_str == "shared":
            sharable = True
        

        # Create new Prayer object
        new_prayer = Prayer(title=title, description=description, user_id=current_user.id, sharable=sharable, tag=new_tag,reminder=reminder_days_str)

        # Add new prayer to database and save changes
        db.session.add(new_prayer)
        db.session.commit()
        
        jsonify({'message': 'Prayer added successfully'}), 200
        return redirect(url_for('home'))



    return render_template('add_prayer.html', categories=prayer_categories, days_of_week=days_of_week)


@app.route('/edit_prayer/<int:prayer_id>', methods=['GET', 'POST'])
@login_required
def edit_prayer(prayer_id):

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
    per_page = DEFAULT_PER_PAGE
    paginated_prayers = user_prayers_query.paginate(page=page, per_page=per_page, error_out=False)

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


@app.route('/account_settings')
@login_required
def account_settings():
    
    return render_template('account_settings.html')


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
    today = datetime.now().strftime("%A").lower()
    
    # Set the query
    all_prayers_query = Prayer.query \
        .join(User, Prayer.user_id == User.id) \
        .join(FriendRequest, and_(User.id == FriendRequest.sender_id, FriendRequest.status == 'Accepted')) \
        .filter(or_(
            and_(Prayer.user_id == current_user.id, or_(Prayer.answered ==False, Prayer.answered_at >= seven_days_ago), Prayer.reminder.like(f"%{today}%")),
            and_(Prayer.sharable == True, not_(User.id == current_user.id))
        )) \
        .order_by(case((Prayer.user_id == current_user.id, 0), else_= Prayer.user_id), Prayer.id)

    # Paginate the query
    page = request.args.get('page', 1, type=int)
    per_page = DEFAULT_PER_PAGE
    paginated_query = all_prayers_query.paginate(page=page, per_page=5, error_out=True)


    return render_template('home.html', firstname=firstname, lastname=lastname, prayers=paginated_query, user_id = current_user.id, today=current_utc_time, page_name='home')
    

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
    per_page = DEFAULT_PER_PAGE
    paginated_prayers = friends_prayers_query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('friends_prayers.html', prayers=paginated_prayers, page_name='friends_prayers')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
