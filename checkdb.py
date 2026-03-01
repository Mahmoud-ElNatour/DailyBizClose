from app import app, db

print("STEP 1")
print("DB:", app.config.get("SQLALCHEMY_DATABASE_URI"))

with app.app_context():
    print("Known tables BEFORE:", list(db.metadata.tables.keys()))
    db.create_all()
    print("Known tables AFTER:", list(db.metadata.tables.keys()))

print("DONE")