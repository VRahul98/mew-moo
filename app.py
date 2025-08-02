from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

DB_PATH = 'data/products.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/admin')
def admin():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('admin.html', products=products, orders=[])

@app.route('/add', methods=['POST'])
def add_product():
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO products (name, category, price, stock, image) VALUES (?, ?, ?, ?, ?)',
        (request.form['name'], request.form['category'], float(request.form['price']), int(request.form['stock']), request.form['image'])
    )
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/update', methods=['POST'])
def update_product():
    conn = get_db_connection()
    conn.execute(
        'UPDATE products SET price = ?, stock = ? WHERE id = ?',
        (float(request.form['price']), int(request.form['stock']), int(request.form['id']))
    )
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/delete', methods=['POST'])
def delete_product():
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (int(request.form['id']),))
    conn.commit()
    conn.close()
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)
