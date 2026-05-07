from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import deque
import time

app = Flask(__name__)
CORS(app)

# 1. User Login Details using Hash Map (Dictionary)
# Format: { "username": {"password": "pwd", "fullName": "name", "email": "email", "phone": "phone"} }
users = {
    "Surya": {
        "password": "12345",
        "fullName": "Surya",
        "email": "surya@openbid.com",
        "phone": "+91 98765 43210"
    }
    
}

# 2. Bid History using Stack
# List used as a stack (append for push, pop for pop)
bid_history = []

# 3. Remaining Bids using Queue
# Deque used as a queue (append for enqueue, popleft for dequeue)
bid_queue = deque()


@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    
    if not username or username in users:
        return jsonify({"error": "User already exists or invalid data"}), 400
        
    users[username] = {
        "password": data.get('password'),
        "fullName": data.get('fullName'),
        "email": data.get('email'),
        "phone": data.get('phone')
    }
    return jsonify({"message": "User registered successfully", "user": users[username]}), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if username in users and users[username]['password'] == password:
        user_info = users[username].copy()
        user_info['username'] = username
        del user_info['password']
        return jsonify({"message": "Login successful", "user": user_info}), 200
        
    return jsonify({"error": "Invalid credentials"}), 401


@app.route('/api/bid', methods=['POST'])
def place_bid():
    data = request.json
    bid_item = {
        "itemId": data.get('itemId'),
        "amount": data.get('amount'),
        "bidder": data.get('bidder'),
        "time": int(time.time() * 1000)
    }
    
    # Push to Stack
    bid_history.append(bid_item)
    
    # Enqueue to Queue
    bid_queue.append(bid_item)
    
    return jsonify({"message": "Bid placed", "bid": bid_item}), 201


@app.route('/api/bids/history', methods=['GET'])
def get_history():
    item_id = request.args.get('itemId')
    
    # Reading stack top to bottom (LIFO, reverse order)
    if item_id:
        history = [bid for bid in reversed(bid_history) if bid['itemId'] == item_id]
    else:
        history = list(reversed(bid_history))
        
    return jsonify({"history": history}), 200


@app.route('/api/bids/queue', methods=['GET'])
def get_queue():
    # Return current remaining bids without popping
    return jsonify({"queue": list(bid_queue)}), 200


@app.route('/api/bids/process', methods=['POST'])
def process_bid():
    if not bid_queue:
        return jsonify({"message": "Queue is empty"}), 200
        
    # Dequeue from Queue
    processed_bid = bid_queue.popleft()
    return jsonify({"message": "Bid processed", "bid": processed_bid}), 200


@app.route('/api/bids/suggestions', methods=['GET'])
def get_suggestions():
    item_id = request.args.get('itemId')
    current_price = float(request.args.get('currentPrice', 0))
    
    # Count bids for this item in history
    item_bids = [bid for bid in bid_history if bid.get('itemId') == item_id]
    bid_count = len(item_bids)
    
    # Dynamic Increment Algorithm
    if bid_count < 5:
        inc_percent = 0.05
    elif bid_count < 15:
        inc_percent = 0.10
    else:
        inc_percent = 0.15
        
    import math
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
    items = data.get('items', [])
    sort_mode = data.get('sortMode')
    
    if sort_mode == 'asc':
        # Sort by basePrice ascending
        items = sorted(items, key=lambda x: float(x.get('basePrice', 0)))
    elif sort_mode == 'desc':
        # Sort by basePrice descending
        items = sorted(items, key=lambda x: float(x.get('basePrice', 0)), reverse=True)
        
    return jsonify({"items": items}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
