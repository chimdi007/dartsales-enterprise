# app.py
from flask import Flask, session, render_template, request, json, url_for
from auth import auth, login, add_to_cart, clear_cart, checkout, dashboard, remove_stock, add_stock, search, remove_from_cart, update_inventory, barcode_search, reprint_receipt
from auth import return_item, report_incident, report_expenditure
from config import config, appconsole, settings, change_password, create_user, app_configuration, delete_user, backup_sale, start_scheduler
import os
import threading

app = Flask(__name__)
app.register_blueprint(auth, url_prefix='/auth')

app.secret_key= os.urandom(24)




#_____________________AUTHENTICATION___________________________
@app.route('/appconsole', methods=['POST'])
def appconsole_route():
    return appconsole()

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    return login()

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return render_template('index.html')

@app.route('/')
def index():
    return render_template('index.html')




#________________________APP CONFIGURATIONS AND MANAGEMENT______________________
@app.route('/settings')
def settings_route():
    return settings()


@app.route('/change_password', methods=['POST'])
def change_password_route():
    return change_password()


@app.route('/create_user', methods=['POST'])
def create_user_route():
    return create_user()


@app.route('/app_configuration', methods=['POST'])
def app_configuration_route():
    return app_configuration()


@app.route('/delete_user', methods=['POST'])
def delete_user_route():
    return delete_user()




#______________________SHOP SECTION_____________________________
@app.route('/dashboard')
def dashboard_route():
    return dashboard()


@app.route('/add_to_cart', methods=['GET'])
def route_to_add_to_cart():
    return add_to_cart()

@app.route('/clear_cart')
def clear_cart_route():
    return clear_cart()

@app.route('/checkout', methods=['GET', 'POST'])
def checkout_route():
    return checkout()

@app.route('/remove_from_cart', methods=['POST', 'GET'])
def remove_from_cart_route():
    return remove_from_cart()

@app.route('/reprint_receipt/<receipt_number>', methods=['POST'])
def reprint_receipt_route(receipt_number):
    return reprint_receipt(receipt_number)

@app.route('/return_item', methods=['POST'])
def return_item_route():
    return return_item()
#_____________________________INVENTORY MANAGEMENT____________________________

@app.route('/remove_stock', methods=['POST'])
def remove_stock_route():
    return remove_stock()

@app.route('/add_stock', methods=['POST'])
def add_stock_route():
    return add_stock()

@app.route('/search')
def search_route():
    return search()

@app.route('/barcode_search', methods=['POST', 'GET'])
def barcode_search_route():
    return barcode_search()

@app.route('/update_inventory', methods=['POST'])
def update_inentory_route():
    return update_inventory()


#_____________________________________________________________
#_______________________REPORTS AND INCIDENTS_______________________
@app.route('/report_incident', methods=['POST'])
def report_incident_route():
    return report_incident()

@app.route('/report_expenditure', methods=['POST'])
def report_expenditure_route():
    return report_expenditure()
#_____________________________________________________________

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=start_scheduler)
    scheduler_thread.daemon = True  # Allows the program to exit if only daemon threads are left
    scheduler_thread.start()
    app.run(debug=True, host='0.0.0.0', port=4005)
