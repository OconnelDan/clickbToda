from app import app, db
from sqlalchemy import text
import logging

def execute_migration():
    try:
        with app.app_context():
            # Read migration SQL
            with open('migrations/split_categoria.sql', 'r') as f:
                sql = f.read()
                
            # Split the SQL into individual statements and execute
            statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
            
            for statement in statements:
                db.session.execute(text(statement))
            
            db.session.commit()
            logging.info("Migration completed successfully")
            
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    execute_migration()
