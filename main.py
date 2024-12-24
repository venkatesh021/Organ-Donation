from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from pymongo import MongoClient
from bson import ObjectId
import os

app = Flask(__name__)

# Secret key for session management
app.secret_key = os.urandom(24)  # For production, use a secure key!

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["OrgonDonation"]  #  database name
admin_collection = db["Admin"]  #  admin collection name
user_collection = db['Users']  # User collection 
donor_collection = db['Donors'] # Donor collection
request_collection = db['Requests']  # Organ request collection 

# Route: Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Route: Admin Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()  # Get JSON data sent from frontend
        username = data.get('username')
        password = data.get('password')

        # Verify admin credentials from MongoDB (plain-text password)
        admin = admin_collection.find_one({'username': username})

        if admin and admin['password'] == password:  # Direct comparison with plain text password
            session['admin'] = username
            flash("Login successful!", "success")
            return jsonify({'message': 'Login successful!'}), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401

    return render_template('login.html')

# Route: Admin Dashboard
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')


# Route: Logout
@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('user', None)
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))

@app.route('/view_donor_list')
def view_donor_list():
    # Fetch donors from MongoDB
    donors = list(donor_collection.find())  # Converts cursor to list
    for donor in donors:
        donor['_id'] = str(donor['_id'])  # Convert ObjectId to string for JSON compatibility
    return render_template('view_donor_list.html', donors=donors)


@app.route('/view_donor_requests')
def view_donor_requests():
    # Fetch all organ requests from the database
    organ_requests = list(request_collection.find())  # Replace 'db.requests' with your actual MongoDB collection

    # Pass the data to the template
    return render_template('view_donor_requests.html', organ_requests=organ_requests)
@app.route('/approve_requests', methods=['POST'])
def approve_requests():
    data = request.get_json()  # Get JSON data from the request
    request_ids = data.get('request_ids', [])  # Get the list of selected IDs

    if not request_ids:
        return jsonify({'success': False, 'message': 'No requests selected'})

    # Update the status of the selected requests to "Approved"
    for request_id in request_ids:
        request_collection.update_many(
            {'_id': ObjectId(request_id)},  # Match the request by its ID
            {'$set': {'status': 'Approved'}}  # Update the status field
        )

    return jsonify({'success': True, 'message': 'Requests approved successfully'})

@app.route('/remove_requests', methods=['POST'])
def remove_requests():
    try:
        data = request.get_json()
        request_ids = data.get('request_ids', [])

        if not request_ids:
            return jsonify({'success': False, 'message': 'No requests selected.'}), 400

        for request_id in request_ids:
            request_collection.update_many(
                {'_id': ObjectId(request_id)},  # Match the request by its ID
                {'$set': {'status': 'Dis-Approved'}}  # Update the status field
            )
        return jsonify({'success': True, 'message': 'Requests Denied.'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/add_donor', methods=['POST'])
def add_donor():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    address = data.get('address')
    organ = data.get('organ')

    # Insert new donor into the MongoDB collection
    new_donor = {
        "name": name,
        "email": email,
        "phone": phone,
        "address": address,
        "organ_to_donate": organ
    }
    result = donor_collection.insert_one(new_donor)

    # Check if the insertion was successful
    if result.inserted_id:
        return jsonify(success=True)
    return jsonify(success=False)

@app.route('/remove_donors', methods=['POST'])
def remove_donors():
    data = request.get_json()
    donor_ids = data.get('donor_ids')

    # Ensure donor_ids are ObjectId types
    donor_ids = [ObjectId(donor_id) for donor_id in donor_ids]
    
    # Remove selected donors from MongoDB
    result = donor_collection.delete_many({'_id': {'$in': donor_ids}})
    
    # Check if any donors were removed
    if result.deleted_count > 0:
        return jsonify(success=True)
    return jsonify(success=False)

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validate passwords
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('signin'))

        # Hash password
        user = {
            "email": email,
            "username": username,
            "password": password
        }

        # Insert user into MongoDB
        user_collection.insert_one(user)

        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('user_login'))

    return render_template('signin.html')

@app.route('/user-login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verify user credentials from MongoDB
        user = user_collection.find_one({'username': username})
        if user and user['password'] == password:  # Compare hashed passwords
            session['user'] = username  # Store username in session
            flash("Login successful!", "success")
            return redirect(url_for('user_dashboard'))  # Redirect to user dashboard or homepage
        else:
            flash("Invalid username or password", "danger")
            return render_template('ulogin.html')  # Render the login page again with error
    return render_template('ulogin.html')  # Render the login page for GET requests

@app.route('/user-dashboard')
def user_dashboard():
    # Check if the user is logged in
    if 'user' in session:
        username = session['user']  # Retrieve the username from the session
        return render_template('userdashboard.html', username=username)
    else:
        flash("Please log in to access your dashboard.", "warning")
        return redirect(url_for('user_login'))
    
@app.route('/ulogout')
def ulogout():
    session.pop('user', None)  # Remove user from session
    flash("You have been logged out.", "info")
    return redirect(url_for('user_login'))  # Redirect to login page


@app.route('/request-organ', methods=['GET', 'POST'])
def request_organ():
    if request.method == 'POST':
        # Extract form data
        full_name = request.form['fullName']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        organ_needed = request.form['organNeeded']
        
        # Prepare the data to be inserted
        request_data = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "address": address,
            "organ_needed": organ_needed,
            "status": "Pending"  # Default status
        }
        
        # Insert data into MongoDB
        try:
            request_collection.insert_one(request_data)
            flash('Your request has been submitted successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')

        return redirect(url_for('request_organ'))        
    return render_template('request.html')



@app.route('/view-request-status')
def view_request_status():
    # Ensure the user is logged in
    user = session.get('user')
    if not user:
        flash('Please log in to view your request status.', 'danger')
        return redirect(url_for('ulogout'))
    
    try:
        # Query the database for requests associated with the logged-in user
        user_requests = list(request_collection.find())  

        # Convert MongoDB documents to Python dictionaries
        for request in user_requests:
            request['_id'] = str(request['_id'])  # Convert ObjectId to string for template rendering

    except Exception as e:
        flash(f"Error fetching request data: {str(e)}", "danger")
        user_requests = []

    return render_template('requeststatus.html', requests=user_requests)



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        organ_type = request.form['organType']

        # Save donor details to MongoDB
        donor = {
            "name": name,
            "email": email,
            "phone": phone,
            "address": address,
            "organ_to_donate": organ_type,
        }
        # Insert donor data into the MongoDB 'donors' collection
        try:
            donor_collection.insert_one(donor)
            flash("Thank you for registering as a donor!", "success")
            return redirect(url_for('register'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            return render_template('register.html')
    return render_template('register.html')



if __name__ == '__main__':
    app.run(debug=True)
