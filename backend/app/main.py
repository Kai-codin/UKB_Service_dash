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


@app.get("/api/sites/{site_id}")
def get_site(site_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(auth.get_current_user)):
    s = crud.get_site(db, site_id)
    if not s:
        raise HTTPException(status_code=404, detail="Site not found")
    return s


@app.put("/api/sites/{site_id}")
def edit_site(site_id: int, site: schemas.SiteCreate, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("edit site"))):
    s = crud.update_site(db, site_id, site.dict())
    if not s:
        raise HTTPException(status_code=404, detail="Site not found")
    return s


@app.delete("/api/sites/{site_id}")
def remove_site(site_id: int, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("edit site"))):
    ok = crud.delete_site(db, site_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Site not found")
    return {"status": "deleted"}


@app.get("/api/sites/{site_id}/commands")
def get_commands(site_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(auth.get_current_user)):
    return crud.get_commands_for_site(db, site_id)


@app.post("/api/commands")
def add_command(command: schemas.CommandCreate, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("add service"))):
    return crud.create_command(db, command)


@app.get("/api/commands/{command_id}")
def get_command_detail(command_id: int, db: Session = Depends(database.get_db), user: models.User = Depends(auth.get_current_user)):
    c = crud.get_command(db, command_id)
    if not c:
        raise HTTPException(status_code=404, detail="Command not found")
    run_cmd = None
    try:
        run_cmd = runner.build_command(c)
    except Exception:
        run_cmd = None
    return {
        "id": c.id,
        "name": c.name,
        "command_template": c.command_template,
        "site_id": c.site_id,
        "envs": [{"id": e.id, "key": e.key, "value": e.value} for e in c.envs],
        "current_pid": c.current_pid,
        "run_command": run_cmd,
    }


@app.put("/api/commands/{command_id}")
def edit_command(command_id: int, command: schemas.CommandCreate, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("edit service"))):
    # allow updating name, template and envs
    data = command.dict()
    # command.site_id may or may not change; keep original if omitted
    if 'site_id' not in data or data.get('site_id') is None:
        data['site_id'] = crud.get_command(db, command_id).site_id
    c = crud.update_command(db, command_id, data)
    if not c:
        raise HTTPException(status_code=404, detail="Command not found")
    return c


@app.delete("/api/commands/{command_id}")
def remove_command(command_id: int, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("edit service"))):
    ok = crud.delete_command(db, command_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Command not found")
    return {"status": "deleted"}


@app.post("/api/commands/{command_id}/start")
def start(command_id: int, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("start service"))):
    try:
        pid, log, cmd = runner.start_command(db, command_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"pid": pid, "log": log, "command": cmd}


@app.post("/api/commands/{command_id}/stop")
def stop(command_id: int, db: Session = Depends(database.get_db), _=Depends(auth.require_perm("stop service"))):
    try:
        runner.stop_command(db, command_id)
    except Exception as e:
        msg = str(e)
        # if not running, return a friendly status instead of 400
        if "not running" in msg.lower():
            cmd = crud.get_command(db, command_id)
            run_cmd = None
            try:
                run_cmd = runner.build_command(cmd) if cmd else None
            except Exception:
                run_cmd = None
            return {"status": "not_running", "message": msg, "command": run_cmd}
        raise HTTPException(status_code=400, detail=msg)
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
