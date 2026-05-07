import os
import time
import math
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Initialize Flask App
# Serve static files from the current directory
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Configure Database
# Use DATABASE_URL from environment if available (for Render Postgres),
# otherwise fallback to local SQLite database (for local development)
database_url = os.environ.get('DATABASE_URL', 'sqlite:///openbid.db')
# Fix for Render Postgres URL which might start with postgres:// instead of postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─── Database Models ──────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)

class Item(db.Model):
    id = db.Column(db.String(100), primary_key=True) # e.g. "item-123"
    name = db.Column(db.String(200), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    seller = db.Column(db.String(80), nullable=False)
    room = db.Column(db.Integer, nullable=False)
    token = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100))
    image = db.Column(db.Text)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default="active") # active or sold
    created_at = db.Column(db.Float, default=lambda: time.time() * 1000)

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.String(100), db.ForeignKey('item.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    bidder = db.Column(db.String(80), nullable=False)
    time = db.Column(db.Float, default=lambda: time.time() * 1000)
    status = db.Column(db.String(50), default="queued") # queued, processed

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.String(100), db.ForeignKey('item.id'), nullable=False)
    user_username = db.Column(db.String(80), nullable=False)

# Create tables
with app.app_context():
    db.create_all()
    # Safely add missing columns to existing table
    try:
        db.session.execute(db.text('ALTER TABLE item ADD COLUMN image TEXT'))
        db.session.commit()
    except Exception:
        db.session.rollback()
    
    try:
        db.session.execute(db.text('ALTER TABLE item ADD COLUMN description TEXT'))
        db.session.commit()
    except Exception:
        db.session.rollback()

# ─── Frontend Routes ──────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    # This will serve other HTML files, JS, CSS, etc.
    if os.path.exists(path):
        return send_from_directory('.', path)
    return "File not found", 404

# ─── API Routes: Auth ─────────────────────────────────────────

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({"error": "Invalid data"}), 400
        
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"error": "User already exists"}), 400
        
    new_user = User(
        username=username,
        password=data.get('password'),
        full_name=data.get('fullName'),
        email=data.get('email'),
        phone=data.get('phone')
    )
    db.session.add(new_user)
    db.session.commit()
    
    user_info = {
        "username": new_user.username,
        "fullName": new_user.full_name,
        "email": new_user.email,
        "phone": new_user.phone
    }
    return jsonify({"message": "User registered successfully", "user": user_info}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        user_info = {
            "username": user.username,
            "fullName": user.full_name,
            "email": user.email,
            "phone": user.phone
        }
        return jsonify({"message": "Login successful", "user": user_info}), 200
        
    return jsonify({"error": "Invalid credentials"}), 401

# ─── API Routes: Items ────────────────────────────────────────

@app.route('/api/items', methods=['GET', 'POST'])
def handle_items():
    if request.method == 'POST':
        data = request.json
        new_item = Item(
            id=data.get('id'),
            name=data.get('name'),
            base_price=float(data.get('basePrice')),
            seller=data.get('seller'),
            room=int(data.get('room')),
            token=int(data.get('token')),
            category=data.get('category', ''),
            image=data.get('image', ''),
            description=data.get('description', ''),
            status='active'
        )
        db.session.add(new_item)
        db.session.commit()
        return jsonify({"message": "Item added successfully", "item": data}), 201
    
    else: # GET
        items = Item.query.all()
        result = []
        for item in items:
            result.append({
                "id": item.id,
                "name": item.name,
                "basePrice": item.base_price,
                "seller": item.seller,
                "room": item.room,
                "token": item.token,
                "category": item.category,
                "image": item.image,
                "description": item.description,
                "status": item.status
            })
        return jsonify({"items": result}), 200

@app.route('/api/items/<item_id>/sold', methods=['POST'])
def mark_item_sold(item_id):
    item = Item.query.get(item_id)
    if item:
        item.status = 'sold'
        db.session.commit()
        return jsonify({"message": "Item marked as sold"}), 200
    return jsonify({"error": "Item not found"}), 404

# ─── API Routes: Notifications ────────────────────────────────

@app.route('/api/notify', methods=['POST'])
def add_notification():
    data = request.json
    item_id = data.get('itemId')
    username = data.get('user')
    
    existing = Notification.query.filter_by(item_id=item_id, user_username=username).first()
    if not existing:
        new_notify = Notification(item_id=item_id, user_username=username)
        db.session.add(new_notify)
        db.session.commit()
    return jsonify({"message": "Notification added"}), 200

@app.route('/api/notify/<item_id>', methods=['GET'])
def get_notifications(item_id):
    notifs = Notification.query.filter_by(item_id=item_id).all()
    users = [n.user_username for n in notifs]
    return jsonify({"users": users}), 200

# ─── API Routes: Bids ─────────────────────────────────────────

@app.route('/api/bid', methods=['POST'])
def place_bid():
    data = request.json
    item_id = data.get('itemId')
    new_amount = float(data.get('amount'))
    
    # Check if bid is valid (must be higher than current top bid)
    top_bid = Bid.query.filter_by(item_id=item_id).order_by(Bid.amount.desc()).first()
    if top_bid and new_amount <= top_bid.amount:
        return jsonify({"error": f"Bid must be higher than ₹{int(top_bid.amount)}"}), 400
        
    item = Item.query.get(item_id)
    if item and new_amount < item.base_price:
        return jsonify({"error": f"Bid must be at least ₹{int(item.base_price)}"}), 400

    new_bid = Bid(
        item_id=item_id,
        amount=new_amount,
        bidder=data.get('bidder'),
        status="queued"
    )
    db.session.add(new_bid)
    db.session.commit()
    
    bid_item = {
        "id": new_bid.id,
        "itemId": new_bid.item_id,
        "amount": new_bid.amount,
        "bidder": new_bid.bidder,
        "time": new_bid.time
    }
    return jsonify({"message": "Bid placed", "bid": bid_item}), 201

@app.route('/api/bids/history', methods=['GET'])
def get_history():
    item_id = request.args.get('itemId')
    
    if item_id:
        bids = Bid.query.filter_by(item_id=item_id).order_by(Bid.time.desc()).all()
    else:
        bids = Bid.query.order_by(Bid.time.desc()).all()
        
    history = []
    for bid in bids:
        history.append({
            "id": bid.id,
            "itemId": bid.item_id,
            "amount": bid.amount,
            "bidder": bid.bidder,
            "time": bid.time,
            "status": bid.status
        })
    return jsonify({"history": history}), 200

@app.route('/api/bids/queue', methods=['GET'])
def get_queue():
    bids = Bid.query.filter_by(status='queued').order_by(Bid.time.asc()).all()
    queue = []
    for bid in bids:
        queue.append({
            "id": bid.id,
            "itemId": bid.item_id,
            "amount": bid.amount,
            "bidder": bid.bidder,
            "time": bid.time
        })
    return jsonify({"queue": queue}), 200

@app.route('/api/bids/process', methods=['POST'])
def process_bid():
    bid = Bid.query.filter_by(status='queued').order_by(Bid.time.asc()).first()
    if not bid:
        return jsonify({"message": "Queue is empty"}), 200
        
    bid.status = 'processed'
    db.session.commit()
    
    processed_bid = {
        "id": bid.id,
        "itemId": bid.item_id,
        "amount": bid.amount,
        "bidder": bid.bidder,
        "time": bid.time
    }
    return jsonify({"message": "Bid processed", "bid": processed_bid}), 200

@app.route('/api/bids/suggestions', methods=['GET'])
def get_suggestions():
    item_id = request.args.get('itemId')
    current_price = float(request.args.get('currentPrice', 0))
    
    bid_count = Bid.query.filter_by(item_id=item_id).count()
    
    # Dynamic Increment Algorithm
    if bid_count < 5:
        inc_percent = 0.05
    elif bid_count < 15:
        inc_percent = 0.10
    else:
        inc_percent = 0.15
        
    suggested = math.ceil(current_price + (current_price * inc_percent))
    option2_percent = inc_percent + 0.05
    option3_percent = inc_percent + 0.15
    option2 = math.ceil(current_price + (current_price * option2_percent))
    option3 = math.ceil(current_price + (current_price * option3_percent))
    
    options = [
        {"label": "Suggested", "amount": suggested},
        {"label": f"+{int(option2_percent * 100)}%", "amount": option2},
        {"label": f"+{int(option3_percent * 100)}%", "amount": option3}
    ]
    
    return jsonify({"options": options}), 200

@app.route('/api/items/sort', methods=['POST'])
def sort_items():
    data = request.json
    items_data = data.get('items', [])
    sort_mode = data.get('sortMode')
    
    if sort_mode == 'asc':
        # Sort by basePrice ascending
        items_data = sorted(items_data, key=lambda x: float(x.get('basePrice', 0)))
    elif sort_mode == 'desc':
        # Sort by basePrice descending
        items_data = sorted(items_data, key=lambda x: float(x.get('basePrice', 0)), reverse=True)
        
    return jsonify({"items": items_data}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
