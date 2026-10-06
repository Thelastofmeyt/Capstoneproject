# --- DEBUG STARTUP CHECK ---
print("DEBUG: app.py script started execution (1).")
# --- END DEBUG STARTUP CHECK ---

from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import timedelta, datetime
import requests
from sqlalchemy import inspect, func
import json

# Imports for OCR functionality
import cv2
from PIL import Image
import easyocr
import re
import numpy as np
import isbnlib
import io # For handling image bytes in memory

print("DEBUG: All imports successful (2).")

# --- SECRET_KEY Management ---
SECRET_KEY_FILE = 'secret_key.txt'
if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, 'r') as f:
        APP_SECRET_KEY = f.read().strip()
    print(f"DEBUG: SECRET_KEY loaded from {SECRET_KEY_FILE}.")
else:
    APP_SECRET_KEY = os.urandom(24).hex()
    with open(SECRET_KEY_FILE, 'w') as f:
        f.write(APP_SECRET_KEY)

app = Flask(__name__)
app.secret_key = APP_SECRET_KEY

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app)

# Initialize OCR reader
print("DEBUG: Initializing EasyOCR Reader (3)...")
# Note: This might take a few seconds on first run to load models
reader = easyocr.Reader(['en'])
print("DEBUG: EasyOCR Reader initialized (4).")

# --- Database Models ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    books = db.relationship('Book', backref='owner', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200))
    isbn = db.Column(db.String(20))
    description = db.Column(db.Text)
    cover_image_url = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Track when the book was added for the activity chart
    date_added = db.Column(db.DateTime, default=func.now())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Database Migration/Initialization ---

def migrate_database():
    """
    Manually handles database schema updates for SQLite since we aren't using Flask-Migrate yet.
    """
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            if 'book' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('book')]
                with db.engine.connect() as conn:
                    # 1. Check for cover_image_url column
                    if 'cover_image_url' not in columns:
                        print("DEBUG: Adding 'cover_image_url' column to 'book' table (5).")
                        conn.execute(db.text("ALTER TABLE book ADD COLUMN cover_image_url VARCHAR(500)"))
                    
                    # 2. Check for date_added column (Required for Activity Chart)
                    if 'date_added' not in columns:
                        print("DEBUG: Adding 'date_added' column to 'book' table (6).")
                        conn.execute(db.text("ALTER TABLE book ADD COLUMN date_added DATETIME"))
                        # Backfill existing books so they appear on the chart
                        conn.execute(db.text("UPDATE book SET date_added = CURRENT_TIMESTAMP WHERE date_added IS NULL"))
                    
                    conn.commit()
                    print("DEBUG: Migration checks completed successfully (7).")
        except Exception as e:
            print(f"DEBUG: Migration check failed: {e}")

# --- API Routes for Dashboard & Dynamic Content ---

@app.route('/api/stats/books_per_month')
@login_required
def books_per_month():
    """
    Returns the count of books added by the user per month for the Chart.js line graph.
    """
    try:
        # Query: Count books grouped by month for the current user
        stats = db.session.query(
            func.strftime('%m', Book.date_added).label('month'),
            func.count(Book.id).label('count')
        ).filter(Book.user_id == current_user.id).group_by('month').all()

        months_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        counts = [0] * 12

        for month_str, count in stats:
            if month_str:
                month_idx = int(month_str) - 1
                counts[month_idx] = count

        return jsonify({
            'labels': months_labels,
            'data': counts
        })
    except Exception as e:
        print(f"DEBUG: Chart API Error: {e}")
        return jsonify({'labels': [], 'data': []}), 500

# --- Standard Routes ---

@app.route('/')
@login_required
def home():
    print(f"DEBUG: Rendering dashboard for user: {current_user.username}")
    # Get the single most recently added book for the dashboard card
    last_book = Book.query.filter_by(user_id=current_user.id).order_by(Book.date_added.desc()).first()
    return render_template('dashboard.html', username=current_user.username, last_book=last_book)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            print(f"DEBUG: User {username} logged in (Remember: {remember}).")
            return redirect(url_for('home'))
        
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
            
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            print(f"DEBUG: New user registered: {username}")
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Registration error: {e}")
            flash('Username already exists.', 'danger')
            
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    print(f"DEBUG: User {current_user.username} logging out.")
    logout_user()
    return redirect(url_for('login'))

@app.route('/my_library')
@login_required
def my_library():
    print(f"DEBUG: Loading library for {current_user.username}.")
    user_books = Book.query.filter_by(user_id=current_user.id).all()
    return render_template('my_library.html', username=current_user.username, books=user_books)

@app.route('/delete_book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.user_id != current_user.id:
        print(f"DEBUG: Unauthorized delete attempt by {current_user.username} on book {book_id}")
        return "Unauthorized", 403
        
    db.session.delete(book)
    db.session.commit()
    print(f"DEBUG: Book {book_id} deleted by {current_user.username}.")
    flash('Book successfully removed from your library.', 'success')
    return redirect(url_for('my_library'))

# --- OCR and Image Processing Routes ---

@app.route('/ocr_upload')
@login_required
def ocr_upload():
    return render_template('ocr_upload.html', username=current_user.username)

@app.route('/process_ocr_image', methods=['POST'])
@login_required
def process_ocr_image():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('ocr_upload'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('ocr_upload'))

    if file:
        try:
            print(f"DEBUG: Starting OCR processing for file: {file.filename}")
            in_memory_file = io.BytesIO()
            file.save(in_memory_file)
            data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)

            # Perform OCR
            results = reader.readtext(img)
            extracted_text = " ".join([res[1] for res in results])
            
            print(f"DEBUG: OCR extracted text: {extracted_text[:100]}...")
            session['ocr_text'] = extracted_text
            return redirect(url_for('ocr_results'))
            
        except Exception as e:
            print(f"DEBUG: OCR Processing error: {e}")
            flash('Error processing image. Please try again with a clearer photo.', 'danger')
            return redirect(url_for('ocr_upload'))

@app.route('/ocr_results')
@login_required
def ocr_results():
    ocr_text = session.get('ocr_text', '')
    return render_template('ocr_results.html', username=current_user.username, ocr_text=ocr_text)

# --- Book Search & Addition APIs ---

@app.route('/api/search_books', methods=['POST'])
@login_required
def search_books():
    query = request.json.get('query', '')
    if not query:
        return jsonify({'books': []})

    print(f"DEBUG: Searching Google Books for: {query}")
    try:
        # Call Google Books API
        response = requests.get(f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5")
        data = response.json()
        
        books = []
        for item in data.get('items', []):
            info = item.get('volumeInfo', {})
            # Extract basic identifiers
            industry_ids = info.get('industryIdentifiers', [])
            isbn = industry_ids[0].get('identifier', 'N/A') if industry_ids else 'N/A'
            
            books.append({
                'title': info.get('title', 'Unknown Title'),
                'author': ", ".join(info.get('authors', ['Unknown Author'])),
                'isbn': isbn,
                'description': info.get('description', 'No description available.'),
                'cover_image_url': info.get('imageLinks', {}).get('thumbnail', '')
            })
        
        return jsonify({'books': books})
    except Exception as e:
        print(f"DEBUG: Google Books API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/add_book', methods=['POST'])
@login_required
def add_book():
    data = request.json
    try:
        new_book = Book(
            title=data.get('title'),
            author=data.get('author'),
            isbn=data.get('isbn'),
            description=data.get('description'),
            cover_image_url=data.get('cover_image_url'),
            user_id=current_user.id
        )
        db.session.add(new_book)
        db.session.commit()
        print(f"DEBUG: Book '{new_book.title}' added to {current_user.username}'s library.")
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error adding book: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# --- SocketIO Event Handlers ---

@socketio.on('connect')
def handle_connect():
    print("DEBUG: Client connected to SocketIO.")

@socketio.on('disconnect')
def handle_disconnect():
    print("DEBUG: Client disconnected from SocketIO.")

# --- Main execution block ---

if __name__ == "__main__":
    print("DEBUG: Entering main execution block (10).")
    with app.app_context():
        print("DEBUG: Inside app context for db.create_all() (11).")
        
        # Running migration before create_all, in case a table already exists but lacks columns
        migrate_database()
        
        db.create_all()
        print("DEBUG: Database tables checked/created (12).")
        
        if not os.path.exists(app.config["UPLOAD_FOLDER"]):
            os.makedirs(app.config["UPLOAD_FOLDER"])
            print(f"DEBUG: Upload folder '{app.config['UPLOAD_FOLDER']}' created (13).")
        else:
            print(f"DEBUG: Upload folder exists (14).")

    # Start the application
    print("DEBUG: Starting SocketIO server (15)...")
    socketio.run(app, debug=True)
