from sqlalchemy.orm import Session
from . import models, schemas


def create_site(db: Session, site: schemas.SiteCreate):
    s = models.Site(name=site.name, base_path=site.base_path or "", base_command=site.base_command or "")
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def get_sites(db: Session):
    return db.query(models.Site).all()


def get_site(db: Session, site_id: int):
    return db.query(models.Site).filter(models.Site.id == site_id).first()


def create_command(db: Session, command: schemas.CommandCreate):
    c = models.Command(site_id=command.site_id, name=command.name, command_template=command.command_template)
    db.add(c)
    db.commit()
    db.refresh(c)
    for e in command.envs or []:
        env = models.Env(command_id=c.id, key=e.key, value=e.value)
        db.add(env)
    db.commit()
    db.refresh(c)
    return c


def get_commands_for_site(db: Session, site_id: int):
    return db.query(models.Command).filter(models.Command.site_id == site_id).all()


def get_command(db: Session, command_id: int):
    return db.query(models.Command).filter(models.Command.id == command_id).first()


def create_user(db: Session, username: str, email: str, password_hash: str, perms: str = ""):
    u = models.User(username=username, email=email, password_hash=password_hash, perms=perms)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_token(db: Session, token: str):
    return db.query(models.User).filter(models.User.token == token).first()


def create_log(db: Session, command_id: int, output_path: str, status: str = "running"):
    l = models.Log(command_id=command_id, output_path=output_path, status=status)
    db.add(l)
    db.commit()
    db.refresh(l)
    return l
