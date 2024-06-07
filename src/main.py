import db
from datetime import date
import sqlite3
import datetime

def list_rooms():
    conn = db.get_db_connection()
    cursor = conn.cursor()

    # query to calculate room popularity, next available check-in date, and length of the most recent completed stay
    query = """
    WITH Occupancy AS (
    SELECT
        Room,
        SUM(DATEDIFF(LEAST(Checkout, '2024-06-01'), GREATEST(CheckIn, DATE_SUB('2024-06-01', INTERVAL 180 DAY)))) AS occupied_days
    FROM mjaege02.lab7_reservations
    WHERE Checkout > DATE_SUB('2024-06-01', INTERVAL 180 DAY)
    GROUP BY Room
    ),
    NextAvailableDate AS (
        SELECT
            Room,
            MIN(CheckIn) AS next_available
        FROM mjaege02.lab7_reservations
        WHERE Checkout > '2024-06-01'
        GROUP BY Room
    ),
    RecentStay AS (
        SELECT
            Room,
            DATEDIFF(MAX(Checkout), MAX(CheckIn)) AS recent_stay_length
        FROM mjaege02.lab7_reservations
        WHERE Checkout <= '2024-06-01'
        GROUP BY Room
    )
    SELECT
        r.RoomCode,
        r.RoomName,
        r.Beds,
        r.bedType,
        r.maxOcc,
        r.basePrice,
        r.decor,
        ROUND(IFNULL(o.occupied_days, 0) / 180, 2) AS popularity_score,
        IFNULL(n.next_available, '2024-06-01') AS next_available_checkin,
        IFNULL(rs.recent_stay_length, 0) AS recent_stay_length
    FROM
        mjaege02.lab7_rooms r
        LEFT JOIN Occupancy o ON r.RoomCode = o.Room
        LEFT JOIN NextAvailableDate n ON r.RoomCode = n.Room
        LEFT JOIN RecentStay rs ON r.RoomCode = rs.Room
    ORDER BY
        popularity_score DESC;

    """

    cursor.execute(query)
    rooms = cursor.fetchall()

    print(f"{'RoomCode':<10}{'RoomName':<30}{'Beds':<5}{'BedType':<10}{'MaxOcc':<7}{'BasePrice':<10}{'Decor':<15}{'Popularity':<12}{'NextCheckIn':<15}{'LastStayLength'}")
    print("="*140)
    for room in rooms:
        print(f"{room[0]:<10}{room[1]:<30}{room[2]:<5}{room[3]:<10}{room[4]:<7}{room[5]:<10}{room[6]:<15}{room[7]:<12}{room[8]:<15}{room[9]}")

    cursor.close()
    conn.close()

def make_reservation():
    conn = sqlite3.connect('inn.db')
    cursor = conn.cursor()

    first_name = input("Enter first name: ")
    last_name = input("Enter last name: ")
    room_code = input("Enter room code (or 'Any'): ")
    bed_type = input("Enter bed type (or 'Any'): ")
    begin_date = input("Enter begin date of stay (YYYY-MM-DD): ")
    end_date = input("Enter end date of stay (YYYY-MM-DD): ")
    num_children = int(input("Enter number of children: "))
    num_adults = int(input("Enter number of adults: "))

    

def main():
    while True:
        print("0 -> Exit")
        print("1 -> List Rooms and Rates")
        print("2 -> Make a Reservation")
        print("3 -> Cancel a Reservation")
        print("4 -> View Detailed Reservation Information")
        print("5 -> View Revenue")
        choice = input("Select an option: ")
        
        if choice == '0':
            break
        elif choice == '1':
            list_rooms()
        elif choice == '2':
            make_reservation()
        elif choice == '3':
            pass
        elif choice == '4':
            pass
        elif choice == '5':
            pass
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
