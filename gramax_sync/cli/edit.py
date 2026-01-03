"""Команда edit для редактирования локальной конфигурации."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from gramax_sync.auth.token_manager import TokenManager
from gramax_sync.config.config_manager import load_config, save_config
from gramax_sync.config.local_config import LocalConfig
from gramax_sync.config.models import Catalog, Section, Source, Workspace
from gramax_sync.config.parser import load_workspace_from_string
from gramax_sync.gitlab.client import GitLabClient
from gramax_sync.gitlab.exceptions import GitLabError
from gramax_sync.utils.selection import (
    display_workspace_structure,
    prompt_catalog_selection,
    prompt_section_selection,
    prompt_selection_mode,
)

console = Console()


@click.group()
def edit() -> None:
    """Редактирование локальной конфигурации."""
    pass


@edit.command()
@click.option(
    "--section",
    "-s",
    help="Имя секции для добавления",
)
@click.option(
    "--catalog",
    "-c",
    help="Имя каталога для добавления",
)
@click.option(
    "--source-url",
    help="URL источника для каталога",
)
def add(section: str | None, catalog: str | None, source_url: str | None) -> None:
    """Добавить секцию или каталог в конфигурацию."""
    config = load_config()
    if not config:
        console.print(
            "[red]❌ Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки.[/red]"
        )
        raise click.Abort()

    if section and catalog:
        # Добавляем каталог в секцию
        if not source_url:
            source_url = Prompt.ask("[cyan]URL источника[/cyan]")

        try:
            catalog_obj = Catalog(name=catalog, source=Source(url=source_url))
            if config.add_catalog(section, catalog_obj):
                save_config(config)
                console.print(f"[green]✅ Каталог '{catalog}' добавлен в секцию '{section}'[/green]")
            else:
                console.print(f"[red]❌ Секция '{section}' не найдена[/red]")
                raise click.Abort()
        except ValueError as e:
            console.print(f"[red]❌ {e}[/red]")
            raise click.Abort()

    elif section:
        # Добавляем новую секцию
        try:
            section_obj = Section(name=section, catalogs=[])
            config.add_section(section_obj)
            save_config(config)
            console.print(f"[green]✅ Секция '{section}' добавлена[/green]")
        except ValueError as e:
            console.print(f"[red]❌ {e}[/red]")
            raise click.Abort()

    else:
        # Интерактивный режим
        console.print(
            Panel.fit(
                "[bold cyan]➕ Добавление в конфигурацию[/bold cyan]",
                border_style="cyan",
            )
        )

        # Загружаем доступные секции/каталоги с сервера
        client = GitLabClient(config.base_url)
        saved_token = TokenManager.get_token(config.base_url)
        if saved_token:
            client.token = saved_token

        try:
            workspace_content = client.get_workspace_file(config.repo_url, config.config_branch)
            workspace = load_workspace_from_string(workspace_content)

            console.print("\n[bold]Доступные секции и каталоги на сервере:[/bold]")
            display_workspace_structure(workspace)

            mode = prompt_selection_mode()

            if mode == "sections":
                selected_sections = prompt_section_selection(workspace)
                for section_name in selected_sections:
                    server_section = next(
                        (s for s in workspace.sections if s.name == section_name), None
                    )
                    if server_section:
                        try:
                            config.add_section(server_section)
                        except ValueError:
                            console.print(
                                f"[yellow]⚠️ Секция '{section_name}' уже существует, пропускаем[/yellow]"
                            )

            elif mode == "catalogs":
                selected_catalogs = prompt_catalog_selection(workspace)
                for section_name, catalog_name in selected_catalogs:
                    server_section = next(
                        (s for s in workspace.sections if s.name == section_name), None
                    )
                    if server_section:
                        catalog = next(
                            (c for c in server_section.catalogs if c.name == catalog_name), None
                        )
                        if catalog:
                            try:
                                if config.add_catalog(section_name, catalog):
                                    console.print(
                                        f"[green]✅ Каталог '{catalog_name}' добавлен в секцию '{section_name}'[/green]"
                                    )
                                else:
                                    # Секции нет, создаём её
                                    new_section = Section(name=section_name, catalogs=[catalog])
                                    config.add_section(new_section)
                                    console.print(
                                        f"[green]✅ Секция '{section_name}' и каталог '{catalog_name}' добавлены[/green]"
                                    )
                            except ValueError as e:
                                console.print(f"[yellow]⚠️ {e}[/yellow]")

            save_config(config)
            console.print("\n[bold green]✅ Конфигурация обновлена![/bold green]")

        except GitLabError as e:
            console.print(f"[red]❌ Ошибка при загрузке конфигурации с сервера: {e}[/red]")
            raise click.Abort()


@edit.command()
@click.option(
    "--section",
    "-s",
    required=True,
    help="Имя секции для удаления",
)
@click.option(
    "--catalog",
    "-c",
    help="Имя каталога для удаления (если не указан, удаляется вся секция)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Удалить без подтверждения",
)
def remove(section: str, catalog: str | None, force: bool) -> None:
    """Удалить секцию или каталог из конфигурации."""
    config = load_config()
    if not config:
        console.print(
            "[red]❌ Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки.[/red]"
        )
        raise click.Abort()

    if catalog:
        # Удаляем каталог
        if not force:
            if not Confirm.ask(
                f"[cyan]Удалить каталог '{catalog}' из секции '{section}'?[/cyan]",
                default=False,
            ):
                console.print("[yellow]Удаление отменено[/yellow]")
                raise click.Abort()

        if config.remove_catalog(section, catalog):
            save_config(config)
            console.print(f"[green]✅ Каталог '{catalog}' удалён из секции '{section}'[/green]")
        else:
            console.print(f"[red]❌ Каталог '{catalog}' не найден в секции '{section}'[/red]")
            raise click.Abort()
    else:
        # Удаляем секцию
        if not force:
            if not Confirm.ask(
                f"[cyan]Удалить секцию '{section}' и все её каталоги?[/cyan]",
                default=False,
            ):
                console.print("[yellow]Удаление отменено[/yellow]")
                raise click.Abort()

        if config.remove_section(section):
            save_config(config)
            console.print(f"[green]✅ Секция '{section}' удалена[/green]")
        else:
            console.print(f"[red]❌ Секция '{section}' не найдена[/red]")
            raise click.Abort()


@edit.command()
@click.option(
    "--workspace-dir",
    "-w",
    help="Новая директория для workspace",
)
def set_workspace_dir(workspace_dir: str | None) -> None:
    """Изменить директорию для workspace."""
    config = load_config()
    if not config:
        console.print(
            "[red]❌ Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки.[/red]"
        )
        raise click.Abort()

    if not workspace_dir:
        console.print(
            Panel.fit(
                "[bold cyan]📁 Изменение workspace директории[/bold cyan]",
                border_style="cyan",
            )
        )
        console.print(f"\n[bold]Текущая директория:[/bold] {config.workspace_dir}")
        workspace_dir = Prompt.ask(
            "[cyan]Введите новую директорию для workspace[/cyan]",
            default=config.workspace_dir,
        )

    if not workspace_dir:
        console.print("[red]❌ Директория не может быть пустой[/red]")
        raise click.Abort()

    # Обновляем workspace_dir
    config.workspace_dir = workspace_dir
    save_config(config)
    
    from pathlib import Path
    full_path = Path(workspace_dir).expanduser().absolute()
    console.print(f"[green]✅ Workspace директория изменена на:[/green]")
    console.print(f"  [bold]{workspace_dir}[/bold]")
    console.print(f"  [dim]Полный путь: {full_path}[/dim]")


@edit.command()
def show() -> None:
    """Показать текущую локальную конфигурацию."""
    config = load_config()
    if not config:
        console.print(
            "[red]❌ Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки.[/red]"
        )
        raise click.Abort()

    console.print(
        Panel.fit(
            "[bold cyan]📋 Текущая локальная конфигурация[/bold cyan]",
            border_style="cyan",
        )
    )

    console.print(f"\n[bold]Репозиторий:[/bold] {config.repo_url}")
    console.print(f"[bold]Ветка конфигураций:[/bold] {config.config_branch}")
    console.print(f"[bold]Ветка каталогов:[/bold] {config.catalog_branch}")
    
    from pathlib import Path
    full_path = Path(config.workspace_dir).expanduser().absolute()
    console.print(f"[bold]Workspace директория:[/bold] {config.workspace_dir}")
    console.print(f"[dim]Полный путь: {full_path}[/dim]")

    if config.sections:
        console.print("\n[bold]Секции и каталоги:[/bold]")
        workspace = Workspace(
            workspace_dir=config.workspace_dir, sections=config.sections
        )
        display_workspace_structure(workspace)
    else:
        console.print("\n[yellow]Конфигурация не содержит секций[/yellow]")

