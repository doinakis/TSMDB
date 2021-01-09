#!/usr/bin/env python3
import os
from flask import Flask, escape, request, send_file, render_template, redirect, url_for
from scripts import dbmanager
from datetime import datetime
# SECTION: Constants
# Flags if on HEROKU environment
ON_HEROKU = 'IS_HEROKU' in os.environ
# !SECTION

db = dbmanager.Database(host        = "tsmdbs.mysql.database.azure.com",
                        user        = "tsmdbadmin@tsmdbs",
                        password    = "u!2Uy@2D7t",
                        db          = "tsmdb",
                        charset     = 'utf8',
                        use_unicode = True)

db.open()

# Creating a flask app
app = Flask(__name__, template_folder='templates')

@app.route('/', methods=[ 'GET'])
def get_index():
    """Redirects default page to login.html"""
    store               = db.createObject(name="store")
    results             = store.query(cols=("street_name", "street_number", "postal_code", "area"), condition="WHERE manager=668975412")[0]
    greek_keys          = ("Οδός", "Αριθμός", "Ταχ. Κώδικας", "Επιφάνεια (τμ)")
    store_info          = {k:v for k,v in zip(greek_keys,results)}
    move_to             = db.createObject(name="move_to")
    move_to_stores_to   = move_to.join(store,"move_to.destination=store.id")
    transfer_to         = move_to_stores_to.query(cols    = ("street_name", "street_number", "date", "info","status"),
                                        condition = "WHERE move_to.origin=5 AND (status = 'Accepted' or status = 'Pending')")
    move_to_stores_from = move_to.join(store,"move_to.origin=store.id")
    transfer_from       = move_to_stores_from.query(cols  = ("street_name", "street_number", "date", "info","status"),
                                        condition = "WHERE move_to.destination=5 AND (status = 'Accepted' or status = 'Pending')")
    transfer_from = list(transfer_from)
    transfer_from.sort(key=lambda x: x[2], reverse= True)
    transfer_to = list(transfer_to)
    transfer_to.sort(key=lambda x: x[2], reverse= True)
    day_off          = db.createObject(name="`day-off`")
    employee         = db.createObject(name="employee")
    employee_day_off = day_off.join(employee,"`day-off`.employee_id=employee.tin")
    store_day_off    = employee_day_off.query(cols=("first_name", "last_name", "phone_number", "type", "duration", "date"), condition="WHERE store_id=5")
    return render_template('index.html', store_info=store_info, transfer_to=transfer_to, transfer_from=transfer_from, store_day_off=store_day_off)

@app.route('/stores', methods=[ 'GET' ])
def get_stores():
    return render_template('stores.html')

@app.route('/clients', methods=[ 'GET' ])
def get_clients():
    return render_template('clients.html')

@app.route('/images/<filename>', methods=[ 'GET' ])
def get_image(filename):
    """Redirects the /images/ path to return an image from the images directory"""
    try:
        return send_file(f"images/{filename}", mimetype='image/png')
    except FileNotFoundError:
        return "Image Not Found", 404

@app.route('/styles.css', methods=[ 'GET' ])
def get_style():
    """Redirects styles.css to the default css file"""
    return send_file('templates/styles.css', mimetype='text/css')

@app.route('/login', methods=[ 'GET' ])
def get_login():
    return render_template('login.html')

@app.route('/login', methods=[ 'POST' ])
def post_login():
    error = None
    if valid_login(request.form['username'], request.form['password']):
        return redirect(url_for('get_index'))
    else:
        error = 'Invalid username/password'
    return render_template('login.html', error=error)

def valid_login(username, password):
    if (username == 'Michalis') and (password == 'Doinakis'):
        return True
    else:
        return False

@app.route('/stock', methods=[ 'GET' ])
def get_stock():
    stock   = db.createObject(name="stock")
    product = db.createObject(name="product")
    store   = db.createObject(name="store")
    joined  = stock.join(store,"store.id=stock.store_id")
    joined  = joined.join(product,"stock.product_id=product.id")
    results = joined.query(cols=("product.id", "product.name", "product.category", "product.price", "product.manufacturer",
                                 "product.description", "stock.amount"),condition="WHERE store.id = 5")
    return render_template('stock.html', info=results)

@app.route('/stock/move', methods=[ 'POST' ])
def post_stock():
    checked_ids = tuple(request.form.keys())
    checked_ids = ','.join(checked_ids)
    
    stock   = db.createObject(name="stock")
    store   = db.createObject(name="store")
    product = db.createObject(name="product")
    
    joined  = stock.join(store,on="stock.store_id=store.id").join(product,on="product.id=stock.product_id")
    
    results = joined.query(cols=("store.id", "store.street_name", "store.street_number", \
    "product.id", "product.name", "product.category", "product.manufacturer", "amount"), \
    condition=f"WHERE product.id IN ({checked_ids})")
    
    info = {}
    for result in results:
        key = result[0]
        product_info = tuple( result[i] for i in range(3,8) )
        if key in info:
            info[key]['products'].append(product_info)
        else:
            info[key] = { 'products': [ product_info ], 'store_info': tuple( result[i] for i in range(1,3) ) }
    
    return render_template('stock_move.html', info=info)

@app.route('/stock/move/complete', methods=[ 'POST' ])
def post_products_request():
    info = dict(request.form)
    
    if 'description' in info:
        desc = info['description']
        del info['description']
    else:
        desc = ''
    
    info = tuple( (*k.split('_'), a) for k, a in info.items() if a and int(a) > 0 )
    consists_of = db.createObject("consists_of")
    results = consists_of.query(cols=("MAX(product_list_id)",))
    product_list_id = -1 if len(results) == 0 else results[0][0]
    
    info_dict = {}
    for (sk, pk, a) in info:
        sk, pk, a = int(sk), int(pk), int(a)
        
        if sk in info_dict:
            info_dict[sk][pk] = a
        else:
            product_list_id = product_list_id + 1
            info_dict[sk] =  { pk: a, "product_list_id": product_list_id }
    
    info = info_dict
    stock   = db.createObject(name="stock")
    store   = db.createObject(name="store")
    product = db.createObject(name="product")
    joined  = stock.join(store,on="stock.store_id=store.id").join(product,on="product.id=stock.product_id")
    results = joined.query(cols=("store.id", "product.id", "amount"), condition=f"WHERE store.id IN {tuple(info.keys())}")
    

    try:
        for (sk, pk, a) in results:
            if pk not in info[sk]:
                continue
            amount = info[sk][pk]
            if amount > a:
                raise ValueError(f"Amount at key: {sk}, {pk} exeeded the acceptable range")
            else:
                consists_of.insert(values={  "product_id": pk, "product_list_id": info[sk]['product_list_id'],  "amount": amount })
        consists_of.db.con.commit()
    except:
        consists_of.db.con.rollback()


    return
# SECTION: Main
if __name__ == '__main__':
    host = '0.0.0.0' if ON_HEROKU else 'localhost'
    port = os.environ.get('PORT') if ON_HEROKU else 8080
    if port is None:
        raise EnvironmentError("Could not find port")
    
    app.run(host=host, port=port)
    db.close()
# !SECTION
