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
# PythonAnywhere does not support WebSockets; force threading/polling fallback
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- Startup ---
with app.app_context():
    os.makedirs(os.path.join(app.instance_path, 'signatures'), exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, 'barcodes'), exist_ok=True)
    
    # Skip DB init/seeding if testing (let tests handle it)
    if not os.environ.get('FLASK_TESTING'):
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
            # print("Seeds Created")

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
    # Make sure we pass items/teachers for the new UI
    items = Item.query.filter_by(active=True).all()
    teachers = Teacher.query.filter_by(active=True).all()
    
    # Generate a random pairing code for this session/tab
    code = create_pairing_code()
    return render_template('checkout.html', pairing_code=code, items=items, teachers=teachers)

@app.route('/checkout/complete', methods=['POST'])
def checkout_complete():
    cart = session.get('cart', {})
    teacher_id = request.form.get('teacher_id')
    
    # If using client-side cart (if we move to it), we'd parse it here.
    # But for now sticking to session cart for compatibility with existing logic
    # OR we might receive a JSON cart if we change the flow. 
    # Let's keep using session cart for now which is populated via HTMX.
    
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
    teachers = Teacher.query.filter_by(active=True).all()
    # Pass teachers to mobile view
    return render_template('scan_status.html', code=code, teachers=teachers)

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
            
    items = Item.query.all()
    return render_template('restock.html', items=items)

@app.route('/inventory')
def inventory():
    items = Item.query.all()
    return render_template('inventory.html', items=items)

@app.route('/items/<int:item_id>')
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)

# ... (Previous imports remain, ensuring random/string are imported if needed)
import random
import string

# Helper
def generate_sku():
    """Generates a unique SKU: SKU-YYYYMMDD-XXXX"""
    date_str = datetime.now().strftime("%Y%m%d")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"SKU-{date_str}-{suffix}"

@app.route('/items/new', methods=['GET', 'POST'])
def item_new():
    if request.method == 'POST':
        try:
            name = request.form['name']
            stock = int(request.form.get('stock_on_hand', 0))
            
            # SKU Logic
            sku = request.form.get('sku', '').strip()
            if not sku:
                sku = generate_sku()
                
            barcode_val = request.form.get('barcode', '').strip() or None
            
            # Auto-generate if empty
            if not barcode_val:
                barcode_val = generate_barcode_value()
                
            # Init with 0, then adjust to create log
            item = Item(name=name, sku=sku, stock_on_hand=0, barcode=barcode_val)
            db.session.add(item)
            db.session.commit()
            
            # Log initial stock
            if stock > 0:
                adjust_stock(item.id, stock, "ADJUST", note="Initial Stock", user_id=session.get('user_id'))
                db.session.commit()
                
            flash(f"Item '{name}' created. SKU: {sku}", "success")
            return redirect(url_for('inventory'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating item: {str(e)}", "danger")
            
    return render_template('item_new.html')

@app.route('/items/<int:item_id>/barcode.png')
def get_barcode_image(item_id):
    item = Item.query.get_or_404(item_id)
    
    # Ensure folder exists (PythonAnywhere filesystem safety)
    os.makedirs(os.path.join(app.instance_path, 'barcodes'), exist_ok=True)
    
    if not item.barcode:
        item.barcode = generate_barcode_value()
        db.session.commit()
    
    try:
        path = get_barcode_path(item.barcode, app.instance_path)
        return send_file(path, mimetype='image/png')
    except Exception as e:
        return f"Error creating barcode: {e}", 500

@app.route('/labels', methods=['GET', 'POST'])
def labels():
    preview_items = []
    if request.method == 'POST':
        item_ids = request.form.getlist('item_ids')
        preview_items = Item.query.filter(Item.id.in_(item_ids)).all()
    
    items = Item.query.filter_by(active=True).all()
    return render_template('labels.html', kems=items, labels=preview_items, items=items)

@app.route('/teachers', methods=['GET', 'POST'])
def teachers():
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form.get('email')
            dept_id = request.form.get('department_id')
            
            t = Teacher(name=name, email=email, department_id=dept_id)
            db.session.add(t)
            db.session.commit()
            flash(f"Teacher '{name}' added.", "success")
        except Exception as e:
            flash(f"Error adding teacher: {e}", "danger")
        return redirect(url_for('teachers'))

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
    # emit('status', {'msg': 'Connected'}, room=code)

@socketio.on('get_item_details')
def on_get_item(data):
    # Mobile scans barcode, wants details to show "Add Qty" screen
    code = data.get('code')
    barcode = data.get('barcode')
    item = Item.query.filter_by(barcode=barcode).first()
    if item:
        emit('item_details', {
            'found': True,
            'id': item.id,
            'name': item.name,
            'stock': item.stock_on_hand
        }, room=code) # Reply to room (or just request.sid but room is fine)
    else:
        emit('item_details', {'found': False}, room=code)

@socketio.on('mobile_add_item')
def on_mobile_add(data):
    # Mobile said "Add 5x Item A"
    # We relay this to the Desktop to perform the Session update
    code = data.get('code')
    emit('trigger_add_to_cart', data, room=code)

@socketio.on('mobile_approve_tx')
def on_mobile_approve(data):
    code = data.get('code')
    sig = data.get('signature')
    tid = data.get('teacher_id')
    print(f"Mobile approved tx for {code} teacher={tid}")
    # Tell Desktop to submit the form, pass the signature AND teacher
    emit('trigger_checkout_submission', {'signature': sig, 'teacher_id': tid}, room=code)

if __name__ == '__main__':
    # ... (Keep existing startup)
    import socket
    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
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

