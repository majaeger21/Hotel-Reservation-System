import db
from datetime import datetime, timedelta
import mysql.connector

def list_rooms():
    try:
        conn = db.get_db_connection()
        if conn is None:
            print("Failed to connect to the database.")
            return

        cursor = conn.cursor()

        # Query to calculate room popularity, next available check-in date, and length of the most recent completed stay
        query = """
        WITH Occupancy AS (
            SELECT
                Room,
                SUM(DATEDIFF(LEAST(Checkout, '2024-06-01'), GREATEST(CheckIn, DATE_SUB('2024-06-01', INTERVAL 180 DAY)))) AS occupied_days
            FROM lab7_reservations
            WHERE Checkout > DATE_SUB('2024-06-01', INTERVAL 180 DAY)
            GROUP BY Room
        ),
        NextAvailableDate AS (
            SELECT
                Room,
                MIN(CheckIn) AS next_available
            FROM lab7_reservations
            WHERE Checkout > '2024-06-01'
            GROUP BY Room
        ),
        RecentStay AS (
            SELECT
                Room,
                DATEDIFF(MAX(Checkout), MAX(CheckIn)) AS recent_stay_length
            FROM lab7_reservations
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
            lab7_rooms r
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
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def calculate_total_cost(begin_date, end_date, base_rate):
    begin_date = datetime.strptime(begin_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    total_cost = 0.0
    current_date = begin_date
    base_rate = float(base_rate)  # Convert base_rate to float

    while current_date < end_date:
        if current_date.weekday() < 5:  # Weekday
            total_cost += base_rate
        else:  # Weekend
            total_cost += base_rate * 1.1
        current_date += timedelta(days=1)

    return round(total_cost, 2)

def make_reservation():
    try:
        conn = db.get_db_connection()
        if conn is None:
            print("Failed to connect to the database.")
            return
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
            print("No exact matches found. Suggesting 5 alternatives...")
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
            cursor.execute("""
            INSERT INTO lab7_reservations (Room, CheckIn, Checkout, Rate, LastName, FirstName, Adults, Kids)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (selected_room[1], begin_date, end_date, total_cost, last_name, first_name, num_adults, num_children))

            conn.commit()

            # Get the reservation code of the newly inserted reservation
            reservation_code = cursor.lastrowid

            # Confirmation screen
            print("\nReservation Confirmation:")
            print(f"Reservation code: {reservation_code}")
            print(f"First name: {first_name}")
            print(f"Last name: {last_name}")
            print(f"Room code: {selected_room[1]}")
            print(f"Room name: {selected_room[2]}")
            print(f"Bed type: {selected_room[4]}")
            print(f"Begin date of stay: {begin_date}")
            print(f"End date of stay: {end_date}")
            print(f"Number of adults: {num_adults}")
            print(f"Number of children: {num_children}")
            print(f"Total cost of stay: ${total_cost} \n ")

        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def cancel_reservation():
    try:
        conn = db.get_db_connection()
        if conn is None:
            print("Failed to connect to the database.")
            return
        cursor = conn.cursor()

        reservation_code = input("Enter the reservation code: ")

        # Query to check if the reservation exists
        query = """
        SELECT 
            CODE, Room, CheckIn, Checkout, LastName, FirstName 
        FROM 
            lab7_reservations 
        WHERE 
            CODE = %s
        """

        cursor.execute(query, (reservation_code,))
        reservation = cursor.fetchone()

        if reservation:
            # Confirm the reservation details
            print("\nReservation Details:")
            print(f"Reservation ID: {reservation[0]}")
            print(f"Room code: {reservation[1]}")
            print(f"Check-in date: {reservation[2]}")
            print(f"Check-out date: {reservation[3]}")
            print(f"Guest name: {reservation[5]} {reservation[4]}")
            
            confirm = input("Do you want to cancel this reservation? (yes/no): ")
            if confirm.lower() == 'yes':
                # Delete the reservation
                delete_query = "DELETE FROM lab7_reservations WHERE CODE = %s"
                cursor.execute(delete_query, (reservation[0],))
                conn.commit()
                print("Reservation cancelled successfully.\n")
            else:
                print("Reservation cancellation aborted.")
        else:
            print("No reservation found with the given code.")

        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def d_r_i(): 
    try:
        conn = db.get_db_connection()
        if conn is None:
            print("Failed to connect to the database.")
            return
        cursor = conn.cursor()

        first_name = input("Enter first name: ")
        last_name = input("Enter last name: ")
        reservation_code = input("Enter reservation code: ")
        room_code = input("Enter room code: ")
        begin_date = input("Enter begin date of stay (YYYY-MM-DD): ")
        end_date = input("Enter end date of stay (YYYY-MM-DD): ")

        # Query to find available rooms based on user input
        query = f"""
        SELECT 
            CODE,
            Room,
            CheckIn,
            Checkout,
            Rate,
            LastName,
            Firstname,
            Adults,
            Kids,
            RoomName
        FROM
             lab7_reservations
        INNER JOIN lab7_rooms ON Room = RoomCode
        WHERE
            (FirstName LIKE '{first_name}' OR '{first_name}' = '')
            AND (LastName LIKE '{last_name}' OR '{last_name}' = '')
            AND (CODE LIKE '{reservation_code}' OR '{reservation_code}' = '')
            AND (Room LIKE '{room_code}' OR '{room_code}' = '')
            AND CheckIn = '{begin_date}'
            AND CheckOut = '{end_date}'
        """
        cursor.execute(query)
        reservations = cursor.fetchall()

        if reservations:
            print(f"{'CODE':<12}{'Room':<6}{'CheckIn':<12}{'CheckOut':<12}{'Rate':<9}{'LastName':<16}{'FirstName':<16}{'Adults':<12}{'Kids':<12}{'RoomName':<31}")
            print("="*138)
            for reservation in reservations:
                print(f"{reservation[0]:<12}{reservation[1]:<6}{begin_date:<12}{end_date:<12}{reservation[4]:<9}{reservation[5]:<16}{reservation[6]:<16}{reservation[7]:<12}{reservation[8]:<12}{reservation[9]:<31}")
        else:
            print("Reservation not found.")

        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    except Exception as e:
        print(f"Unexpected error: {e}")


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
            cancel_reservation()
        elif choice == '4':
            d_r_i() 
        elif choice == '5':
            pass  # Add your revenue view logic here
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
