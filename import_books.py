import json
from app import app, db
from models import Book

with app.app_context():
    with open('books.json', 'r', encoding='utf-8') as f:
        books = json.load(f)
        for item in books:
            book = Book(
                title=item.get('title'),
                author=item.get('author'),
                category=item.get('category'),
                available_copies=item.get('available_copies', 1),
                description=item.get('description'),
                cover_url=item.get('cover_url')
            )
            db.session.add(book)
        db.session.commit()
    print("✅ Books imported successfully!")
