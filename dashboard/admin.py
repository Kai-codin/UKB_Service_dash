from django.contrib import admin
from .models import Site, Command, Log
from .models import CommandRun


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_dir', 'base_command')


@admin.register(Command)
class CommandAdmin(admin.ModelAdmin):
    list_display = ('name', 'site', 'command_string', 'active')
    list_filter = ('site', 'active')


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'site', 'command', 'level')
    list_filter = ('level', 'site')
    readonly_fields = ('created_at', 'message')


@admin.register(CommandRun)
class CommandRunAdmin(admin.ModelAdmin):
    list_display = ('command', 'pid', 'started_at', 'stopped_at', 'manually_stopped', 'killed', 'restart_count')
    list_filter = ('manually_stopped', 'command__site', 'killed')
    readonly_fields = ('pid', 'started_at', 'stopped_at', 'exit_code', 'restart_count', 'killed')
