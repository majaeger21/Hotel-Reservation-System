import db
from datetime import date, datetime, timedelta
import sqlite3


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

def calculate_total_cost(begin_date, end_date, base_rate):
    begin_date = datetime.strptime(begin_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    total_cost = 0.0
    current_date = begin_date

    while current_date < end_date:
        if current_date.weekday() < 5:  # Weekday
            total_cost += base_rate
        else:  # Weekend
            total_cost += base_rate * 1.1
        current_date += timedelta(days=1)

    return round(total_cost, 2)

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

    total_guests = num_children + num_adults

    # Check if the requested person count exceeds the maximum capacity of any room
    cursor.execute("SELECT MAX(maxOcc) FROM lab7_rooms")
    max_capacity = cursor.fetchone()[0]
    if total_guests > max_capacity:
        print("No suitable rooms are available for the requested number of guests.")
        return

    # Query to find available rooms based on user input
    query = f"""
    WITH InputParameters AS (
        SELECT
            '{begin_date}' AS user_checkin,
            '{end_date}' AS user_checkout,
            '{bed_type}' AS user_bedtype,
            {total_guests} AS user_max_occ,
            {num_adults} AS user_adults,
            {num_children} AS user_children
    ),
    AvailableRooms AS (
        SELECT
            r.RoomCode,
            r.RoomName,
            r.Beds,
            r.bedType,
            r.maxOcc,
            r.basePrice,
            r.decor
        FROM
            lab7_rooms r
        LEFT JOIN
            lab7_reservations res
        ON
            r.RoomCode = res.Room
        AND (
            (res.CheckIn <= (SELECT user_checkin FROM InputParameters) AND res.Checkout > (SELECT user_checkin FROM InputParameters)) OR
            (res.CheckIn < (SELECT user_checkout FROM InputParameters) AND res.Checkout >= (SELECT user_checkout FROM InputParameters)) OR
            (res.CheckIn >= (SELECT user_checkin FROM InputParameters) AND res.Checkout <= (SELECT user_checkout FROM InputParameters))
        )
        WHERE
            res.Room IS NULL
            AND (r.RoomCode = '{room_code}' OR '{room_code}' = 'Any')
            AND (r.bedType = (SELECT user_bedtype FROM InputParameters) OR '{bed_type}' = 'Any')
            AND r.maxOcc >= (SELECT user_max_occ FROM InputParameters)
    )
    SELECT
        ROW_NUMBER() OVER (ORDER BY RoomCode) AS RoomNumber,
        RoomCode,
        RoomName,
        Beds,
        bedType,
        maxOcc,
        basePrice,
        decor
    FROM
        AvailableRooms;
    """

    cursor.execute(query)
    rooms = cursor.fetchall()

    if not rooms:
        # Suggest alternative rooms if no exact match is found
        print("No exact matches found. Suggesting alternatives...")
        alternative_query = f"""
        WITH InputParameters AS (
            SELECT
                '{begin_date}' AS user_checkin,
                '{end_date}' AS user_checkout,
                '{bed_type}' AS user_bedtype,
                {total_guests} AS user_max_occ,
                {num_adults} AS user_adults,
                {num_children} AS user_children
        ),
        AlternativeRooms AS (
            SELECT
                r.RoomCode,
                r.RoomName,
                r.Beds,
                r.bedType,
                r.maxOcc,
                r.basePrice,
                r.decor,
                LEAST(ABS(r.maxOcc - (SELECT user_max_occ FROM InputParameters)), ABS(r.Beds - (SELECT user_max_occ FROM InputParameters))) AS similarity
            FROM
                lab7_rooms r
            WHERE
                r.maxOcc >= (SELECT user_max_occ FROM InputParameters)
            ORDER BY
                similarity ASC
            LIMIT 5
        )
        SELECT
            ROW_NUMBER() OVER (ORDER BY RoomCode) AS RoomNumber,
            RoomCode,
            RoomName,
            Beds,
            bedType,
            maxOcc,
            basePrice,
            decor
        FROM
            AlternativeRooms;
        """

        cursor.execute(alternative_query)
        rooms = cursor.fetchall()

    print(f"{'No':<5}{'RoomCode':<10}{'RoomName':<30}{'Beds':<5}{'BedType':<10}{'MaxOcc':<7}{'BasePrice':<10}{'Decor'}")
    print("="*90)
    for room in rooms:
        print(f"{room[0]:<5}{room[1]:<10}{room[2]:<30}{room[3]:<5}{room[4]:<10}{room[5]:<7}{room[6]:<10}{room[7]}")

    if rooms:
        choice = input("Enter the number of the room you want to book or 'cancel' to return to the main menu: ")
        if choice.lower() == 'cancel':
            return

        selected_room = rooms[int(choice) - 1]

        # Calculate the total cost of the stay
        total_cost = calculate_total_cost(begin_date, end_date, selected_room[6])

        # Insert the reservation into the database
        cursor.execute(f"""
        INSERT INTO lab7_reservations (Room, CheckIn, Checkout, Rate, LastName, FirstName, Adults, Kids)
        VALUES ('{selected_room[1]}', '{begin_date}', '{end_date}', {total_cost}, '{last_name}', '{first_name}', {num_adults}, {num_children})
        """)

        conn.commit()

        # Confirmation screen
        print("\nReservation Confirmation:")
        print(f"First name: {first_name}")
        print(f"Last name: {last_name}")
        print(f"Room code: {selected_room[1]}")
        print(f"Room name: {selected_room[2]}")
        print(f"Bed type: {selected_room[4]}")
        print(f"Begin date of stay: {begin_date}")
        print(f"End date of stay: {end_date}")
        print(f"Number of adults: {num_adults}")
        print(f"Number of children: {num_children}")
        print(f"Total cost of stay: ${total_cost}")

    cursor.close()
    conn.close()


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
