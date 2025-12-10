from flask import Flask, render_template, request, redirect, url_for, flash
from config import SQLALCHEMY_DATABASE_URI, SECRET_KEY
from models import db, User, Employee, Boss, JobOffer, Application
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime
from functools import wraps

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = SECRET_KEY

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            app.logger.exception("load_user error: %s", e)
            return None

    # --- Decoradores de Roles ---
    def boss_required(f):
        @wraps(f)
        def wrap(*args, **kwargs):
            if not current_user.is_authenticated or getattr(current_user, "user_type", None) != "boss":
                flash("Acceso denegado. Se requiere cuenta Boss.", "danger")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrap

    def worker_required(f):
        @wraps(f)
        def wrap(*args, **kwargs):
            if not current_user.is_authenticated or getattr(current_user, "user_type", None) != "employee":
                flash("Acceso denegado. Se requiere cuenta Worker.", "danger")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrap

    # --- Rutas Públicas ---
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/quienessomos")
    def quienessomos():
        return render_template("quienessomos.html")

    @app.route("/porque")
    def porque():
        return render_template("porque.html")

    # --- Rutas de Registro y Login ---
    @app.route("/registroa")
    def registroa():
        return render_template("registroa.html")

    @app.route("/registro")   # worker
    def registro():
        return render_template("registro.html")

    @app.route("/registrob")  # boss
    def registrob():
        return render_template("registrob.html")

    @app.route("/registrar_worker", methods=["POST"])
    def registrar_worker():
        nombre = request.form.get("nombre", "").strip()
        apellidos = request.form.get("apellidos", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        if not (nombre and apellidos and correo and password):
            flash("Completa todos los campos.", "danger")
            return redirect(url_for("registro"))

        password_hash = generate_password_hash(password)
        user = User(
            name=f"{nombre} {apellidos}",
            email=correo,
            password_hash=password_hash,
            user_type="employee"
        )

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("El correo ya está registrado.", "danger")
            return redirect(url_for("registro"))
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.exception("Error al crear usuario worker: %s", e)
            flash("Error al crear usuario.", "danger")
            return redirect(url_for("registro"))

        try:
            employee = Employee(
                user_id=user.user_id,
                name=f"{nombre} {apellidos}",
                skills="",
                experience="",
                resume=""
            )
            db.session.add(employee)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.exception("Error al crear perfil employee: %s", e)
            try:
                db.session.delete(user)
                db.session.commit()
            except Exception:
                db.session.rollback()
            flash("Error al crear perfil de Worker.", "danger")
            return redirect(url_for("registro"))

        flash("Registro exitoso. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    @app.route("/registrar_boss", methods=["POST"])
    def registrar_boss():
        nombre = request.form.get("nombre", "").strip()
        apellidos = request.form.get("apellidos", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "")
        empresa = request.form.get("empresa", "").strip()
        telefono = request.form.get("telefono", "").strip()
        cargo = request.form.get("cargo", "").strip()

        if not (nombre and apellidos and correo and password and empresa):
            flash("Completa todos los campos.", "danger")
            return redirect(url_for("registrob"))

        password_hash = generate_password_hash(password)
        user = User(
            name=f"{nombre} {apellidos}",
            email=correo,
            password_hash=password_hash,
            user_type="boss"
        )

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("El correo ya está registrado.", "danger")
            return redirect(url_for("registrob"))
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.exception("Error al crear usuario boss: %s", e)
            flash("Error al crear usuario Boss.", "danger")
            return redirect(url_for("registrob"))

        try:
            boss = Boss(
                user_id=user.user_id,
                name=f"{nombre} {apellidos}",
                contact=cargo,
                phone=telefono,
                address=empresa
            )
            db.session.add(boss)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.exception("Error al crear boss profile: %s", e)
            try:
                db.session.delete(user)
                db.session.commit()
            except Exception:
                db.session.rollback()
            flash("Error al crear perfil Boss.", "danger")
            return redirect(url_for("registrob"))

        flash("Registro Boss completo.", "success")
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            if getattr(current_user, "user_type", None) == 'boss':
                return redirect(url_for('perfilb')) 
            elif getattr(current_user, "user_type", None) == 'employee':
                return redirect(url_for('perfilw')) 
            return redirect(url_for('index')) 

        if request.method == "GET":
            return render_template("login.html")

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not (email and password):
            flash("Completa los campos de login.", "warning")
            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User.query.filter_by(name=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Credenciales incorrectas.", "danger")
            return redirect(url_for("login"))

        login_user(user)
        
        if getattr(user, "user_type", None) == "boss":
            return redirect(url_for("perfilb"))
        else:
            return redirect(url_for("proyectow")) 

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Sesión cerrada.", "info")
        return redirect(url_for("login")) 

    # --- RUTAS DE BOSS ---

    @app.route("/perfilb")
    @login_required
    @boss_required
    def perfilb():
        boss_obj = Boss.query.filter_by(user_id=current_user.user_id).first()
        if not boss_obj:
            flash("Perfil Boss no encontrado.", "warning")
            return redirect(url_for("index"))

        boss = {
            "nombre": boss_obj.name or "",
            "area": boss_obj.address or "",
            "usuario": boss_obj.name or "",
            "correo": boss_obj.user.email if getattr(boss_obj, "user", None) else "",
            "descripcion": boss_obj.contact or ""
        }
        return render_template("perfilb.html", boss=boss, boss_obj=boss_obj)

    # NUEVA RUTA: Editar Perfil Boss
    @app.route("/editar_perfil_boss", methods=["GET", "POST"])
    @login_required
    @boss_required
    def editar_perfil_boss():
        boss = Boss.query.filter_by(user_id=current_user.user_id).first()
        
        if request.method == "POST":
            boss.name = request.form.get("nombre")
            boss.address = request.form.get("empresa")
            boss.contact = request.form.get("cargo")
            boss.phone = request.form.get("telefono")
            
            # Actualizamos también el nombre en la tabla User para coherencia
            current_user.name = request.form.get("nombre")
            
            try:
                db.session.commit()
                flash("Perfil actualizado correctamente.", "success")
                return redirect(url_for("perfilb"))
            except Exception:
                db.session.rollback()
                flash("Error al actualizar el perfil.", "danger")

        return render_template("editarperfilb.html", boss=boss)

    @app.route("/proyectob")
    @login_required
    @boss_required
    def proyectob():
        boss_obj = Boss.query.filter_by(user_id=current_user.user_id).first()
        if not boss_obj:
            flash("Perfil Boss no encontrado.", "warning")
            return redirect(url_for("index"))

        all_jobs = JobOffer.query.filter_by(boss_id=boss_obj.boss_id).order_by(JobOffer.publish_date.desc()).all()

        activos = []
        finalizados = []

        for p in all_jobs:
            es_completado = False
            if p.applications:
                for app in p.applications:
                    if app.status == 'completed':
                        es_completado = True
                        break
            
            datos_proyecto = {
                "id": p.offer_id,
                "titulo": p.title,
                "descripcion": p.description,
                "fecha_limite": p.publish_date.strftime('%Y-%m-%d'),
                "postulaciones": len(p.applications) if p.applications else 0
            }

            if es_completado:
                finalizados.append(datos_proyecto)
            else:
                activos.append(datos_proyecto)

        return render_template("proyectob.html", activos=activos, finalizados=finalizados)

    @app.route("/crearproyecto", methods=["GET", "POST"])
    @login_required
    @boss_required
    def crearproyecto():
        if request.method == "GET":
            return render_template("crearproyecto.html")

        titulo = request.form.get("titulo")
        descripcion = request.form.get("descripcion")
        ubicacion = request.form.get("ubicacion")
        presupuesto = request.form.get("presupuesto")

        boss = Boss.query.filter_by(user_id=current_user.user_id).first()
        if not boss:
            flash("Perfil Boss no encontrado.", "warning")
            return redirect(url_for("index"))

        try:
            project = JobOffer(
                boss_id=boss.boss_id,
                title=titulo,
                description=descripcion,
                salary=float(presupuesto) if presupuesto else None,
                location=ubicacion,
                status="open",
                publish_date=datetime.now()
            )
            db.session.add(project)
            db.session.commit()
            flash("Proyecto creado.", "success")
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.exception("Error al crear proyecto: %s", e)
            flash("Error al crear proyecto.", "danger")

        return redirect(url_for("proyectob"))

    @app.route("/detallesolicitud/<int:id>")
    @login_required
    @boss_required
    def detallesolicitud(id):
        job = JobOffer.query.get_or_404(id)
        
        boss_obj = Boss.query.filter_by(user_id=current_user.user_id).first()
        if not boss_obj or job.boss_id != boss_obj.boss_id:
             flash("Acceso denegado.", "danger")
             return redirect(url_for("proyectob"))

        postulaciones_q = Application.query.filter_by(offer_id=job.offer_id).all()
        postulaciones = []
        for a in postulaciones_q:
            emp = Employee.query.get(a.employee_id)
            postulaciones.append({
                "id": a.application_id,
                "worker": emp.name if emp else "N/A",
                "status": a.status,
                "fecha": a.application_date.strftime('%Y-%m-%d')
            })
        solicitud = {
            "id": job.offer_id, 
            "proyecto": job.title,
            "descripcion": job.description,
            "categoria": job.location,
            "fecha_entrega": job.publish_date.strftime('%Y-%m-%d'),
            "presupuesto": job.salary
        }
        return render_template("detallesolicitud.html", solicitud=solicitud, postulaciones=postulaciones)

    # NUEVA RUTA: Editar Proyecto
    @app.route("/editar_proyecto/<int:id>", methods=["GET", "POST"])
    @login_required
    @boss_required
    def editar_proyecto(id):
        job = JobOffer.query.get_or_404(id)
        boss = Boss.query.filter_by(user_id=current_user.user_id).first()
        
        if job.boss_id != boss.boss_id:
            flash("No tienes permiso para editar este proyecto.", "danger")
            return redirect(url_for("proyectob"))

        if request.method == "POST":
            job.title = request.form.get("titulo")
            job.description = request.form.get("descripcion")
            job.location = request.form.get("ubicacion")
            presupuesto = request.form.get("presupuesto")
            if presupuesto:
                job.salary = float(presupuesto)
            
            db.session.commit()
            flash("Proyecto actualizado correctamente.", "success")
            return redirect(url_for("detallesolicitud", id=job.offer_id))

        return render_template("editarproyecto.html", proyecto=job)

    # NUEVA RUTA: Eliminar Proyecto
    @app.route("/eliminar_proyecto/<int:id>", methods=["POST"])
    @login_required
    @boss_required
    def eliminar_proyecto(id):
        job = JobOffer.query.get_or_404(id)
        boss = Boss.query.filter_by(user_id=current_user.user_id).first()

        if job.boss_id != boss.boss_id:
            flash("No tienes permiso para eliminar este proyecto.", "danger")
            return redirect(url_for("proyectob"))

        try:
            db.session.delete(job)
            db.session.commit()
            flash("Proyecto eliminado.", "success")
        except Exception:
            db.session.rollback()
            flash("Error al eliminar el proyecto.", "danger")

        return redirect(url_for("proyectob"))

    @app.route("/gestionar_solicitud", methods=["POST"])
    @login_required
    @boss_required
    def gestionar_solicitud():
        app_id = request.form.get("app_id")
        accion = request.form.get("accion") 

        application = Application.query.get_or_404(int(app_id))
        job = JobOffer.query.get(application.offer_id)
        
        boss = Boss.query.filter_by(user_id=current_user.user_id).first()
        if job.boss_id != boss.boss_id:
            flash("No tienes permiso.", "danger")
            return redirect(url_for("proyectob"))

        if accion == 'aceptar':
            application.status = 'accepted'
            job.status = 'closed' 
            flash(f"Candidato aceptado. Ahora aparecerá en sus trabajos pendientes.", "success")
        elif accion == 'rechazar':
            application.status = 'rejected'
            flash("Candidato rechazado.", "info")

        db.session.commit()
        return redirect(url_for('detallesolicitud', id=job.offer_id))

    # --- RUTAS DE WORKER ---

    @app.route("/perfilw")
    @login_required
    @worker_required
    def perfilw():
        worker_obj = Employee.query.filter_by(user_id=current_user.user_id).first()
        if not worker_obj:
            return redirect(url_for("index"))

        worker = {
            "nombre": worker_obj.name or "",
            "profesion": worker_obj.skills or "",
            "ubicacion": "",
            "correo": worker_obj.user.email if getattr(worker_obj, "user", None) else "",
            "descripcion": worker_obj.experience or ""
        }
        return render_template("perfilw.html", worker=worker, worker_obj=worker_obj)

    # NUEVA RUTA: Editar Perfil Worker
    @app.route("/editar_perfil_worker", methods=["GET", "POST"])
    @login_required
    @worker_required
    def editar_perfil_worker():
        worker = Employee.query.filter_by(user_id=current_user.user_id).first()
        
        if request.method == "POST":
            worker.name = request.form.get("nombre")
            worker.skills = request.form.get("profesion")
            worker.experience = request.form.get("experiencia")
            
            # Actualizamos también el nombre en la tabla User
            current_user.name = request.form.get("nombre")
            
            try:
                db.session.commit()
                flash("Perfil actualizado correctamente.", "success")
                return redirect(url_for("perfilw"))
            except Exception:
                db.session.rollback()
                flash("Error al actualizar el perfil.", "danger")

        return render_template("editarperfilw.html", worker=worker)

    @app.route("/proyectow")
    @login_required
    @worker_required
    def proyectow():
        proyectos_q = JobOffer.query.filter_by(status="open").order_by(JobOffer.publish_date.desc()).all()
        proyectos = []
        for p in proyectos_q:
            proyectos.append({
                "id": p.offer_id,
                "titulo": p.title,
                "descripcion": p.description,
                "fecha_limite": p.publish_date.strftime('%Y-%m-%d')
            })
        return render_template("proyectow.html", proyectos=proyectos)

    @app.route("/solicitudes", methods=["GET", "POST"])
    @login_required
    def solicitudes():
        if request.method == "GET":
            if current_user.user_type == "employee":
                worker = Employee.query.filter_by(user_id=current_user.user_id).first()
                if not worker: return redirect(url_for("index"))
                
                apps = Application.query.filter_by(employee_id=worker.employee_id).all()
                trabajos = []
                for a in apps:
                    job = JobOffer.query.get(a.offer_id)
                    trabajos.append({
                        "id": a.application_id,
                        "titulo": job.title if job else "N/A",
                        "cliente": job.boss.name if job and job.boss else "N/A",
                        "descripcion": job.description if job else "",
                        "fecha_limite": job.publish_date.strftime('%Y-%m-%d') if job else "N/A",
                        "estado": a.status
                    })
                return render_template("solicitudes.html", trabajos=trabajos, is_boss=False)
            
            # BOSS: Ve postulaciones recibidas
            else:
                boss = Boss.query.filter_by(user_id=current_user.user_id).first()
                if not boss: return redirect(url_for("index"))
                
                postulaciones = []
                ofertas = JobOffer.query.filter_by(boss_id=boss.boss_id).all()
                for off in ofertas:
                    for a in off.applications:
                        emp = Employee.query.get(a.employee_id)
                        postulaciones.append({
                            "id": a.application_id,
                            "proyecto": off.title,
                            "worker": emp.name if emp else "N/A",
                            "estado": a.status,
                            "fecha": a.application_date.strftime('%Y-%m-%d')
                        })
                return render_template("solicitudes.html", postulaciones=postulaciones, is_boss=True)

        proyecto_id = request.form.get("proyecto_id")
        if not proyecto_id:
            return redirect(url_for("proyectow"))

        if current_user.user_type != "employee":
            flash("Solo Workers pueden postularse.", "danger")
            return redirect(url_for("proyectow"))

        worker = Employee.query.filter_by(user_id=current_user.user_id).first()
        try:
            job = JobOffer.query.get(int(proyecto_id))
        except:
            job = None

        if not job or job.status != "open":
            flash("Proyecto no disponible.", "warning")
            return redirect(url_for("proyectow"))
        
        existe = Application.query.filter_by(employee_id=worker.employee_id, offer_id=job.offer_id).first()
        if existe:
            flash("Ya te has postulado a este proyecto.", "info")
            return redirect(url_for("proyectow"))

        app_entry = Application(employee_id=worker.employee_id, offer_id=job.offer_id)
        db.session.add(app_entry)
        db.session.commit()
        flash("Postulación enviada.", "success")
        return redirect(url_for("proyectow"))

    @app.route("/trabajospendientes")
    @login_required
    @worker_required
    def trabajospendientes():
        worker = Employee.query.filter_by(user_id=current_user.user_id).first()
        if not worker:
            return redirect(url_for("index"))
        
        apps = Application.query.filter(
            Application.employee_id == worker.employee_id,
            Application.status.in_(['accepted', 'completed'])
        ).all()

        pendientes = []
        completados = []

        for a in apps:
            job = JobOffer.query.get(a.offer_id)
            info = {
                "id": a.application_id, 
                "titulo": job.title,
                "cliente": job.boss.name if job.boss else "N/A",
                "descripcion": job.description,
                "fecha_limite": job.publish_date.strftime('%Y-%m-%d'),
                "pago": job.salary,
                "estado": a.status
            }
            
            if a.status == 'accepted':
                pendientes.append(info)
            elif a.status == 'completed':
                completados.append(info)

        return render_template("trabajospendientes.html", pendientes=pendientes, completados=completados)

    @app.route("/ver_trabajopendiente", methods=["POST"])
    @login_required
    def ver_trabajopendiente():
        app_id = request.form.get("id")
        application = Application.query.get_or_404(int(app_id))
        job = JobOffer.query.get(application.offer_id)

        if current_user.user_type == "employee":
            worker = Employee.query.filter_by(user_id=current_user.user_id).first()
            if application.employee_id != worker.employee_id:
                flash("No tienes permiso.", "danger")
                return redirect(url_for("trabajospendientes"))
        
        trabajo_detalle = {
            "id": application.application_id,
            "titulo": job.title,
            "cliente": job.boss.name if job.boss else "N/A",
            "descripcion": job.description,
            "fecha_limite": job.publish_date.strftime('%Y-%m-%d'),
            "pago": job.salary,
            "estado": application.status
        }
        return render_template("ver_trabajopendiente.html", trabajo=trabajo_detalle)

    @app.route("/marcar_completado", methods=["POST"])
    @login_required
    def marcar_completado():
        app_id = request.form.get("id")
        application = Application.query.get_or_404(int(app_id))
        
        application.status = 'completed'
        db.session.commit()
        
        flash("Trabajo marcado como completado.", "success")
        return redirect(url_for("trabajospendientes"))

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        print("Tablas creadas.")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)