from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from pathlib import Path
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

BASE=Path(__file__).resolve().parent
DB=BASE/"store.db"
app=Flask(__name__)
app.secret_key="CHANGE-THIS-SECRET-KEY"

PRODUCTS=[
("Royal Kanjivaram Silk Saree","Kanjivaram",4999,6499,"https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=900&q=85","Bestseller"),
("Rose Gold Banarasi Saree","Banarasi",3799,4999,"https://images.unsplash.com/photo-1610189012906-4c5f4e5d6f5b?auto=format&fit=crop&w=900&q=85","New"),
("Classic Soft Silk Saree","Soft Silk",2899,3599,"https://images.unsplash.com/photo-1583391733956-6c78276477e2?auto=format&fit=crop&w=900&q=85","Popular"),
("Handloom Cotton Saree","Cotton",1699,2199,"https://images.unsplash.com/photo-1617627143750-d86bc21e42bb?auto=format&fit=crop&w=900&q=85",""),
("Emerald Temple Silk Saree","Kanjivaram",5299,6999,"https://images.unsplash.com/photo-1610030469668-8e9f641aaf35?auto=format&fit=crop&w=900&q=85","Premium"),
("Midnight Blue Banarasi","Banarasi",4199,5499,"https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=900&q=85",""),
("Peach Organza Silk Saree","Soft Silk",3299,4299,"https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?auto=format&fit=crop&w=900&q=85","New"),
("Maroon Festive Cotton Silk","Cotton",1999,2599,"https://images.unsplash.com/photo-1605763240000-7e93b172d754?auto=format&fit=crop&w=900&q=85","")]

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c

def init_db():
    c=db()
    c.executescript("""CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT NOT NULL,
    price INTEGER NOT NULL,old_price INTEGER DEFAULT 0,image TEXT NOT NULL,tag TEXT DEFAULT '',active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,order_code TEXT UNIQUE,customer_name TEXT NOT NULL,
    phone TEXT NOT NULL,address TEXT NOT NULL,total INTEGER NOT NULL,shipping INTEGER DEFAULT 0,
    status TEXT DEFAULT 'Pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS order_items(
    id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER NOT NULL,product_id INTEGER,
    product_name TEXT NOT NULL,quantity INTEGER NOT NULL,price INTEGER NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE,password_hash TEXT NOT NULL);""")
    if c.execute("SELECT COUNT(*) FROM products").fetchone()[0]==0:
        c.executemany("INSERT INTO products(name,category,price,old_price,image,tag) VALUES(?,?,?,?,?,?)",PRODUCTS)
    if c.execute("SELECT COUNT(*) FROM admins").fetchone()[0]==0:
        c.execute("INSERT INTO admins(username,password_hash) VALUES(?,?)",("admin",generate_password_hash("admin123")))
    c.commit(); c.close()

def admin_required(f):
    @wraps(f)
    def w(*a,**k):
        return f(*a,**k) if session.get("admin_id") else redirect(url_for("admin_login"))
    return w

def products(active=True):
    c=db(); q="SELECT * FROM products"+(" WHERE active=1" if active else "")+" ORDER BY id DESC"; r=c.execute(q).fetchall(); c.close(); return r
def product(pid):
    c=db(); r=c.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone(); c.close(); return r
def cart_data():
    c=db(); items=[]; total=0; count=0
    for pid,qty in session.get("cart",{}).items():
        p=c.execute("SELECT * FROM products WHERE id=? AND active=1",(int(pid),)).fetchone()
        if p:
            sub=p["price"]*qty; items.append({"product":p,"qty":qty,"subtotal":sub}); total+=sub; count+=qty
    c.close(); return items,total,count
@app.context_processor
def ctx(): return {"cart_count":cart_data()[2]}

@app.route("/")
def home():
    p=products(); return render_template("index.html",products=p[:4],new_products=p[4:])
@app.route("/shop")
def shop():
    cat=request.args.get("category","All"); q=request.args.get("q","").lower().strip(); p=products()
    if cat!="All": p=[x for x in p if x["category"].lower()==cat.lower()]
    if q: p=[x for x in p if q in x["name"].lower() or q in x["category"].lower()]
    return render_template("shop.html",products=p,category=cat,query=q)
@app.route("/product/<int:pid>")
def product_page(pid):
    p=product(pid)
    if not p or not p["active"]: return "Product not found",404
    c=db(); rel=c.execute("SELECT * FROM products WHERE active=1 AND category=? AND id!=? LIMIT 4",(p["category"],pid)).fetchall(); c.close()
    return render_template("product.html",product=p,related=rel)
@app.post("/add-to-cart/<int:pid>")
def add(pid):
    if not product(pid): return jsonify(ok=False),404
    cart=session.get("cart",{}); k=str(pid); cart[k]=min(cart.get(k,0)+max(1,int(request.form.get("qty",1))),20); session["cart"]=cart
    if request.headers.get("X-Requested-With")=="XMLHttpRequest": return jsonify(ok=True,count=cart_data()[2])
    return redirect(request.referrer or url_for("shop"))
@app.route("/cart")
def cart(): 
    i,t,_=cart_data(); s=0 if t>=999 or t==0 else 99; return render_template("cart.html",items=i,total=t,shipping=s,grand_total=t+s)
@app.post("/update-cart")
def update():
    cart=session.get("cart",{})
    for k,v in request.form.items():
        if k.isdigit():
            n=int(v); cart.pop(k,None) if n<=0 else cart.__setitem__(k,min(n,20))
    session["cart"]=cart; return redirect(url_for("cart"))
@app.post("/remove/<int:pid>")
def remove(pid):
    cart=session.get("cart",{}); cart.pop(str(pid),None); session["cart"]=cart; return redirect(url_for("cart"))
@app.route("/checkout",methods=["GET","POST"])
def checkout():
    items,total,_=cart_data()
    if not items:return redirect(url_for("shop"))
    shipping=0 if total>=999 else 99
    if request.method=="POST":
        name=request.form.get("name","").strip(); phone=request.form.get("phone","").strip(); address=request.form.get("address","").strip()
        if not all([name,phone,address]): flash("Please complete all required fields.","error"); return redirect(url_for("checkout"))
        c=db(); cur=c.execute("INSERT INTO orders(customer_name,phone,address,total,shipping,status) VALUES(?,?,?,?,?,'Pending')",(name,phone,address,total,shipping))
        oid=cur.lastrowid; code=f"KS{oid:05d}"; c.execute("UPDATE orders SET order_code=? WHERE id=?",(code,oid))
        c.executemany("INSERT INTO order_items(order_id,product_id,product_name,quantity,price) VALUES(?,?,?,?,?)",[(oid,x["product"]["id"],x["product"]["name"],x["qty"],x["product"]["price"]) for x in items])
        c.commit(); c.close(); session["cart"]={}
        return render_template("success.html",order_id=code,name=name,grand_total=total+shipping)
    return render_template("checkout.html",items=items,total=total,shipping=shipping,grand_total=total+shipping)
@app.route("/about")
def about(): return render_template("about.html")
@app.route("/contact",methods=["GET","POST"])
def contact():
    if request.method=="POST": flash("Thank you! Your message has been received.","success"); return redirect(url_for("contact"))
    return render_template("contact.html")

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        c=db(); a=c.execute("SELECT * FROM admins WHERE username=?",(request.form.get("username",""),)).fetchone(); c.close()
        if a and check_password_hash(a["password_hash"],request.form.get("password","")):
            session["admin_id"]=a["id"]; session["admin_username"]=a["username"]; return redirect(url_for("admin_dashboard"))
        flash("Invalid username or password.","error")
    return render_template("admin/login.html")
@app.post("/admin/logout")
def admin_logout(): session.pop("admin_id",None); session.pop("admin_username",None); return redirect(url_for("admin_login"))
@app.route("/admin")
@admin_required
def admin_dashboard():
    c=db(); stats={"orders":c.execute("SELECT COUNT(*) FROM orders").fetchone()[0],"pending":c.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'").fetchone()[0],"delivered":c.execute("SELECT COUNT(*) FROM orders WHERE status='Delivered'").fetchone()[0],"sales":c.execute("SELECT COALESCE(SUM(total+shipping),0) FROM orders WHERE status!='Cancelled'").fetchone()[0],"products":c.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]}; recent=c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 8").fetchall(); c.close()
    return render_template("admin/dashboard.html",stats=stats,recent=recent)
@app.route("/admin/orders")
@admin_required
def admin_orders():
    s=request.args.get("status","All"); c=db(); orders=c.execute("SELECT * FROM orders "+("" if s=="All" else "WHERE status=? ")+"ORDER BY id DESC",(() if s=="All" else (s,))).fetchall(); c.close(); return render_template("admin/orders.html",orders=orders,status=s)
@app.route("/admin/orders/<int:oid>")
@admin_required
def admin_order_detail(oid):
    c=db(); o=c.execute("SELECT * FROM orders WHERE id=?",(oid,)).fetchone(); items=c.execute("SELECT * FROM order_items WHERE order_id=?",(oid,)).fetchall(); c.close()
    if not o:return "Order not found",404
    return render_template("admin/order_detail.html",order=o,items=items)
@app.post("/admin/orders/<int:oid>/status")
@admin_required
def order_status(oid):
    s=request.form.get("status"); allowed={"Pending","Confirmed","Shipped","Delivered","Cancelled"}
    if s in allowed:
        c=db(); c.execute("UPDATE orders SET status=? WHERE id=?",(s,oid)); c.commit(); c.close(); flash("Order status updated.","success")
    return redirect(url_for("admin_order_detail",oid=oid))
@app.route("/admin/products")
@admin_required
def admin_products(): return render_template("admin/products.html",products=products(False))
@app.route("/admin/products/new",methods=["GET","POST"])
@admin_required
def new_product():
    if request.method=="POST":
        d=[request.form.get(x,"").strip() for x in ["name","category","image","tag"]]; price=int(request.form.get("price",0)); old=int(request.form.get("old_price",0))
        if not d[0] or not d[1] or not d[2] or price<=0: flash("Fill the required fields.","error"); return render_template("admin/product_form.html",product=None)
        c=db(); c.execute("INSERT INTO products(name,category,price,old_price,image,tag) VALUES(?,?,?,?,?,?)",(d[0],d[1],price,old,d[2],d[3])); c.commit(); c.close(); return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html",product=None)
@app.route("/admin/products/<int:pid>/edit",methods=["GET","POST"])
@admin_required
def edit_product(pid):
    p=product(pid)
    if not p:return "Product not found",404
    if request.method=="POST":
        name=request.form["name"].strip(); cat=request.form["category"].strip(); price=int(request.form["price"]); old=int(request.form.get("old_price",0)); image=request.form["image"].strip(); tag=request.form.get("tag","").strip(); active=1 if request.form.get("active") else 0
        c=db(); c.execute("UPDATE products SET name=?,category=?,price=?,old_price=?,image=?,tag=?,active=? WHERE id=?",(name,cat,price,old,image,tag,active,pid)); c.commit(); c.close(); return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html",product=p)
@app.post("/admin/products/<int:pid>/delete")
@admin_required
def delete_product(pid):
    c=db(); c.execute("UPDATE products SET active=0 WHERE id=?",(pid,)); c.commit(); c.close(); return redirect(url_for("admin_products"))

if __name__=="__main__":
    init_db(); app.run(debug=True,host="127.0.0.1",port=5000)
