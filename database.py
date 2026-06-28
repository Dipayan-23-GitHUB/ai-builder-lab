import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = 'tutorial.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def init_db():
    """Creates the database tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    # Progress table (linked to user_id)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            user_id INTEGER PRIMARY KEY,
            current_step INTEGER DEFAULT 0,
            completed_topics TEXT DEFAULT '[]',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

def create_user(email, password):
    """Hashes password and saves user. Returns user_id or None if email exists."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        password_hash = generate_password_hash(password)
        cursor.execute('INSERT INTO users (email, password_hash) VALUES (?, ?)', (email, password_hash))
        user_id = cursor.lastrowid
        
        # Initialize empty progress for the new user
        cursor.execute('INSERT INTO progress (user_id) VALUES (?)', (user_id,))
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None # Email already exists
    finally:
        conn.close()

def verify_user(email, password):
    """Checks if email exists and password matches. Returns user_id or None."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, password_hash FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        return user['id']
    return None

def save_progress(user_id, step, topics_json):
    """Saves or updates the user's progress."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO progress (user_id, current_step, completed_topics) 
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
        current_step = excluded.current_step, 
        completed_topics = excluded.completed_topics
    ''', (user_id, step, topics_json))
    conn.commit()
    conn.close()

def get_progress(user_id):
    """Fetches the user's saved progress."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT current_step, completed_topics FROM progress WHERE user_id = ?', (user_id,))
    progress = cursor.fetchone()
    conn.close()
    
    if progress:
        return {'current_step': progress['current_step'], 'completed_topics': progress['completed_topics']}
    return {'current_step': 0, 'completed_topics': '[]'}