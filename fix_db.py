from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("🔧 Iniciando actualización de la base de datos...")
    
    try:
        print("1. Eliminando restricción antigua...")
        db.session.execute(text("ALTER TABLE applications DROP CONSTRAINT IF EXISTS applications_status_check"))
        
        print("2. Creando nueva regla (incluye 'completed')...")
        db.session.execute(text("ALTER TABLE applications ADD CONSTRAINT applications_status_check CHECK (status IN ('pending', 'accepted', 'rejected', 'completed'))"))
        
        db.session.commit()
        print("✅ ¡Éxito! La base de datos ha sido actualizada.")
        print("Ahora puedes marcar trabajos como completados sin errores.")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {e}")