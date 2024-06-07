import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="db.labthreesixfive.com",
            user=os.getenv("HP_JDBC_USER"),
            password=os.getenv("HP_JDBC_PW"),
            database=os.getenv("HP_JDBC_USER")
        )
        if connection.is_connected():
            print("Connected to MySQL database")
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None
