from app import app, db
from sqlalchemy import text

def execute_migration():
    try:
        with open('migrations/split_categoria.sql', 'r') as f:
            sql = f.read()
            
        with app.app_context():
            # Execute the migration using SQLAlchemy
            with db.engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
                
        print("Migration executed successfully")
        return True
    except Exception as e:
        print(f"Error executing migration: {str(e)}")
        return False

if __name__ == "__main__":
    execute_migration()
