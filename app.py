import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import mysql.connector
from mysql.connector import Error
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)  # ✅ this must come BEFORE any @app.route


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.secret_key = os.getenv('SECRET_KEY', 'devkey')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.permanent_session_lifetime = timedelta(days=7)


def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password=os.getenv("DB_PASSWORD"),   # <-- your MySQL password
        database='artstore'
    )
    return conn


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT a.*, ar.name as artist_name FROM artworks a LEFT JOIN artists ar ON a.artist_id = ar.artist_id')
    artworks = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', artworks=artworks)




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                           (username, email, hashed))
            conn.commit()
            flash('Registered! Please login.', 'success')
            return redirect(url_for('login'))
        except Error as e:
            flash('Error: ' + str(e), 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session.permanent = True
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM admins WHERE username = %s', (username,))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()
        if admin and check_password_hash(admin['password'], password):
            session['admin_id'] = admin['admin_id']
            session['admin_username'] = admin['username']
            flash('Admin logged in.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'danger')
    return render_template('admin_login.html')

@app.route('/admin')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT a.*, ar.name as artist_name FROM artworks a LEFT JOIN artists ar ON a.artist_id = ar.artist_id')
    artworks = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_dashboard.html', artworks=artworks)

@app.route('/admin/add', methods=['GET', 'POST'])
def add_artwork():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM artists')
    artists = cursor.fetchall()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        artist_id = request.form.get('artist_id') or None
        qty = request.form.get('qty', 1)
        file = request.files.get('image')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        cursor.execute('INSERT INTO artworks (title, description, price, image_filename, artist_id, available_qty) VALUES (%s,%s,%s,%s,%s,%s)',
                       (title, description, price, filename, artist_id, qty))
        conn.commit()
        flash('Artwork added!', 'success')
        cursor.close()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    cursor.close()
    conn.close()
    return render_template('add_artwork.html', artists=artists)




@app.route('/artwork/<int:artwork_id>')
def artwork_detail(artwork_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT a.*, ar.name as artist_name FROM artworks a LEFT JOIN artists ar ON a.artist_id = ar.artist_id WHERE a.artwork_id = %s', (artwork_id,))
    art = cursor.fetchone()
    cursor.close()
    conn.close()
    if not art:
        flash('Artwork not found', 'warning')
        return redirect(url_for('index'))
    return render_template('artwork_detail.html', art=art)

@app.route('/add_to_cart/<int:artwork_id>', methods=['POST'])
def add_to_cart(artwork_id):
    qty = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    cart[str(artwork_id)] = cart.get(str(artwork_id), 0) + qty
    session['cart'] = cart
    flash('Added to cart', 'success')
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    items = []
    total = 0.0
    if cart:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        format_ids = ','.join(['%s'] * len(cart.keys()))
        cursor.execute(f'SELECT * FROM artworks WHERE artwork_id IN ({format_ids})', tuple(cart.keys()))
        rows = cursor.fetchall()
        for r in rows:
            aid = str(r['artwork_id'])
            q = cart.get(aid, 0)
            subtotal = q * float(r['price'])
            total += subtotal
            items.append({'art': r, 'qty': q, 'subtotal': subtotal})
        cursor.close()
        conn.close()
    return render_template('cart.html', items=items, total=total)

@app.route('/checkout_page')
def checkout_page():
    if 'user_id' not in session:
        flash('Please login to continue checkout.', 'warning')
        return redirect(url_for('login'))
    return render_template('checkout.html')


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Please login to checkout.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        address = request.form.get('address')
        delivery_date = request.form.get('delivery_date')
        payment_mode = request.form.get('payment_mode')

        if not address or not delivery_date or not payment_mode:
            flash('Please fill all fields before submitting.', 'danger')
            return redirect(url_for('checkout'))

        cart = session.get('cart', {})
        if not cart:
            flash('Cart is empty.', 'warning')
            return redirect(url_for('index'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch artworks
        ids = tuple(cart.keys())
        format_ids = ','.join(['%s'] * len(ids))
        cursor.execute(f'SELECT * FROM artworks WHERE artwork_id IN ({format_ids})', ids)
        rows = cursor.fetchall()

        # Calculate total
        total = sum(float(r['price']) * cart[str(r['artwork_id'])] for r in rows)

        # Apply order discount
        discount_percentage = 0
        if total >= 10000:
            discount_percentage = 15
        elif total >= 5000:
            discount_percentage = 10

        discount_amount = total * discount_percentage / 100
        total_after_discount = total - discount_amount


        # Insert order
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orders (user_id, total_amount, address, delivery_date, payment_mode)
            VALUES (%s, %s, %s, %s, %s)
        ''', (session['user_id'], total_after_discount, address, delivery_date, payment_mode))
        order_id = cursor.lastrowid
        

        # Insert items
        for r in rows:
            qty = cart[str(r['artwork_id'])]
            cursor.execute('''
                INSERT INTO order_items (order_id, artwork_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
            ''', (order_id, r['artwork_id'], qty, float(r['price'])))
            cursor.execute('UPDATE artworks SET status = %s WHERE artwork_id = %s', ('Sold', r['artwork_id']))
            cursor.execute('''
                UPDATE artworks
                SET available_qty = available_qty - %s
                WHERE artwork_id = %s
            ''', (qty, r['artwork_id']))



        conn.commit()
        cursor.close()
        conn.close()

        session.pop('cart', None)
        # Prepare success message
        if discount_percentage > 0:
            message = f"🎉 Congrats! You got a {discount_percentage}% discount."
        else:
            message = "✅ Order placed successfully!"

        return render_template(
            'order_success.html',
            message=message,
            total=total_after_discount,
            order_id=order_id
        )
    # For GET → show checkout form
    return render_template('checkout.html')



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    return redirect(url_for('admin_login'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# --------------------------
# ADMIN DELETE ARTWORK
# --------------------------
@app.route('/admin/delete_artwork/<int:artwork_id>', methods=['POST'])
def delete_artwork(artwork_id):
    if 'admin_id' not in session:
        flash('Access denied! Admin login required.', 'danger')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM artworks WHERE artwork_id = %s', (artwork_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Artwork deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


# --------------------------
# ADMIN UPDATE QUANTITY
# --------------------------
@app.route('/admin/update_quantity/<int:artwork_id>', methods=['POST'])
def update_quantity(artwork_id):
    if 'admin_id' not in session:
        flash('Access denied! Admin login required.', 'danger')
        return redirect(url_for('admin_login'))

    new_qty = request.form.get('new_qty')

    if not new_qty or not new_qty.isdigit():
        flash('Invalid quantity input.', 'danger')
        return redirect(url_for('admin_dashboard'))

    new_qty = int(new_qty)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Update the quantity in DB
    cursor.execute('UPDATE artworks SET available_qty = %s WHERE artwork_id = %s', (new_qty, artwork_id))

    # Also update status based on stock
    if new_qty > 0:
        cursor.execute("UPDATE artworks SET status = 'Available' WHERE artwork_id = %s", (artwork_id,))
    else:
        cursor.execute("UPDATE artworks SET status = 'Sold' WHERE artwork_id = %s", (artwork_id,))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Artwork quantity updated successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/analytics')
def analytics():
    # Allow only logged-in users or admins
    if 'user_id' not in session and 'admin_id' not in session:
        flash("Please login to view analytics.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --- Price distribution (for donut chart) ---
    cursor.execute("""
        SELECT 
            CASE 
                WHEN price < 1000 THEN 'Below ₹1000'
                WHEN price BETWEEN 1000 AND 5000 THEN '₹1000 - ₹5000'
                WHEN price BETWEEN 5000 AND 10000 THEN '₹5000 - ₹10000'
                ELSE 'Above ₹10000'
            END AS price_range,
            COUNT(*) AS count
        FROM artworks
        GROUP BY price_range
    """)
    price_data = cursor.fetchall()

    # --- Top 5 expensive artworks ---
    cursor.execute("SELECT title, price FROM artworks ORDER BY price DESC LIMIT 5")
    expensive_artworks = cursor.fetchall()

    # --- 5 most recent artworks ---
    cursor.execute("""
        SELECT title, price, image_filename 
        FROM artworks 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    recent_artworks = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'analytics.html',
        price_data=price_data,
        expensive_artworks=expensive_artworks,
        recent_artworks=recent_artworks
    )

@app.route('/search', methods=['GET'])
def search():
    if 'user_id' not in session:
        flash('Please login to search artworks.', 'warning')
        return redirect(url_for('login'))

    query = request.args.get('q', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check available columns dynamically
    cursor.execute("SHOW COLUMNS FROM artworks")
    columns = [col['Field'] for col in cursor.fetchall()]

    sql = "SELECT * FROM artworks"
    params = ()

    if query:
        conditions = []
        if 'title' in columns:
            conditions.append("title LIKE %s")
        if 'artist_name' in columns:
            conditions.append("artist_name LIKE %s")
        if 'artist' in columns:
            conditions.append("artist LIKE %s")
        if 'description' in columns:
            conditions.append("description LIKE %s")

        if conditions:
            sql += " WHERE " + " OR ".join(conditions)
            params = tuple([f"%{query}%"] * len(conditions))

    cursor.execute(sql, params)
    artworks = cursor.fetchall()

    cursor.close()
    conn.close()

    # ✅ If no artworks found, flash message & return index with message
    if not artworks:
        flash(f'No results found for "{query}". Please try another search.', 'info')
        return render_template('index.html', artworks=[], query=query, no_results=True)

    # ✅ If artworks found, show them
    return render_template('index.html', artworks=artworks, query=query, no_results=False)

from datetime import date, datetime

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Please login to view your profile.", "warning")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch user info
    cursor.execute("""
        SELECT username, email 
        FROM users 
        WHERE user_id = %s
    """, (session['user_id'],))
    user_info = cursor.fetchone()

    # Fetch all orders for this user
    cursor.execute("""
        SELECT order_id, total_amount, status, delivery_date, created_at
        FROM orders
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (session['user_id'],))
    orders = cursor.fetchall()

    # ---------------------- 🔥 AUTO UPDATE STATUS ----------------------
    for order in orders:
        order_date = order["created_at"]
        delivery_date = order["delivery_date"]

        # Convert datetime to date only
        if isinstance(order_date, datetime):
            order_date = order_date.date()

        if isinstance(delivery_date, datetime):
            delivery_date = delivery_date.date()

        # --- If delivery date passed → mark completed ---
        if delivery_date < date.today() and order["status"] != "Completed":
            cursor.execute("""
                UPDATE orders 
                SET status = 'Completed'
                WHERE order_id = %s
            """, (order["order_id"],))
            conn.commit()
            order["status"] = "Completed"

        # --- If delivery date is today or future → pending ---
        elif delivery_date >= date.today() and order["status"] != "Pending":
            cursor.execute("""
                UPDATE orders 
                SET status = 'Pending'
                WHERE order_id = %s
            """, (order["order_id"],))
            conn.commit()
            order["status"] = "Pending"

        # Save cleaned date formats so they are easy to show in HTML
        order["order_date"] = order_date
        order["delivery_date"] = delivery_date

    # ---------------------- Fetch order items ----------------------
    for order in orders:
        cursor.execute("""
            SELECT oi.quantity, oi.unit_price,
                   a.title, a.image_filename
            FROM order_items oi
            JOIN artworks a ON oi.artwork_id = a.artwork_id
            WHERE oi.order_id = %s
        """, (order["order_id"],))
        
        items_list = cursor.fetchall()

        final_items = []
        for item in items_list:
            image = item["image_filename"] or "placeholder.png"

            final_items.append({
                "title": item["title"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "image_url": url_for("static", filename="uploads/" + image)
            })

        order["items"] = final_items

    cursor.close()
    conn.close()

    return render_template("profile.html", user=user_info, orders=orders)



@app.route('/admin/manage')
def admin_manage():
    if not session.get('admin_id'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS count FROM users")
    total_users = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) AS count FROM orders")
    total_orders = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) AS count FROM artworks")
    total_artworks = cursor.fetchone()['count']

    cursor.close()
    conn.close()

    return render_template('admin_manage.html',
                           total_users=total_users,
                           total_orders=total_orders,
                           total_artworks=total_artworks,
                           current_year=datetime.now().year)



@app.route('/admin/manage/users')
def admin_manage_users():
    if not session.get('admin_id'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()  # get connection
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users")
    user_data = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('admin_users.html', users=user_data)


@app.route('/admin/manage/orders')
def admin_manage_orders():
    if not session.get('admin_id'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()  # get connection
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, u.username, o.total_amount, o.status, o.created_at
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
    """)
    order_data = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('admin_orders.html', orders=order_data)




if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
