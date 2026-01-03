"""Основные команды для работы с репозиториями."""

import fnmatch
from pathlib import Path
from urllib.parse import urlparse

import click
from git.exc import GitCommandError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from gramax_sync.core.adapters import (
    ConfigManagerAdapter,
    GitOperationsAdapter,
    WorkspaceManagerAdapter,
)
from gramax_sync.core.protocols import (
    ConfigManagerProtocol,
    GitOperationsProtocol,
    WorkspaceManagerProtocol,
)
from gramax_sync.exceptions import ConfigurationError, GitOperationError
from gramax_sync.utils.logging import get_logger

# Импортируем модули для обратной совместимости с остальными командами
# TODO: Рефакторить остальные команды с использованием DI
import gramax_sync.config.config_manager as config_manager_module
import gramax_sync.git.operations as git_operations_module
import gramax_sync.git.status as git_status_module
import gramax_sync.workspace.manager as workspace_manager_module

# Используем функции через модули для возможности патчинга в тестах
require_config = config_manager_module.require_config
clone_repository = git_operations_module.clone_repository
commit_repository = git_operations_module.commit_repository
pull_repository = git_operations_module.pull_repository
push_repository = git_operations_module.push_repository
get_repository_status = git_status_module.get_repository_status
ensure_workspace_structure = workspace_manager_module.ensure_workspace_structure
list_repositories = workspace_manager_module.list_repositories

console = Console()
logger = get_logger(__name__)


@click.group()
def main_group() -> None:
    """Основные команды для работы с репозиториями."""
    pass


@main_group.command()
@click.option(
    "--section",
    help="Фильтр по секции (glob pattern, например: '1-*')",
    default=None,
)
@click.option(
    "--catalog",
    help="Фильтр по каталогу (glob pattern, например: 'ritm-*')",
    default=None,
)
def clone(
    section: str | None = None,
    catalog: str | None = None,
    config_manager: ConfigManagerProtocol | None = None,
    workspace_manager: WorkspaceManagerProtocol | None = None,
    git_operations: GitOperationsProtocol | None = None,
) -> None:
    """Клонировать все репозитории из конфигурации.

    Args:
        section: Фильтр по секции (glob pattern)
        catalog: Фильтр по каталогу (glob pattern)
        config_manager: Менеджер конфигурации (для тестирования)
        workspace_manager: Менеджер workspace (для тестирования)
        git_operations: Git операции (для тестирования)
    """
    # Используем DI или создаём дефолтные реализации
    config_manager = config_manager or ConfigManagerAdapter()
    workspace_manager = workspace_manager or WorkspaceManagerAdapter()
    git_operations = git_operations or GitOperationsAdapter()

    logger.log_operation(
        "clone_start",
        section=section,
        catalog=catalog,
    )

    try:
        config = config_manager.require_config()
    except FileNotFoundError as e:
        error = ConfigurationError(
            str(e),
            context={"operation": "clone"},
        )
        logger.error("clone_config_error", error=str(e))
        console.print(f"[red]❌ {error.message}[/red]")
        console.print("[yellow]Запустите 'gramax-sync init' для первоначальной настройки[/yellow]")
        raise click.Abort() from error

    # Создаём структуру workspace
    from gramax_sync.config.models import Workspace

    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )

    try:
        workspace_manager.ensure_workspace_structure(workspace)
    except OSError as e:
        error = GitOperationError(
            f"Не удалось создать структуру workspace: {e}",
            operation="ensure_workspace_structure",
            context={"workspace_dir": config.workspace_dir},
        )
        logger.error("clone_workspace_error", error=str(e), workspace_dir=config.workspace_dir)
        console.print(f"[red]❌ {error.message}[/red]")
        raise click.Abort() from error

    # Получаем список репозиториев
    repositories = workspace_manager.list_repositories(workspace)

    # Фильтруем репозитории
    if section:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(s, section)
        ]
    if catalog:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(c, catalog)
        ]

    if not repositories:
        console.print("[yellow]⚠️  Нет репозиториев для клонирования[/yellow]")
        logger.log_operation("clone_no_repositories", section=section, catalog=catalog)
        return

    console.print(f"[green]📦 Клонирование {len(repositories)} репозиториев...[/green]")
    logger.log_operation("clone_repositories_found", count=len(repositories))

    # Получаем токен для добавления в URL клонирования
    from gramax_sync.auth.token_manager import TokenManager
    token = TokenManager.get_token(config.base_url)
    
    # Клонируем репозитории
    success_count = 0
    skip_count = 0
    error_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for section_name, catalog_name, repo_path in repositories:
            task = progress.add_task(
                f"[cyan]Клонирование {section_name}/{catalog_name}...",
                total=None,
            )

            # Формируем URL репозитория с токеном для аутентификации
            base_repo_url = f"{config.base_url}/ritm-authors/{catalog_name}"
            if token:
                # Добавляем токен в URL для аутентификации Git
                # Формат: https://oauth2:TOKEN@gitlab.example.com/path/to/repo
                parsed = urlparse(base_repo_url)
                repo_url = f"{parsed.scheme}://oauth2:{token}@{parsed.netloc}{parsed.path}"
            else:
                repo_url = base_repo_url

            try:
                # Проверяем, существует ли уже репозиторий
                if repo_path.exists() and (repo_path / ".git").exists():
                    progress.update(
                        task,
                        description=f"[yellow]⏭️  {section_name}/{catalog_name} уже существует[/yellow]",
                    )
                    skip_count += 1
                    logger.log_operation(
                        "clone_repository_skipped",
                        section=section_name,
                        catalog=catalog_name,
                        reason="already_exists",
                    )
                else:
                    git_operations.clone_repository(repo_url, repo_path, config.catalog_branch)
                    progress.update(
                        task,
                        description=f"[green]✅ {section_name}/{catalog_name} клонирован[/green]",
                    )
                    success_count += 1
                    logger.log_operation(
                        "clone_repository_success",
                        section=section_name,
                        catalog=catalog_name,
                        url=repo_url,
                        branch=config.catalog_branch,
                    )
            except GitCommandError as e:
                error = GitOperationError(
                    str(e),
                    repository=str(repo_path),
                    operation="clone",
                    context={
                        "section": section_name,
                        "catalog": catalog_name,
                        "url": repo_url,
                        "branch": config.catalog_branch,
                    },
                )
                logger.error(
                    "clone_repository_error",
                    section=section_name,
                    catalog=catalog_name,
                    error=str(e),
                    error_type="GitCommandError",
                )
                progress.update(
                    task,
                    description=f"[red]❌ {section_name}/{catalog_name} ошибка: {str(e)[:50]}[/red]",
                )
                error_count += 1
            except Exception as e:
                error = GitOperationError(
                    f"Неожиданная ошибка: {e}",
                    repository=str(repo_path),
                    operation="clone",
                    context={
                        "section": section_name,
                        "catalog": catalog_name,
                        "url": repo_url,
                    },
                )
                logger.error(
                    "clone_repository_unexpected_error",
                    section=section_name,
                    catalog=catalog_name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                progress.update(
                    task,
                    description=f"[red]❌ {section_name}/{catalog_name} ошибка: {str(e)[:50]}[/red]",
                )
                error_count += 1

    # Выводим итоги
    console.print("\n[bold]Итоги клонирования:[/bold]")
    console.print(f"  [green]✅ Успешно: {success_count}[/green]")
    if skip_count > 0:
        console.print(f"  [yellow]⏭️  Пропущено: {skip_count}[/yellow]")
    if error_count > 0:
        console.print(f"  [red]❌ Ошибок: {error_count}[/red]")

    logger.log_operation(
        "clone_complete",
        success_count=success_count,
        skip_count=skip_count,
        error_count=error_count,
    )


@main_group.command()
@click.option(
    "--section",
    help="Фильтр по секции (glob pattern, например: '1-*')",
    default=None,
)
@click.option(
    "--catalog",
    help="Фильтр по каталогу (glob pattern, например: 'ritm-*')",
    default=None,
)
def status(section: str | None, catalog: str | None) -> None:
    """Показать статус всех репозиториев."""
    try:
        config = require_config()
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        console.print("[yellow]Запустите 'gramax-sync init' для первоначальной настройки[/yellow]")
        raise click.Abort()

    from gramax_sync.config.models import Workspace

    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )

    # Получаем список репозиториев
    repositories = list_repositories(workspace)

    # Фильтруем репозитории
    if section:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(s, section)
        ]
    if catalog:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(c, catalog)
        ]

    if not repositories:
        console.print("[yellow]⚠️  Нет репозиториев для проверки[/yellow]")
        return

    # Определяем статусы
    status_data: list[tuple[str, str, str, str]] = []
    for section_name, catalog_name, repo_path in repositories:
        status = get_repository_status(repo_path)
        status_data.append((section_name, catalog_name, status, str(repo_path)))

    # Создаём таблицу
    table = Table(title="Статус репозиториев", show_header=True, header_style="bold magenta")
    table.add_column("Секция", style="cyan", no_wrap=True)
    table.add_column("Каталог", style="cyan", no_wrap=True)
    table.add_column("Статус", style="bold")
    table.add_column("Путь", style="dim")

    # Цветовое кодирование статусов
    status_colors = {
        "clean": "green",
        "modified": "yellow",
        "ahead": "blue",
        "behind": "magenta",
        "diverged": "red",
        "error": "red",
        "not_found": "dim",
    }

    status_labels = {
        "clean": "✅ Чистый",
        "modified": "📝 Изменён",
        "ahead": "⬆️  Впереди",
        "behind": "⬇️  Отстаёт",
        "diverged": "⚠️  Разошёлся",
        "error": "❌ Ошибка",
        "not_found": "❓ Не найден",
    }

    for section_name, catalog_name, status, path in status_data:
        color = status_colors.get(status, "white")
        label = status_labels.get(status, status)
        table.add_row(
            section_name,
            catalog_name,
            f"[{color}]{label}[/{color}]",
            path,
        )

    console.print(table)

    # Статистика
    status_counts = {}
    for _, _, status, _ in status_data:
        status_counts[status] = status_counts.get(status, 0) + 1

    console.print("\n[bold]Статистика:[/bold]")
    for status, count in sorted(status_counts.items()):
        color = status_colors.get(status, "white")
        label = status_labels.get(status, status)
        console.print(f"  [{color}]{label}: {count}[/{color}]")


@main_group.command()
@click.option(
    "--section",
    help="Фильтр по секции (glob pattern, например: '1-*')",
    default=None,
)
@click.option(
    "--catalog",
    help="Фильтр по каталогу (glob pattern, например: 'ritm-*')",
    default=None,
)
def pull(section: str | None, catalog: str | None) -> None:
    """Обновить все репозитории."""
    try:
        config = require_config()
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        console.print("[yellow]Запустите 'gramax-sync init' для первоначальной настройки[/yellow]")
        raise click.Abort()

    from gramax_sync.config.models import Workspace

    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )

    # Получаем список репозиториев
    repositories = list_repositories(workspace)

    # Фильтруем репозитории
    if section:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(s, section)
        ]
    if catalog:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(c, catalog)
        ]

    if not repositories:
        console.print("[yellow]⚠️  Нет репозиториев для обновления[/yellow]")
        return

    console.print(f"[green]🔄 Обновление {len(repositories)} репозиториев...[/green]")

    # Обновляем репозитории
    success_count = 0
    skip_count = 0
    error_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for section_name, catalog_name, repo_path in repositories:
            task = progress.add_task(
                f"[cyan]Обновление {section_name}/{catalog_name}...",
                total=None,
            )

            try:
                # Проверяем существование репозитория
                if not repo_path.exists() or not (repo_path / ".git").exists():
                    progress.update(
                        task,
                        description=f"[yellow]⏭️  {section_name}/{catalog_name} не найден (запустите clone)[/yellow]",
                    )
                    skip_count += 1
                    continue

                # Проверяем статус перед pull
                status = get_repository_status(repo_path)
                if status == "modified":
                    progress.update(
                        task,
                        description=f"[yellow]⏭️  {section_name}/{catalog_name} имеет незакоммиченные изменения[/yellow]",
                    )
                    skip_count += 1
                    continue

                pull_repository(repo_path, config.catalog_branch)
                progress.update(
                    task,
                    description=f"[green]✅ {section_name}/{catalog_name} обновлён[/green]",
                )
                success_count += 1
            except GitCommandError as e:
                error_msg = str(e)
                if "conflict" in error_msg.lower():
                    progress.update(
                        task,
                        description=f"[red]⚠️  {section_name}/{catalog_name} конфликты при слиянии[/red]",
                    )
                else:
                    progress.update(
                        task,
                        description=f"[red]❌ {section_name}/{catalog_name} ошибка: {error_msg[:50]}[/red]",
                    )
                error_count += 1
            except Exception as e:
                progress.update(
                    task,
                    description=f"[red]❌ {section_name}/{catalog_name} ошибка: {str(e)[:50]}[/red]",
                )
                error_count += 1

    # Выводим итоги
    console.print("\n[bold]Итоги обновления:[/bold]")
    console.print(f"  [green]✅ Успешно: {success_count}[/green]")
    if skip_count > 0:
        console.print(f"  [yellow]⏭️  Пропущено: {skip_count}[/yellow]")
    if error_count > 0:
        console.print(f"  [red]❌ Ошибок: {error_count}[/red]")


@main_group.command()
@click.option(
    "--message",
    "-m",
    help="Сообщение коммита (иначе автогенерация)",
    default=None,
)
@click.option(
    "--section",
    help="Фильтр по секции (glob pattern, например: '1-*')",
    default=None,
)
@click.option(
    "--catalog",
    help="Фильтр по каталогу (glob pattern, например: 'ritm-*')",
    default=None,
)
@click.option(
    "--add-all",
    "-a",
    "add_all",
    is_flag=True,
    default=True,
    help="Добавить все файлы перед коммитом (по умолчанию включено)",
)
@click.option(
    "--no-add",
    is_flag=True,
    default=False,
    help="Не добавлять файлы автоматически",
)
def commit(
    message: str | None,
    section: str | None,
    catalog: str | None,
    add_all: bool,
    no_add: bool,
) -> None:
    """Закоммитить изменения во всех репозиториях."""
    try:
        config = require_config()
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        console.print("[yellow]Запустите 'gramax-sync init' для первоначальной настройки[/yellow]")
        raise click.Abort()

    from gramax_sync.config.models import Workspace

    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )

    # Получаем список репозиториев
    repositories = list_repositories(workspace)

    # Фильтруем репозитории
    if section:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(s, section)
        ]
    if catalog:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(c, catalog)
        ]

    if not repositories:
        console.print("[yellow]⚠️  Нет репозиториев для коммита[/yellow]")
        return

    # Определяем, нужно ли добавлять файлы
    should_add = add_all and not no_add

    console.print(f"[green]📝 Коммит изменений в {len(repositories)} репозиториях...[/green]")

    # Коммитим изменения
    success_count = 0
    skip_count = 0
    error_count = 0
    commits_info: list[tuple[str, str, str]] = []  # (section, catalog, commit_hash)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for section_name, catalog_name, repo_path in repositories:
            task = progress.add_task(
                f"[cyan]Коммит {section_name}/{catalog_name}...",
                total=None,
            )

            try:
                # Проверяем существование репозитория
                if not repo_path.exists() or not (repo_path / ".git").exists():
                    progress.update(
                        task,
                        description=f"[yellow]⏭️  {section_name}/{catalog_name} не найден (запустите clone)[/yellow]",
                    )
                    skip_count += 1
                    continue

                # Проверяем, есть ли изменения
                status = get_repository_status(repo_path)
                if status not in ("modified", "ahead"):
                    progress.update(
                        task,
                        description=f"[yellow]⏭️  {section_name}/{catalog_name} нет изменений[/yellow]",
                    )
                    skip_count += 1
                    continue

                # Выполняем коммит
                commit_hash = commit_repository(repo_path, message, should_add)

                if commit_hash is None:
                    progress.update(
                        task,
                        description=f"[yellow]⏭️  {section_name}/{catalog_name} нет изменений для коммита[/yellow]",
                    )
                    skip_count += 1
                else:
                    short_hash = commit_hash[:7]
                    progress.update(
                        task,
                        description=f"[green]✅ {section_name}/{catalog_name} закоммичен ({short_hash})[/green]",
                    )
                    success_count += 1
                    commits_info.append((section_name, catalog_name, short_hash))
            except GitCommandError as e:
                error_msg = str(e)
                progress.update(
                    task,
                    description=f"[red]❌ {section_name}/{catalog_name} ошибка: {error_msg[:50]}[/red]",
                )
                error_count += 1
            except Exception as e:
                progress.update(
                    task,
                    description=f"[red]❌ {section_name}/{catalog_name} ошибка: {str(e)[:50]}[/red]",
                )
                error_count += 1

    # Выводим итоги
    console.print("\n[bold]Итоги коммита:[/bold]")
    console.print(f"  [green]✅ Успешно: {success_count}[/green]")
    if skip_count > 0:
        console.print(f"  [yellow]⏭️  Пропущено: {skip_count}[/yellow]")
    if error_count > 0:
        console.print(f"  [red]❌ Ошибок: {error_count}[/red]")

    # Выводим информацию о коммитах
    if commits_info:
        console.print("\n[bold]Созданные коммиты:[/bold]")
        current_section = None
        for section_name, catalog_name, commit_hash in commits_info:
            if current_section != section_name:
                console.print(f"\n[cyan]📂 {section_name}/[/cyan]")
                current_section = section_name
            console.print(f"  [green]✓[/green] {catalog_name} → {commit_hash}")


@main_group.command()
@click.option(
    "--section",
    help="Фильтр по секции (glob pattern, например: '1-*')",
    default=None,
)
@click.option(
    "--catalog",
    help="Фильтр по каталогу (glob pattern, например: 'ritm-*')",
    default=None,
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Force push (осторожно!)",
)
@click.option(
    "--set-upstream",
    is_flag=True,
    default=False,
    help="Установить upstream для новых веток",
)
def push(
    section: str | None,
    catalog: str | None,
    force: bool,
    set_upstream: bool,
) -> None:
    """Отправить изменения в remote репозитории."""
    try:
        config = require_config()
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        console.print("[yellow]Запустите 'gramax-sync init' для первоначальной настройки[/yellow]")
        raise click.Abort()

    from gramax_sync.config.models import Workspace

    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )

    # Получаем список репозиториев
    repositories = list_repositories(workspace)

    # Фильтруем репозитории
    if section:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(s, section)
        ]
    if catalog:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(c, catalog)
        ]

    if not repositories:
        console.print("[yellow]⚠️  Нет репозиториев для отправки[/yellow]")
        return

    # Предупреждение при force push
    if force:
        if not click.confirm("⚠️  Вы уверены, что хотите выполнить force push?"):
            return

    console.print(f"[green]🚀 Отправка изменений в {len(repositories)} репозиториях...[/green]")

    # Отправляем изменения
    success_count = 0
    skip_count = 0
    error_count = 0
    total_commits = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for section_name, catalog_name, repo_path in repositories:
            task = progress.add_task(
                f"[cyan]Отправка {section_name}/{catalog_name}...",
                total=None,
            )

            try:
                # Проверяем существование репозитория
                if not repo_path.exists() or not (repo_path / ".git").exists():
                    progress.update(
                        task,
                        description=f"[yellow]⏭️  {section_name}/{catalog_name} не найден (запустите clone)[/yellow]",
                    )
                    skip_count += 1
                    continue

                # Проверяем статус перед push
                status = get_repository_status(repo_path)
                if status not in ("ahead", "diverged"):
                    if status == "modified":
                        progress.update(
                            task,
                            description=f"[yellow]⏭️  {section_name}/{catalog_name} имеет незакоммиченные изменения[/yellow]",
                        )
                    else:
                        progress.update(
                            task,
                            description=f"[yellow]⏭️  {section_name}/{catalog_name} нет изменений для отправки[/yellow]",
                        )
                    skip_count += 1
                    continue

                # Выполняем push
                commits_pushed = push_repository(
                    repo_path,
                    config.catalog_branch,
                    force=force,
                    set_upstream=set_upstream,
                )

                if commits_pushed is None:
                    progress.update(
                        task,
                        description=f"[yellow]⏭️  {section_name}/{catalog_name} нет изменений для отправки[/yellow]",
                    )
                    skip_count += 1
                else:
                    total_commits += commits_pushed
                    commit_word = "коммит" if commits_pushed == 1 else "коммитов"
                    progress.update(
                        task,
                        description=f"[green]✅ {section_name}/{catalog_name} → origin/{config.catalog_branch} ({commits_pushed} {commit_word})[/green]",
                    )
                    success_count += 1
            except GitCommandError as e:
                error_msg = str(e)
                progress.update(
                    task,
                    description=f"[red]❌ {section_name}/{catalog_name} ошибка: {error_msg[:50]}[/red]",
                )
                error_count += 1
            except Exception as e:
                progress.update(
                    task,
                    description=f"[red]❌ {section_name}/{catalog_name} ошибка: {str(e)[:50]}[/red]",
                )
                error_count += 1

    # Выводим итоги
    console.print("\n[bold]Итоги отправки:[/bold]")
    console.print(f"  [green]✅ Успешно: {success_count}[/green]")
    if skip_count > 0:
        console.print(f"  [yellow]⏭️  Пропущено: {skip_count}[/yellow]")
    if error_count > 0:
        console.print(f"  [red]❌ Ошибок: {error_count}[/red]")
    if total_commits > 0:
        commit_word = "коммит" if total_commits == 1 else "коммитов"
        console.print(f"  [cyan]📊 Всего коммитов отправлено: {total_commits} {commit_word}[/cyan]")


@main_group.command()
@click.option(
    "--section",
    help="Фильтр по секции (glob pattern, например: '1-*')",
    default=None,
)
@click.option(
    "--catalog",
    help="Фильтр по каталогу (glob pattern, например: 'ritm-*')",
    default=None,
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Предварительный просмотр операций без выполнения",
)
@click.option(
    "--message",
    "-m",
    help="Сообщение коммита (если нужен коммит)",
    default=None,
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Force push (осторожно!)",
)
def sync(
    section: str | None,
    catalog: str | None,
    dry_run: bool,
    message: str | None,
    force: bool,
) -> None:
    """Полная синхронизация репозиториев (pull + commit + push)."""
    try:
        config = require_config()
    except FileNotFoundError as e:
        console.print(f"[red]❌ {e}[/red]")
        console.print("[yellow]Запустите 'gramax-sync init' для первоначальной настройки[/yellow]")
        raise click.Abort()

    from gramax_sync.config.models import Workspace

    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )

    # Получаем список репозиториев
    repositories = list_repositories(workspace)

    # Фильтруем репозитории
    if section:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(s, section)
        ]
    if catalog:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(c, catalog)
        ]

    if not repositories:
        console.print("[yellow]⚠️  Нет репозиториев для синхронизации[/yellow]")
        return

    # Предупреждение при force push
    if force and not dry_run:
        if not click.confirm("⚠️  Вы уверены, что хотите выполнить force push?"):
            return

    if dry_run:
        console.print(f"[cyan]🔍 Предварительный просмотр синхронизации {len(repositories)} репозиториев...[/cyan]")
    else:
        console.print(f"[green]🔄 Синхронизация {len(repositories)} репозиториев...[/green]")

    # Статистика операций
    success_count = 0
    skip_count = 0
    error_count = 0
    pull_count = 0
    commit_count = 0
    push_count = 0
    total_commits_pushed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for section_name, catalog_name, repo_path in repositories:
            task = progress.add_task(
                f"[cyan]Синхронизация {section_name}/{catalog_name}...",
                total=None,
            )

            try:
                # Проверяем существование репозитория
                if not repo_path.exists() or not (repo_path / ".git").exists():
                    progress.update(
                        task,
                        description=f"[yellow]⏭️  {section_name}/{catalog_name} не найден (запустите clone)[/yellow]",
                    )
                    skip_count += 1
                    continue

                # Получаем статус репозитория
                status = get_repository_status(repo_path)

                # Определяем, какие операции нужны
                needs_pull = status in ("behind", "diverged")
                needs_commit = status in ("modified", "ahead", "diverged")
                needs_push = status in ("ahead", "diverged")

                if dry_run:
                    # Dry-run режим: показываем планируемые операции
                    operations = []
                    if needs_pull:
                        operations.append("⬇️  Pull: будет выполнено")
                    else:
                        operations.append("⬇️  Pull: пропущено (нет обновлений)")
                    if needs_commit:
                        operations.append("📝 Commit: будет выполнено")
                    else:
                        operations.append("📝 Commit: пропущено (нет изменений)")
                    if needs_push:
                        operations.append("⬆️  Push: будет выполнено")
                    else:
                        operations.append("⬆️  Push: пропущено (нет unpushed commits)")

                    progress.update(
                        task,
                        description=f"[cyan]{section_name}/{catalog_name}[/cyan]",
                    )
                    # Выводим операции после обновления задачи
                    for op in operations:
                        console.print(f"  {op}")
                else:
                    # Реальный режим: выполняем операции
                    operations_log = []
                    repo_has_error = False

                    # 1. Pull
                    if needs_pull:
                        try:
                            pull_repository(repo_path, config.catalog_branch)
                            pull_count += 1
                            operations_log.append("⬇️  Pull: обновлён")
                        except GitCommandError as e:
                            if "conflict" in str(e).lower():
                                operations_log.append("⬇️  Pull: конфликты при слиянии")
                            else:
                                operations_log.append(f"⬇️  Pull: ошибка ({str(e)[:30]})")
                            repo_has_error = True
                            error_count += 1
                    else:
                        operations_log.append("⬇️  Pull: нет обновлений")

                    # 2. Commit (только если нет ошибок после pull)
                    if needs_commit and not repo_has_error:
                        try:
                            # Обновляем статус после pull
                            status_after_pull = get_repository_status(repo_path)
                            if status_after_pull in ("modified", "ahead", "diverged"):
                                commit_hash = commit_repository(repo_path, message, add_all=True)
                                if commit_hash:
                                    commit_count += 1
                                    short_hash = commit_hash[:7]
                                    operations_log.append(f"📝 Commit: закоммичен ({short_hash})")
                                else:
                                    operations_log.append("📝 Commit: нет изменений")
                            else:
                                operations_log.append("📝 Commit: нет изменений")
                        except GitCommandError as e:
                            operations_log.append(f"📝 Commit: ошибка ({str(e)[:30]})")
                            repo_has_error = True
                            error_count += 1
                    else:
                        if not repo_has_error:
                            operations_log.append("📝 Commit: нет изменений")

                    # 3. Push (только если нет ошибок)
                    if needs_push and not repo_has_error:
                        try:
                            # Обновляем статус после commit
                            status_after_commit = get_repository_status(repo_path)
                            if status_after_commit in ("ahead", "diverged"):
                                commits_pushed = push_repository(
                                    repo_path,
                                    config.catalog_branch,
                                    force=force,
                                    set_upstream=False,
                                )
                                if commits_pushed:
                                    push_count += 1
                                    total_commits_pushed += commits_pushed
                                    commit_word = "коммит" if commits_pushed == 1 else "коммитов"
                                    operations_log.append(f"⬆️  Push: отправлено ({commits_pushed} {commit_word})")
                                else:
                                    operations_log.append("⬆️  Push: нет изменений для отправки")
                            else:
                                operations_log.append("⬆️  Push: нет изменений для отправки")
                        except GitCommandError as e:
                            operations_log.append(f"⬆️  Push: ошибка ({str(e)[:30]})")
                            repo_has_error = True
                            error_count += 1
                    else:
                        if not repo_has_error:
                            operations_log.append("⬆️  Push: нет изменений для отправки")

                    # Обновляем прогресс с результатами
                    if not repo_has_error:
                        progress.update(
                            task,
                            description=f"[green]✅ {section_name}/{catalog_name}[/green]",
                        )
                        success_count += 1
                    else:
                        progress.update(
                            task,
                            description=f"[red]❌ {section_name}/{catalog_name}[/red]",
                        )

                    # Выводим операции
                    for op in operations_log:
                        console.print(f"  {op}")

            except Exception as e:
                progress.update(
                    task,
                    description=f"[red]❌ {section_name}/{catalog_name} ошибка: {str(e)[:50]}[/red]",
                )
                error_count += 1

    # Выводим итоги
    console.print("\n[bold]Итоги синхронизации:[/bold]")
    console.print(f"  [green]✅ Успешно: {success_count}[/green]")
    if skip_count > 0:
        console.print(f"  [yellow]⏭️  Пропущено: {skip_count}[/yellow]")
    if error_count > 0:
        console.print(f"  [red]❌ Ошибок: {error_count}[/red]")
    if not dry_run:
        console.print(f"  [cyan]⬇️  Pull: {pull_count} обновлён[/cyan]")
        console.print(f"  [cyan]📝 Commit: {commit_count} закоммичен[/cyan]")
        console.print(f"  [cyan]⬆️  Push: {push_count} отправлено[/cyan]")
        if total_commits_pushed > 0:
            commit_word = "коммит" if total_commits_pushed == 1 else "коммитов"
            console.print(f"  [cyan]📊 Всего коммитов отправлено: {total_commits_pushed} {commit_word}[/cyan]")

