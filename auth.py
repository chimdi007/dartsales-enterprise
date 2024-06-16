from flask import Blueprint, request, session, json, render_template, url_for, flash, jsonify, redirect
import os
from datetime import datetime
import json
import uuid
from escpos.printer import Usb

auth = Blueprint('auth', __name__)

#______________________________GLOBAL VARIABLES______________________________
current_directory = os.path.dirname(os.path.abspath(__file__))
users_path = os.path.join(current_directory, 'database', 'users')
sales_path = os.path.join(current_directory, 'database', 'sales')
inventory_path = os.path.join(current_directory, 'database', 'inventory')
config_path = os.path.join(current_directory, 'database', 'config')
reports_path = os.path.join(current_directory, 'database', 'reports')

items = []
date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
sale = {}
vat_rate= 0
total=0 #total for individual item x qty
grand_total=0   #total for each transaction
inventory = {}
currency=""
recent_trans = []
shop_name = ""

#_________________________________________________________________________
#__________________________________RECEIPT________________________________


class Receipt:
    def __init__(self, date, receipt_number, items, vat_rate):
        self.date = date
        self.receipt_number = receipt_number
        self.items = items
        self.vat_rate = vat_rate
        self.vat = self.calculate_vat()
        self.total = self.calculate_total()

    def calculate_vat(self):
        total = 0
        for item in self.items:
            total += int(item['quantity']) * float(item['price'])
        vat = total * self.vat_rate / 100
        return vat

    def calculate_total(self):
        total = 0
        for item in self.items:
            total += int(item['quantity']) * float(item['price'])
        total_with_vat = total + self.calculate_vat()
        return total_with_vat

    def to_dict(self):
        return {
            'receipt_id': self.receipt_number,
            'items': self.items,
            'total': self.total,
            'date': self.date
        }

    def generate_receipt(self):
        receipt_str = f"Receipt Number: {self.receipt_number}\n"
        receipt_str += f"Date: {self.date}\n"
        receipt_str += "Items:\n"
        for item in self.items:
            receipt_str += f"{item['item']} x {item['quantity']} @ {item['price']} each\n"
        receipt_str += f"VAT: {currency}{self.vat:.2f}\n"
        receipt_str += f"Total: {currency}{self.total:.2f}\n"
        return receipt_str
    
    def print_receipt(self):
        # Initialize the printer (adjust vendor_id and product_id to match your printer)
        p = Usb(0x0416, 0x5011)  # Example vendor_id and product_id for Epson printers
        print("RECEIPT NUMBER: ", self.receipt_number) #DEBUG PRINT
        # Print the receipt
        p.text(f"Receipt Number: {self.receipt_number}\n")
        print("We got here!")
        p.text(f"Date: {self.date}\n")
        p.text("Items:\n")
        for item in self.items:
            p.text(f"{item['item']} x {item['quantity']} @ {item['price']} each\n")
        p.text(f"VAT: ${self.vat:.2f}\n")
        p.text(f"Total: ${self.total:.2f}\n")

        # Cut the paper
        p.cut()
#––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––



def reprint_receipt(receipt_number):
    global vat_rate, sales_path
    try:        
        receipt_number = int(receipt_number)
        # Read all lines from the sales file
        with open(sales_path, 'r') as file:
            all_transactions = file.readlines()
        
        # Find the transaction with the given receipt number
        for transaction_str in all_transactions:
            transaction = json.loads(transaction_str)
            if receipt_number == transaction['receipt_number']:
                date = transaction['date']
                items = transaction['items']
                receipt = Receipt(date, receipt_number, items, vat_rate)
                print(receipt.print_receipt())
                return jsonify(receipt=receipt.print_receipt()), 200

        return jsonify(message="Receipt not found"), 404
    except Exception as e:
        return jsonify(message=f"{str(e)}"), 500
#________________________________________________________________________
#_____________________________AUTHENTICATION______________________________



def login():
    global users_path
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with open( users_path, 'r') as file:  # Assuming users are stored in a JSON file
            users = json.load(file)  # Load JSON data
            for user in users:
                if user['username'] == username and user['password'] == password:
                    session['username'] = user['username']
                    session['name'] = user['name']
                    session['access_level'] = user['access_level']
                    return dashboard()
            flash("Invalid login details!")
            return redirect(url_for('index'))
    return render_template('index.html')
    
    
def dashboard():
    global items, sale, vat_rate, grand_total, inventory, currency, recent_trans, shop_name
    if 'username' in session:
        recent_transactions()
        stock_records()
        shop_parameters()
        #print("NEW VAT RATE: ", vat_rate) #debug print
        name=session['name']
        access_level = session['access_level']
        return render_template('dashboard.html', name=name, access_level=access_level, items=items, vat_rate=vat_rate, currency=currency, grand_total=grand_total, inventory=inventory, recent_trans=recent_trans, shop_name=shop_name)
    else:
        return f"Please <a href='{url_for('index')}'>log in</a>"    
    


def shop_parameters():
    global vat_rate,currency, shop_name
    try:
        with open(config_path, 'r') as file:
            data = json.load(file)
            vat_rate = float(data['vat'])
            currency = data['currency']
            shop_name = data['shop_name']
    except Exception as e:
        vat_rate = f"{e}"
        currency = f"[e]"
        return None
#_______________________________________________________________________________________________
#__________________________________________SHOP SECTION__________________________________________
def return_item():
    global vat_rate
    try:
        items = []
        data = request.get_json()
        order_number = data.get('order_number')
        item_sku = data.get('item_sku')
        quantity = (0 - int(data.get('quantity')))
        reason = data.get('reason')
        attendant = data.get('attendant')
        return_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        receipt_number = generate_receipt_number()
        transaction_type = 'return'
        print("quantity: ", quantity, order_number, item_sku)
        print("reason: ", reason)
        
        if not order_number or not item_sku or not quantity or not reason:
            return jsonify(message="some field missing"), 400
        
        item_found = False
        with open(inventory_path, 'r') as file:
            inventory = json.load(file)  # Load the entire JSON array
            for rec in inventory:
                if rec['sku'] == item_sku:
                    item = rec['item']
                    price = float(rec['price'])
                    item_found = True
                    break
        vat = price * quantity * vat_rate/100
        if not item_found:
            return jsonify(message="Item not found in inventory"), 404

        items.append({
            'item': item,
            'price': price,
            'quantity': quantity,
            'sku': item_sku,
            'total': price * quantity,
            'reason': reason,
            'old_receipt_number': order_number
        })
        
        sale = {
            'receipt_number': receipt_number,
            'date': return_date,
            'items': items,
            'transaction_type': transaction_type,
            'attendant': attendant,
            'price': price * quantity,
            'vat': vat,
            'total': price * quantity + vat
        }
        
        items_str = json.dumps(sale)
        
        with open(sales_path, 'a') as file:
            file.write(items_str + '\n')
            update_stock_count(items)
            receipt = Receipt(return_date, receipt_number, items, vat_rate)
            print(receipt.generate_receipt())
        
        items.clear()
        return jsonify(message="Item returned to stock!")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return jsonify(message=f"Error decoding JSON: {e}"), 500
    except Exception as e:
        print("Error: ", str(e))
        return jsonify(message=f"Error: {str(e)}"), 500




def add_to_cart():
    try:
        global items
        item_id = str(uuid.uuid4())
        item = request.args.get('item')
        quantity= request.args.get('quantity')
        price = request.args.get('price')
        sku = request.args.get('sku')
        total = (int(quantity) * float(price))
        items.append({'item_id':item_id, 'item': item, 'quantity': quantity, 'price': price, 'total':total, 'sku':sku}) #,"sku": sku})    
        return f"success!", 200
    except Exception as e:
        return f"{e}"
    
    

def remove_from_cart():
    global items
    item_id = request.args.get('item_id')
    if not item_id:
        return jsonify(message="Item ID missing"), 400

    items = [item for item in items if not (item['item_id'] == item_id)]
    
    return jsonify(message="Item removed from cart!"), 200


    
def clear_cart():
    global items
    #print('here')
    try:
        items.clear()
        return f"cart emptied!", 200
    except Exception as e:
        return f"{e}", 500

        

    
def checkout():
    global sales_path, sale, receipt_number, date, vat_rate
    try:
        data = request.get_json()
        items = data.get('items')
        print('Items to checkout: ', items)
        receipt_number= generate_receipt_number()
        attendant = session['name']
        price = 0
        
        for i in items:
            price += float(i['price'])*int(i['quantity'])
        vat = price * vat_rate/100
        total = price+vat
           
        sale={"receipt_number":receipt_number, "date":date, "items":items, "transaction_type":"credit", 'attendant':attendant, 'price':price, 'vat':vat, 'total':total}
        print("Sales: ", sale)
        items_str = json.dumps(sale)      
        with open(sales_path, 'a') as file:
            file.write(items_str + '\n')
            #print("ITEMS TO CHECKOUT: ", items) #debug printing
            update_stock_count(items)
            #print(items)
            receipt = Receipt(date, receipt_number, items, vat_rate)  #bugs to be fixed
            print(receipt.generate_receipt())        #bugs to be fixed
        items.clear()
        return jsonify(message="Checkout successful"), 200
    except Exception as e:
        print(str(e))        
        return str(e), 500
    
    
    
    
    
def generate_receipt_number():
    global sales_path
    with open(sales_path, 'r') as file:
        lines = file.readlines()
        if not lines:
            return 1001
        last_line = lines[-1]
        last_transaction = json.loads(last_line)
        return last_transaction['receipt_number'] + 1
    
    
def recent_transactions():
    global vat_rate, recent_trans, currency
    recent_trans = []  # Initialize the recent transactions list

    try:
        # Read all lines from the file
        with open(sales_path, 'r') as file:
            all_transactions = file.readlines()
        
        # Get the last 10 transactions
        recent = all_transactions[-10:]
        if not recent:
            return "No recent transactions"
        
        # Process the transactions
        for trans_str in recent:
            trans = json.loads(trans_str)  # Parse JSON string to a dictionary
            trans_receipt = trans['receipt_number']
            trans_date = trans['date']
            trans_items = trans['items']  # Access the items correctly
            trans_total = 0
            for item in trans_items:
                item_total = float(item['quantity']) * float(item['price'])
                item_vat = item_total * vat_rate/100
                trans_total += item_total + item_vat  # Accumulate the total including VAT

            recent_trans.append({
                'trans_receipt': trans_receipt,
                'trans_date': trans_date,
                'trans_total': trans_total      #f"{currency}{trans_total:.2f}"
            })
        
        return recent_trans
    except Exception as e:
        return str(e)

# Example usage
#recent_transactions_data = recent_transactions()
#print(recent_transactions_data)

#______________________________INVENTORY SECTION____________________________


def update_stock_count(items):  # inventory_path is passed as an argument
    global inventory_path
    try:
        with open(inventory_path, 'r+') as file:
            updated_inventory = json.load(file)
        for item in items:
            sku = item['sku']
            quantity_sold = int(item['quantity']) 

            for i in updated_inventory:
                if i['sku'] == sku:
                    i['quantity'] = int(i['quantity']) - quantity_sold
                    #i['quantity'] = str(int(i['quantity']) - quantity_sold)  # Update the quantity and keep it as string
                    break  # Exit the loop once the item is found and updated

        with open(inventory_path, 'w') as file:
            json.dump(updated_inventory, file, indent=4)

        return jsonify(message="Stock count updated!"), 200

    except Exception as e:
        return jsonify(message=f"An error occurred: {str(e)}"), 500
                    
        


def stock_records():
    global inventory_path, inventory
    try:
        
        with open(inventory_path, 'r') as file:
            inventory = json.load(file)
            for i in inventory:
                i.setdefault('item', None)
                i.setdefault('description', None)
                i.setdefault('sku', None)
                i.setdefault('upc', None)
                i.setdefault('quantity', None)
                i.setdefault('price', None)   
        return inventory
    except Exception as e:
        return flash("{e}")



            
def remove_stock():
    global inventory_path
    data = request.get_json()
    sku = data.get('sku')
    if not sku:
        return jsonify(message="SKU not provided"), 400
    
    try:
        with open(inventory_path, 'r+') as file:
            stocks = json.load(file)
            original_length = len(stocks)
            stocks = [stock for stock in stocks if stock.get('sku') != sku]
            
            if len(stocks) == original_length:
                return jsonify(message="Item not in stock"), 404
            
            file.seek(0)
            file.truncate()
            json.dump(stocks, file, indent=4)
            return jsonify(message="Item removed from inventory!"), 200
    
    except Exception as e:
        return jsonify({"message": str(e)}), 500


def add_stock():
    global inventory_path
    data = request.get_json()
    if not data:
        return jsonify({"message": "No data received or incorrect content type", "success": False}), 400
    item = data.get('item')
    description = data.get('description')
    sku = data.get('sku')
    upc = data.get('upc')
    quantity = data.get('quantity')
    price = data.get('price')
    print("item:",item, "desc:",description, "sku:",sku, "upc:",upc, "qty:",quantity, "price:", price)
    if not all([item, description, sku, upc, quantity, price]):
        return jsonify({"message": "All fields are requiredxxxx", "success": False}), 400
    try:
        new_stock = {
            "item": item,
            "description": description,
            "sku": sku,
            "upc": upc,
            "quantity": quantity,
            "price": price
        }

        with open(inventory_path, 'r+') as file:
            inventory = json.load(file)
            inventory.append(new_stock)
            file.seek(0)
            json.dump(inventory, file, indent=4)
            file.truncate()

        return jsonify({"message": "Item added to inventory!", "success": True}), 200
    except Exception as e:
        return jsonify({"message": str(e), "success": False}), 500

    
   
def search():
    global inventory_path
    query = request.args.get('q', '')
    with open(inventory_path, 'r') as file:
        products = json.load(file)
    if query:
        matches = [product for product in products if query.lower() in product['item'].lower()]
        #print(matches)
        return jsonify(matches)
    return jsonify([])


def barcode_search():
    global inventory_path
    query = request.args.get('q', '')
    with open(inventory_path, 'r') as file:
        products = json.load(file)
    if query:
        matches = [product for product in products if query in product['upc']]
        print("Matches: ", matches)
        return jsonify(data=f"{matches}")
        #return f"{matches}"
    return jsonify([])


def update_inventory():
    sku = request.args.get('sku')
    quantity = request.args.get('quantity')
    price = request.args.get('price')

    # Check if SKU or quantity is missing
    if not sku or not quantity:
        return jsonify(message="SKU and quantity are required!"), 400
    print("Parsed quantity: ", quantity)
    try:
        # Convert quantity to integer
        quantity = int(quantity)
        price = float(price)
    except ValueError:
        return jsonify(message="Quantity must be an integer!"), 400

    try:
        # Open the inventory file
        with open(inventory_path, 'r+') as file:
            inventory = json.load(file)

            # Find the item with the given SKU and update its quantity
            item_found = False
            for item in inventory:
                if item['sku'] == sku:
                    item['quantity'] = quantity
                    item['price'] = price
                    item_found = True
                    break
            
            if not item_found:
                return jsonify(message="SKU not found in inventory!"), 404

            # Reset file pointer and truncate file after update
            file.seek(0)
            file.truncate()

            # Save the updated inventory back to the file
            json.dump(inventory, file, indent=4)

        return jsonify(message="Inventory updated!"), 200

    except FileNotFoundError:
        return jsonify(message="Inventory file not found!"), 500
    except json.JSONDecodeError:
        return jsonify(message="Error reading inventory file!"), 500
    except Exception as e:
        return jsonify(message=f"An error occurred: {str(e)}"), 500

#_____________________________________________________________________________




#______________________________INCIDENTS AND REPORTS_______________________________


def report_incident():
    try:
        data = request.get_json()
        reporter = data.get('reporter')
        location = data.get('location')
        incident = data.get('incident')

        with open(config_path, 'r') as file:
            sd = json.load(file)
            user_unique_id = sd['user_unique_id']
            shop_key = sd['shop_key']

        new_report = {
            'user_unique_id': user_unique_id,
            'shop_key': shop_key,
            'location': location,
            'reporter': reporter,
            'incident': incident
        }
        try:
            with open(reports_path, 'r') as file:
                reports = json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            reports = []

        reports.append(new_report)
        with open(reports_path, 'w') as file:
            json.dump(reports, file, indent=4)

        return jsonify(message="Incident submitted!"), 200
    except Exception as e:
        return jsonify(message=f"Error submitting incident: {str(e)}"), 400
    
    
def report_expenditure():
    try:
        data = request.get_json()
        print("DATA: ", data)
        reporter = data.get('reporter')
        category = data.get('category')
        location = data.get('location')
        description = data.get('description')
        amount = float(data.get('amount'))
        receipt_number= generate_receipt_number()
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        attendant = session['name']
        items = {'reporter':reporter, 'location':location, 'category':category, 'description':description, 'price':amount}
        sale={"receipt_number":receipt_number, "date":date, "items":items, "transaction_type":"debit", 'attendant':attendant, 'price': 0-amount, 'vat':0, 'total':0-amount}
        items_str = json.dumps(sale)      
        with open(sales_path, 'a') as file:
            file.write(items_str + '\n')
        return jsonify(message="Expenditure recorded successfully. Form will now reset."), 200

    except Exception as e:
        print(str(e))        
        return str(e), 500
#____________________________________________________________________________
