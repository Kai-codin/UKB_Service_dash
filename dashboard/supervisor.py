import os
import signal
import subprocess
import threading
import time
from datetime import datetime
import shlex
import shutil

from django.conf import settings
from django.utils import timezone

from .models import CommandRun, Command, Log

import requests


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


class ProcessSupervisor:
    def __init__(self, poll_interval=5):
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)

    def _run_loop(self):
        while not self._stop.is_set():
            try:
                self._check_and_restart()
            except Exception:
                # avoid crashing the thread
                pass
            time.sleep(self.poll_interval)

    def _check_and_restart(self):
        runs = CommandRun.objects.filter(stopped_at__isnull=True)
        for run in runs:
            pid = run.pid
            if not pid:
                continue
            if _process_exists(pid):
                continue
            # process died
            run.stopped_at = timezone.now()
            run.exit_code = None
            run.save()

            if run.manually_stopped:
                continue

            # unexpected death: notify and restart
            self._notify_discord(run)

            # attempt restart
            try:
                self.start_command(run.command, restart_count=run.restart_count + 1)
            except Exception:
                pass

    def _notify_discord(self, run: CommandRun):
        url = getattr(settings, 'DISCORD_WEBHOOK_URL', None)
        if not url:
            return
        text = f"Command '{run.command}' on site '{run.command.site}' died unexpectedly and will be restarted."
        try:
            requests.post(url, json={'content': text}, timeout=5)
        except Exception:
            pass

    def start_command(self, command: Command, restart_count: int = 0) -> CommandRun:
        site = command.site
        # Build full command line
        cmd_line = f"{site.base_command} {command.command_string}" if site.base_command else command.command_string

        # Sanitize: remove leading sudo tokens so we don't depend on sudo being available
        try:
            parts = shlex.split(cmd_line)
        except Exception:
            parts = cmd_line.split()

        while parts and parts[0] == 'sudo':
            parts.pop(0)

        # Ensure the executable exists on PATH (check first token)
        if parts:
            exe = parts[0]
            # If command is a shell built-in/compound, skip check; otherwise verify presence
            if shutil.which(exe) is None:
                # Log the failure and avoid tight restart loops
                Log.objects.create(
                    site=site,
                    command=command,
                    level='ERROR',
                    message=f"Executable not found: '{exe}' when attempting to start command: {cmd_line}",
                )
                raise RuntimeError(f"Executable not found: {exe}")

        # Start the process
        proc = subprocess.Popen(cmd_line, shell=True, cwd=site.base_dir or None, preexec_fn=os.setsid)
        run = CommandRun.objects.create(
            command=command,
            pid=proc.pid,
            restart_count=restart_count,
            manually_stopped=False,
        )
        return run

    def stop_command(self, command: Command) -> None:
        runs = CommandRun.objects.filter(command=command, stopped_at__isnull=True)
        for run in runs:
            pid = run.pid
            run.manually_stopped = True
            try:
                if pid:
                    os.killpg(pid, signal.SIGTERM)
            except Exception:
                pass
            run.stopped_at = timezone.now()
            run.save()


supervisor = ProcessSupervisor()
