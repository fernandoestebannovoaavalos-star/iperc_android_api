from app import create_app, db
from app.models import Usuario, RegistroIPERC, FirmaDigital, PeligroAdicional, RegistroPeligro

app = create_app()

with app.app_context():
    # 1. Borrar firmas digitales
    FirmaDigital.query.delete()
    print("✅ Firmas borradas")

    # 2. Borrar peligros adicionales
    PeligroAdicional.query.delete()
    print("✅ Peligros adicionales borrados")

    # 3. Borrar registros peligros
    RegistroPeligro.query.delete()
    print("✅ Registros peligros borrados")

    # 4. Borrar registros IPERC
    RegistroIPERC.query.delete()
    print("✅ Registros IPERC borrados")

    # 5. Borrar usuarios excepto admin
    Usuario.query.filter(Usuario.dni != '99999999').delete()
    print("✅ Usuarios de prueba borrados")

    db.session.commit()
    print("\n✅ Reset completado. Solo queda el admin.")

    usuarios = Usuario.query.all()
    print(f"Usuarios restantes: {len(usuarios)}")
    for u in usuarios:
        print(f"  - {u.nombre} {u.apellido} | {u.dni} | {u.rol}")