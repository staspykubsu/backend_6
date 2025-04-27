#!/usr/bin/env python3

import pymysql
import hashlib
import getpass

def create_connection():
    return pymysql.connect(
        host='158.160.182.8',
        user='u68593',
        password='9258357',
        database='web_db',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def main():
    print("Инициализация учетных данных администратора")
    username = input("Введите логин администратора: ")
    password = getpass.getpass("Введите пароль администратора: ")
    
    connection = create_connection()
    try:
        with connection.cursor() as cursor:
            # Check if admin exists
            cursor.execute("SELECT id FROM user_credentials WHERE username = %s", (username,))
            if cursor.fetchone():
                print("Ошибка: пользователь с таким логином уже существует")
                return
            
            # Create admin application (dummy record)
            cursor.execute("""
                INSERT INTO applications 
                (last_name, first_name, phone, email, birthdate, gender, bio, contract, username, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                'Admin', 'Admin', '+00000000000', 'admin@example.com', 
                '2000-01-01', 'male', 'Administrator', 1,
                username, hash_password(password)
            ))
            
            app_id = cursor.lastrowid
            
            # Insert into user_credentials
            cursor.execute("""
                INSERT INTO user_credentials 
                (application_id, username, password_hash)
                VALUES (%s, %s, %s)
            """, (
                app_id, username, hash_password(password)
            ))
            
            connection.commit()
            print("Учетные данные администратора успешно созданы")
            
    except Exception as e:
        print(f"Ошибка: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == "__main__":
    main()
