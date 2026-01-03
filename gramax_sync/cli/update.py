"""Команда update для обновления конфигурации с сервера."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from gramax_sync.auth.token_manager import TokenManager
from gramax_sync.config.config_manager import load_config, save_config
from gramax_sync.config.local_config import LocalConfig
from gramax_sync.config.parser import load_workspace_from_string
from gramax_sync.gitlab.client import GitLabClient
from gramax_sync.gitlab.exceptions import (
    GitLabAuthError,
    GitLabError,
    GitLabNotFoundError,
    GitLabPermissionError,
)
from gramax_sync.utils.selection import display_workspace_structure

console = Console()


@click.command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Обновить конфигурацию без подтверждения",
)
def update(force: bool) -> None:
    """Обновить локальную конфигурацию с сервера.

    Команда загружает актуальный workspace.yaml с сервера и обновляет
    локальную конфигурацию, сохраняя выбранные секции и каталоги.
    """
    console.print(
        Panel.fit(
            "[bold cyan]🔄 Обновление конфигурации[/bold cyan]",
            border_style="cyan",
        )
    )

    # Загружаем текущую конфигурацию
    current_config = load_config()
    if not current_config:
        console.print(
            "[red]❌ Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки.[/red]"
        )
        raise click.Abort()

    console.print(f"\n[dim]Репозиторий: {current_config.repo_url}[/dim]")
    console.print(f"[dim]Ветка: {current_config.config_branch}[/dim]")

    # Создаём клиент GitLab
    client = GitLabClient(current_config.base_url)
    saved_token = TokenManager.get_token(current_config.base_url)
    if saved_token:
        client.token = saved_token

    # Загружаем workspace.yaml с сервера
    console.print("\n[bold]Загрузка конфигурации с сервера...[/bold]")

    try:
        workspace_content = client.get_workspace_file(
            current_config.repo_url, current_config.config_branch
        )
        workspace = load_workspace_from_string(workspace_content)
        console.print("[green]✅ Конфигурация загружена с сервера[/green]")
    except GitLabAuthError:
        console.print("[red]❌ Требуется авторизация. Проверьте токен.[/red]")
        raise click.Abort()
    except GitLabError as e:
        console.print(f"[red]❌ Ошибка при загрузке конфигурации: {e}[/red]")
        raise click.Abort()

    # Отображаем новую структуру
    console.print("\n[bold]Новая структура конфигурации:[/bold]")
    display_workspace_structure(workspace)

    # Показываем текущую конфигурацию
    console.print("\n[bold]Текущая локальная конфигурация:[/bold]")
    if current_config.sections:
        from gramax_sync.config.models import Workspace

        current_workspace = Workspace(
            workspace_dir=current_config.workspace_dir, sections=current_config.sections
        )
        display_workspace_structure(current_workspace)
    else:
        console.print("[yellow]Локальная конфигурация пуста[/yellow]")

    # Подтверждение обновления
    if not force:
        if not Confirm.ask("\n[cyan]Обновить локальную конфигурацию?[/cyan]", default=True):
            console.print("[yellow]Обновление отменено[/yellow]")
            raise click.Abort()

    # Обновляем конфигурацию, сохраняя выбранные секции/каталоги
    from gramax_sync.config.models import Section

    # Создаём маппинг текущих секций и каталогов
    current_sections_map = {s.name: s for s in current_config.sections}
    current_catalogs_map: dict[str, dict[str, bool]] = {}
    for section in current_config.sections:
        current_catalogs_map[section.name] = {c.name: True for c in section.catalogs}

    # Обновляем секции, сохраняя только те, что есть в текущей конфигурации
    updated_sections = []
    for server_section in workspace.sections:
        if server_section.name in current_sections_map:
            # Секция есть в текущей конфигурации - обновляем каталоги
            # Сохраняем только каталоги, которые есть и в сервере, и в текущей конфигурации
            updated_catalogs = [
                catalog
                for catalog in server_section.catalogs
                if catalog.name in current_catalogs_map.get(server_section.name, {})
            ]
            if updated_catalogs:
                updated_sections.append(Section(name=server_section.name, catalogs=updated_catalogs))
        # Если секции нет в текущей конфигурации, не добавляем её

    # Создаём обновлённую конфигурацию
    updated_config = LocalConfig(
        repo_url=current_config.repo_url,
        config_branch=current_config.config_branch,
        catalog_branch=current_config.catalog_branch,
        base_url=current_config.base_url,
        workspace_dir=workspace.workspace_dir,
        sections=updated_sections,
    )

    save_config(updated_config)

    console.print("\n[bold green]✅ Конфигурация обновлена успешно![/bold green]")
    console.print(
        "[dim]Примечание: Обновлены только секции и каталоги, которые были в локальной конфигурации.[/dim]"
    )
    console.print(
        "[dim]Для добавления новых секций/каталогов используйте команду 'gramax-sync edit'.[/dim]"
    )

