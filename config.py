from flask import Blueprint, request, session, json, render_template, url_for, jsonify, flash, redirect
import json
import os
from datetime import datetime
import requests
import schedule
import time

config = Blueprint('config', __name__)

#_________________IMPORTS______________________

current_directory = os.path.dirname(os.path.abspath(__file__))
users_path = os.path.join(current_directory, 'database', 'users')
sales_path = os.path.join(current_directory, 'database', 'sales')
config_path = os.path.join(current_directory, 'database', 'config')
inventory_path = os.path.join(current_directory, 'database', 'inventory')
#ownership_path = os.path.join(current_directory, 'database', 'ownership')
reports_path = os.path.join(current_directory, 'database', 'reports')

users =[]
shop = {}


#______________________________________

def appconsole2():
    global ownership_path
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with open( ownership_path, 'r') as file:  # Assuming users are stored in a JSON file
            user = json.load(file)  # Load JSON data
        if user['username']==username and user['password']==password:
            session['username'] = user['username']
            return settings()
        else:
            return "Invalid username or password"
    else:
        return f"Please <a href='{url_for('index')}'>log in</a>"
    
def appconsole():
    global config_path
    if request.method == 'POST':
        shop_key = request.form['shop_key']
        shop_password = request.form['password']
        retrieve_access(shop_key, shop_password)
        with open( config_path, 'r') as file:  # Assuming users are stored in a JSON file
            user = json.load(file)  # Load JSON data
        if user['shop_key']==shop_key and user['shop_password']==shop_password:
            session['username'] = user['shop_key']
            return settings()
        flash("Invalid shop details or subscription!")
        return redirect(url_for('index'))
    else:
        return f"Please <a href='{url_for('index')}'>log in</a>"
    
    
    
def settings():
    global users, shop
    if 'username' in session:
        #username=session['username']
        define_users()
        read_settings()
        return render_template('settings.html', users=users, shop=shop)
    else:
        return render_template('index.html')
    


def change_password():
    global ownership_path
    try:
        data = request.get_json()
        if not data:
            return jsonify(message="No data received or incorrect content type"), 400

        old_username = data.get('old_username')
        new_username = data.get('new_username')
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        # Read the existing user data
        with open(ownership_path, 'r') as file:
            user = json.load(file)

        print("old_username: ", old_username) #debug debug
        print("new_username: ", new_username) #debug debug
        print("old_password: ", old_password) #debug debug
        print("new_password: ", new_password) #debug debug

        # Check if the old username and password match
        if user['username'] == old_username and user['password'] == old_password:
            user['username'] = new_username #if new_username else old_username
            user['password'] = new_password

            # Write the updated user data
            with open(ownership_path, 'w') as file:
                json.dump(user, file)

            return jsonify(message="Administrator details updated!"), 200
        else:
            return jsonify(message="Old username or password unrecognized"), 400

    except Exception as e:
        return jsonify(message=str(e)), 500
    
    
def define_users():
    global users_path, users
    with open(users_path, 'r') as file:
        users = json.load(file)
    if not isinstance(users, list):
        return None
    
    for user in users:
        user.setdefault('username', None)
        user.setdefault('name', None)
        user.setdefault('date', None)
        user.setdefault('access_level', None) 
    return None


    
def create_user():
    global users_path
    data = request.get_json()
    if not data:
        return jsonify(message="No data received or incorrect content type"), 400

    try:
        new_user = {
            'username': data.get('username'),
            'name': data.get('name'),
            'access_level': data.get('access_level'),
            'password': data.get('password'),
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            with open(users_path, 'r') as file:
                users = json.load(file)
                if not isinstance(users, list):
                    users = []
        except (json.JSONDecodeError, FileNotFoundError):
            users = []
        users.append(new_user)
        with open(users_path, 'w') as file:
            file.write(json.dump(users, file, indent=1) + '\n')

        return jsonify(message="New user successfully created!"), 200
    except Exception as e:
        return jsonify(message=str(e)), 500    


def app_configuration():
    global config_path
    data = request.get_json()
    if not data:
        return jsonify(message="No data received or incorrect content type"), 400
    
    try:
        config = {
            "shop_name" : data.get('shop_name'),
            "shop_key" : data.get('shop_key'),
            "currency" : data.get('currency'),
            "user_unique_id":data.get('user_unique_id'),
            "vat": data.get('vat'),
            "shop_password": data.get('shop_password')
        }
        #print(config) #debug print 
        try:
            with open(config_path, 'w', encoding='utf-8') as file:
                json.dump(config, file, indent=1, ensure_ascii=False)
                return jsonify(message="settings saved!"), 200
        except Exception as e:
            return jsonify(message=str(e)), 500
        
    except Exception as e:
        return jsonify(message=str(e)), 500
    
    
def read_settings():
    global config_path, vat, shop_name, shop_key, shop_password, currency, user_unique_id, shop
    try:
        with open(config_path, 'r') as file:
            data = json.load(file)
            vat = float(data['vat'])
            shop_name = data['shop_name']
            shop_key = data['shop_key']
            shop_password = data['shop_password']
            currency = data['currency']
            user_unique_id = data['user_unique_id']
            #name = data['name']
            #username = data['username']
            shop = {
                "user_unique_id": user_unique_id,
                "shop_name": shop_name,
                "shop_key": shop_key,
                "shop_password": shop_password,
                "vat":vat,
                "currency":currency#,
                #"username": username,
                #"name": name
                }
            #print("AAA", shop['shop_password'])
    except Exception as e:
        vat = f"{e}"
        shop_name = f"{e}"
        shop_key = f"{e}"
        user_unique_id = f"{e}"
        return None
    
    


    
def delete_user():
    data = request.get_json()
    username = data.get('username')
    if not username:
        return jsonify({"message": "Username not provided"}), 400
    try:
        with open(users_path, 'r') as file:
            users = json.load(file)
                    
        # filter out user from the list if found
        users = [user for user in users if user.get('username') != username]
        
        with open(users_path, 'w') as file:
            json.dump(users, file, indent=4)
        return jsonify(message="User deleted!"), 200
    except Exception as e:
        return jsonify(message=str(e)), 500
    
    #______________________________BACKUP SECTION_______________________________________
def backup_sale():
    try:
        # Load the configuration
        with open(config_path, 'r') as file:
            config = json.load(file)
            last_backup = config['last_backup']
            user_unique_id = config['user_unique_id']
            shop_key = config['shop_key']
            shop_password = config['shop_password']
        
        # Read and parse sales data
        sales = []
        with open(sales_path, 'r') as file:
            lines = file.readlines()
            for line in lines:
                sale = json.loads(line.strip())  # Ensure each line is parsed as JSON
                if sale['date'] > last_backup:
                    sales.append(sale)
        
        if not sales:
            print('Backup is upto date')
            return None

        # Prepare the payload
        payload = {
            'user_unique_id': user_unique_id,
            'shop_key': shop_key,
            'shop_password': shop_password,
            'sales': sales,
            'last_backup': sales[-1]['date']
        }

        # Send backup to server
        url = 'https://www.dartfox.org/backup_sales'
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            # Update last_backup in config and save it
            config['last_backup'] = sales[-1]['date']
            with open(config_path, 'w') as file:
                json.dump(config, file, indent=4)
            
            #print('Backup successful!')
            return 200
        else:
            print('Backup failed with status code: {}'.format(response.status_code))
            return None
    except Exception as e:
        print(f"Error during backup: {str(e)}")
        return None

#backup_sale()

def incident_report():
    try:
        reports = []
        #print("Reading reports...")
        
        with open(reports_path, 'r+') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError as json_err:
                print(f"JSON decode error: {json_err}")

            #print("Reports to be sent: ", reports)

            url = 'https://www.dartfox.org/incident_report'
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                file.seek(0)
                file.truncate()
                print("Success: ", response.text)
            else:
                print("Failed to send reports, status code: ", response.status_code)
        
    except Exception as e:
        print("Error: ", str(e))
    
#incident_report()


def retrieve_access(shop_key, shop_password):
    payload = {"shop_key": shop_key, "shop_password": shop_password}
    url = "https://www.dartfox.org/retrieve_access"
    
    response = requests.get(url, params=payload)
    
    if response.status_code == 200:
        data = response.json()
        config = data.get('config')
        users = data.get('users')
        with open(config_path, 'w') as file:
            file.seek(0)
            file.truncate()
            json.dump(config, file, indent=4)
        with open(users_path, 'w') as file:
            file.seek(0)
            file.truncate()
            json.dump(users, file, indent=4)
        #print("Config:", config)
        #print("Users:", users)
    else:
        print(f"Error: {response.status_code}")
        return f"{response.text}", 400


#_________________________________________________________________________________
#____________________________INVENTORY BACKUPS AND SYNCING_________________________

def sync_inv_to_server():
    inventory = []
    with open(config_path, 'r') as file:
        config = json.load(file)
    user_unique_id = config['user_unique_id']
    shop_key = config['shop_key']
    try:
        with open(inventory_path, 'r') as file:
            rawData = json.load(file)
            for item_data in rawData:
                item = item_data['item']
                description = item_data['description']
                sku = item_data['sku']
                upc = item_data['upc']
                price = item_data['price']
                quantity = item_data['quantity']
                inventory.append({
                    "item": item,
                    "description": description,
                    "sku": sku,
                    "upc": upc,
                    "price": price,
                    "quantity": quantity
                })
    
    except FileNotFoundError as e:
        print(f"Error: Inventory file not found. {e}")
        return

    # Send payload
    url = 'https://www.dartfox.org/sync_inv_to_server'
    
    payload = {
        "user_unique_id": user_unique_id,
        "shop_key": shop_key,
        "inventory": inventory
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print("Success Message: ", response.text)
        else:
            print("Error message: ", response.text)
    except requests.RequestException as e:
        print(f"Error sending request: {e}")
    
#sync_inv_to_server()   
    
    
    #________sync from_server_______


def sync_inv_from_server():
    with open(config_path, 'r') as file:
        config = json.load(file)
    user_unique_id = config['user_unique_id']
    shop_key = config['shop_key']
    
    payload = {"user_unique_id": user_unique_id, "shop_key": shop_key}
    url = "https://www.dartfox.org/sync_inv_from_server"
    updated_skus = []
    
    try:
        response = requests.get(url, params=payload)
        if response.status_code == 200:
            data = response.json()
            update = data.get('update')
            if update:
                with open(inventory_path, 'r+') as file:
                    inventory = json.load(file)
                    
                    # Create a mapping of SKU to inventory items for quick lookup
                    sku_to_item = {item['sku']: item for item in inventory}
                    
                    for i in update:
                        if i['sku'] in sku_to_item and i['action']=='update':
                            # Update existing item
                            existing_item = sku_to_item[i['sku']]
                            existing_item['quantity'] += i['quantity']
                            existing_item['price'] = i['price']
                            
                        elif i['sku'] in sku_to_item and i['action']=='remove':
                            inventory = [item for item in inventory if item['sku'] != i['sku']]
                        
                        elif i['action']=='add':
                            # Add new item
                            inventory.append({
                                "description": i['description'],
                                "item": i['item'],
                                "price": i['price'],
                                "quantity": i['quantity'],
                                "sku": i['sku'],
                                "upc": i['upc']
                            })
                        updated_skus.append({"user_unique_id":user_unique_id, "shop_key":shop_key, "sku":i['sku']})
                    
                    # Write updated inventory back to the file
                    file.seek(0)
                    file.truncate()
                    json.dump(inventory, file, indent=4)
                
                # Notify server of the successful update
                notify_url = "https://www.dartfox.org/mark_as_updated"
                notify_response = requests.post(notify_url, json=updated_skus)
                
                if notify_response.status_code == 200:
                    print("Inventory update notification sent successfully.")
                else:
                    print(f"Failed to notify server. Status code: {notify_response.status_code}")
            else:
                print("No updates found.")
        else:
            print(f"Failed to fetch updates. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error during request: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        
#sync_inv_from_server()
#sync_inv_to_server()


def sync_config():
    global shop
    read_settings()
    #print("Syncing...")
    shop_key= shop['shop_key']
    shop_password = shop['shop_password']
    retrieve_access(shop_key, shop_password)

schedule.every(100).seconds.do(sync_config)
schedule.every(950).seconds.do(sync_inv_from_server, sync_inv_to_server)
schedule.every(900).seconds.do(incident_report)
#schedule.every(250).seconds.do(sync_inv_to_server)
schedule.every(7200).seconds.do(backup_sale)


#sync_config()

def start_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(50)