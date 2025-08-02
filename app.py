from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import smtplib
from email.message import EmailMessage
import requests

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_FILE = "data/store.db"
SHOP_PHONE = "+916305003539"  # Owner's number for SMS

# --- Helper: Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        price REAL,
        stock INTEGER,
        image TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        email TEXT,
        phone TEXT,
        items TEXT,
        total REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        service TEXT
    )""")
    conn.commit()
    conn.close()

# --- DB Access Functions ---
def get_products():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = [dict(id=row[0], name=row[1], category=row[2], price=row[3],
                     stock=row[4], image=row[5]) for row in c.fetchall()]
    conn.close()
    return products

def get_orders():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM orders")
    orders = []
    for row in c.fetchall():
        orders.append({
            "customer_name": row[1],
            "email": row[2],
            "phone": row[3],
            "items": eval(row[4]),
            "total": row[5]
        })
    conn.close()
    return orders

def save_order(order):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO orders (customer_name, email, phone, items, total) VALUES (?, ?, ?, ?, ?)",
              (order["customer_name"], order["email"], order["phone"], str(order["items"]), order["total"]))
    conn.commit()
    conn.close()

def save_booking(booking):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO bookings (name, email, phone, service) VALUES (?, ?, ?, ?)",
              (booking["name"], booking["email"], booking["phone"], booking["service"]))
    conn.commit()
    conn.close()

# --- Mail/SMS Functions ---
def send_email(to_email, name, cart, total):
    email = EmailMessage()
    email["Subject"] = "Your Mew & Moo Order Confirmation"
    email["From"] = os.environ.get("EMAIL_USER")
    email["To"] = to_email

    body = f"Hello {name},\n\nThanks for your order from Mew & Moo!\n\n"
    for item in cart:
        body += f"- {item['name']} x{item['quantity']} ₹{item['price']}\n"
    body += f"\nTotal: ₹{total}\n\nWe’ll get your items to you soon! 🐾"
    email.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASS"))
        smtp.send_message(email)

def send_sms(phone, name, total):
    message = f"Hi {name}, your Mew & Moo order of ₹{total} is confirmed! 🐾"
    url = "https://www.fast2sms.com/dev/bulkV2"
    headers = {
        "authorization": os.environ.get("FAST2SMS_API_KEY"),
    }
    payload = {
        "route": "v3",
        "sender_id": "TXTIND",
        "message": message,
        "language": "english",
        "numbers": phone
    }
    requests.post(url, headers=headers, data=payload)

# --- Routes ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/products")
def products():
    return render_template("products.html", products=get_products())

@app.route("/cart")
def cart():
    cart = session.get("cart", [])
    total = sum([p["price"] * p["quantity"] for p in cart])
    total_items = sum([p["quantity"] for p in cart])
    return render_template("cart.html", cart=cart, total=total, total_items=total_items)

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    product_id = int(request.form["id"])
    quantity = int(request.form.get("quantity", 1))
    products = get_products()
    selected = next((p for p in products if p["id"] == product_id), None)
    if selected:
        cart = session.get("cart", [])
        existing = next((item for item in cart if item["id"] == selected["id"]), None)
        if existing:
            existing["quantity"] += quantity
        else:
            selected_copy = selected.copy()
            selected_copy["quantity"] = quantity
            cart.append(selected_copy)
        session["cart"] = cart
    return redirect("/products")

@app.route("/checkout", methods=["POST"])
def checkout():
    cart = session.get("cart", [])
    if not cart:
        return redirect("/cart")

    customer_email = request.form.get("email")
    customer_name = request.form.get("name")
    phone = request.form.get("phone")
    total = sum([item["price"] * item["quantity"] for item in cart])

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for item in cart:
        c.execute("UPDATE products SET stock = MAX(stock - ?, 0) WHERE id = ?", (item["quantity"], item["id"]))
    conn.commit()
    conn.close()

    order = {
        "customer_name": customer_name,
        "email": customer_email,
        "phone": phone,
        "items": cart,
        "total": total
    }
    save_order(order)
    send_email(customer_email, customer_name, cart, total)
    send_sms(phone, customer_name, total)
    send_sms(SHOP_PHONE, customer_name, total)
    session.pop("cart", None)
    return redirect("/thankyou")

@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")

@app.route("/book_service", methods=["POST"])
def book_service():
    booking = {
        "name": request.form["name"],
        "email": request.form["email"],
        "phone": request.form["phone"],
        "service": request.form["service"]
    }
    save_booking(booking)
    flash("Your service has been booked!")
    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "mewmoo123":
            session["admin"] = True
            return redirect("/admin")
        else:
            return "Invalid credentials. <a href='/login'>Try again</a>"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")
    return render_template("admin.html", products=get_products(), orders=get_orders())

@app.route("/add", methods=["POST"])
def add_product():
    if not session.get("admin"):
        return redirect("/login")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO products (name, category, price, stock, image) VALUES (?, ?, ?, ?, ?)",
              (request.form["name"], request.form["category"], float(request.form["price"]),
               int(request.form["stock"]), request.form["image"]))
    conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/update", methods=["POST"])
def update_product():
    if not session.get("admin"):
        return redirect("/login")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE products SET price=?, stock=? WHERE id=?",
              (float(request.form["price"]), int(request.form["stock"]), int(request.form["id"])))
    conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/delete", methods=["POST"])
def delete_product():
    if not session.get("admin"):
        return redirect("/login")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (int(request.form["id"]),))
    conn.commit()
    conn.close()
    return redirect("/admin")

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
