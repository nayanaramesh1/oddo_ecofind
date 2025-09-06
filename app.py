import os
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    current_user, logout_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------
# App & DB setup
# -------------------------
app = Flask(__name__, instance_relative_config=True, static_url_path="/static", static_folder="static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-please-change")
os.makedirs(app.instance_path, exist_ok=True)
db_path = os.path.join(app.instance_path, "ecofinds.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# -------------------------
# Constants
# -------------------------
CATEGORIES = [
    "Clothing", "Electronics", "Home & Kitchen", "Books",
    "Furniture", "Sports", "Toys", "Other"
]
PLACEHOLDER_IMG = "https://placehold.co/600x400?text=EcoFinds"

# -------------------------
# Models
# -------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(80), nullable=False)

    products = db.relationship("Product", backref="seller", lazy=True)
    cart_items = db.relationship("CartItem", backref="owner", lazy=True)
    orders = db.relationship("Order", backref="buyer", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def image(self):
        return self.image_url.strip() if self.image_url else PLACEHOLDER_IMG


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)

    product = db.relationship("Product")


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    items = db.relationship("OrderItem", backref="order", lazy=True)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_title = db.Column(db.String(140), nullable=False)
    product_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    product_category = db.Column(db.String(50), nullable=False)
    product_image_url = db.Column(db.String(500), nullable=True)

# -------------------------
# Auth helpers
# -------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    q = request.args.get("q", "", type=str).strip()
    cat = request.args.get("category", "", type=str).strip()

    query = Product.query.order_by(Product.created_at.desc())
    if q:
        query = query.filter(Product.title.ilike(f"%{q}%"))
    if cat and cat in CATEGORIES:
        query = query.filter_by(category=cat)

    products = query.all()
    return render_template("index.html", products=products, q=q, category=cat, categories=CATEGORIES)

# ---- Auth ----
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        username = request.form.get("username", "").strip()

        if not email or not password or not username:
            flash("Please fill all fields.", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for("register"))

        user = User(email=email, username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome to EcoFinds!", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid credentials.", "error")
            return redirect(url_for("login"))
        login_user(user)
        flash("Logged in successfully.", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

# ---- Profile & Dashboard ----
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if username:
            current_user.username = username
            db.session.commit()
            flash("Profile updated.", "success")
        else:
            flash("Username cannot be empty.", "error")
        return redirect(url_for("dashboard"))

    my_products = Product.query.filter_by(seller_id=current_user.id).order_by(Product.created_at.desc()).all()
    return render_template("dashboard.html", my_products=my_products)

# ---- Product CRUD ----
@app.route("/products/new", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        price = request.form.get("price", "").strip()
        image_url = request.form.get("image_url", "").strip()

        if not title or not description or category not in CATEGORIES or not price:
            flash("Please complete all fields correctly.", "error")
            return redirect(url_for("add_product"))

        try:
            price = float(price)
        except ValueError:
            flash("Price must be a number.", "error")
            return redirect(url_for("add_product"))

        product = Product(
            title=title,
            description=description,
            category=category,
            price=price,
            image_url=image_url or PLACEHOLDER_IMG,
            seller_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash("Product added.", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_product.html", categories=CATEGORIES)


@app.route("/products/<int:pid>")
def product_detail(pid):
    product = Product.query.get_or_404(pid)
    return render_template("product_detail.html", product=product)


@app.route("/products/<int:pid>/edit", methods=["POST"])
@login_required
def edit_product(pid):
    product = Product.query.get_or_404(pid)
    if product.seller_id != current_user.id:
        flash("Not authorized.", "error")
        return redirect(url_for("dashboard"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip()
    price = request.form.get("price", "").strip()
    image_url = request.form.get("image_url", "").strip()

    if not title or not description or category not in CATEGORIES or not price:
        flash("Please complete all fields correctly.", "error")
        return redirect(url_for("dashboard"))

    try:
        product.price = float(price)
    except ValueError:
        flash("Price must be a number.", "error")
        return redirect(url_for("dashboard"))

    product.title = title
    product.description = description
    product.category = category
    product.image_url = image_url or PLACEHOLDER_IMG
    db.session.commit()
    flash("Product updated.", "success")
    return redirect(url_for("dashboard"))


@app.route("/products/<int:pid>/delete", methods=["POST"])
@login_required
def delete_product(pid):
    product = Product.query.get_or_404(pid)
    if product.seller_id != current_user.id:
        flash("Not authorized.", "error")
        return redirect(url_for("dashboard"))
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "info")
    return redirect(url_for("dashboard"))

# ---- Cart ----
@app.route("/cart")
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(i.product.price * i.quantity for i in items)
    return render_template("cart.html", items=items, subtotal=subtotal)


@app.route("/cart/add/<int:pid>", methods=["POST"])
@login_required
def cart_add(pid):
    product = Product.query.get_or_404(pid)
    existing = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    qty = int(request.form.get("quantity", 1))
    if existing:
        existing.quantity += max(1, qty)
    else:
        db.session.add(CartItem(user_id=current_user.id, product_id=product.id, quantity=max(1, qty)))
    db.session.commit()
    flash("Added to cart.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
def cart_update(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash("Not authorized.", "error")
        return redirect(url_for("cart"))
    qty = int(request.form.get("quantity", 1))
    item.quantity = max(1, qty)
    db.session.commit()
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def cart_remove(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash("Not authorized.", "error")
        return redirect(url_for("cart"))
    db.session.delete(item)
    db.session.commit()
    flash("Item removed.", "info")
    return redirect(url_for("cart"))


@app.route("/cart/checkout", methods=["POST"])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart"))

    order = Order(user_id=current_user.id)
    total = 0.0
    db.session.add(order)
    db.session.flush()  # get order.id

    for item in items:
        total += item.product.price * item.quantity
        oi = OrderItem(
            order_id=order.id,
            product_title=item.product.title,
            product_price=item.product.price,
            quantity=item.quantity,
            product_category=item.product.category,
            product_image_url=item.product.image()
        )
        db.session.add(oi)
        db.session.delete(item)  # clear cart

    order.total_amount = total
    db.session.commit()
    flash("Purchase complete!", "success")
    return redirect(url_for("purchases"))

# ---- Previous Purchases ----
@app.route("/purchases")
@login_required
def purchases():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("purchases.html", orders=orders)

# -------------------------
# CLI helper: init DB with sample data
# -------------------------
@app.cli.command("init-db")
def init_db():
    """Initialize database tables and add sample data."""
    db.create_all()
    if not User.query.filter_by(email="demo@ecofinds.app").first():
        demo = User(email="demo@ecofinds.app", username="demo")
        demo.set_password("demo123")
        db.session.add(demo)
        db.session.commit()

    if Product.query.count() == 0:
        demo = User.query.filter_by(email="demo@ecofinds.app").first()
        samples = [
            ("Vintage Denim Jacket", "Classic blue denim jacket in great condition.", "Clothing", 29.99, ""),
            ("Kindle Paperwhite", "2019 model, works perfectly.", "Electronics", 65.0, ""),
            ("IKEA Lamp", "Minimal bedside lamp.", "Home & Kitchen", 12.5, ""),
            ("Dumbbell Set", "Pair of 10lb dumbbells.", "Sports", 25.0, ""),
        ]
        for t, d, c, p, img in samples:
            db.session.add(Product(
                title=t, description=d, category=c, price=p,
                image_url=img or PLACEHOLDER_IMG, seller_id=demo.id
            ))
        db.session.commit()
    print("Database initialized with sample data.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
