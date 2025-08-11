# psuite/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_login import LoginManager

db = SQLAlchemy()
socketio = SocketIO()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

def create_app():
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(__file__))

    app.config['SECRET_KEY'] = 'a-super-secret-key-that-you-should-change'
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, '..', 'instance', 'suite.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config.from_mapping({
        'UPLOAD_FOLDER': os.path.join(basedir, '..', 'uploads'),
        'UNPACKED_FOLDER': os.path.join(basedir, '..', 'unpacked'),
        'PROCESSED_FOLDER': os.path.join(basedir, '..', 'processed'),
        'CACHE_FOLDER': os.path.join(basedir, '..', 'cache'),
        'ORIGINALS_FOLDER': os.path.join(basedir, '..', 'originals')
    })

    # Ensure instance folder exists
    try:
        os.makedirs(os.path.join(basedir, '..', 'instance'))
    except OSError:
        pass
        
    # Create other folders
    for key in ['UPLOAD_FOLDER', 'UNPACKED_FOLDER', 'PROCESSED_FOLDER', 'CACHE_FOLDER', 'ORIGINALS_FOLDER']:
        folder_path = app.config.get(key)
        if folder_path and not os.path.exists(folder_path):
            os.makedirs(folder_path)

    db.init_app(app)
    socketio.init_app(app)
    login_manager.init_app(app)
    
    from .models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .blueprints.main import main_bp
    from .blueprints.auth import auth_bp
    from .blueprints.tools import tools_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tools_bp, url_prefix='/tools')

    with app.app_context():
        db.create_all()

    return app