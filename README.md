# 🌿 EcoFinds – Sustainable Second-Hand Marketplace (Prototype)

EcoFinds is a **Flask-based prototype** of a sustainable second-hand marketplace where users can buy and sell pre-loved items.  
The project demonstrates key features of a full-fledged marketplace, focusing on **user authentication, product listings, and cart/checkout flow**.

---

## ✨ Features

- 👤 **User Management**
  - User registration & login  
  - Edit profile (username)

- 🛍️ **Product Listings**
  - Create, Read, Update, Delete (CRUD) items  
  - Each listing includes: title, description, category, price, image (URL or placeholder)

- 🔎 **Browse & Search**
  - Keyword search (title-based)  
  - Category filtering  
  - Product detail view

- 🛒 **Cart & Orders**
  - Add items to cart, update quantity, or remove  
  - Checkout process  
  - View purchase history

---

## 🚀 Quickstart

```bash
python -m venv .venv
. .venv/Scripts/activate    # Windows
# or: source .venv/bin/activate  #macOS

pip install -r requirements.txt
flask --app app.py run  # first run to create instance folder
flask --app app.py init-db  # seed demo data
flask --app app.py run
