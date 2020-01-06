from flask import Flask, render_template, redirect, request, url_for, make_response, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pdfkit

app = Flask(__name__)
app.secret_key = 'inventory-management-system'
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


@app.route('/')
def index():

    big_data = index_data()
    return render_template('index.html', summary_data=big_data)


@app.route('/products', methods=['GET', 'POST'])
def product():
    if request.method == 'POST':
        if 'delete_product_id' in request.form:
            delete_id = request.form['delete_product_id']
            prod = Product.query.filter_by(id=delete_id).first()
            movement_data = ProductMovement.query.filter_by(product_name=prod.product_name).first()
            if movement_data:
                flash(f'{prod.product_name} cannot be deleted', 'info')
            else:
                Product.query.filter_by(id=delete_id).delete()
        else:
            if 'product_name' in request.form:
                product_name = request.form['product_name']
            if 'product_id' in request.form:
                product_id = request.form['product_id']
                exist = Product.query.filter_by(id=product_id).first()
                old_product = exist.product_name
                exist.product_name = product_name
                exist.updated_at = datetime.utcnow()
                product_movement_data = ProductMovement.query.filter_by(product_name=old_product).all()
                if product_movement_data:
                    for product_data in product_movement_data:
                        product_data.product_name = product_name
                flash(f'{product_name} edited', 'info')
            else:
                new_product = Product()
                new_product.product_name = product_name
                db.session.add(new_product)
                db.session.flush()
                flash(f'{product_name} added', 'info')

        db.session.commit()
        return redirect(url_for('product'))

    data = get_all_items_data()
    return render_template('product.html', data=data)


@app.route('/locations', methods=['GET', 'POST'])
def location():
    if request.method == 'POST':
        warehouse_location = request.form['location_name']
        if 'location_id' in request.form:
            location_id = request.form['location_id']
            exist = Location.query.filter_by(id=location_id).first()
            old_location = exist.warehouse_location
            exist.warehouse_location = warehouse_location
            exist.updated_at = datetime.utcnow()
            from_movement_data = ProductMovement.query.filter_by(from_location=old_location).all()
            if from_movement_data:
                for from_data in from_movement_data:
                    from_data.from_location = warehouse_location

            to_movement_data = ProductMovement.query.filter_by(to_location=old_location).all()
            if to_movement_data:
                for to_data in to_movement_data:
                    to_data.to_location = warehouse_location

            flash(f'{warehouse_location} edited', 'info')
        else:
            warehouse = Location()
            warehouse.warehouse_location = warehouse_location
            db.session.add(warehouse)
            db.session.flush()
            flash(f'{warehouse_location} added', 'info')
        db.session.commit()
        return redirect(url_for('location'))

    data = get_all_location()

    return render_template('location.html', locations=data)


@app.route('/movements', methods=['GET', 'POST'])
def movement():
    if request.method == 'POST':
        allow_entry = True
        product_name = None
        product_quantity = None

        from_location = request.form['from_location']

        to_location = request.form['to_location']

        if from_location or to_location:
            if from_location == to_location:
                allow_entry = False
                flash('From and To location cannot be same', 'warning')
        else:
            flash('From and To location are not selected', 'warning')
            allow_entry = False

        if int(request.form['product_quantity']) > 0:
            product_quantity = request.form['product_quantity']
        else:
            flash('Invalid quantity', 'warning')
            allow_entry = False
        if request.form['product_name'] != 'Select product':
            product_name = request.form['product_name']
        else:
            flash('No product selected', 'warning')
            allow_entry = False

        product_details = Product.query.filter_by(product_name=product_name).first()
        if from_location == 'Select warehouse':
            pass
        else:
            total_count = get_total_count(product_name, from_location)
            if total_count == 0:
                flash('Stock for selected product is not available at selected location', 'info')
                allow_entry = False
            elif int(product_quantity) > total_count:
                flash('Quantity selected is not available', 'warning')
                allow_entry = False
        if allow_entry:
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
            flash('Product movement added', 'info')
            db.session.commit()
        return redirect(url_for('movement'))
    products, locations, movements = all_movemnent_data()

    return render_template('movements.html', products=products, locations=locations, movements=movements)


@app.route('/get_report')
def generate_report():
    big_data = index_data()
    timestamp = datetime.utcnow()
    renderer = render_template('pdf.html', summary_data=big_data)
    pdf = pdfkit.from_string(renderer, False)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=report' + str(timestamp) + '.pdf'
    return response


def index_data():
    products = Product.query.all()
    locations = Location.query.all()
    big_data = []
    for product in products:
        for location in locations:
            data = {}
            total_count = get_total_count(product, location)
            data['product_name'] = product.product_name
            data['location_name'] = location.warehouse_location
            data['available_quantity'] = total_count
            big_data.append(data)
    return big_data


def get_all_items_data():
    products = Product.query.all()
    locations = Location.query.all()
    big_data = []
    for product in products:
        inward_count = 0
        outward_count = 0
        data = {}
        for location in locations:
            inward = get_inward(product, location)
            if inward:
                for entry in inward:
                    inward_count += entry.product_qty
            outward = get_outward(product, location)
            if outward:
                for entry in outward:
                    outward_count += entry.product_qty
                print(outward)
        total_count = inward_count - outward_count
        data['id'] = product.id
        data['product_name'] = product.product_name
        data['total_quantity'] = total_count
        big_data.append(data)

    return big_data


def get_all_location():
    locations = Location.query.all()
    products = Product.query.all()
    big_data = []
    for loc in locations:
        data = {}
        prods = []
        for product in products:
            total_count = get_total_count(product, loc)
            if total_count > 0:
                prods.append(product.product_name)

        prod_list = ', '.join(prods)
        data['id'] = loc.id
        data['location_name'] = loc.warehouse_location
        data['product_list'] = prod_list
        big_data.append(data)
    return big_data


def get_total_count(product, location):
    inward_count = 0
    outward_count = 0
    inward = get_inward(product, location)
    if inward:
        for entry in inward:
            inward_count += entry.product_qty
    outward = get_outward(product, location)
    if outward:
        for entry in outward:
            outward_count += entry.product_qty
        print(outward)
    total_count = inward_count - outward_count
    return total_count


def get_inward(product, location):
    prod, loc = check_type(product, location)
    inward = ProductMovement.query.filter_by(product_name=prod.get('product_name')).filter_by(
        to_location=loc.get('warehouse_location')).all()
    return inward


def get_outward(product, location):
    prod, loc = check_type(product, location)
    outward = ProductMovement.query.filter_by(product_name=prod.get('product_name')).filter_by(
        from_location=loc.get('warehouse_location')).all()
    return outward


def check_type(product, location):
    # product location can be a string too
    if type(location) == str:
        loc = {'warehouse_location': location}
    else:
        loc = {'warehouse_location': location.warehouse_location}
    if type(product) == str:
        prod = {'product_name': product}
    else:
        prod = {'product_name': product.product_name}
    return prod, loc


def all_movemnent_data():
    products = Product.query.all()
    select_product = {'id': 0, 'product_name': 'Select product'}
    products.insert(0, select_product)
    locations = Location.query.all()
    select_warehouse = {'id': 0, 'warehouse_location': 'Select warehouse'}
    locations.insert(0, select_warehouse)
    movements = ProductMovement.query.all()
    return products, locations, movements

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
