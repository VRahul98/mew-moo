
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import smtplib
import sqlite3
from email.message import EmailMessage
import json
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'
DB = 'data/store.db'
SHOP_PHONE = "YOUR_SHOP_PHONE_NUMBER"

def query_db(query, args=(), one=False, commit=False):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    if commit:
        conn.commit()
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/products')
def products():
    items = query_db("SELECT * FROM products")
    return render_template('products.html', products=items)

@app.route('/cart')
def cart():
    cart = session.get("cart", [])
    total = sum([p["price"] * p["quantity"] for p in cart])
    total_items = sum([p["quantity"] for p in cart])
    return render_template("cart.html", cart=cart, total=total, total_items=total_items)

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    product_id = int(request.form["id"])
    quantity = int(request.form.get("quantity", 1))
    product = query_db("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
    if product:
        cart = session.get("cart", [])
        existing = next((item for item in cart if item["id"] == product["id"]), None)
        if existing:
            existing["quantity"] += quantity
        else:
            item_copy = dict(product)
            item_copy["quantity"] = quantity
            cart.append(item_copy)
        session["cart"] = cart
    return redirect("/products")

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
    headers = { "authorization": os.environ.get("FAST2SMS_API_KEY") }
    payload = {
        "route": "v3", "sender_id": "TXTIND", "message": message,
        "language": "english", "numbers": phone
    }
    requests.post(url, headers=headers, data=payload)

@app.route("/checkout", methods=["POST"])
def checkout():
    cart = session.get("cart", [])
    if not cart: return redirect("/cart")
    customer_email = request.form.get("email")
    customer_name = request.form.get("name")
    phone = request.form.get("phone")
    total = sum([item["price"] * item["quantity"] for item in cart])
    for item in cart:
        query_db("UPDATE products SET stock = MAX(0, stock - ?) WHERE id = ?",
                 (item["quantity"], item["id"]), commit=True)
    query_db("INSERT INTO orders (customer_name, email, phone, items, total) VALUES (?, ?, ?, ?, ?)",
             (customer_name, customer_email, phone, json.dumps(cart), total), commit=True)
    send_email(customer_email, customer_name, cart, total)
    send_sms(phone, customer_name, total)
    send_sms(SHOP_PHONE, customer_name, total)
    session.pop("cart", None)
    return redirect("/thankyou")

@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")

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
    if not session.get("admin"): return redirect("/login")
    items = query_db("SELECT * FROM products")
    raw_orders = query_db("SELECT * FROM orders ORDER BY id DESC")
    orders = [{
        "customer_name": o["customer_name"],
        "email": o["email"],
        "phone": o["phone"],
        "total": o["total"],
        "items": json.loads(o["items"])
    } for o in raw_orders]
    return render_template("admin.html", products=items, orders=orders)

@app.route('/add', methods=['POST'])
def add_product():
    if not session.get("admin"): return redirect("/login")
    query_db("INSERT INTO products (name, category, price, stock, image) VALUES (?, ?, ?, ?, ?)",
             (request.form["name"], request.form["category"], float(request.form["price"]),
              int(request.form["stock"]), request.form["image"]), commit=True)
    return redirect("/admin")

@app.route('/update', methods=['POST'])
def update_product():
    if not session.get("admin"): return redirect("/login")
    query_db("UPDATE products SET price = ?, stock = ? WHERE id = ?",
             (float(request.form["price"]), int(request.form["stock"]), int(request.form["id"])), commit=True)
    return redirect("/admin")

@app.route('/delete', methods=['POST'])
def delete_product():
    if not session.get("admin"): return redirect("/login")
    query_db("DELETE FROM products WHERE id = ?", (int(request.form["id"]),), commit=True)
    return redirect("/admin")

@app.route("/book_service", methods=["POST"])
def book_service():
    data = (request.form["name"], request.form["email"], request.form["phone"], request.form["service"])
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, phone TEXT, service TEXT)")
    cur.execute("INSERT INTO bookings (name, email, phone, service) VALUES (?, ?, ?, ?)", data)
    conn.commit()
    conn.close()
    flash("Your service has been booked!")
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
