from flask import Flask, render_template, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.sql import label
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'

db = SQLAlchemy(app)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return self.product_name


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    warehouse_location = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return self.warehouse_location


class ProductMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    from_location = db.Column(db.String(100))
    to_location = db.Column(db.String(100))
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(50), nullable=False)
    product_qty = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return 'Movement ' + str(self.id)


class ProductLocationAvailabilityMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(50), nullable=False)
    location_name = db.Column(db.String(100), nullable=False)
    product_qty_balance = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


@app.route('/')
def index():
    product_movement_data = ProductMovement.query.group_by(ProductMovement.product_id).all()
    if product_movement_data:
        for data in product_movement_data:
            pass
            # product = Product.query.filter_by(Product.id == data.product_id)

    return render_template('index.html')


@app.route('/products', methods=['GET', 'POST'])
def product():
    if request.method == 'POST':

        product_name = request.form['product_name']
        if 'product_id' in request.form:
            product_id = request.form['product_id']
            exist = Product.query.filter_by(id=product_id).first()
            exist.product_name = product_name
            exist.updated_at = datetime.utcnow()
            db.session.commit()
        else:
            new_product = Product()
            new_product.product_name = product_name
            db.session.add(new_product)
            db.session.flush()
            db.session.commit()
            return redirect(url_for('product'))

    products = Product.query.all()
    quantity = ProductLocationAvailabilityMapping.query.with_entities(ProductLocationAvailabilityMapping.product_name, label('sum', func.sum(ProductLocationAvailabilityMapping.product_qty_balance))).group_by(ProductLocationAvailabilityMapping.product_name).all()
    return render_template('product.html', products=products, quantity=quantity)


@app.route('/locations', methods=['GET', 'POST'])
def location():
    if request.method == 'POST':
        warehouse_location = request.form['location_name']
        if 'location_id' in request.form:
            location_id = request.form['location_id']
            exist = Location.query.filter_by(id=location_id).first()
            exist.warehouse_location = warehouse_location
            db.session.commit()
        else:
            warehouse = Location()
            warehouse.warehouse_location = warehouse_location
            db.session.add(warehouse)
            db.session.flush()
            db.session.commit()
            return redirect(url_for('location'))

    locations = Location.query.all()
    for loc in locations:
        product_list = []
        products = ProductLocationAvailabilityMapping.query.filter_by(location_name=loc.warehouse_location).all()
        if products:
            for product in products:
                product_list.append(product.product_name)

        if product_list:
            string = ''
            count = 1
            for product in product_list:
                string += product
                if count < len(product_list):
                    string += ', '
                count += 1
        setattr(loc, 'product_list', string)

        print(products)
    return render_template('location.html', locations=locations)


@app.route('/movements', methods=['GET', 'POST'])
def movement():
    if request.method == 'POST':
        allow_entry = True
        product_name = None
        product_quantity = None
        mapped_record_location = None

        from_location = request.form['from_location']

        to_location = request.form['to_location']

        if from_location or to_location:
            if from_location == to_location:
                allow_entry = False
                print('From and To location cannot be same')
        else:
            print('From and To location are not selected')
            allow_entry = False

        if int(request.form['product_quantity']) > 0:
            product_quantity = request.form['product_quantity']
        else:
            print('Invalid quantity')
            allow_entry = False
        if request.form['product_name'] != 'Select product':
            product_name = request.form['product_name']
        else:
            print('no product selected')
            allow_entry = False

        product_details = Product.query.filter_by(product_name=product_name).first()
        if from_location == 'Select warehouse':
            pass
        else:
            mapped_record_location = ProductLocationAvailabilityMapping.query.filter_by(product_name=product_name).filter_by(location_name=from_location).first()
            if mapped_record_location:
                if int(product_quantity) > mapped_record_location.product_qty_balance:
                    print('Quantity not available')
                    allow_entry = False
            else:
                print('From entry not found in mapping')
                allow_entry = False

        if allow_entry:

            if 'movement_id' in request.form:
                old_movement = ProductMovement.query.filter_by(id=request.form['movement_id']).first()
                old_movement.product_id = product_details.id
                old_movement.product_name = product_name
                if from_location != 'Select warehouse':
                    old_movement.from_location = from_location
                else:
                    old_movement.from_location = '---'
                if to_location != 'Select warehouse':
                    old_movement.to_location = to_location
                else:
                    old_movement.to_location = '---'
                old_movement.timestamp = datetime.utcnow()
                old_movement.product_qty = product_quantity
            else:
                new_movement = ProductMovement()
                new_movement.product_id = product_details.id
                new_movement.product_name = product_name
                if from_location != 'Select warehouse':
                    new_movement.from_location = from_location
                else:
                    new_movement.from_location = '---'
                if to_location != 'Select warehouse':
                    new_movement.to_location = to_location
                else:
                    new_movement.to_location = '---'
                new_movement.product_qty = product_quantity
                db.session.add(new_movement)
                db.session.flush()

            from_mapped_records = ProductLocationAvailabilityMapping.query.filter_by(product_name=product_name).filter_by(location_name=from_location).first()
            if from_mapped_records:
                from_mapped_records.product_qty_balance -= int(product_quantity)

            to_mapped_records = ProductLocationAvailabilityMapping.query.filter_by(product_name=product_name).filter_by(location_name=to_location).first()
            if to_mapped_records:
                to_mapped_records.product_qty_balance += int(product_quantity)
            else:
                if to_location == 'Select warehouse':
                    pass
                else:
                    to_record = ProductLocationAvailabilityMapping()
                    to_record.location_name = to_location
                    to_record.product_name = product_name
                    to_record.product_qty_balance = product_quantity
                    db.session.add(to_record)

            db.session.commit()
        return redirect(url_for('movement'))

    products = Product.query.all()
    select_product = {'id': 0, 'product_name': 'Select product'}
    products.insert(0, select_product)
    locations = Location.query.all()
    print(locations)
    select_warehouse = {'id': 0, 'warehouse_location': 'Select warehouse'}
    locations.insert(0, select_warehouse)
    print(locations)
    movements = ProductMovement.query.all()
    print(movements)
    return render_template('movements.html', products=products, locations=locations, movements=movements)


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
