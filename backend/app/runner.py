import os
import shlex
import subprocess
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from . import models, crud
from .database import SessionLocal

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def build_command(command: models.Command):
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


def _stream_output(proc, out_path, command_id, log_id):
    # This runs in a background thread: read stdout and write to file, update DB on finish
    db = SessionLocal()
    try:
        with open(out_path, "a", encoding="utf-8", errors="ignore") as f:
            for line in proc.stdout:
                f.write(line)
                f.flush()
        ret = proc.wait()
        # update log status and command
        log = db.query(models.Log).filter(models.Log.id == log_id).first()
        if log:
            log.status = "finished" if ret == 0 else f"error:{ret}"
            db.add(log)
        cmd = db.query(models.Command).filter(models.Command.id == command_id).first()
        if cmd:
            cmd.current_pid = None
            db.add(cmd)
        db.commit()
    except Exception:
        try:
            log = db.query(models.Log).filter(models.Log.id == log_id).first()
            if log:
                log.status = "error"
                db.add(log)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def start_command(db: Session, command_id: int):
    command = crud.get_command(db, command_id)
    if not command:
        raise RuntimeError("Command not found")
    cmd = build_command(command)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    log_path = os.path.abspath(os.path.join(LOG_DIR, f"cmd_{command_id}_{ts}.log"))
    # Create log DB entry first
    log = crud.create_log(db, command.id, log_path, status="running")
    # Start process with PIPE so we can stream output to file and flush
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=os.environ.copy(), cwd=command.site.base_path or None, text=True, bufsize=1)
    command.current_pid = proc.pid
    db.add(command)
    db.commit()
    # start background thread to write stdout to file and update DB
    t = threading.Thread(target=_stream_output, args=(proc, log_path, command.id, log.id), daemon=True)
    t.start()
    return proc.pid, log_path, cmd


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
