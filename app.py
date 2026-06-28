from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import re
import subprocess
import sys
import os
import tempfile
from database import init_db, create_user, verify_user, save_progress, get_progress

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_in_production'

# Initialize database on startup
init_db()

# Regex for basic email validation
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # 1. Validate email format
        if not EMAIL_REGEX.match(email):
            return render_template('auth.html', error="Invalid email format.", mode='signup')
        
        # 2. Try to create user
        user_id = create_user(email, password)
        if user_id:
            session['user_id'] = user_id
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            return render_template('auth.html', error="Email already registered. Please login.", mode='signup')
            
    return render_template('auth.html', mode='signup')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user_id = verify_user(email, password)
        if user_id:
            session['user_id'] = user_id
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            return render_template('auth.html', error="Invalid email or password.", mode='login')
            
    return render_template('auth.html', mode='login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# MAIN DASHBOARD ROUTE
# ==========================================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # We will create index.html in Part 2
    return render_template('index.html', email=session['email'])

# ==========================================
# API ROUTES (PROGRESS & CODE EXECUTION)
# ==========================================
@app.route('/api/get_progress')
def api_get_progress():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(get_progress(session['user_id']))

@app.route('/api/save_progress', methods=['POST'])
def api_save_progress():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    step = data.get('step', 0)
    topics = data.get('topics', '[]')
    
    save_progress(session['user_id'], step, topics)
    return jsonify({'status': 'success'})

@app.route('/api/execute_code', methods=['POST'])
def api_execute_code():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    code = request.json.get('code', '')
    
    # Create a temporary file to run the user's code
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
        temp_file.write(code.encode('utf-8'))
        temp_file_path = temp_file.name
        
    try:
        # Execute using the SAME python environment (so it has access to torch/numpy)
        result = subprocess.run(
            [sys.executable, temp_file_path],
            capture_output=True,
            text=True,
            timeout=5 # 5 second timeout to prevent infinite loops
        )
        
        output = result.stdout
        error = result.stderr
        
        # Format the output for the UI
        if result.returncode != 0 and not output:
            output = f"Error:\n{error}"
        elif error:
            output += f"\nWarnings/Stderr:\n{error}"
            
        return jsonify({'output': output})
        
    except subprocess.TimeoutExpired:
        return jsonify({'output': 'Execution timed out! (Infinite loop detected or code took > 5 seconds)'})
    except Exception as e:
        return jsonify({'output': f'An internal error occurred: {str(e)}'})
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
    
