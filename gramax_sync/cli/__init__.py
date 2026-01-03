"""CLI команды для gramax-sync."""

import click

from gramax_sync.cli.auth import auth
from gramax_sync.cli.edit import edit
from gramax_sync.cli.init import init
from gramax_sync.cli.main import main_group
from gramax_sync.cli.update import update

__all__ = ["cli", "edit", "init", "update", "auth", "main_group"]


@click.group()
@click.version_option(version="0.1.0", prog_name="gramax-sync")
def cli() -> None:
    """gramax-sync — CLI для управления репозиториями РИТМ."""
    pass


# Регистрируем команды из main_group напрямую для обратной совместимости
# Команды будут доступны как gramax-sync status, а не gramax-sync main status
for command_name in main_group.list_commands(None):
    command = main_group.get_command(None, command_name)
    if command:
        cli.add_command(command, name=command_name)

# Регистрируем остальные команды
cli.add_command(auth)
cli.add_command(edit)
cli.add_command(init)
cli.add_command(update)
