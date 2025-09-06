# EcoFinds – Sustainable Second-Hand Marketplace (Prototype)

A Flask-based prototype covering:
- User registration/login
- Profile (username) editing
- Product listing CRUD (title, description, category, price, image URL/placeholder)
- Browse listings with keyword search (title) & category filter
- Product detail
- Cart (add/update/remove) & checkout
- Previous purchases history

## Quickstart

```bash
python -m venv .venv
. .venv/Scripts/activate    # Windows
# or: source .venv/bin/activate

pip install -r requirements.txt
flask --app app.py run  # first run to create instance folder
flask --app app.py init-db  # seed demo data
flask --app app.py run
