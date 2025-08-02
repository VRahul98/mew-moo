from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import smtplib
from email.message import EmailMessage
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'

DATABASE = 'data/database.db'
SHOP_PHONE = "9876543210"  # Example number

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript(open("schema.sql").read())

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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/products')
def products():
    db = get_db()
    items = db.execute("SELECT * FROM products").fetchall()
    return render_template('products.html', products=items)

@app.route('/cart')
def cart():
    cart = session.get("cart", [])
    total = sum([p["price"] * p["quantity"] for p in cart])
    return render_template("cart.html", cart=cart, total=total)

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    product_id = int(request.form["id"])
    quantity = int(request.form.get("quantity", 1))
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product:
        cart = session.get("cart", [])
        for item in cart:
            if item["id"] == product["id"]:
                item["quantity"] += quantity
                break
        else:
            cart.append({"id": product["id"], "name": product["name"], "price": product["price"], "quantity": quantity})
        session["cart"] = cart
    return redirect("/products")

@app.route("/checkout", methods=["POST"])
def checkout():
    cart = session.get("cart", [])
    if not cart:
        return redirect("/cart")
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    total = sum([item["price"] * item["quantity"] for item in cart])
    db = get_db()
    for item in cart:
        db.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item["quantity"], item["id"]))
    db.execute("INSERT INTO orders (customer_name, email, phone, total) VALUES (?, ?, ?, ?)", (name, email, phone, total))
    order_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for item in cart:
        db.execute("INSERT INTO order_items (order_id, product_name, quantity, price) VALUES (?, ?, ?, ?)",
                   (order_id, item["name"], item["quantity"], item["price"]))
    db.commit()
    send_email(email, name, cart, total)
    send_sms(phone, name, total)
    send_sms(SHOP_PHONE, name, total)
    session.pop("cart", None)
    return redirect("/thankyou")

@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "mewmoo123":
            session["admin"] = True
            return redirect("/admin")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")
    db = get_db()
    products = db.execute("SELECT * FROM products").fetchall()
    orders = db.execute("SELECT * FROM orders").fetchall()
    order_items = db.execute("SELECT * FROM order_items").fetchall()
    return render_template("admin.html", products=products, orders=orders, order_items=order_items)

@app.route("/add", methods=["POST"])
def add():
    db = get_db()
    db.execute("INSERT INTO products (name, category, price, stock, image) VALUES (?, ?, ?, ?, ?)", (
        request.form["name"],
        request.form["category"],
        float(request.form["price"]),
        int(request.form["stock"]),
        request.form["image"]
    ))
    db.commit()
    return redirect("/admin")

@app.route("/update", methods=["POST"])
def update():
    db = get_db()
    db.execute("UPDATE products SET price=?, stock=? WHERE id=?", (
        float(request.form["price"]),
        int(request.form["stock"]),
        int(request.form["id"])
    ))
    db.commit()
    return redirect("/admin")

@app.route("/delete", methods=["POST"])
def delete():
    db = get_db()
    db.execute("DELETE FROM products WHERE id=?", (int(request.form["id"]),))
    db.commit()
    return redirect("/admin")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
