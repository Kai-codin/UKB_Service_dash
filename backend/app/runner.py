import os
import shlex
import subprocess
from datetime import datetime
from sqlalchemy.orm import Session
from . import models, crud

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def build_command(db: Session, command: models.Command):
    site = command.site
    envs = {e.key: e.value for e in command.envs}
    try:
        formatted = command.command_template.format_map(envs)
    except Exception:
        formatted = command.command_template
    parts = []
    if site and site.base_path:
        parts.append(f"cd {shlex.quote(site.base_path)}")
    if site and site.base_command:
        parts.append(site.base_command)
    parts.append(formatted)
    return " && ".join([p for p in parts if p])


def start_command(db: Session, command_id: int):
    command = crud.get_command(db, command_id)
    if not command:
        raise RuntimeError("Command not found")
    cmd = build_command(db, command)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    log_path = os.path.abspath(os.path.join(LOG_DIR, f"cmd_{command_id}_{ts}.log"))
    f = open(log_path, "wb")
    # Run in shell so complex commands work
    proc = subprocess.Popen(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, env=os.environ.copy(), cwd=command.site.base_path or None)
    command.current_pid = proc.pid
    db.add(command)
    db.commit()
    crud.create_log(db, command.id, log_path, status="running")
    return proc.pid, log_path


def stop_command(db: Session, command_id: int):
    command = crud.get_command(db, command_id)
    if not command or not command.current_pid:
        raise RuntimeError("Command not running")
    try:
        os.kill(command.current_pid, 15)
    except Exception:
        pass
    # mark command as stopped
    command.current_pid = None
    db.add(command)
    db.commit()
    return True
