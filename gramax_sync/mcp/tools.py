"""MCP инструменты для работы с репозиториями."""

import fnmatch
from pathlib import Path

from gramax_sync.config.models import Workspace
from gramax_sync.git.operations import (
    clone_repository,
    commit_repository,
    pull_repository,
    push_repository,
)
from gramax_sync.git.status import get_repository_status as get_git_status
from gramax_sync.mcp.server import mcp, require_mcp_config
from gramax_sync.workspace.manager import ensure_workspace_structure, list_repositories as workspace_list_repositories


@mcp.tool()
def list_repositories(section: str | None = None) -> str:
    """Показать все секции и каталоги из workspace.yaml.
    
    Args:
        section: Фильтр по секции (glob pattern, опционально)
    
    Returns:
        Форматированный список секций и каталогов
    """
    try:
        config = require_mcp_config()
    except FileNotFoundError as e:
        return f"❌ Ошибка: {e}"
    
    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )
    
    # Получаем список репозиториев
    repositories = workspace_list_repositories(workspace)
    
    # Фильтруем по секции, если указана
    if section:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(s, section)
        ]
    
    if not repositories:
        return "⚠️  Нет репозиториев, соответствующих фильтру"
    
    # Форматируем вывод
    result = ["📦 Список репозиториев:\n"]
    current_section = None
    
    for section_name, catalog_name, repo_path in sorted(repositories):
        if current_section != section_name:
            result.append(f"\n📂 {section_name}/")
            current_section = section_name
        result.append(f"  • {catalog_name} ({repo_path})")
    
    result.append(f"\n\nВсего: {len(repositories)} репозиториев")
    return "\n".join(result)


@mcp.tool()
def get_repository_status(section: str | None = None, catalog: str | None = None) -> str:
    """Показать git статус репозиториев.
    
    Args:
        section: Фильтр по секции (glob pattern, опционально)
        catalog: Конкретный каталог (опционально)
    
    Returns:
        Форматированный статус репозиториев
    """
    try:
        config = require_mcp_config()
    except FileNotFoundError as e:
        return f"❌ Ошибка: {e}"
    
    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )
    
    # Получаем список репозиториев
    repositories = workspace_list_repositories(workspace)
    
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
        return "⚠️  Нет репозиториев, соответствующих фильтру"
    
    # Определяем статусы
    result = ["📊 Статус репозиториев:\n"]
    status_counts = {}
    
    for section_name, catalog_name, repo_path in sorted(repositories):
        status = get_git_status(repo_path)
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # Эмодзи для статусов
        status_icons = {
            "clean": "✅",
            "modified": "📝",
            "ahead": "⬆️",
            "behind": "⬇️",
            "diverged": "⚠️",
            "error": "❌",
            "not_found": "❓",
        }
        
        icon = status_icons.get(status, "❓")
        result.append(f"{icon} {section_name}/{catalog_name}: {status}")
    
    # Статистика
    result.append("\n📈 Статистика:")
    for status, count in sorted(status_counts.items()):
        result.append(f"  {status}: {count}")
    
    return "\n".join(result)


@mcp.tool()
def clone_repositories(section: str | None = None) -> str:
    """Клонировать репозитории из workspace.yaml.
    
    Args:
        section: Фильтр по секции (glob pattern, опционально)
    
    Returns:
        Результаты клонирования
    """
    try:
        config = require_mcp_config()
    except FileNotFoundError as e:
        return f"❌ Ошибка: {e}"
    
    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )
    
    # Создаём структуру workspace
    ensure_workspace_structure(workspace)
    
    # Получаем список репозиториев
    repositories = workspace_list_repositories(workspace)
    
    # Фильтруем по секции, если указана
    if section:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(s, section)
        ]
    
    if not repositories:
        return "⚠️  Нет репозиториев, соответствующих фильтру"
    
    # Клонируем репозитории
    result = ["📦 Клонирование репозиториев:\n"]
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for section_name, catalog_name, repo_path in sorted(repositories):
        # Формируем URL репозитория
        repo_url = f"{config.base_url}/ritm-authors/{catalog_name}"
        
        try:
            # Проверяем, существует ли уже репозиторий
            if repo_path.exists() and (repo_path / ".git").exists():
                result.append(f"⏭️  {section_name}/{catalog_name}: уже существует")
                skip_count += 1
            else:
                clone_repository(repo_url, repo_path, config.catalog_branch)
                result.append(f"✅ {section_name}/{catalog_name}: клонирован")
                success_count += 1
        except Exception as e:
            error_msg = str(e)[:100]  # Ограничиваем длину сообщения
            result.append(f"❌ {section_name}/{catalog_name}: ошибка - {error_msg}")
            error_count += 1
    
    # Итоги
    result.append(f"\n📊 Итоги:")
    result.append(f"  ✅ Успешно: {success_count}")
    if skip_count > 0:
        result.append(f"  ⏭️  Пропущено: {skip_count}")
    if error_count > 0:
        result.append(f"  ❌ Ошибок: {error_count}")
    
    return "\n".join(result)


@mcp.tool()
def pull_repositories(section: str | None = None, catalog: str | None = None) -> str:
    """Обновить репозитории (git pull).
    
    Args:
        section: Фильтр по секции (glob pattern, опционально)
        catalog: Конкретный каталог (опционально)
    
    Returns:
        Результаты обновления
    """
    try:
        config = require_mcp_config()
    except FileNotFoundError as e:
        return f"❌ Ошибка: {e}"
    
    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )
    
    # Получаем список репозиториев
    repositories = workspace_list_repositories(workspace)
    
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
        return "⚠️  Нет репозиториев, соответствующих фильтру"
    
    # Обновляем репозитории
    result = ["🔄 Обновление репозиториев:\n"]
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for section_name, catalog_name, repo_path in sorted(repositories):
        try:
            # Проверяем существование репозитория
            if not repo_path.exists() or not (repo_path / ".git").exists():
                result.append(f"⏭️  {section_name}/{catalog_name}: не найден (запустите clone)")
                skip_count += 1
                continue
            
            # Проверяем статус перед pull
            status = get_git_status(repo_path)
            if status == "modified":
                result.append(f"⏭️  {section_name}/{catalog_name}: есть незакоммиченные изменения")
                skip_count += 1
                continue
            
            pull_repository(repo_path, config.catalog_branch)
            result.append(f"✅ {section_name}/{catalog_name}: обновлён")
            success_count += 1
        except Exception as e:
            error_msg = str(e)[:100]
            if "conflict" in error_msg.lower():
                result.append(f"⚠️  {section_name}/{catalog_name}: конфликты при слиянии")
            else:
                result.append(f"❌ {section_name}/{catalog_name}: ошибка - {error_msg}")
            error_count += 1
    
    # Итоги
    result.append(f"\n📊 Итоги:")
    result.append(f"  ✅ Успешно: {success_count}")
    if skip_count > 0:
        result.append(f"  ⏭️  Пропущено: {skip_count}")
    if error_count > 0:
        result.append(f"  ❌ Ошибок: {error_count}")
    
    return "\n".join(result)


@mcp.tool()
def commit_changes(
    message: str | None = None,
    section: str | None = None,
    catalog: str | None = None,
) -> str:
    """Закоммитить изменения в репозиториях.
    
    Args:
        message: Сообщение коммита (автогенерация если не указано)
        section: Фильтр по секции (glob pattern, опционально)
        catalog: Конкретный каталог (опционально)
    
    Returns:
        Результаты коммитов
    """
    try:
        config = require_mcp_config()
    except FileNotFoundError as e:
        return f"❌ Ошибка: {e}"
    
    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )
    
    # Получаем список репозиториев
    repositories = workspace_list_repositories(workspace)
    
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
        return "⚠️  Нет репозиториев, соответствующих фильтру"
    
    # Коммитим изменения
    result = ["📝 Коммит изменений:\n"]
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for section_name, catalog_name, repo_path in sorted(repositories):
        try:
            # Проверяем существование репозитория
            if not repo_path.exists() or not (repo_path / ".git").exists():
                result.append(f"⏭️  {section_name}/{catalog_name}: не найден (запустите clone)")
                skip_count += 1
                continue
            
            # Проверяем, есть ли изменения
            status = get_git_status(repo_path)
            if status not in ("modified", "ahead"):
                result.append(f"⏭️  {section_name}/{catalog_name}: нет изменений")
                skip_count += 1
                continue
            
            # Выполняем коммит
            commit_hash = commit_repository(repo_path, message, add_all=True)
            
            if commit_hash is None:
                result.append(f"⏭️  {section_name}/{catalog_name}: нет изменений для коммита")
                skip_count += 1
            else:
                short_hash = commit_hash[:7]
                result.append(f"✅ {section_name}/{catalog_name}: закоммичен ({short_hash})")
                success_count += 1
        except Exception as e:
            error_msg = str(e)[:100]
            result.append(f"❌ {section_name}/{catalog_name}: ошибка - {error_msg}")
            error_count += 1
    
    # Итоги
    result.append(f"\n📊 Итоги:")
    result.append(f"  ✅ Успешно: {success_count}")
    if skip_count > 0:
        result.append(f"  ⏭️  Пропущено: {skip_count}")
    if error_count > 0:
        result.append(f"  ❌ Ошибок: {error_count}")
    
    return "\n".join(result)


@mcp.tool()
def push_changes(section: str | None = None, catalog: str | None = None) -> str:
    """Отправить изменения в remote (git push).
    
    Args:
        section: Фильтр по секции (glob pattern, опционально)
        catalog: Конкретный каталог (опционально)
    
    Returns:
        Результаты отправки
    """
    try:
        config = require_mcp_config()
    except FileNotFoundError as e:
        return f"❌ Ошибка: {e}"
    
    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )
    
    # Получаем список репозиториев
    repositories = workspace_list_repositories(workspace)
    
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
        return "⚠️  Нет репозиториев, соответствующих фильтру"
    
    # Отправляем изменения
    result = ["🚀 Отправка изменений:\n"]
    success_count = 0
    skip_count = 0
    error_count = 0
    total_commits = 0
    
    for section_name, catalog_name, repo_path in sorted(repositories):
        try:
            # Проверяем существование репозитория
            if not repo_path.exists() or not (repo_path / ".git").exists():
                result.append(f"⏭️  {section_name}/{catalog_name}: не найден (запустите clone)")
                skip_count += 1
                continue
            
            # Проверяем статус перед push
            status = get_git_status(repo_path)
            if status not in ("ahead", "diverged"):
                if status == "modified":
                    result.append(f"⏭️  {section_name}/{catalog_name}: есть незакоммиченные изменения")
                else:
                    result.append(f"⏭️  {section_name}/{catalog_name}: нет изменений для отправки")
                skip_count += 1
                continue
            
            # Выполняем push
            commits_pushed = push_repository(
                repo_path,
                config.catalog_branch,
                force=False,
                set_upstream=False,
            )
            
            if commits_pushed is None:
                result.append(f"⏭️  {section_name}/{catalog_name}: нет изменений для отправки")
                skip_count += 1
            else:
                total_commits += commits_pushed
                commit_word = "коммит" if commits_pushed == 1 else "коммитов"
                result.append(
                    f"✅ {section_name}/{catalog_name}: отправлено ({commits_pushed} {commit_word})"
                )
                success_count += 1
        except Exception as e:
            error_msg = str(e)[:100]
            result.append(f"❌ {section_name}/{catalog_name}: ошибка - {error_msg}")
            error_count += 1
    
    # Итоги
    result.append(f"\n📊 Итоги:")
    result.append(f"  ✅ Успешно: {success_count}")
    if skip_count > 0:
        result.append(f"  ⏭️  Пропущено: {skip_count}")
    if error_count > 0:
        result.append(f"  ❌ Ошибок: {error_count}")
    if total_commits > 0:
        commit_word = "коммит" if total_commits == 1 else "коммитов"
        result.append(f"  📊 Всего коммитов отправлено: {total_commits} {commit_word}")
    
    return "\n".join(result)


@mcp.tool()
def sync_repositories(section: str | None = None, message: str | None = None) -> str:
    """Полная синхронизация: pull → commit → push.
    
    Args:
        section: Фильтр по секции (glob pattern, опционально)
        message: Сообщение коммита (опционально)
    
    Returns:
        Результаты синхронизации
    """
    try:
        config = require_mcp_config()
    except FileNotFoundError as e:
        return f"❌ Ошибка: {e}"
    
    workspace = Workspace(
        workspace_dir=config.workspace_dir,
        sections=config.sections,
    )
    
    # Получаем список репозиториев
    repositories = workspace_list_repositories(workspace)
    
    # Фильтруем репозитории
    if section:
        repositories = [
            (s, c, p) for s, c, p in repositories if fnmatch.fnmatch(s, section)
        ]
    
    if not repositories:
        return "⚠️  Нет репозиториев, соответствующих фильтру"
    
    # Синхронизируем репозитории
    result = ["🔄 Синхронизация репозиториев:\n"]
    success_count = 0
    skip_count = 0
    error_count = 0
    pull_count = 0
    commit_count = 0
    push_count = 0
    total_commits_pushed = 0
    
    for section_name, catalog_name, repo_path in sorted(repositories):
        try:
            # Проверяем существование репозитория
            if not repo_path.exists() or not (repo_path / ".git").exists():
                result.append(f"⏭️  {section_name}/{catalog_name}: не найден (запустите clone)")
                skip_count += 1
                continue
            
            # Получаем статус репозитория
            status = get_git_status(repo_path)
            
            # Определяем, какие операции нужны
            needs_pull = status in ("behind", "diverged")
            needs_commit = status in ("modified", "ahead", "diverged")
            needs_push = status in ("ahead", "diverged")
            
            operations_log = []
            repo_has_error = False
            
            # 1. Pull
            if needs_pull:
                try:
                    pull_repository(repo_path, config.catalog_branch)
                    pull_count += 1
                    operations_log.append("⬇️  Pull: обновлён")
                except Exception as e:
                    error_msg = str(e)[:50]
                    if "conflict" in error_msg.lower():
                        operations_log.append("⬇️  Pull: конфликты при слиянии")
                    else:
                        operations_log.append(f"⬇️  Pull: ошибка ({error_msg})")
                    repo_has_error = True
                    error_count += 1
            else:
                operations_log.append("⬇️  Pull: нет обновлений")
            
            # 2. Commit (только если нет ошибок после pull)
            if needs_commit and not repo_has_error:
                try:
                    # Обновляем статус после pull
                    status_after_pull = get_git_status(repo_path)
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
                except Exception as e:
                    error_msg = str(e)[:50]
                    operations_log.append(f"📝 Commit: ошибка ({error_msg})")
                    repo_has_error = True
                    error_count += 1
            else:
                if not repo_has_error:
                    operations_log.append("📝 Commit: нет изменений")
            
            # 3. Push (только если нет ошибок)
            if needs_push and not repo_has_error:
                try:
                    # Обновляем статус после commit
                    status_after_commit = get_git_status(repo_path)
                    if status_after_commit in ("ahead", "diverged"):
                        commits_pushed = push_repository(
                            repo_path,
                            config.catalog_branch,
                            force=False,
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
                except Exception as e:
                    error_msg = str(e)[:50]
                    operations_log.append(f"⬆️  Push: ошибка ({error_msg})")
                    repo_has_error = True
                    error_count += 1
            else:
                if not repo_has_error:
                    operations_log.append("⬆️  Push: нет изменений для отправки")
            
            # Выводим результаты для репозитория
            if not repo_has_error:
                result.append(f"✅ {section_name}/{catalog_name}:")
                success_count += 1
            else:
                result.append(f"❌ {section_name}/{catalog_name}:")
            
            for op in operations_log:
                result.append(f"  {op}")
        
        except Exception as e:
            error_msg = str(e)[:100]
            result.append(f"❌ {section_name}/{catalog_name}: ошибка - {error_msg}")
            error_count += 1
    
    # Итоги
    result.append(f"\n📊 Итоги синхронизации:")
    result.append(f"  ✅ Успешно: {success_count}")
    if skip_count > 0:
        result.append(f"  ⏭️  Пропущено: {skip_count}")
    if error_count > 0:
        result.append(f"  ❌ Ошибок: {error_count}")
    result.append(f"  ⬇️  Pull: {pull_count} обновлён")
    result.append(f"  📝 Commit: {commit_count} закоммичен")
    result.append(f"  ⬆️  Push: {push_count} отправлено")
    if total_commits_pushed > 0:
        commit_word = "коммит" if total_commits_pushed == 1 else "коммитов"
        result.append(f"  📊 Всего коммитов отправлено: {total_commits_pushed} {commit_word}")
    
    return "\n".join(result)

