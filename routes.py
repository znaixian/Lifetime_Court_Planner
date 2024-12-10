from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from app import app, db, User, Booking
from datetime import datetime, time

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', bookings=user_bookings)

@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if request.method == 'POST':
        court_number = int(request.form['court_number'])
        date_str = request.form['date']
        start_time_str = request.form['start_time']
        end_time_str = request.form['end_time']
        
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Check for existing bookings
        existing_booking = Booking.query.filter_by(
            court_number=court_number,
            date=date
        ).filter(
            ((Booking.start_time <= start_time) & (Booking.end_time > start_time)) |
            ((Booking.start_time < end_time) & (Booking.end_time >= end_time))
        ).first()
        
        if existing_booking:
            flash('This court is already booked for the selected time')
            return redirect(url_for('book'))
        
        booking = Booking(
            court_number=court_number,
            date=date,
            start_time=start_time,
            end_time=end_time,
            user_id=current_user.id
        )
        
        db.session.add(booking)
        db.session.commit()
        flash('Booking successful')
        return redirect(url_for('dashboard'))
    
    return render_template('book.html')
