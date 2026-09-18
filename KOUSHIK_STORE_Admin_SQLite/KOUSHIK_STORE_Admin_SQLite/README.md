# KOUSHIK STORE

Run:
`py -m venv .venv`
`.venv\\Scripts\\activate`
`py -m pip install -r requirements.txt`
`py app.py`

Store: http://127.0.0.1:5000
Admin: http://127.0.0.1:5000/admin/login

Default admin: **admin** / **admin123**

Orders are stored in SQLite (`store.db`) when customers place checkout orders. Admin can view orders, customer contact/address, products and update status: Pending, Confirmed, Shipped, Delivered, Cancelled. Products can be added/edited/hidden.

Before production: change `app.secret_key`, change the admin password, use HTTPS, add real payment processing, and replace demo image URLs with your licensed product images.
