
from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
import smtplib
from email.message import EmailMessage
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'

SHOP_PHONE = "YOUR_SHOP_PHONE_NUMBER"

# Utility: Load/Save JSON
def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath) as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

# Data helpers
def load_products():
    return load_json('data/products.json')

def save_products(data):
    save_json('data/products.json', data)

def load_orders():
    return load_json('data/orders.json')

def save_order(order):
    orders = load_orders()
    orders.append(order)
    save_json('data/orders.json', orders)

def load_bookings():
    return load_json('data/bookings.json')

def save_booking(booking):
    bookings = load_bookings()
    bookings.append(booking)
    save_json('data/bookings.json', bookings)

# Email & SMS
def send_email(to_email, name, cart, total):
    email = EmailMessage()
    email["Subject"] = "Your Mew & Moo Order Confirmation"
    email["From"] = os.environ.get("EMAIL_USER")
    email["To"] = to_email
    body = f"Hello {{name}},\n\nThanks for your order from Mew & Moo!\n\n"
    for item in cart:
        body += f"- {{item['name']}} x{{item['quantity']}} ₹{{item['price']}}\n"
    body += f"\nTotal: ₹{{total}}\n\nWe’ll get your items to you soon! 🐾"
    email.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASS"))
        smtp.send_message(email)

def send_sms(phone, name, total):
    message = f"Hi {{name}}, your Mew & Moo order of ₹{{total}} is confirmed! 🐾"
    url = "https://www.fast2sms.com/dev/bulkV2"
    headers = { "authorization": os.environ.get("FAST2SMS_API_KEY") }
    payload = {
        "route": "v3",
        "sender_id": "TXTIND",
        "message": message,
        "language": "english",
        "numbers": phone
    }
    requests.post(url, headers=headers, data=payload)

# Route definitions continued...

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/products')
def products():
    items = load_products()
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
    products = load_products()
    selected = next((p for p in products if p["id"] == product_id), None)
    if selected and selected["stock"] > 0:
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
    products = load_products()
    for item in cart:
        for product in products:
            if product["id"] == item["id"]:
                product["stock"] = max(0, product["stock"] - item["quantity"])
    save_products(products)
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

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "mewmoo123":
            session["admin"] = True
            return redirect("/admin")
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
    return render_template("admin.html", products=load_products(), orders=load_orders(), bookings=load_bookings())

@app.route('/add', methods=['POST'])
def add_product():
    if not session.get("admin"):
        return redirect("/login")
    data = load_products()
    new_id = max([p["id"] for p in data], default=0) + 1
    data.append({
        "id": new_id,
        "name": request.form["name"],
        "category": request.form["category"],
        "price": float(request.form["price"]),
        "stock": int(request.form["stock"]),
        "image": request.form["image"]
    })
    save_products(data)
    return redirect("/admin")

@app.route('/update', methods=['POST'])
def update_product():
    if not session.get("admin"):
        return redirect("/login")
    data = load_products()
    for p in data:
        if p["id"] == int(request.form["id"]):
            p["price"] = float(request.form["price"])
            p["stock"] = int(request.form["stock"])
    save_products(data)
    return redirect("/admin")

@app.route('/delete', methods=['POST'])
def delete_product():
    if not session.get("admin"):
        return redirect("/login")
    product_id = int(request.form["id"])
    data = [p for p in load_products() if p["id"] != product_id]
    save_products(data)
    return redirect("/admin")

@app.route("/delete_order", methods=["POST"])
def delete_order():
    if not session.get("admin"):
        return redirect("/login")
    order_index = int(request.form["index"])
    orders = load_orders()
    if 0 <= order_index < len(orders):
        orders.pop(order_index)
    save_json("data/orders.json", orders)
    return redirect("/admin")

@app.route("/book_service", methods=["POST"])
def book_service():
    booking = {
        "name": request.form["name"],
        "email": request.form["email"],
        "phone": request.form["phone"],
        "service": request.form["service"]
    }
    save_booking(booking)
    flash("Service booked successfully!")
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

