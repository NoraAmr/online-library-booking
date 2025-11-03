from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Book, Booking
from forms import RegisterForm, LoginForm, BookForm, ImportForm
import json
from datetime import datetime

bp = Blueprint('main', __name__)

# --- Home / Catalog ---
@bp.route('/')
@login_required

def index():
    q = request.args.get('q', '', type=str)
    category = request.args.get('category', '', type=str)
    sort = request.args.get('sort', 'title', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 9

    query = Book.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Book.title.ilike(like),
                Book.author.ilike(like),
                Book.category.ilike(like)
            )
        )
    if category:
        query = query.filter_by(category=category)

    if sort == 'author':
        query = query.order_by(Book.author)
    elif sort == 'available':
        query = query.order_by(Book.available_copies.desc())
    else:
        query = query.order_by(Book.title)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    books = pagination.items

    # trending: top 5 by booking count
    popular = db.session.query(Book, db.func.count(Booking.id).label('cnt')) \
        .join(Booking, Booking.book_id == Book.id, isouter=True) \
        .group_by(Book.id).order_by(db.text('cnt DESC')).limit(5).all()
    trending = [p[0] for p in popular]
    categories = [c[0] for c in db.session.query(Book.category).distinct().all()]

    return render_template('index.html', books=books, pagination=pagination,
                           q=q, category=category, sort=sort, categories=categories,
                           trending=trending)

# --- Register / Login / Logout ---
@bp.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.')
            return redirect(url_for('main.register'))
        user = User(
            name=form.name.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        flash('Registered. Please login.')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

@bp.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('main.index'))
        flash('Invalid email or password.')
    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# --- Book detail & booking ---
@bp.route('/book/<int:book_id>', methods=['GET', 'POST'])
@login_required
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    if request.method == 'POST':
        if book.available_copies and book.available_copies > 0:
            booking = Booking(user_id=current_user.id, book_id=book.id)
            book.available_copies -= 1
            db.session.add(booking)
            db.session.commit()
            flash('Book reserved successfully!')
            return redirect(url_for('main.my_bookings'))
        else:
            flash('No copies available.')
    return render_template('book_detail.html', book=book)

# --- My bookings (with details) ---
@bp.route('/my_bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()
    data = []
    for b in bookings:
        book = Book.query.get(b.book_id)
        data.append({
            'id': b.id,
            'title': book.title if book else 'Unknown',
            'author': book.author if book else '',
            'category': book.category if book else '',
            'date': b.booking_date.strftime('%Y-%m-%d'),
            'status': b.status
        })
    return render_template('my_bookings.html', bookings=data)

# --- Return a book (mark returned and increment copies) ---
@bp.route('/return/<int:booking_id>', methods=['POST'])
@login_required
def return_book(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id and not current_user.is_admin():
        flash('You can only return your own bookings.')
        return redirect(url_for('main.my_bookings'))
    book = Book.query.get(booking.book_id)
    if book:
        book.available_copies += 1
    booking.status = 'returned'
    booking.return_date = datetime.utcnow()
    db.session.commit()
    flash('Book returned successfully.')
    return redirect(url_for('main.my_bookings'))

# --- Profile ---
@bp.route('/profile')
@login_required
def profile():
    total = Booking.query.filter_by(user_id=current_user.id).count()
    active = Booking.query.filter_by(user_id=current_user.id, status='active').count()
    returned = Booking.query.filter_by(user_id=current_user.id, status='returned').count()
    return render_template('profile.html', user=current_user, total=total, active=active, returned=returned)

# --- Admin dashboard: add, delete, import ---
def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin():
        flash('Admin access required.')
        return False
    return True

@bp.route('/admin', methods=['GET','POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin():
        flash('Access denied.')
        return redirect(url_for('main.index'))
    form = BookForm()
    import_form = ImportForm()
    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data,
            category=form.category.data,
            available_copies=form.copies.data or 0,
            cover_url=form.cover_url.data,
            description=form.description.data
        )
        db.session.add(book)
        db.session.commit()
        flash('Book added.')
        return redirect(url_for('main.admin_dashboard'))
    books = Book.query.order_by(Book.title).all()
    users = User.query.order_by(User.created_at.desc()).all()
    total_books = Book.query.count()
    total_users = User.query.count()
    total_bookings = Booking.query.count()
    popular = db.session.query(Book, db.func.count(Booking.id).label('cnt')) \
        .join(Booking, Booking.book_id == Book.id, isouter=True) \
        .group_by(Book.id).order_by(db.text('cnt DESC')).limit(10).all()
    return render_template('admin.html', form=form, import_form=import_form, books=books, users=users,
                           total_books=total_books, total_users=total_users, total_bookings=total_bookings, popular=popular)

@bp.route('/admin/delete/<int:book_id>')
@login_required
def admin_delete_book(book_id):
    if not current_user.is_admin():
        flash('Access denied.')
        return redirect(url_for('main.index'))
    b = Book.query.get_or_404(book_id)
    db.session.delete(b)
    db.session.commit()
    flash('Book deleted.')
    return redirect(url_for('main.admin_dashboard'))

@bp.route('/admin/import', methods=['POST'])
@login_required
def admin_import():
    if not current_user.is_admin():
        flash('Access denied.')
        return redirect(url_for('main.index'))
    f = request.files.get('file')
    if not f:
        flash('No file uploaded.')
        return redirect(url_for('main.admin_dashboard'))
    try:
        data = json.load(f)
        for item in data:
            book = Book(
                title=item.get('title'),
                author=item.get('author'),
                category=item.get('category'),
                description=item.get('description'),
                cover_url=item.get('cover_url'),
                available_copies=item.get('available_copies', 1)
            )
            db.session.add(book)
        db.session.commit()
        flash('Imported books.')
    except Exception as e:
        flash('Failed to import: ' + str(e))
    return redirect(url_for('main.admin_dashboard'))

# --- Chatbot placeholder page ---
@bp.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')
