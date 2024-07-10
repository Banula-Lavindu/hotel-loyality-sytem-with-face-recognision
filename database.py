import sqlite3
import pickle
import face_recognition
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

def connect_db():
    return sqlite3.connect('users.db')

def create_tables():
    conn = connect_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT NOT NULL,
                  face_encoding BLOB NOT NULL,
                  visits INTEGER DEFAULT 0,
                  rewards INTEGER DEFAULT 0,
                  last_visit_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS credentials
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL UNIQUE,
                  password TEXT NOT NULL)''')
    conn.commit()
    conn.close()

def add_user(name, email, face_encoding):
    conn = connect_db()
    c = conn.cursor()
    c.execute('INSERT INTO users (name, email, face_encoding) VALUES (?, ?, ?)',
              (name, email, pickle.dumps(face_encoding)))
    conn.commit()
    conn.close()

def get_users():
    conn = connect_db()
    c = conn.cursor()
    c.execute('SELECT id, name, email, visits, rewards FROM users')
    users = c.fetchall()
    conn.close()
    return users

def increment_visits(user_id):
    conn = connect_db()
    c = conn.cursor()
    current_date = datetime.now().date().isoformat()

    c.execute('SELECT visits, last_visit_date FROM users WHERE id = ?', (user_id,))
    visits, last_visit_date = c.fetchone()

    if last_visit_date != current_date:
        visits = 0  # Reset visit count for a new day
    if visits < 2:
        visits += 1
        if visits == 2:
            rewards = 10
        else:
            rewards = 20  # Add points for the second visit
        c.execute('UPDATE users SET visits = ?, rewards = rewards + ?, last_visit_date = ? WHERE id = ?',
                  (visits, rewards, current_date, user_id))
    conn.commit()
    conn.close()

def get_user_by_face(face_encoding):
    conn = connect_db()
    c = conn.cursor()
    c.execute('SELECT id, face_encoding FROM users')
    users = c.fetchall()
    conn.close()
    for user_id, db_face_encoding in users:
        if face_recognition.compare_faces([pickle.loads(db_face_encoding)], face_encoding)[0]:
            return user_id
    return None

def get_user_by_id(user_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_credential(username, password):
    conn = connect_db()
    c = conn.cursor()
    hashed_password = generate_password_hash(password)
    c.execute('INSERT INTO credentials (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()

def verify_credential(username, password):
    conn = connect_db()
    c = conn.cursor()
    c.execute('SELECT password FROM credentials WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    if result is None:
        return False
    return check_password_hash(result[0], password)

def add_last_visit_date_column():
    conn = connect_db()
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE users ADD COLUMN last_visit_date TEXT')
    except sqlite3.OperationalError as e:
        print(f"Column already exists: {e}")
    conn.commit()
    conn.close()

def delete_user_by_name(name):
    conn = connect_db()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE name = ?', (name,))
    conn.commit()
    conn.close()

# Initialize database
create_tables()
add_last_visit_date_column()
