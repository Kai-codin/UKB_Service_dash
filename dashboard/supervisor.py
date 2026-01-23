import os
import signal
import subprocess
import threading
import time
from datetime import datetime
import shlex
import shutil
import sys

from django.conf import settings
from django.utils import timezone
from django.db import close_old_connections

from .models import CommandRun, Command, Log, Site

import requests


def _try_kill_pid(pid: int, sig=signal.SIGTERM, wait: float = 1.0) -> None:
    try:
        # Try killing the process group first (covers children)
        os.killpg(pid, sig)
    except Exception:
        try:
            os.kill(pid, sig)
        except Exception:
            return

    # wait briefly for process to exit
    if wait and _process_exists(pid):
        end = time.time() + wait
        while time.time() < end:
            if not _process_exists(pid):
                return
            time.sleep(0.1)
        # force kill if still alive
        try:
            os.killpg(pid, signal.SIGKILL)
        except Exception:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass


    def _kill_matching_processes(patterns: list, site: Site = None, command_obj: Command = None) -> None:
        """Aggressively kill processes whose command line matches any pattern.

        Tries to use psutil when available; otherwise falls back to `pgrep -f`.
        """
        pids = set()

        # Try psutil first
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info.get('cmdline') or [])
                    if not cmdline:
                        continue
                    for pat in patterns:
                        if pat in cmdline:
                            pids.add(proc.info['pid'])
                            break
                except Exception:
                    continue
        except Exception:
            # Fallback: use pgrep -f to find pids for each pattern
            for pat in patterns:
                try:
                    cmd = f"pgrep -f {shlex.quote(pat)}"
                    out = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if out.returncode == 0 and out.stdout:
                        for line in out.stdout.splitlines():
                            try:
                                pids.add(int(line.strip()))
                            except Exception:
                                continue
                except Exception:
                    continue

        for pid in list(pids):
            try:
                Log.objects.create(site=site, command=command_obj, level='INFO', message=f'Killing matched process before restart: pid={pid}')
            except Exception:
                pass
            try:
                _try_kill_pid(pid, signal.SIGTERM, wait=2.0)
            except Exception:
                pass
            # mark any DB runs with this pid as stopped
            try:
                runs = CommandRun.objects.filter(pid=pid, stopped_at__isnull=True)
                for r in runs:
                    try:
                        r.stopped_at = timezone.now()
                        r.save()
                    except Exception:
                        pass
            except Exception:
                pass


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
                # If docker (or sudo + docker) was expected, try a safe fallback: run the command via the venv python manage.py
                if 'docker' in exe or 'docker' in cmd_line or exe == 'sudo':
                    try:
                        py = sys.executable
                        # If the command_string looks like a manage.py subcommand, use that
                        fallback_cmd = f"{shlex.quote(py)} manage.py {command.command_string}"
                        proc = subprocess.Popen(fallback_cmd, shell=True, cwd=site.base_dir or None, preexec_fn=os.setsid)
                        run = CommandRun.objects.create(
                            command=command,
                            pid=proc.pid,
                            restart_count=restart_count,
                            manually_stopped=False,
                        )
                        Log.objects.create(site=site, command=command, level='WARNING', message=f"Fell back to local manage.py for command: {command.command_string}")
                        return run
                    except Exception as e:
                        Log.objects.create(site=site, command=command, level='ERROR', message=f"Fallback to local manage.py failed: {e}")
                        raise RuntimeError(f"Executable not found: {exe}")
                # Otherwise fail
                raise RuntimeError(f"Executable not found: {exe}")

        # If this is an automatic restart, ensure we kill any other active runs
        if restart_count and restart_count > 0:
            try:
                # build patterns to search for existing processes
                patterns = [cmd_line, command.command_string, f"manage.py {command.command_string}"]
                _kill_matching_processes(patterns, site=site, command_obj=command)
            except Exception:
                pass

        # Start the process (capture output)
        proc = subprocess.Popen(
            cmd_line,
            shell=True,
            cwd=site.base_dir or None,
            preexec_fn=os.setsid,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        run = CommandRun.objects.create(
            command=command,
            pid=proc.pid,
            restart_count=restart_count,
            manually_stopped=False,
        )

        # start background threads to stream output and monitor process
        threading.Thread(target=self._monitor_process, args=(proc, site, command, run), daemon=True).start()
        return run

    def _monitor_process(self, proc: subprocess.Popen, site: Site, command: Command, run: CommandRun):
        # Ensure DB connections are usable in this thread
        close_old_connections()

        def _read_stream(stream, level):
            try:
                for line in iter(stream.readline, ''):
                    text = line.rstrip('\n')
                    if text:
                        Log.objects.create(site=site, command=command, level=level, message=text)
            except Exception:
                pass
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        # Start readers
        if proc.stdout:
            threading.Thread(target=_read_stream, args=(proc.stdout, 'INFO'), daemon=True).start()
        if proc.stderr:
            threading.Thread(target=_read_stream, args=(proc.stderr, 'ERROR'), daemon=True).start()

        # Wait for process to finish
        try:
            ret = proc.wait()
        except Exception as e:
            ret = None

        # Record stop
        run.stopped_at = timezone.now()
        run.exit_code = ret
        run.save()

        # Log exit
        Log.objects.create(site=site, command=command, level='INFO', message=f'Process exited with code {ret}')

        # Auto-restart if not manually stopped
        if not run.manually_stopped:
            Log.objects.create(site=site, command=command, level='WARNING', message='Process died unexpectedly; attempting restart')
            try:
                self.start_command(command, restart_count=run.restart_count + 1)
            except Exception:
                Log.objects.create(site=site, command=command, level='ERROR', message='Restart attempt failed')

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
