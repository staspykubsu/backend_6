#!/usr/bin/env python3

import cgi
import http.cookies
import pymysql
from datetime import datetime, timedelta
import os
import hashlib
import base64

def create_connection():
    try:
        return pymysql.connect(
            host='158.160.182.8',
            user='u68593',
            password='9258357',
            database='web_db',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.Error as e:
        print("Content-Type: text/html; charset=utf-8")
        print("\n")
        print(f"Ошибка подключения к базе данных: {e}")
        return None

def check_admin_auth():
    auth = os.environ.get('HTTP_AUTHORIZATION', '')
    if not auth or not auth.startswith('Basic '):
        return False
    
    auth_decoded = base64.b64decode(auth[6:]).decode('utf-8')
    username, password = auth_decoded.split(':', 1)
    
    connection = create_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT password_hash FROM user_credentials 
                WHERE username = %s
            """, (username,))
            result = cursor.fetchone()
            
            if result:
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                return hashed_password == result['password_hash']
    finally:
        connection.close()
    
    return False

def require_auth():
    print("WWW-Authenticate: Basic realm=\"Admin Area\"")
    print("Status: 401 Unauthorized")
    print("Content-Type: text/html; charset=utf-8")
    print("\n")
    print("<h1>401 Unauthorized</h1>")
    exit()

def get_all_applications(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT a.id, a.last_name, a.first_name, a.patronymic, 
                   a.phone, a.email, a.birthdate, a.gender, a.bio, a.contract,
                   GROUP_CONCAT(pl.name) as languages
            FROM applications a
            LEFT JOIN application_languages al ON a.id = al.application_id
            LEFT JOIN programming_languages pl ON al.language_id = pl.id
            GROUP BY a.id
            ORDER BY a.id DESC
        """)
        return cursor.fetchall()

def get_language_stats(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT pl.name as language, COUNT(al.application_id) as count
            FROM programming_languages pl
            LEFT JOIN application_languages al ON pl.id = al.language_id
            GROUP BY pl.id
            ORDER BY count DESC
        """)
        return cursor.fetchall()

def delete_application(connection, app_id):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM application_languages WHERE application_id = %s", (app_id,))
        cursor.execute("DELETE FROM applications WHERE id = %s", (app_id,))
        connection.commit()

def get_application(connection, app_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT a.*, GROUP_CONCAT(pl.name) as languages
            FROM applications a
            LEFT JOIN application_languages al ON a.id = al.application_id
            LEFT JOIN programming_languages pl ON al.language_id = pl.id
            WHERE a.id = %s
            GROUP BY a.id
        """, (app_id,))
        return cursor.fetchone()

def update_application(connection, app_id, data):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE applications 
            SET last_name=%s, first_name=%s, patronymic=%s, phone=%s, email=%s, 
                birthdate=%s, gender=%s, bio=%s, contract=%s
            WHERE id=%s
        """, (
            data['last_name'], data['first_name'], data['patronymic'],
            data['phone'], data['email'], data['birthdate'],
            data['gender'], data['bio'], data['contract'],
            app_id
        ))
        
        cursor.execute("DELETE FROM application_languages WHERE application_id=%s", (app_id,))
        
        language_ids = {
            'Pascal': 1, 'C': 2, 'C++': 3, 'JavaScript': 4, 'PHP': 5,
            'Python': 6, 'Java': 7, 'Haskel': 8, 'Clojure': 9,
            'Prolog': 10, 'Scala': 11, 'Go': 12
        }

        for language in data['languages']:
            language_id = language_ids.get(language)
            if language_id:
                cursor.execute("""
                    INSERT INTO application_languages (application_id, language_id)
                    VALUES (%s, %s)
                """, (app_id, language_id))
        
        connection.commit()

def generate_admin_page(applications, stats, message=None):
    print("Content-Type: text/html; charset=utf-8")
    print("\n")
    print("""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Админ-панель</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                line-height: 1.6;
            }
            h1, h2 {
                color: #333;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
            tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            .action-buttons {
                white-space: nowrap;
            }
            .stats {
                margin: 30px 0;
            }
            .message {
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
            }
            .success {
                background-color: #d4edda;
                color: #155724;
            }
            .error {
                background-color: #f8d7da;
                color: #721c24;
            }
            .edit-form {
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            .edit-form label {
                display: block;
                margin-top: 10px;
            }
            .edit-form input[type="text"],
            .edit-form input[type="tel"],
            .edit-form input[type="email"],
            .edit-form input[type="date"],
            .edit-form select,
            .edit-form textarea {
                width: 100%;
                padding: 8px;
                margin-top: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            .edit-form button {
                margin-top: 20px;
                padding: 8px 16px;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            .edit-form button:hover {
                background-color: #0069d9;
            }
        </style>
    </head>
    <body>
        <h1>Админ-панель</h1>
    """)
    
    if message:
        print(f'<div class="message {message["type"]}">{message["text"]}</div>')
    
    print("""
        <div class="stats">
            <h2>Статистика по языкам программирования</h2>
            <table>
                <tr>
                    <th>Язык программирования</th>
                    <th>Количество пользователей</th>
                </tr>
    """)
    
    for stat in stats:
        print(f"""
                <tr>
                    <td>{stat['language']}</td>
                    <td>{stat['count']}</td>
                </tr>
        """)
    
    print("""
            </table>
        </div>
        
        <h2>Все заявки</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>ФИО</th>
                <th>Телефон</th>
                <th>Email</th>
                <th>Дата рождения</th>
                <th>Пол</th>
                <th>Языки программирования</th>
                <th>Действия</th>
            </tr>
    """)
    
    for app in applications:
        full_name = f"{app['last_name']} {app['first_name']}"
        if app['patronymic']:
            full_name += f" {app['patronymic']}"
        
        languages = app['languages'].split(',') if app['languages'] else []
        languages_html = ', '.join(languages)
        
        print(f"""
            <tr>
                <td>{app['id']}</td>
                <td>{full_name}</td>
                <td>{app['phone']}</td>
                <td>{app['email']}</td>
                <td>{app['birthdate']}</td>
                <td>{'Мужской' if app['gender'] == 'male' else 'Женский'}</td>
                <td>{languages_html}</td>
                <td class="action-buttons">
                    <a href="admin.py?action=edit&id={app['id']}">Редактировать</a> | 
                    <a href="admin.py?action=delete&id={app['id']}" onclick="return confirm('Вы уверены?')">Удалить</a>
                </td>
            </tr>
        """)
    
    print("""
        </table>
    </body>
    </html>
    """)

def generate_edit_form(application, languages):
    print("Content-Type: text/html; charset=utf-8")
    print("\n")
    print(f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Редактирование заявки #{application['id']}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                line-height: 1.6;
            }}
            .edit-form {{
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }}
            .edit-form label {{
                display: block;
                margin-top: 10px;
            }}
            .edit-form input[type="text"],
            .edit-form input[type="tel"],
            .edit-form input[type="email"],
            .edit-form input[type="date"],
            .edit-form select,
            .edit-form textarea {{
                width: 100%;
                padding: 8px;
                margin-top: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }}
            .edit-form button {{
                margin-top: 20px;
                padding: 8px 16px;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }}
            .edit-form button:hover {{
                background-color: #0069d9;
            }}
            .back-link {{
                display: block;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>Редактирование заявки #{application['id']}</h1>
        <form method="post" class="edit-form">
            <input type="hidden" name="action" value="update">
            <input type="hidden" name="id" value="{application['id']}">
            
            <label for="last_name">Фамилия:</label>
            <input type="text" id="last_name" name="last_name" value="{application['last_name']}" required>
            
            <label for="first_name">Имя:</label>
            <input type="text" id="first_name" name="first_name" value="{application['first_name']}" required>
            
            <label for="patronymic">Отчество:</label>
            <input type="text" id="patronymic" name="patronymic" value="{application['patronymic'] or ''}">
            
            <label for="phone">Телефон:</label>
            <input type="tel" id="phone" name="phone" value="{application['phone']}" required>
            
            <label for="email">Email:</label>
            <input type="email" id="email" name="email" value="{application['email']}" required>
            
            <label for="birthdate">Дата рождения:</label>
            <input type="date" id="birthdate" name="birthdate" value="{application['birthdate']}" required>
            
            <label>Пол:</label>
            <label><input type="radio" name="gender" value="male" {'checked' if application['gender'] == 'male' else ''}> Мужской</label>
            <label><input type="radio" name="gender" value="female" {'checked' if application['gender'] == 'female' else ''}> Женский</label>
            
            <label for="languages">Любимые языки программирования:</label>
            <select id="languages" name="languages[]" multiple required>
    """)
    
    all_languages = ['Pascal', 'C', 'C++', 'JavaScript', 'PHP', 'Python', 
                    'Java', 'Haskel', 'Clojure', 'Prolog', 'Scala', 'Go']
    
    for lang in all_languages:
        selected = 'selected' if lang in languages else ''
        print(f'<option value="{lang}" {selected}>{lang}</option>')
    
    print(f"""
            </select>
            
            <label for="bio">Биография:</label>
            <textarea id="bio" name="bio" rows="4" required>{application['bio']}</textarea>
            
            <label>
                <input type="checkbox" name="contract" {'checked' if application['contract'] else ''}>
                С контрактом ознакомлен(а)
            </label>
            
            <button type="submit">Сохранить</button>
        </form>
        
        <a href="admin.py" class="back-link">← Назад к списку заявок</a>
    </body>
    </html>
    """)

if __name__ == "__main__":
    if not check_admin_auth():
        require_auth()
    
    form = cgi.FieldStorage()
    action = form.getvalue('action')
    app_id = form.getvalue('id')
    
    connection = create_connection()
    if not connection:
        print("Content-Type: text/html; charset=utf-8")
        print("\n")
        print("<h1>Ошибка подключения к базе данных</h1>")
        exit()
    
    message = None
    
    try:
        if action == 'delete' and app_id:
            delete_application(connection, app_id)
            message = {'type': 'success', 'text': 'Заявка успешно удалена'}
        
        elif action == 'edit' and app_id:
            application = get_application(connection, app_id)
            if not application:
                message = {'type': 'error', 'text': 'Заявка не найдена'}
            else:
                languages = application['languages'].split(',') if application['languages'] else []
                generate_edit_form(application, languages)
                exit()
        
        elif action == 'update' and app_id:
            data = {
                'last_name': form.getvalue('last_name', '').strip(),
                'first_name': form.getvalue('first_name', '').strip(),
                'patronymic': form.getvalue('patronymic', '').strip(),
                'phone': form.getvalue('phone', '').strip(),
                'email': form.getvalue('email', '').strip(),
                'birthdate': form.getvalue('birthdate', '').strip(),
                'gender': form.getvalue('gender', '').strip(),
                'languages': form.getlist('languages[]'),
                'bio': form.getvalue('bio', '').strip(),
                'contract': form.getvalue('contract') == 'on'
            }
            
            update_application(connection, app_id, data)
            message = {'type': 'success', 'text': 'Заявка успешно обновлена'}
    
    except Exception as e:
        message = {'type': 'error', 'text': f'Ошибка: {str(e)}'}
    
    applications = get_all_applications(connection)
    stats = get_language_stats(connection)
    generate_admin_page(applications, stats, message)
    
    connection.close()
