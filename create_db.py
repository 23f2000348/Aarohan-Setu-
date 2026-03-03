from app import create_app
from extensions import db
from models import User, Admin
from werkzeug.security import generate_password_hash

app = create_app()

def create_tables_and_seed():
    with app.app_context():
        # Create all tables
        db.create_all()
        print(" All tables created successfully.")

        # Seed predefined Admin (only once)
        existing_admin = User.query.filter_by(role='admin').first()
        if not existing_admin:
            hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256')
            admin_user = User(
                username='admin',
                password_hash=hashed_password,
                role='admin',
                status='Active'
            )
            db.session.add(admin_user)
            db.session.flush()  # get admin_user.id before commit

            admin_profile = Admin(
                user_id=admin_user.id,
                email='admin@aarohansetu.com'
            )
            db.session.add(admin_profile)
            db.session.commit()
            print(" Admin user seeded — username: 'admin', password: 'admin123'")
        else:
            print("ℹ  Admin user already exists, skipping seed.")

if __name__ == '__main__':
    create_tables_and_seed()
