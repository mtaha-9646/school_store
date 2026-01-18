import os
import io
import csv
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for, flash, make_response, send_file
from flask_socketio import SocketIO, join_room, emit
from sqlalchemy import or_

from config import Config
from models import db, User, Teacher, Item, Issue, InventoryLog, Department

# Services
from services.inventory import adjust_stock
from services.issues import process_issue
from services.reports import get_stats
from services.barcodes import get_barcode_path, generate_barcode_value
from services.pairing import create_pairing_code, active_pairings

from api_deploy import deploy_bp

app = Flask(__name__)
app.config.from_object(Config)

app.register_blueprint(deploy_bp)

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Startup ---
with app.app_context():
    os.makedirs(os.path.join(app.instance_path, 'signatures'), exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, 'barcodes'), exist_ok=True)
    db.create_all()
    
    # Seeds
    if not User.query.first():
        db.session.add(User(name="Admin", role="admin"))
        
        # Depts
        math = Department(name="Math")
        sci = Department(name="Science")
        eng = Department(name="English")
        db.session.add_all([math, sci, eng])
        db.session.commit() # Commit to get IDs
        
        # Teachers
        db.session.add_all([
            Teacher(name="Mr. Anderson", department_id=math.id),
            Teacher(name="Ms. Frizzle", department_id=sci.id),
            Teacher(name="Mr. Keating", department_id=eng.id)
        ])
        
        # Items
        db.session.add_all([
            Item(name="Whiteboard Marker (Red)", sku="WBM-R", stock_on_hand=50, barcode="SS-100001"),
            Item(name="A4 Paper Ream", sku="PPR-A4", stock_on_hand=100, barcode="SS-100002"),
            Item(name="Stapler", sku="STP-01", stock_on_hand=10, barcode="SS-100003")
        ])
        db.session.commit()
        print("Seeds Created")

# --- Context ---
@app.context_processor
def inject_user():
    # MVP Mock User
    if 'user_id' not in session:
        u = User.query.first()
        if u: session['user_id'] = u.id
    return dict()

# --- Routes ---

@app.route('/')
def dashboard():
    stats = get_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/checkout')
def checkout():
    # Generate a random pairing code for this session/tab
    code = create_pairing_code()
    return render_template('checkout.html', pairing_code=code)

@app.route('/checkout/complete', methods=['POST'])
def checkout_complete():
    cart = session.get('cart', {})
    teacher_id = request.form.get('teacher_id')
    sig_data = request.form.get('signature_data')
    
    try:
        process_issue(
            user_id=session.get('user_id'),
            teacher_id=teacher_id,
            cart_items=cart,
            signature_data=sig_data,
            instance_path=app.instance_path
        )
        session.pop('cart', None)
        flash("Items issued successfully", "success")
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for('checkout'))

@app.route('/scan')
def scan_page():
    code = request.args.get('code')
    return render_template('scan_status.html', code=code)

@app.route('/scan/redirect')
def scan_redirect():
    # From QR code? 
    # Logic: QR code is /scan?code=1234
    pass

@app.route('/restock', methods=['GET', 'POST'])
def restock():
    if request.method == 'POST':
        # Simple restock implementation
        try:
            item_id = request.form.get('item_id')
            qty = int(request.form.get('qty', 0))
            if qty > 0:
                adjust_stock(item_id, qty, "RESTOCK", note="Manual", user_id=session.get('user_id'))
                db.session.commit()
                flash("Stock added", "success")
        except Exception as e:
            flash(str(e), "danger")
    return render_template('restock.html') # Using similar structure to prev

@app.route('/inventory')
def inventory():
    items = Item.query.all()
    return render_template('inventory.html', items=items)

@app.route('/items/<int:item_id>')
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)

@app.route('/items/<int:item_id>/barcode.png')
def get_barcode_image(item_id):
    item = Item.query.get_or_404(item_id)
    if not item.barcode:
        item.barcode = generate_barcode_value()
        db.session.commit()
    
    path = get_barcode_path(item.barcode, app.instance_path)
    return send_file(path, mimetype='image/png')

@app.route('/labels', methods=['GET', 'POST'])
def labels():
    preview_items = []
    if request.method == 'POST':
        item_ids = request.form.getlist('item_ids')
        preview_items = Item.query.filter(Item.id.in_(item_ids)).all()
    
    items = Item.query.filter_by(active=True).all()
    return render_template('labels.html', kems=items, labels=preview_items, items=items)

@app.route('/teachers')
def teachers():
    ts = Teacher.query.all()
    ds = Department.query.all()
    return render_template('teachers.html', teachers=ts, departments=ds)

@app.route('/departments')
def departments():
    ds = Department.query.all()
    return render_template('departments.html', departments=ds)

@app.route('/reports')
def reports():
    return render_template('reports.html')

# --- HTMX ---

@app.route('/hx/items/search')
def hx_item_search():
    q = request.args.get('q', '').strip()
    if not q: return ''
    
    # Exact barcode match?
    exact = Item.query.filter_by(barcode=q).first()
    if exact: # Add directly if scanned? For now just show result top
        items = [exact]
    else:
        items = Item.query.filter(
            or_(Item.name.ilike(f'%{q}%'), Item.sku.ilike(f'%{q}%'))
        ).limit(10).all()
        
    return render_template('hx/item_search.html', items=items)

@app.route('/hx/teachers/search')
def hx_teacher_search():
    q = request.args.get('q', '').strip()
    if len(q) < 2: return ''
    teachers = Teacher.query.filter(Teacher.name.ilike(f'%{q}%')).limit(10).all()
    return render_template('hx/teacher_search.html', teachers=teachers)

@app.route('/hx/cart/view')
def hx_cart_view():
    cart = session.get('cart', {})
    cart_items = []
    if cart:
        items = Item.query.filter(Item.id.in_(cart.keys())).all()
        for i in items:
            i.qty = cart[str(i.id)]
            cart_items.append(i)
    return render_template('hx/cart.html', cart_items=cart_items)

@app.route('/hx/cart/add', methods=['POST'])
def hx_cart_add():
    item_id = str(request.form.get('item_id'))
    qty = int(request.form.get('qty', 1))
    cart = session.get('cart', {})
    cart[item_id] = cart.get(item_id, 0) + qty
    session['cart'] = cart
    resp = make_response("Added")
    resp.headers['HX-Trigger'] = 'cartUpdated'
    return resp

@app.route('/hx/cart/update', methods=['POST'])
def hx_cart_update():
    item_id = str(request.form.get('item_id'))
    qty = int(request.form.get('qty', 1))
    cart = session.get('cart', {})
    if qty > 0:
        cart[item_id] = qty
    else:
        cart.pop(item_id, None)
    session['cart'] = cart
    return redirect(url_for('hx_cart_view'))

@app.route('/hx/cart/remove', methods=['POST'])
def hx_cart_remove():
    item_id = str(request.form.get('item_id'))
    cart = session.get('cart', {})
    cart.pop(item_id, None)
    session['cart'] = cart
    return redirect(url_for('hx_cart_view'))

@app.route('/hx/scan/pull')
def hx_scan_pull():
    """Fallback polling if socketio fails or for connection status check"""
    # code = request.args.get('code')
    # Actually just used to verify connection visually
    return '' 

# --- Websockets ---

@socketio.on('join_pairing')
def on_join(code):
    join_room(code)
    # Store mapping
    # active_pairings[code] = request.sid
    pass

@socketio.on('barcode_scanned')
def on_scan(data):
    code = data.get('code')
    barcode = data.get('barcode')
    print(f"Received scan {barcode} for {code}")
    # Broadcast to room (the laptop)
    emit('barcode_to_laptop', {'barcode': barcode}, room=code)

if __name__ == '__main__':
    import socket
    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    host_ip = get_ip()
    print(f"\n\n === MOBILE CONNECT: http://{host_ip}:5000 === \n\n")
    
    # Use socketio.run instead of app.run
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
