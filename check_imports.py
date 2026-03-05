try:
    import flask
    print("flask imported")
    import flask_sqlalchemy
    print("flask_sqlalchemy imported")
    import flask_login
    print("flask_login imported")
    from app import create_app
    print("app imported")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
