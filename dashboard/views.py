from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Site, Command, Log
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseForbidden, HttpResponse
from .supervisor import supervisor
from django.contrib import messages
from .models import Log


class SiteListView(LoginRequiredMixin, ListView):
    model = Site
    template_name = 'dashboard/sites/list.html'
    context_object_name = 'sites'


class SiteCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Site
    fields = ['name', 'base_dir', 'base_command']
    template_name = 'dashboard/sites/form.html'
    success_url = reverse_lazy('dashboard:site_list')
    permission_required = 'dashboard.add_site'


class SiteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Site
    fields = ['name', 'base_dir', 'base_command']
    template_name = 'dashboard/sites/form.html'
    success_url = reverse_lazy('dashboard:site_list')
    permission_required = 'dashboard.change_site'


class SiteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Site
    template_name = 'dashboard/sites/confirm_delete.html'
    success_url = reverse_lazy('dashboard:site_list')
    permission_required = 'dashboard.delete_site'


class CommandListView(LoginRequiredMixin, ListView):
    model = Command
    template_name = 'dashboard/commands/list.html'
    context_object_name = 'commands'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # identify running commands
        running = set()
        for c in ctx['commands']:
            runs = c.runs.filter(stopped_at__isnull=True)
            if runs.exists():
                running.add(c.id)
        ctx['running_command_ids'] = running
        return ctx


class CommandCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Command
    fields = ['site', 'name', 'command_string', 'active']
    template_name = 'dashboard/commands/form.html'
    success_url = reverse_lazy('dashboard:command_list')
    permission_required = 'dashboard.add_command'


class CommandUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Command
    fields = ['site', 'name', 'command_string', 'active']
    template_name = 'dashboard/commands/form.html'
    success_url = reverse_lazy('dashboard:command_list')
    permission_required = 'dashboard.change_command'


class CommandDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Command
    template_name = 'dashboard/commands/confirm_delete.html'
    success_url = reverse_lazy('dashboard:command_list')
    permission_required = 'dashboard.delete_command'


class LogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Log
    template_name = 'dashboard/logs/list.html'
    context_object_name = 'logs'
    permission_required = 'dashboard.view_logs'

    def get_queryset(self):
        qs = super().get_queryset().order_by('-created_at')
        site_id = self.request.GET.get('site')
        cmd_id = self.request.GET.get('command')
        if site_id:
            qs = qs.filter(site_id=site_id)
        if cmd_id:
            qs = qs.filter(command_id=cmd_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sites'] = Site.objects.all()
        ctx['all_commands'] = Command.objects.all()
        return ctx


@login_required
@permission_required('dashboard.add_command', raise_exception=True)
def start_command_view(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden('POST required')
    cmd = get_object_or_404(Command, pk=pk)
    # First, aggressively kill any lingering system processes for this command
    try:
        from .supervisor import _kill_matching_processes
        patterns = []
        if cmd.site.base_command:
            patterns.append(f"{cmd.site.base_command} {cmd.command_string}")
        patterns.append(cmd.command_string)
        patterns.append(f"manage.py {cmd.command_string}")
        _kill_matching_processes(patterns, site=cmd.site, command_obj=cmd)
    except Exception:
        pass

    # ensure only one running in DB after cleanup
    active = cmd.runs.filter(stopped_at__isnull=True)
    if active.exists():
        messages.info(request, f"Command '{cmd.name}' already running after cleanup.")
        return redirect('dashboard:command_list')
    try:
        supervisor.start_command(cmd)
        messages.success(request, f"Started command '{cmd.name}'.")
    except RuntimeError as e:
        # Log the error to the Log model and show message to user
        Log.objects.create(site=cmd.site, command=cmd, level='ERROR', message=str(e))
        messages.error(request, f"Could not start command: {e}")
    return redirect('dashboard:command_list')


@login_required
@permission_required('dashboard.delete_command', raise_exception=True)
def stop_command_view(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden('POST required')
    cmd = get_object_or_404(Command, pk=pk)
    supervisor.stop_command(cmd)
    return redirect('dashboard:command_list')

