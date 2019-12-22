from flask import Flask, render_template, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'

db = SQLAlchemy(app)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(50), nullable=False)
    product_qty = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return 'Added Product ' + self.product_name


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    warehouse_location = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return 'Added Location ' + self.warehouse_location


class ProductMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    from_location = db.Column(db.String(100))
    to_location = db.Column(db.String(100))
    product_id = db.Column(db.Integer, nullable=False)
    product_qty = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return 'Added Movement ' + str(self.id)


@app.route('/')
def index():
    product_movement_data = ProductMovement.query.group_by(ProductMovement.product_id).all()
    if product_movement_data:
        for data in product_movement_data:
            product = Product.query.filter_by(Product.id == data.product_id)

    return render_template('index.html')


@app.route('/products', methods=['GET', 'POST'])
def product():

    if request.method == 'POST':

        product_name = request.form['product_name']
        product_quantity = request.form['product_quantity']
        if 'product_id' in request.form:
            product_id = request.form['product_id']
            exist = Product.query.filter_by(id=product_id).first()
            exist.product_name = product_name
            exist.product_qty = product_quantity
            db.session.commit()
        else:
            new_product = Product()
            new_product.product_name = product_name
            new_product.product_qty = product_quantity
            db.session.add(new_product)
            db.session.flush()
            db.session.commit()
            return redirect(url_for('product'))

    products = Product.query.all()
    return render_template('product.html', products=products)


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
    print(locations)
    return render_template('location.html', locations=locations)


@app.route('/movements')
def movement():
    return render_template('movements.html')


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
