import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash

import mysql.connector

app = Flask(__name__)
app.secret_key = 'my_super_secret_key_12345' 


db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="APP@123", 
    database="inventory_system"
)


@app.route("/login", methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        
        if user:
            session['loggedin'] = True
            session['username'] = user['username']
            session['role'] = user['role'] 
            return redirect(url_for('home'))
        else:
            error = "Invalid Username or Password."
            
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    session.pop('role', None) 
    return redirect(url_for('login'))


@app.route("/")
def home():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    

    if session['role'] == 'boss':

        return render_template("index.html", user_role=session['role'], username=session['username'])
    elif session['role'] == 'worker':
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT product_id, product_name, actual_quantity FROM inventory ORDER BY product_name")
            items = cursor.fetchall()
            return render_template("worker.html", username=session['username'], inventory_items=items)
    else:

        return redirect(url_for('login'))

@app.route("/get_inventory")
def get_inventory():
    if 'loggedin' not in session or session['role'] != 'boss':
        return jsonify({"error": "Unauthorized"}), 401
        
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM inventory ORDER BY product_id ASC")
    items = cursor.fetchall()

    shrinkage = []
    for item in items:
        diff = item['expected_quantity'] - item['actual_quantity']
        if diff > 0:
            shrinkage.append({
                "product_id": item['product_id'],
                "product_name": item['product_name'],
                "missing": diff
            })
    
    return jsonify({"inventory": items, "shrinkage": shrinkage})
    

@app.route("/scan_item", methods=['POST'])
def scan_item():

    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        product_id = request.form['product_id']
        cursor = db.cursor(dictionary=True)
        

        cursor.execute("SELECT * FROM inventory WHERE product_id = %s", (product_id,))
        item = cursor.fetchone()
        
        if item:

            cursor.execute("UPDATE inventory SET actual_quantity = actual_quantity + 1 WHERE product_id = %s", (product_id,))
            db.commit()
            flash(f" Success! Scanned: {item['product_name']}", "success")
        else:

            flash(f" Error! Product ID '{product_id}' not found.", "error")
            
    
    return redirect(url_for('home'))


@app.route("/add_item", methods=['POST'])
def add_item():
    if 'loggedin' not in session or session['role'] != 'boss':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        pid = request.form['product_id']
        name = request.form['product_name']
        expected = request.form['expected_quantity']

        
        cursor = db.cursor()
        try:
            sql = "INSERT INTO inventory (product_id, product_name, expected_quantity, actual_quantity) VALUES (%s, %s, %s, 0)"
            val = (pid, name, expected)
            cursor.execute(sql, val)
            db.commit()
            flash(f" Product '{name}' added successfully!", "success")
        except mysql.connector.Error as err:
            flash(f" Error! Product ID '{pid}' already exists.", "error")
        
    return redirect(url_for('home'))


@app.route("/delete_item/<int:item_id>", methods=['POST'])
def delete_item(item_id):
    if 'loggedin' not in session or session['role'] != 'boss':
        return redirect(url_for('login'))
        
    cursor = db.cursor()
    sql = "DELETE FROM inventory WHERE id = %s"
    val = (item_id,)
    cursor.execute(sql, val)
    db.commit()
    flash("Item deleted.", "success")
    return redirect(url_for('home'))


@app.route("/edit_item/<int:item_id>", methods=['GET'])
def edit_item(item_id):
    if 'loggedin' not in session or session['role'] != 'boss':
        return redirect(url_for('login'))
        
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM inventory WHERE id = %s", (item_id,))
    item = cursor.fetchone()
    
    if item:

        return render_template("edit.html", item=item)
    else:
        return "Item not found!", 404


@app.route("/update_item/<int:item_id>", methods=['POST'])
def update_item(item_id):
    if 'loggedin' not in session or session['role'] != 'boss':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        pid = request.form['product_id']
        name = request.form['product_name']
        expected = request.form['expected_quantity']

        
        cursor = db.cursor()
        sql = "UPDATE inventory SET product_id = %s, product_name = %s, expected_quantity = %s WHERE id = %s"
        val = (pid, name, expected, item_id)
        cursor.execute(sql, val)
        db.commit()
        flash("Item updated successfully!", "success")
        
    return redirect(url_for('home')) 

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
