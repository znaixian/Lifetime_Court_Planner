import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_file="gym_booking.db"):
        self.db_file = db_file
        self.init_database()

    def get_connection(self):
        return sqlite3.connect(self.db_file)

    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create Players table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    password TEXT NOT NULL,
                    warnings INTEGER DEFAULT 0,
                    fines DECIMAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create Courts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS courts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    court_number INTEGER UNIQUE NOT NULL
                )
            ''')

            # Create Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    court_id INTEGER,
                    start_time TIME NOT NULL,
                    end_time TIME NOT NULL,
                    date DATE NOT NULL,
                    FOREIGN KEY (court_id) REFERENCES courts (id),
                    UNIQUE(court_id, start_time, date)
                )
            ''')

            # Create Bookings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    session_id INTEGER,
                    status TEXT DEFAULT 'booked',
                    is_substitute BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players (id),
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            ''')

            # Create WaitingList table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS waiting_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    session_id INTEGER,
                    position INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players (id),
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            ''')

            # Create Notifications table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'sent',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players (id)
                )
            ''')

            # Initialize courts if they don't exist
            cursor.execute('SELECT COUNT(*) FROM courts')
            if cursor.fetchone()[0] == 0:
                for i in range(1, 7):
                    cursor.execute('INSERT INTO courts (court_number) VALUES (?)', (i,))

            conn.commit()

    def check_email_exists(self, email):
        """Check if an email already exists in the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM players WHERE email = ?', (email,))
            return cursor.fetchone()[0] > 0

    def add_player(self, name, email, password):
        """Add a new player to the database"""
        if self.check_email_exists(email):
            raise ValueError("Email already exists")
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'INSERT INTO players (name, email, password) VALUES (?, ?, ?)',
                    (name, email, password)
                )
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                raise ValueError("Error creating user account")

    def get_available_sessions(self, date):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.id, c.court_number, s.start_time, s.end_time,
                       (SELECT COUNT(*) FROM bookings WHERE session_id = s.id AND status = 'booked') as player_count
                FROM sessions s
                JOIN courts c ON s.court_id = c.id
                WHERE s.date = ?
                ORDER BY s.start_time, c.court_number
            ''', (date,))
            return cursor.fetchall()

    def create_booking(self, player_id, session_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Check if session is full
            cursor.execute('''
                SELECT COUNT(*) FROM bookings 
                WHERE session_id = ? AND status = 'booked'
            ''', (session_id,))
            
            if cursor.fetchone()[0] >= 6:
                # Add to waiting list
                cursor.execute('''
                    SELECT MAX(position) FROM waiting_list WHERE session_id = ?
                ''', (session_id,))
                max_position = cursor.fetchone()[0] or 0
                cursor.execute('''
                    INSERT INTO waiting_list (player_id, session_id, position)
                    VALUES (?, ?, ?)
                ''', (player_id, session_id, max_position + 1))
                return "Added to waiting list"
            else:
                cursor.execute('''
                    INSERT INTO bookings (player_id, session_id)
                    VALUES (?, ?)
                ''', (player_id, session_id))
                return "Booking successful"

    def update_player_status(self, player_id, warnings=None, fines=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if warnings is not None:
                cursor.execute('''
                    UPDATE players 
                    SET warnings = warnings + ?
                    WHERE id = ?
                ''', (warnings, player_id))
            if fines is not None:
                cursor.execute('''
                    UPDATE players 
                    SET fines = fines + ?
                    WHERE id = ?
                ''', (fines, player_id))
            conn.commit()

    def get_player_bookings(self, player_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.court_number, s.date, s.start_time, s.end_time, b.status
                FROM bookings b
                JOIN sessions s ON b.session_id = s.id
                JOIN courts c ON s.court_id = c.id
                WHERE b.player_id = ?
                ORDER BY s.date, s.start_time
            ''', (player_id,))
            return cursor.fetchall()

    def delete_player_by_email(self, email):
        """Delete a player record by email"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM players WHERE email = ?', (email,))
            if cursor.rowcount > 0:
                print(f"Successfully deleted player with email: {email}")
            else:
                print(f"No player found with email: {email}")
            conn.commit()
