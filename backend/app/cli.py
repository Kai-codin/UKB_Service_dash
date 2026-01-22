import argparse
from .database import SessionLocal, engine
from . import models, auth


def create_superuser(username, email, password):
    db = SessionLocal()
    models.Base.metadata.create_all(bind=engine)
    if db.query(models.User).filter(models.User.username == username).first():
        print('User exists')
        return
    h = auth.get_password_hash(password)
    u = models.User(username=username, email=email, password_hash=h, perms='all')
    db.add(u)
    db.commit()
    db.refresh(u)
    print('Superuser created. Username:', u.username)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', required=True)
    parser.add_argument('--email', required=True)
    parser.add_argument('--password', required=True)
    args = parser.parse_args()
    create_superuser(args.username, args.email, args.password)


if __name__ == '__main__':
    main()
