from datetime import datetime
from database import Database
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class NotificationSystem:
    def __init__(self, email_config=None):
        self.db = Database()
        self.email_config = email_config or {}
        self.notifications = []

    def send_email(self, to_email, subject, message):
        """Send email notification if email configuration is available"""
        if not self.email_config:
            print(f"Email notification would be sent to {to_email}: {subject}")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender']
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(message, 'plain'))

            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                if self.email_config.get('use_tls'):
                    server.starttls()
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            self.log_notification(to_email, subject, message, 'failed')

    def notify_booking_confirmation(self, player_id, session_info):
        """Send booking confirmation notification"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT email, name FROM players WHERE id = ?', (player_id,))
            player = cursor.fetchone()
            
            if player:
                email, name = player
                subject = "Court Booking Confirmation"
                message = f"""
                Dear {name},

                Your court booking has been confirmed:
                Court: {session_info['court']}
                Date: {session_info['date']}
                Time: {session_info['start_time']} - {session_info['end_time']}

                Please arrive at least 5 minutes before your session.
                Remember:
                - Late arrival (>15 minutes) will result in a warning
                - Three warnings will result in a $25 fine
                - No-shows will be fined $25

                Thank you for choosing Lifetime Gym!
                """
                self.send_email(email, subject, message)
                self.log_notification(player_id, 'booking_confirmation', message)

    def notify_late_warning(self, player_id):
        """Send late arrival warning notification"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT email, name, warnings 
                FROM players 
                WHERE id = ?
            ''', (player_id,))
            player = cursor.fetchone()
            
            if player:
                email, name, warnings = player
                subject = "Late Arrival Warning"
                message = f"""
                Dear {name},

                This is a warning notification for arriving more than 15 minutes late to your court session.
                Current warnings: {warnings}/3

                Please note that three warnings will result in a $25 fine.

                Thank you for your understanding.
                """
                self.send_email(email, subject, message)
                self.log_notification(player_id, 'late_warning', message)

    def notify_fine(self, player_id, reason):
        """Send fine notification"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT email, name, fines FROM players WHERE id = ?', (player_id,))
            player = cursor.fetchone()
            
            if player:
                email, name, fines = player
                subject = "Fine Notice"
                message = f"""
                Dear {name},

                You have been fined $25 for: {reason}
                Total outstanding fines: ${fines}

                Please settle your fines at the front desk.

                Thank you for your understanding.
                """
                self.send_email(email, subject, message)
                self.log_notification(player_id, 'fine_notice', message)

    def notify_waiting_list_spot(self, player_id, session_info):
        """Notify player about available spot from waiting list"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT email, name FROM players WHERE id = ?', (player_id,))
            player = cursor.fetchone()
            
            if player:
                email, name = player
                subject = "Court Spot Available"
                message = f"""
                Dear {name},

                A spot has become available for your wait-listed session:
                Court: {session_info['court']}
                Date: {session_info['date']}
                Time: {session_info['start_time']} - {session_info['end_time']}

                Please confirm your attendance within the next 5 minutes.
                Regular attendance rules apply.

                Thank you for choosing Lifetime Gym!
                """
                self.send_email(email, subject, message)
                self.log_notification(player_id, 'waiting_list_notification', message)

    def log_notification(self, player_id, notification_type, message, status='sent'):
        """Log all notifications in the database"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications (player_id, type, message, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (player_id, notification_type, message, status, datetime.now()))
