from datetime import datetime, timedelta
from database import Database

class Court:
    def __init__(self, court_id):
        self.court_id = court_id
        self.sessions = []  # List of sessions for this court

    def add_session(self, session):
        self.sessions.append(session)


class Session:
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time
        self.players = []  # List of players booked for this session
        self.waiting_list = []  # Waiting list for this session

    def book_player(self, player):
        if len(self.players) < 6:
            self.players.append(player)
            return True
        else:
            self.waiting_list.append(player)
            return False


class Player:
    def __init__(self, player_id, name):
        self.player_id = player_id
        self.name = name
        self.warnings = 0
        self.fines = 0

    def add_warning(self):
        self.warnings += 1
        if self.warnings >= 3:
            self.fines += 25

    def add_no_show_fine(self):
        self.fines += 25


class Booking:
    def __init__(self, player, session, court):
        self.player = player
        self.session = session
        self.court = court
        self.status = 'Booked'  # Other statuses can be 'Waiting', 'Late', 'No-show'

    def mark_late(self):
        self.status = 'Late'
        self.player.add_warning()

    def mark_no_show(self):
        self.status = 'No-show'
        self.player.add_no_show_fine()


class BookingSystem:
    def __init__(self):
        self.db = Database()

    def create_session(self, court_id, date, start_time):
        """Create a new session for a court"""
        end_time = (datetime.combine(date, start_time) + timedelta(hours=2)).time()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO sessions (court_id, date, start_time, end_time)
                    VALUES (?, ?, ?, ?)
                ''', (court_id, date, start_time, end_time))
                return cursor.lastrowid
            except Exception as e:
                raise ValueError(f"Failed to create session: {str(e)}")

    def book_session(self, player_id, court_id, date, start_time):
        """Book a session for a player"""
        # Validate booking time (must be within a week)
        booking_date = datetime.combine(date, start_time)
        current_time = datetime.now()
        if booking_date < current_time:
            raise ValueError("Cannot book sessions in the past")
        if booking_date > current_time + timedelta(days=7):
            raise ValueError("Cannot book sessions more than a week in advance")

        # Check if session exists, create if it doesn't
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM sessions 
                WHERE court_id = ? AND date = ? AND start_time = ?
            ''', (court_id, date, start_time))
            session = cursor.fetchone()
            
            if not session:
                session_id = self.create_session(court_id, date, start_time)
            else:
                session_id = session[0]

        return self.db.create_booking(player_id, session_id)

    def check_late_arrivals(self, current_datetime):
        """Check for late arrivals and update status"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.id, b.player_id, s.start_time, b.status
                FROM bookings b
                JOIN sessions s ON b.session_id = s.id
                WHERE s.date = ? AND b.status = 'booked'
            ''', (current_datetime.date(),))
            
            for booking_id, player_id, start_time, status in cursor.fetchall():
                session_start = datetime.combine(current_datetime.date(), 
                                              datetime.strptime(start_time, '%H:%M').time())
                time_diff = current_datetime - session_start

                if time_diff > timedelta(minutes=30):
                    # Mark as no-show and add fine
                    cursor.execute('''
                        UPDATE bookings SET status = 'no_show'
                        WHERE id = ?
                    ''', (booking_id,))
                    self.db.update_player_status(player_id, fines=25)
                    self._notify_next_in_waiting_list(booking_id)
                elif time_diff > timedelta(minutes=15):
                    # Add warning
                    cursor.execute('''
                        UPDATE bookings SET status = 'late'
                        WHERE id = ?
                    ''', (booking_id,))
                    self.db.update_player_status(player_id, warnings=1)

            conn.commit()

    def _notify_next_in_waiting_list(self, booking_id):
        """Notify next player in waiting list about available spot"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT w.player_id, w.session_id
                FROM waiting_list w
                JOIN bookings b ON b.session_id = w.session_id
                WHERE b.id = ?
                ORDER BY w.position
                LIMIT 1
            ''', (booking_id,))
            next_player = cursor.fetchone()
            
            if next_player:
                player_id, session_id = next_player
                # Move player from waiting list to bookings
                cursor.execute('''
                    INSERT INTO bookings (player_id, session_id, status)
                    VALUES (?, ?, 'pending_confirmation')
                ''', (player_id, session_id))
                
                # Remove from waiting list
                cursor.execute('''
                    DELETE FROM waiting_list
                    WHERE player_id = ? AND session_id = ?
                ''', (player_id, session_id))
                
                conn.commit()
                # TODO: Send actual notification to player
                return player_id
