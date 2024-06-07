import db
from room import Room
from reservation import Reservation

def list_rooms():
    conn = db.get_db_connection()
    cursor = conn.cursor()
    query = """
    SELECT RoomCode, RoomName, Beds, bedType, maxOcc, basePrice, decor
    FROM lab7_rooms
    ORDER BY RoomName
    """
    cursor.execute(query)
    rooms = cursor.fetchall()
    for room in rooms:
        print(room)
    cursor.close()
    conn.close()

def main():
    while True:
        print("1. List Rooms and Rates")
        print("2. Make a Reservation")
        print("3. Cancel a Reservation")
        print("4. View Detailed Reservation Information")
        print("5. View Revenue")
        print("0. Exit")
        choice = input("Select an option: ")
        if choice == '1':
            list_rooms()
        elif choice == '2':
            pass
        elif choice == '3':
            pass
        elif choice == '4':
            pass
        elif choice == '5':
            pass
        elif choice == '0':
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
