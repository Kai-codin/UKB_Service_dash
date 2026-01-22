from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

from . import database, crud, auth, models, runner, schemas

app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(bind=database.engine)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/login")
def login(data: schemas.LoginData, db: Session = Depends(database.get_db)):
    u = crud.get_user_by_username(db, data.username)
    if not u or not auth.verify_password(data.password, u.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not u.token:
        u.token = auth.create_token()
        db.add(u)
        db.commit()
    return {"token": u.token, "perms": u.perms}


@app.post("/api/users")
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("add user"))):
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="User exists")
    h = auth.get_password_hash(user.password)
    u = crud.create_user(db, user.username, user.email, h, perms=user.perms)
    return u


@app.get("/api/sites")
def list_sites(db: Session = Depends(database.get_db), user: models.User = Depends(auth.get_current_user)):
    return crud.get_sites(db)


@app.post("/api/sites")
def add_site(site: schemas.SiteCreate, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("add site"))):
    return crud.create_site(db, site)


@app.get("/api/sites/{site_id}/commands")
def get_commands(site_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(auth.get_current_user)):
    return crud.get_commands_for_site(db, site_id)


@app.post("/api/commands")
def add_command(command: schemas.CommandCreate, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("add service"))):
    return crud.create_command(db, command)


@app.post("/api/commands/{command_id}/start")
def start(command_id: int, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("start service"))):
    try:
        pid, log = runner.start_command(db, command_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"pid": pid, "log": log}


@app.post("/api/commands/{command_id}/stop")
def stop(command_id: int, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("stop service"))):
    try:
        runner.stop_command(db, command_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "stopped"}


@app.get("/api/logs/{command_id}")
def get_logs(command_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(auth.get_current_user)):
    cmd = crud.get_command(db, command_id)
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    logs = cmd.logs
    # return last log content path and tail
    if not logs:
        return {"logs": []}
    last = logs[-1]
    try:
        with open(last.output_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()[-20000:]
    except Exception:
        content = ""
    return {"path": last.output_path, "status": last.status, "output": content}
