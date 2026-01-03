"""Команда init для первоначальной настройки."""

import click
from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from gramax_sync.auth.token_manager import TokenManager
from gramax_sync.config.config_manager import save_config
from gramax_sync.config.local_config import LocalConfig
from gramax_sync.config.parser import load_workspace_from_string
from gramax_sync.gitlab.client import GitLabClient
from gramax_sync.gitlab.exceptions import (
    GitLabAuthError,
    GitLabError,
    GitLabNotFoundError,
    GitLabPermissionError,
)
from gramax_sync.utils.selection import (
    display_workspace_structure,
    filter_workspace,
    prompt_catalog_selection,
    prompt_section_selection,
    prompt_selection_mode,
)

console = Console()


@click.command()
@click.option(
    "--repo-url",
    "-r",
    help="URL репозитория с конфигурациями Gramax",
)
@click.option(
    "--branch",
    "-b",
    default="master",
    help="Ветка репозитория конфигураций (по умолчанию: master)",
)
@click.option(
    "--catalog-branch",
    "-c",
    default="private",
    help="Ветка по умолчанию для каталогов (по умолчанию: private)",
)
@click.option(
    "--token",
    "-t",
    help="Personal Access Token (если не указан, будет запрошен)",
)
def init(
    repo_url: str | None,
    branch: str,
    catalog_branch: str,
    token: str | None,
) -> None:
    """Первоначальная настройка gramax-sync.

    Эта команда выполняет:
    1. Подключение к репозиторию с конфигурациями
    2. Проверку доступа и наличия workspace.yaml
    3. Авторизацию при необходимости
    4. Загрузку и отображение структуры
    5. Интерактивный выбор секций/каталогов
    """
    console.print(
        Panel.fit(
            "[bold cyan]🚀 Первоначальная настройка gramax-sync[/bold cyan]",
            border_style="cyan",
        )
    )

    # Шаг 1: Запрос репозитория
    if not repo_url:
        console.print("\n[bold]Шаг 1: Укажите репозиторий с конфигурациями[/bold]")
        repo_url = Prompt.ask(
            "[cyan]URL репозитория[/cyan]",
            default="https://itsmf.gitlab.yandexcloud.net/ritm-authors/gramax-yaml-manager",
        )

    if not repo_url:
        console.print("[red]❌ URL репозитория обязателен[/red]")
        raise click.Abort()

    # Информируем о ветках
    console.print(f"\n[dim]Ветка репозитория конфигураций: [bold]{branch}[/bold][/dim]")
    console.print(f"[dim]Ветка по умолчанию для каталогов: [bold]{catalog_branch}[/bold][/dim]")

    # Извлекаем базовый URL GitLab
    # Сначала извлекаем базовый URL, затем создаём клиент с базовым URL
    parsed = urlparse(repo_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    client = GitLabClient(base_url)

    # Шаг 2: Проверка доступа
    console.print("\n[bold]Шаг 2: Проверка доступа к репозиторию[/bold]")

    # Пытаемся получить сохранённый токен
    saved_token = TokenManager.get_token(base_url)
    if saved_token:
        client.token = saved_token
        client._reset_client()  # Сбрасываем клиент, чтобы он пересоздался с токеном

    # Если токен передан через параметр, используем его
    if token:
        client.token = token
        client._reset_client()  # Сбрасываем клиент, чтобы он пересоздался с токеном

    try:
        # Проверяем доступ к репозиторию
        has_access, error_msg = client.check_repository_access(repo_url, branch)

        if not has_access:
            if error_msg:
                console.print(f"[yellow]⚠️ {error_msg}[/yellow]")
            # Продолжаем, возможно файл просто не найден в этой ветке
        else:
            console.print("[green]✅ Подключение установлено. Файл workspace.yaml найден.[/green]")

    except GitLabAuthError:
        console.print("[yellow]🔒 Требуется авторизация[/yellow]")
        # Шаг 3: Авторизация
        if not token:
            token = TokenManager.prompt_for_token()
        client.token = token
        # Сбрасываем клиент, чтобы он пересоздался с новым токеном
        client._reset_client()

        # Сохраняем токен
        try:
            TokenManager.save_token(base_url, token)
            console.print("[green]✓ Токен успешно сохранён[/green]")
        except Exception as e:
            console.print(f"[yellow]Предупреждение: Не удалось сохранить токен: {e}[/yellow]")

        # Повторная проверка доступа
        try:
            has_access, error_msg = client.check_repository_access(repo_url, branch)
            if not has_access:
                if error_msg:
                    console.print(f"[red]❌ {error_msg}[/red]")
                    raise click.Abort()
            else:
                console.print("[green]✅ Подключение установлено. Файл workspace.yaml найден.[/green]")
        except GitLabPermissionError as e:
            console.print(f"[red]❌ Нет доступа к репозиторию: {e}[/red]")
            raise click.Abort()
        except GitLabNotFoundError as e:
            console.print(f"[red]❌ {e}[/red]")
            raise click.Abort()

    except GitLabPermissionError as e:
        console.print(f"[red]❌ Нет доступа к репозиторию: {e}[/red]")
        raise click.Abort()

    except GitLabNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise click.Abort()

    except GitLabError as e:
        console.print(f"[red]❌ Ошибка при проверке доступа: {e}[/red]")
        raise click.Abort()

    # Шаг 4: Загрузка workspace.yaml
    console.print("\n[bold]Шаг 3: Загрузка конфигурации[/bold]")

    try:
        workspace_content = client.get_workspace_file(repo_url, branch)
        workspace = load_workspace_from_string(workspace_content)
        console.print("[green]✅ Конфигурация загружена[/green]")
    except GitLabError as e:
        console.print(f"[red]❌ Ошибка при загрузке workspace.yaml: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ Ошибка при парсинге workspace.yaml: {e}[/red]")
        raise click.Abort()

    # Шаг 5: Отображение структуры
    display_workspace_structure(workspace)

    # Шаг 6: Интерактивный выбор
    mode = prompt_selection_mode()

    selected_sections = None
    selected_catalogs = None

    if mode == "sections":
        selected_sections = prompt_section_selection(workspace)
        if not selected_sections:
            console.print("[yellow]⚠️ Не выбрано ни одной секции[/yellow]")
            raise click.Abort()

    elif mode == "catalogs":
        selected_catalogs = prompt_catalog_selection(workspace)
        if not selected_catalogs:
            console.print("[yellow]⚠️ Не выбран ни один каталог[/yellow]")
            raise click.Abort()

    # Фильтруем workspace
    filtered_workspace = filter_workspace(
        workspace, mode, selected_sections, selected_catalogs
    )

    # Сохраняем конфигурацию
    local_config = LocalConfig(
        repo_url=repo_url,
        config_branch=branch,
        catalog_branch=catalog_branch,
        base_url=base_url,
        workspace_dir=filtered_workspace.workspace_dir,
        sections=filtered_workspace.sections,
    )

    save_config(local_config)

    console.print("\n[bold green]✅ Настройка завершена успешно![/bold green]")
    console.print("\nТеперь вы можете использовать команды:")
    console.print("  [cyan]gramax-sync clone[/cyan]  - Клонировать репозитории")
    console.print("  [cyan]gramax-sync status[/cyan] - Показать статус")

