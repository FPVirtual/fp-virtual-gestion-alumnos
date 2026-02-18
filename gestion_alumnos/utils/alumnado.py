import bcrypt
from requests import Session
from gestion_alumnos.models import Alumno


def gest_reincorporaciones() -> int:
    """
    Un alumno puede estar suspendido en moodle y que ahora aparezca en sigad -> Dar de alta.
    Casos: 
        a. Reincorporación con nuevo email de sigad
        b. Reincorporación y pasa de NIE a DNI
        c. Reincorporación con nuevo nombre - identidad de género
    * Identificación por tener el mismo documento
    * Identificación por tener el mismo email -> comprobar que no es familiar
    * 
    """
    return 0


def hash_moodle_password(password: str) -> str:
    """
    Genera hash bcrypt compatible con Moodle 3.0+.
    Moodle usa bcrypt con cost 10 por defecto.
    """
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def alta_nueva(session: Session, alumno: Alumno, password: str) -> int:
    """
    Crea un alumno en Moodle usando SQLAlchemy (transaccional).
    
    Args:
        session: Sesión SQLAlchemy activa (conexión BD Moodle)
        alumno: Objeto Alumno validado
        password: Contraseña en texto plano
        
    Returns:
        int: ID del usuario creado
        
    Raises:
        ValueError: Si el alumno no cumple requisitos
        IntegrityError: Si ya existe username/email en Moodle
    """
    # Validación previa
    if not is_alumno_creable(alumno):
        raise ValueError(f"Alumno {alumno.documento} no es creable")
    
    timestamp = int(time.time())
    
    try:
        # 1. Crear usuario principal
        nuevo = MoodleUser(
            username=alumno.documento.lower(),
            password=hash_moodle_password(password),
            firstname=alumno.nombre,
            lastname=f"{alumno.apellido1} {alumno.apellido2 or ''}".strip(),
            email=alumno.email,  # Asume que este es el email_dominio
            timecreated=timestamp,
            timemodified=timestamp,
            city="Aragón",
            country="ES"
        )
        
        session.add(nuevo)
        session.flush()  # Obtiene el ID sin commit aún
        
        # 2. Insertar email SIGAD en campo personalizado (fieldid=4)
        info = UserInfoData(
            userid=nuevo.id,
            fieldid=4,  # ID del campo 'email_sigad' en tu Moodle
            data=alumno.email  # O alumno.email_sigad si lo tienes separado
        )
        session.add(info)
        
        # 3. Commit atómico (ambos o ninguno)
        session.commit()
        
        logger.info(f"✅ Alumno creado: ID {nuevo.id}, Username {nuevo.username}")
        return nuevo.id
        
    except IntegrityError as e:
        session.rollback()
        logger.error(f"❌ Usuario ya existe (duplicado): {alumno.documento}")
        raise ValueError(f"El usuario {alumno.documento} o su email ya existen") from e
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error creando {alumno.documento}: {e}")
        raise


def matricular_en_cohorte(session: Session, id_alumno: int, 
                          id_cohorte: str = "alumnado") -> bool:
    """
    Matricula un alumno en una cohorte específica (por defecto 'alumnado').
    
    Args:
        session: Sesión SQLAlchemy activa
        id_alumno: ID del usuario en mdl_user
        id_cohorte: Identificador de la cohorte (por defecto "alumnado")
        
    Returns:
        bool: True si se añadió, False si ya existía
        
    Raises:
        ValueError: Si no existe la cohorte
    """
    # 1. Buscar la cohorte por idnumber (más estable que por name)
    stmt = select(Cohort).where(Cohort.idnumber == id_cohorte)
    cohorte = session.execute(stmt).scalar_one_or_none()
    
    if not cohorte:
        raise ValueError(f"Cohorte '{id_cohorte}' no encontrada en Moodle")
    
    # 2. Verificar si ya está matriculado (evitar duplicados)
    stmt_check = select(CohortMember).where(
        and_(
            CohortMember.cohortid == cohorte.id,
            CohortMember.userid == id_alumno
        )
    )
    existe = session.execute(stmt_check).scalar_one_or_none()
    
    if existe:
        logger.info(f"ℹ️ Alumno {id_alumno} ya estaba en cohorte '{id_cohorte}'")
        return False
    
    # 3. Crear la relación
    timestamp = int(time.time())
    membresia = CohortMember(
        cohortid=cohorte.id,
        userid=id_alumno,
        timeadded=timestamp
    )
    
    try:
        session.add(membresia)
        session.flush()  # Verifica integridad sin commit final aún
        logger.info(f"✅ Alumno {id_alumno} añadido a cohorte '{id_cohorte}' (ID: {cohorte.id})")
        return True
        
    except IntegrityError:
        # Race condition: alguien más lo insertó entre el check y el insert
        session.rollback()
        logger.warning(f"⚠️ Conflicto de integridad al matricular {id_alumno} en cohorte")
        return False



def alta_nueva(session: Session, alumno: Alumno, password: str) -> dict:
    """
    Pipeline completo: crear alumno + matricular en cohorte alumnado.
    Transaccional: si falla la cohorte, se revierte todo.
        2. Crear el password
        3. crearAlumnoEnMoodle(moodle, alumno, password)
        4. matricula_alumno_en_cohorte_alumnado(moodle, id_alumno)
        5. logs 
        6. csv para crear cuentas google
        7. enviar emails
        8. listado de alumnos que no se pudieron matricular
    """

    result = {"creado": False, "id": None, "cohorte": False}
    
    try:
        # 1. Crear usuario
        id_user = alta_nueva(session, alumno, password)
        result["creado"] = True
        result["id"] = id_user
        
        # 2. Matricular en cohorte (misma transacción)
        matriculado = matricular_en_cohorte(session, id_user, "alumnado")
        result["cohorte"] = matriculado
        
        # Commit final (ambos pasos o ninguno)
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error en alta completa para {alumno.documento}: {e}")
        raise


