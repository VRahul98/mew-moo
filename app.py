from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
import smtplib
from email.message import EmailMessage
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Replace this in production

SHOP_PHONE = "YOUR_SHOP_PHONE_NUMBER"

# Load/save helpers
def load_products():
    with open('data/products.json') as f:
        return json.load(f)

def save_products(data):
    with open('data/products.json', 'w') as f:
        json.dump(data, f, indent=4)

def load_orders():
    if not os.path.exists('data/orders.json'):
        return []
    with open('data/orders.json') as f:
        return json.load(f)

def save_order(order):
    if not os.path.exists('data/orders.json'):
        with open('data/orders.json', 'w') as f:
            json.dump([], f)

    with open('data/orders.json') as f:
        orders = json.load(f)

    orders.append(order)

    with open('data/orders.json', 'w') as f:
        json.dump(orders, f, indent=4)

# Email & SMS
def send_email(to_email, name, cart, total):
    email = EmailMessage()
    email["Subject"] = "Your Mew & Moo Order Confirmation"
    email["From"] = "youremail@example.com"
    email["To"] = to_email

    body = f"Hello {name},\n\nThanks for your order from Mew & Moo!\n\n"
    for item in cart:
        body += f"- {item['name']} x{item['quantity']} ₹{item['price']}\n"
    body += f"\nTotal: ₹{total}\n\nWe’ll get your items to you soon! 🐾"

    email.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("mew&moo@gmail.com", "mewmoo2025")
        smtp.send_message(email)

def send_sms(phone, name, total):
    message = f"Hi {name}, your Mew & Moo order of ₹{total} is confirmed! 🐾"
    url = "https://www.fast2sms.com/dev/bulkV2"
    headers = {
        "authorization": "YOUR_FAST2SMS_API_KEY",
    }
    payload = {
        "route": "v3",
        "sender_id": "TXTIND",
        "message": message,
        "language": "english",
        "numbers": phone
    }
    requests.post(url, headers=headers, data=payload)

# Routes
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
    send_sms(SHOP_PHONE, f"🛒 New Order from {customer_name}", total)

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
    if not session.get("admin"):
        return redirect("/login")
    items = load_products()
    orders = load_orders()
    return render_template("admin.html", products=items, orders=orders)

@app.route('/add', methods=['POST'])
def add_product():
    if not session.get("admin"):
        return redirect("/login")

    data = load_products()
    new_id = max([p["id"] for p in data], default=0) + 1
    new_product = {
        "id": new_id,
        "name": request.form["name"],
        "category": request.form["category"],
        "price": float(request.form["price"]),
        "stock": int(request.form["stock"]),
        "image": request.form["image"]
    }
    data.append(new_product)
    save_products(data)
    return redirect("/admin")

@app.route('/update', methods=['POST'])
def update_product():
    if not session.get("admin"):
        return redirect("/login")

    data = load_products()
    product_id = int(request.form['id'])
    new_price = float(request.form['price'])
    new_stock = int(request.form['stock'])

    for p in data:
        if p['id'] == product_id:
            p['price'] = new_price
            p['stock'] = new_stock
            break

    save_products(data)
    return redirect("/admin")

@app.route('/delete', methods=['POST'])
def delete_product():
    if not session.get("admin"):
        return redirect("/login")

    product_id = int(request.form["id"])
    data = load_products()
    data = [p for p in data if p["id"] != product_id]
    save_products(data)
    return redirect("/admin")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
