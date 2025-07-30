from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os

app = Flask(__name__)

# Load products from JSON
def load_products():
    with open('data/products.json') as f:
        return json.load(f)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/products')
def products():
    items = load_products()
    return render_template('products.html', products=items)

@app.route('/admin')
def admin():
    items = load_products()
    return render_template('admin.html', products=items)

@app.route('/update', methods=['POST'])
def update_product():
    data = load_products()
    product_id = int(request.form['id'])
    new_price = float(request.form['price'])
    new_stock = int(request.form['stock'])
    
    for p in data:
        if p['id'] == product_id:
            p['price'] = new_price
            p['stock'] = new_stock
            break

    with open('data/products.json', 'w') as f:
        json.dump(data, f, indent=4)

    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
