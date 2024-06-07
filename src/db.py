# src/db.py
import mysql.connector

def get_db_connection(username, password):
    connection = mysql.connector.connect(
        host="db.labthreesixfive.com",
        user=username,
        password=password,
        database=username  
    )
    return connection
