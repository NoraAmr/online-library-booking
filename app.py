from flask import Flask
from config import Config
from models import db
from flask_login import LoginManager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'main.login'
    login_manager.init_app(app)

    # user loader
    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Import routes after app is configured to avoid circular imports
    from routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    # Create DB tables if not exist
    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
