from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, IntegerField, BooleanField, SelectField, FileField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, Optional
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flowershop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите'

# ------------------------- МОДЕЛИ -------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    price = db.Column(db.Float, nullable=False)
    old_price = db.Column(db.Float)
    description = db.Column(db.Text)
    image_filename = db.Column(db.String(200), default='default.jpg')
    stock = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_hit = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=4.8)
    rating_count = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.relationship('Category', backref='products')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='новый')
    total_price = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    comment = db.Column(db.Text)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    user = db.relationship('User', backref='orders')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, nullable=False)
    price_at_time = db.Column(db.Float, nullable=False)
    order = db.relationship('Order', backref='items')
    product = db.relationship('Product')

# ------------------------- ФОРМЫ -------------------------
class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class ProductForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    category_id = SelectField('Категория', coerce=int, validators=[DataRequired()])
    price = FloatField('Цена', validators=[DataRequired(), NumberRange(min=0)])
    old_price = FloatField('Старая цена', validators=[Optional()])
    description = TextAreaField('Описание')
    stock = IntegerField('Количество', default=0)
    is_active = BooleanField('Активно')
    is_hit = BooleanField('Хит продаж')
    rating = FloatField('Рейтинг (0-5)', default=4.8, validators=[NumberRange(min=0, max=5)])
    rating_count = IntegerField('Кол-во оценок', default=100)
    image = FileField('Фото')
    submit = SubmitField('Сохранить')

class CategoryForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    description = StringField('Описание')
    submit = SubmitField('Добавить')

class CheckoutForm(FlaskForm):
    customer_name = StringField('Ваше имя', validators=[DataRequired()])
    customer_phone = StringField('Телефон', validators=[DataRequired()])
    delivery_address = TextAreaField('Адрес доставки', validators=[DataRequired()])
    comment = TextAreaField('Комментарий')
    submit = SubmitField('Оформить заказ')

# ------------------------- ЗАГРУЗЧИК ПОЛЬЗОВАТЕЛЯ -------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------------- МАРШРУТЫ -------------------------
@app.route('/')
def index():
    hits = Product.query.filter_by(is_active=True, is_hit=True).limit(8).all()
    new_products = Product.query.filter_by(is_active=True).order_by(Product.created_at.desc()).limit(8).all()
    categories = Category.query.all()
    return render_template('index.html', hits=hits, new_products=new_products, categories=categories)

@app.route('/catalog/')
def catalog():
    cat_id = request.args.get('category', type=int)
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'new')
    query = Product.query.filter_by(is_active=True)
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    if search:
        query = query.filter(Product.name.contains(search) | Product.description.contains(search))
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort == 'rating':
        query = query.order_by(Product.rating.desc())
    elif sort == 'hit':
        query = query.order_by(Product.is_hit.desc(), Product.created_at.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    products = query.all()
    categories = Category.query.all()
    return render_template('catalog.html', products=products, categories=categories, selected=cat_id, search=search, sort=sort)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/delivery')
def delivery():
    return render_template('delivery.html')

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('product_detail.html', product=product)

# Корзина (сессии)
def get_cart():
    return session.get('cart', {})

def save_cart(cart):
    session['cart'] = cart

@app.route('/cart/add/<int:id>')
def add_to_cart(id):
    cart = get_cart()
    cart[str(id)] = cart.get(str(id), 0) + 1
    save_cart(cart)
    flash('Товар добавлен в корзину', 'success')
    return redirect(request.referrer or url_for('catalog'))

@app.route('/cart/')
def cart_view():
    cart = get_cart()
    items = []
    total = 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product:
            subtotal = product.price * qty
            total += subtotal
            items.append((product, qty, subtotal))
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/update/<int:id>/<int:qty>')
def update_cart(id, qty):
    cart = get_cart()
    if qty <= 0:
        cart.pop(str(id), None)
    else:
        cart[str(id)] = qty
    save_cart(cart)
    return redirect(url_for('cart_view'))

@app.route('/cart/remove/<int:id>')
def remove_from_cart(id):
    cart = get_cart()
    cart.pop(str(id), None)
    save_cart(cart)
    flash('Товар удалён', 'info')
    return redirect(url_for('cart_view'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = get_cart()
    if not cart:
        flash('Корзина пуста', 'warning')
        return redirect(url_for('catalog'))
    items = []
    total = 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product:
            subtotal = product.price * qty
            total += subtotal
            items.append((product, qty, subtotal))
    form = CheckoutForm()
    if form.validate_on_submit():
        order = Order(
            user_id=current_user.id if current_user.is_authenticated else None,
            total_price=total,
            delivery_address=form.delivery_address.data,
            comment=form.comment.data,
            customer_name=form.customer_name.data,
            customer_phone=form.customer_phone.data,
            status='новый'
        )
        db.session.add(order)
        db.session.flush()
        for product, qty, _ in items:
            order_item = OrderItem(order_id=order.id, product_id=product.id, quantity=qty, price_at_time=product.price)
            db.session.add(order_item)
            product.stock -= qty
        db.session.commit()
        session.pop('cart', None)
        flash(f'Заказ №{order.id} оформлен! Мы свяжемся с вами.', 'success')
        return redirect(url_for('index'))
    return render_template('checkout.html', form=form, items=items, total=total)

# Регистрация / вход
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed = generate_password_hash(form.password.data)
        fake_email = f"{form.username.data}@temp.com"
        user = User(username=form.username.data, email=fake_email, password_hash=hashed)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна! Теперь войдите.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из аккаунта', 'info')
    return redirect(url_for('index'))

# ------------------------- АДМИН-ПАНЕЛЬ -------------------------
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin/')
@login_required
@admin_required
def admin_dashboard():
    products = Product.query.all()
    categories = Category.query.all()
    return render_template('admin/dashboard.html', products=products, categories=categories)

@app.route('/admin/product/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_product():
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        filename = 'default.jpg'
        if form.image.data:
            f = form.image.data
            filename = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        product = Product(
            name=form.name.data,
            category_id=form.category_id.data,
            price=form.price.data,
            old_price=form.old_price.data,
            description=form.description.data,
            stock=form.stock.data,
            is_active=form.is_active.data,
            is_hit=form.is_hit.data,
            rating=form.rating.data,
            rating_count=int(form.rating_count.data),
            image_filename=filename
        )
        db.session.add(product)
        db.session.commit()
        flash('Товар добавлен', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/product_form.html', form=form, title='Добавить товар')

@app.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        product.name = form.name.data
        product.category_id = form.category_id.data
        product.price = form.price.data
        product.old_price = form.old_price.data
        product.description = form.description.data
        product.stock = form.stock.data
        product.is_active = form.is_active.data
        product.is_hit = form.is_hit.data
        product.rating = form.rating.data
        product.rating_count = int(form.rating_count.data)
        if form.image.data:
            f = form.image.data
            filename = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.image_filename = filename
        db.session.commit()
        flash('Товар обновлён', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/product_form.html', form=form, title='Редактировать товар')

@app.route('/admin/product/delete/<int:id>')
@login_required
@admin_required
def admin_delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Товар удалён', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/category/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        cat = Category(name=form.name.data, description=form.description.data)
        db.session.add(cat)
        db.session.commit()
        flash('Категория добавлена', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/category_form.html', form=form)

@app.route('/admin/category/delete/<int:id>')
@login_required
@admin_required
def admin_delete_category(id):
    cat = Category.query.get_or_404(id)
    db.session.delete(cat)
    db.session.commit()
    flash('Категория удалена', 'success')
    return redirect(url_for('admin_dashboard'))

# ------------------------- ЗАПУСК -------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role='admin').first():
            admin = User(username='admin', email='admin@admin.com', password_hash=generate_password_hash('admin123'), role='admin')
            db.session.add(admin)
            db.session.commit()
            print('✅ Админ создан: admin / admin123')
    app.run(debug=True)
