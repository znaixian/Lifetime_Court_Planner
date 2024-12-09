from datetime import datetime, timedelta
from BookingSystem import BookingSystem
from NotificationSystem import NotificationSystem
from database import Database
import re
import calendar
from tabulate import tabulate
import colorama
from colorama import Fore, Back, Style

class UserInterface:
    def __init__(self):
        self.booking_system = BookingSystem()
        self.notification_system = NotificationSystem()
        self.db = Database()
        self.current_user = None
        colorama.init()
        self.time_slots = [
            "07:00-09:00", "09:00-11:00", "11:00-13:00",
            "13:00-15:00", "15:00-17:00", "17:00-19:00",
            "19:00-21:00", "21:00-23:00"
        ]

    def validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def register_user(self):
        """Register a new user"""
        print("\nUser Registration")
        while True:
            name = input("Enter your name: ").strip()
            if name:
                break
            print("Name cannot be empty")

        while True:
            email = input("Enter your email: ").strip()
            # Check if email exists before proceeding
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM players WHERE email = ?', (email,))
                if cursor.fetchone()[0] > 0:
                    print(f"\nEmail {email} is already registered.")
                    choice = input("Would you like to: \n1. Login\n2. Try a different email\nChoice (1/2): ")
                    if choice == '1':
                        return self.login()
                    continue

            if self.validate_email(email):
                break
            print("Invalid email format")

        while True:
            password = input("Enter password: ")
            if len(password) >= 6:
                break
            print("Password must be at least 6 characters")

        try:
            player_id = self.db.add_player(name, email, password)
            print("Registration successful!")
            self.current_user = {
                'id': player_id,
                'name': name,
                'email': email
            }
            return player_id
        except ValueError as e:
            print(f"Registration failed: {str(e)}")
            return None

    def login(self):
        """Login existing user"""
        print("\nUser Login")
        email = input("Email: ").strip()
        password = input("Password: ")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, email 
                FROM players 
                WHERE email = ? AND password = ?
            ''', (email, password))
            user = cursor.fetchone()

            if user:
                self.current_user = {
                    'id': user[0],
                    'name': user[1],
                    'email': user[2]
                }
                print(f"Welcome back, {user[1]}!")
                return True
            else:
                print("Invalid email or password")
                return False

    def display_menu(self):
        """Display main menu"""
        print("\nWelcome to the Lifetime Gym Booking System")
        if not self.current_user:
            print("1. Login")
            print("2. Register")
            print("3. Exit")
        else:
            print("1. Book a Session")
            print("2. View My Bookings")
            print("3. View Available Sessions")
            print("4. View My Warnings and Fines")
            print("5. Logout")
            print("6. Exit")

    def display_calendar(self, year, month):
        """Display a formatted calendar for the specified month"""
        cal = calendar.monthcalendar(year, month)
        month_name = calendar.month_name[month]
        
        print(f"\n{Fore.CYAN}{month_name} {year}{Style.RESET_ALL}")
        print("Mo Tu We Th Fr Sa Su")
        
        today = datetime.now().date()
        for week in cal:
            for day in week:
                if day == 0:
                    print("   ", end="")
                else:
                    date = datetime(year, month, day).date()
                    if date == today:
                        print(f"{Fore.GREEN}{day:2d}{Style.RESET_ALL} ", end="")
                    elif date < today:
                        print(f"{Fore.RED}{day:2d}{Style.RESET_ALL} ", end="")
                    else:
                        print(f"{day:2d} ", end="")
            print()

    def display_time_slots(self, date):
        """Display available time slots for all courts"""
        print(f"\n{Fore.CYAN}Available Sessions for {date}{Style.RESET_ALL}")
        
        # Get all bookings for the date
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.court_number, s.start_time, 
                       COUNT(b.id) as booked_players,
                       COUNT(w.id) as waiting_list
                FROM courts c
                CROSS JOIN (
                    SELECT DISTINCT start_time 
                    FROM (
                        SELECT '07:00' as start_time UNION SELECT '09:00' UNION
                        SELECT '11:00' UNION SELECT '13:00' UNION
                        SELECT '15:00' UNION SELECT '17:00' UNION
                        SELECT '19:00' UNION SELECT '21:00'
                    )
                ) times
                LEFT JOIN sessions s ON s.court_id = c.id 
                    AND s.date = ? AND s.start_time = times.start_time
                LEFT JOIN bookings b ON b.session_id = s.id AND b.status = 'booked'
                LEFT JOIN waiting_list w ON w.session_id = s.id
                GROUP BY c.court_number, times.start_time
                ORDER BY times.start_time, c.court_number
            ''', (date,))
            bookings = cursor.fetchall()

        # Prepare the table data
        headers = ["Time"] + [f"Court {i}" for i in range(1, 7)]
        table_data = []
        
        for time_slot in self.time_slots:
            row = [time_slot]
            start_time = time_slot.split('-')[0]
            
            for court in range(1, 7):
                booking = next((b for b in bookings if b[0] == court and b[1] == start_time), None)
                if booking:
                    players = booking[2]
                    waiting = booking[3]
                    if players >= 6:
                        status = f"{Fore.RED}Full ({waiting} waiting){Style.RESET_ALL}"
                    else:
                        status = f"{Fore.GREEN}{players}/6{Style.RESET_ALL}"
                else:
                    status = f"{Fore.GREEN}0/6{Style.RESET_ALL}"
                row.append(status)
            table_data.append(row)
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print(f"\n{Fore.YELLOW}Legend:{Style.RESET_ALL}")
        print(f"{Fore.GREEN}X/6{Style.RESET_ALL} - Available (X players booked)")
        print(f"{Fore.RED}Full (N waiting){Style.RESET_ALL} - Court full with N players in waiting list")

    def book_session(self):
        """Handle session booking with calendar and time slot display"""
        if not self.current_user:
            print("Please login first")
            return

        print("\nBook a Session")
        
        # Show calendar for current month
        now = datetime.now()
        self.display_calendar(now.year, now.month)
        
        # Get date input
        while True:
            try:
                date_str = input("\nEnter date (YYYY-MM-DD): ")
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if date < now.date():
                    print("Cannot book sessions in the past")
                    continue
                if date > now.date() + timedelta(days=7):
                    print("Cannot book sessions more than a week in advance")
                    continue
                break
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD")

        # Show time slots
        self.display_time_slots(date)
        
        # Get booking details
        try:
            court_id = int(input("\nEnter court number (1-6): "))
            if not 1 <= court_id <= 6:
                raise ValueError("Invalid court number")
            
            time_slot = input("Enter time slot (HH:MM): ")
            if not any(time_slot in slot for slot in self.time_slots):
                raise ValueError("Invalid time slot")
            
            start_time = datetime.strptime(time_slot, '%H:%M').time()
            result = self.booking_system.book_session(
                self.current_user['id'],
                court_id,
                date,
                start_time
            )
            print(result)

        except ValueError as e:
            print(f"Booking failed: {str(e)}")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def view_my_bookings(self):
        """View user's bookings"""
        if not self.current_user:
            print("Please login first")
            return

        bookings = self.db.get_player_bookings(self.current_user['id'])
        if not bookings:
            print("You have no bookings")
            return

        print("\nYour Bookings:")
        for court_num, date, start_time, end_time, status in bookings:
            print(f"Court {court_num} on {date}: {start_time}-{end_time} ({status})")

    def view_warnings_and_fines(self):
        """View user's warnings and fines"""
        if not self.current_user:
            print("Please login first")
            return

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT warnings, fines 
                FROM players 
                WHERE id = ?
            ''', (self.current_user['id'],))
            warnings, fines = cursor.fetchone()
            print(f"\nWarnings: {warnings}/3")
            print(f"Outstanding Fines: ${fines}")

    def run(self):
        """Main application loop"""
        while True:
            self.display_menu()
            choice = input("Enter your choice: ").strip()

            if not self.current_user:
                if choice == '1':
                    self.login()
                elif choice == '2':
                    self.register_user()
                elif choice == '3':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice")
            else:
                if choice == '1':
                    self.book_session()
                elif choice == '2':
                    self.view_my_bookings()
                elif choice == '3':
                    date_str = input("Enter date (YYYY-MM-DD): ")
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    sessions = self.db.get_available_sessions(date)
                    for session in sessions:
                        print(f"Court {session[1]}: {session[2]}-{session[3]} ({session[4]}/6 players)")
                elif choice == '4':
                    self.view_warnings_and_fines()
                elif choice == '5':
                    self.current_user = None
                    print("Logged out successfully")
                elif choice == '6':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice")

if __name__ == "__main__":
    ui = UserInterface()
    ui.run()
