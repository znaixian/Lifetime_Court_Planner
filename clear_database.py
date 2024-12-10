from app import app, db, User, Booking

def clear_database():
    with app.app_context():
        # Delete all bookings first (due to foreign key constraints)
        Booking.query.delete()
        # Delete all users
        User.query.delete()
        # Commit the changes
        db.session.commit()
        print("All users and bookings have been deleted from the database.")

if __name__ == "__main__":
    clear_database()
