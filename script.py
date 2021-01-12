#!/usr/bin/env python3
import os
from flask import Flask, escape, request, send_file, render_template, redirect, url_for
from scripts import dbmanager
from datetime import datetime


def redirect_on_error(err_func):
    def deco(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as ex:
                print(ex)
                return redirect(url_for(err_func))
        return wrapper
    return deco


# SECTION: Constants
# Flags if on HEROKU environment
ON_HEROKU = 'IS_HEROKU' in os.environ

# The store that is being demo'ed
current_store_id = 5

# Manager TIN
manager_tin = '668975412'
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



@app.route('/error')
def on_error():
    """Loads error page"""
    return render_template('error.html')

@app.route('/', methods=[ 'GET' ])
def get_index():
    """Redirects default page to login.html"""
    employee            = db.createObject(name="employee")
    manager_info        = employee.query(cols=('first_name', 'last_name'),
                                         condition=f"WHERE tin = {manager_tin}")[0]
    manager_info        = f"{manager_info[0]} {manager_info[1]}"
    
    store               = db.createObject(name="store")
    results             = store.query(cols=("street_name", "street_number", "postal_code", "area"),
                                      condition=f"WHERE manager={manager_tin}")[0]
    greek_keys          = ("Οδός", "Αριθμός", "Ταχ. Κώδικας", "Επιφάνεια (τμ)")
    store_info          = {k:v for k,v in zip(greek_keys,results)}
    move_to             = db.createObject(name="move_to")
    move_to_stores      = move_to.join(store,"move_to.destination=store.id")
    transfer_to         = move_to_stores.query(cols    = ("street_name", "street_number", "date", "info","status"),
                                        condition = f"""WHERE move_to.origin={current_store_id} AND (status = 'Accepted' or status = 'Pending') 
                                                        HAVING DATEDIFF('{datetime.today().strftime('%Y-%m-%d')}', date) <= 7
                                                        ORDER BY date DESC""")
    move_from_stores    = move_to.join(store,"move_to.origin=store.id")
    transfer_from       = move_from_stores.query(cols  = ("street_name", "street_number", "date", "info","status"),
                                        condition = f"""WHERE move_to.destination={current_store_id} AND (status = 'Accepted' or status = 'Pending')
                                                        HAVING DATEDIFF('{datetime.today().strftime('%Y-%m-%d')}', date) <= 7
                                                        ORDER BY date DESC""")
    day_off             = db.createObject(name="`day-off`")
    employee            = db.createObject(name="employee")
    employee_day_off    = day_off.join(employee,"`day-off`.employee_id=employee.tin")
    store_day_off       = employee_day_off.query(cols=("first_name", "last_name", "phone_number", "type", "duration", "date"),
                                              condition=f"""WHERE store_id={current_store_id}
                                                            HAVING DATEDIFF('{datetime.today().strftime('%Y-%m-%d')}', date) <= duration""")
    return render_template('index.html', user_info=manager_info,
                                         store_info=store_info,
                                         transfer_to=transfer_to,
                                         transfer_from=transfer_from,
                                         store_day_off=store_day_off)

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

@app.route('/stock', methods=[ 'GET' ])
def get_stock():
    stock   = db.createObject(name="stock")
    product = db.createObject(name="product")
    store   = db.createObject(name="store")
    joined  = stock.join(store,    on=f"store.id=stock.store_id AND store.id={current_store_id}")
    joined  = joined.join(product, on="stock.product_id=product.id", type="RIGHT")

    results = joined.query(cols=( "product.id",
                                  "product.name",
                                  "product.category",
                                  "product.price",
                                  "product.manufacturer",
                                  "product.description",
                                  "IFNULL(stock.amount,0)"),
                           condition="ORDER BY product.name")

    return render_template('stock.html', info=results)

@app.route('/stock/move', methods=[ 'POST' ])
def post_stock():
    checked_ids = tuple(request.form.keys())
    checked_ids = ','.join(checked_ids)

    stock   = db.createObject(name="stock")
    store   = db.createObject(name="store")
    product = db.createObject(name="product")

    joined  = stock.join(store,   on=f"stock.store_id=store.id AND store.id != {current_store_id}")\
                   .join(product, on="product.id=stock.product_id")

    results = joined.query(cols=( "store.id",
                                  "store.street_name",
                                  "store.street_number",
                                  "product.id",
                                  "product.name",
                                  "product.category",
                                  "product.manufacturer",
                                  "amount"),
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
@redirect_on_error('on_error')
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

    if len(info) == 0:
        raise ValueError('No product selected for move')

    stock   = db.createObject(name="stock")
    store   = db.createObject(name="store")
    product = db.createObject(name="product")
    move_to = db.createObject(name="move_to")
    joined  = stock.join(store, on="stock.store_id=store.id")\
                   .join(product, on="product.id=stock.product_id")
    results = joined.query(cols=("store.id", "product.id", "amount"),
                           condition=f"WHERE store.id IN ({ ','.join(map(str, info.keys())) })")

    try:
        for (sk, pk, actual_amount) in results:
            if pk not in info[sk]:
                continue
            asked_amount = info[sk][pk]
            if asked_amount > actual_amount:
                raise ValueError(f"Amount at key: {sk}, {pk} exeeded the acceptable range")
            else:
                consists_of.insert(values={ "product_id"      : pk,
                                            "product_list_id" : info[sk]['product_list_id'],
                                            "amount"          : asked_amount })
        for sk in info:
            move_to.insert(values={ "destination"     : current_store_id,
                                    "origin"          : sk,
                                    "date"            : datetime.today().strftime('%Y-%m-%d'),
                                    "product_list_id" : info[sk]['product_list_id'],
                                    "info"            : desc,
                                    "status"          : "Pending" })
        consists_of.db.commit()
    except:
        consists_of.db.rollback()
        raise

    return render_template('stock_succes.html')

@app.route('/purchase_history', methods=[ 'GET' ])
def get_history():
    purchase_history = db.createObject("purchase_history")
    employee         = db.createObject("employee")
    client           = db.createObject("client")
    product          = db.createObject("product")
    consists_of      = db.createObject("consists_of")
    results = purchase_history.join(employee,    on=f"purchase_history.employee_id=employee.tin AND purchase_history.store_id={current_store_id}")\
                              .join(client,      on="client.id=purchase_history.client_id")\
                              .join(consists_of, on="purchase_history.product_list_id=consists_of.product_list_id")\
                              .join(product,     on="product.id=consists_of.product_id")\
                              .query(cols=("purchase_history.product_list_id",
                                           "date",
                                           "employee.first_name",
                                           "employee.last_name",
                                           "client.first_name",
                                           "client.last_name",
                                           "SUM(amount)",
                                           "SUM(price*amount)",
                                           "rating"),
                                    condition="GROUP BY purchase_history.product_list_id ORDER BY date DESC")
    return render_template('purchase_history.html', info=results)

@app.route('/purchase_history/<id>', methods=[ 'GET' ])
def get_history_id(id):
    purchase_history = db.createObject("purchase_history")
    employee         = db.createObject("employee")
    client           = db.createObject("client")
    product          = db.createObject("product")
    consists_of      = db.createObject("consists_of")
    results = purchase_history.join(employee,    on=f"purchase_history.employee_id=employee.tin AND purchase_history.store_id={current_store_id} AND purchase_history.product_list_id=%(id)s")\
                              .join(client,      on="client.id=purchase_history.client_id")\
                              .join(consists_of, on="purchase_history.product_list_id=consists_of.product_list_id")\
                              .join(product,     on="product.id=consists_of.product_id")\
                              .query(cols=("purchase_history.date",
                                           "employee.first_name",
                                           "employee.last_name",
                                           "client.first_name",
                                           "client.last_name",
                                           "client.phone_number,"
                                           "rating",
                                           "product.*",
                                           "amount",
                                           "amount*product.price"),
                                     values={ 'id': id })
    date     = results[0][0]
    employee = f"{results[0][1]} {results[0][2]}"
    client   = f"{results[0][3]} {results[0][4]}"
    client_phone_number = results[0][5]
    rating = results[0][6]
    info = tuple( v[8:] for v in results )

    return render_template('purchase_history_id.html' , date=date,
                                                        employee=employee,
                                                        client=client,
                                                        client_phone_number=client_phone_number,
                                                        rating=rating,
                                                        info=info)

@app.route('/move_history', methods=[ 'GET' ])
def get_move():
    store = db.createObject("store")
    move_to          = db.createObject(name="move_to")
    move_to_stores   = move_to.join(store,"move_to.destination=store.id")
    transfer_to      = move_to_stores.query(cols=("move_to.product_list_id","street_name", "street_number", "date", "info","status"),
                                            condition=f"WHERE move_to.origin={current_store_id} ORDER BY date DESC")
    move_from_stores = move_to.join(store,"move_to.origin=store.id")
    transfer_from    = move_from_stores.query(cols=("move_to.product_list_id", "street_name", "street_number", "date", "info","status"),
                                              condition=f"WHERE move_to.destination={current_store_id} ORDER BY date DESC")
    
    return render_template('move_history.html', transfer_to=transfer_to, transfer_from=transfer_from)

@app.route('/move_history/<id>', methods=[ 'GET' ])
def get_move_id(id):
    move_to           = db.createObject("move_to")
    store_origin      = db.createObject("store AS origin")
    store_destination = db.createObject("store AS destination")
    product           = db.createObject("product")
    consists_of       = db.createObject("consists_of")
    results = move_to.join(consists_of,       on="move_to.product_list_id=consists_of.product_list_id AND consists_of.product_list_id=%(plid)s")\
                     .join(product,           on="product.id=consists_of.product_id")\
                     .join(store_destination, on="move_to.destination=destination.id")\
                     .join(store_origin,      on="move_to.origin=origin.id")\
                     .query(cols=("move_to.date",
                                  "move_to.info", 
                                  "move_to.status",
                                  "destination.street_name",
                                  "destination.street_number",
                                  "origin.street_name",
                                  "origin.street_number",
                                  "product.name",
                                  "product.category",
                                  "product.manufacturer",
                                  "product.description",
                                  "consists_of.amount"),
                            values={ 'plid': id })
    date   = results[0][0]
    desc   = results[0][1]
    status = results[0][2]
    destination = f"{results[0][3]} {results[0][4]}"
    origin      = f"{results[0][5]} {results[0][6]}"
    info = tuple( v[7:] for v in results )
    return render_template('move_history_id.html', date=date, 
                                                   desc=desc, 
                                                   status=status,
                                                   destination=destination,
                                                   origin=origin,
                                                   info=info)

# SECTION: Main
if __name__ == '__main__':
    host = '0.0.0.0' if ON_HEROKU else 'localhost'
    port = os.environ.get('PORT') if ON_HEROKU else 8080
    if port is None:
        raise EnvironmentError("Could not find port")
    
    app.run(host=host, port=port)
    db.close()
# !SECTION
