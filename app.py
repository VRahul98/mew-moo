from flask import Flask, render_template, request, redirect, url_for, session
from flask import flash
import json
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Replace with a secure one in production

# Load and Save product helpers
def load_products():
    with open('data/products.json') as f:
        return json.load(f)

def save_products(data):
    with open('data/products.json', 'w') as f:
        json.dump(data, f, indent=4)

# Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Public Products Page
@app.route('/products')
def products():
    items = load_products()
    return render_template('products.html', products=items)

# Admin Login
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

# Admin Logout
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

# Admin Panel (Protected)
@app.route('/admin')
def admin():
    if not session.get("admin"):
        return redirect("/login")
    items = load_products()
    return render_template('admin.html', products=items)

# Update Product (Protected)
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

def save_products(data):
    with open('data/products.json', 'w') as f:
        json.dump(data, f, indent=4)


# Add Product (Protected)
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

# Delete Product (Protected)
@app.route('/delete', methods=['POST'])
def delete_product():
    if not session.get("admin"):
        return redirect("/login")

    product_id = int(request.form["id"])
    data = load_products()
    data = [p for p in data if p["id"] != product_id]
    save_products(data)
    return redirect("/admin")

# Entry Point
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    product_id = int(request.form["id"])
    products = load_products()
    selected = next((p for p in products if p["id"] == product_id), None)

    if selected:
        cart = session.get("cart", [])
        cart.append(selected)
        session["cart"] = cart
    return redirect("/products")
@app.route("/cart")
def cart():
    cart = session.get("cart", [])
    total = sum([p["price"] for p in cart])
    return render_template("cart.html", cart=cart, total=total)
