#!/usr/bin/env python3
import os
from flask import Flask, escape, request, send_file, render_template
import MySQLdb

# SECTION: Constants
# Flags if on HEROKU environment
ON_HEROKU = 'IS_HEROKU' in os.environ
# !SECTION

# Creating a flask app
app = Flask(__name__, template_folder='templates')

@app.route('/', methods=[ 'GET' ])
def get_index():
    """Redirects default page to login.html"""
    return render_template('login.html', mimetype='text/html')

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


# SECTION: Main
if __name__ == '__main__':
    host = '0.0.0.0' if ON_HEROKU else 'localhost'
    port = os.environ.get('PORT') if ON_HEROKU else 8080
    if port is None:
        raise EnvironmentError("Could not find port")
    app.run(host=host, port=port)
# !SECTION
