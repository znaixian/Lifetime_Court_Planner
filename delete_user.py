from database import Database

def delete_user(email):
    db = Database()
    db.delete_player_by_email(email)

if __name__ == "__main__":
    email_to_delete = "znaixian@gmail.com"
    delete_user(email_to_delete)
