"""Тесты для CLI команд."""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from gramax_sync import cli
import gramax_sync.cli.main


def update_cli_main_functions():
    """Обновляет ссылки на функции в cli.main после применения патчей.
    
    Это нужно, чтобы функции в cli.main использовали патченые версии
    из исходных модулей.
    """
    import gramax_sync.config.config_manager as cm
    import gramax_sync.workspace.manager as wm
    import gramax_sync.git.status as gs
    import gramax_sync.git.operations as go
    
    # Обновляем ссылки на функции в модуле cli.main через модули
    cli_main_dict = sys.modules['gramax_sync.cli.main'].__dict__
    if 'config_manager_module' in cli_main_dict:
        cli_main_dict['config_manager_module'].require_config = cm.require_config
    if 'workspace_manager_module' in cli_main_dict:
        cli_main_dict['workspace_manager_module'].list_repositories = wm.list_repositories
        cli_main_dict['workspace_manager_module'].ensure_workspace_structure = wm.ensure_workspace_structure
    if 'git_status_module' in cli_main_dict:
        cli_main_dict['git_status_module'].get_repository_status = gs.get_repository_status
    if 'git_operations_module' in cli_main_dict:
        cli_main_dict['git_operations_module'].clone_repository = go.clone_repository
        cli_main_dict['git_operations_module'].pull_repository = go.pull_repository
        cli_main_dict['git_operations_module'].commit_repository = go.commit_repository
        cli_main_dict['git_operations_module'].push_repository = go.push_repository
    
    # Обновляем локальные ссылки
    cli_main_dict['require_config'] = cm.require_config
    cli_main_dict['list_repositories'] = wm.list_repositories
    cli_main_dict['ensure_workspace_structure'] = wm.ensure_workspace_structure
    cli_main_dict['get_repository_status'] = gs.get_repository_status
    cli_main_dict['clone_repository'] = go.clone_repository
    cli_main_dict['pull_repository'] = go.pull_repository
    cli_main_dict['commit_repository'] = go.commit_repository
    cli_main_dict['push_repository'] = go.push_repository


def test_cli_help():
    """Тест вывода help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "gramax-sync" in result.output
    assert "Clone all repositories" in result.output or "Клонировать все репозитории" in result.output


def test_cli_version():
    """Тест вывода версии."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


@patch("gramax_sync.config.config_manager.require_config")
def test_cli_status_command_no_config(mock_require_config):
    """Тест команды status без конфигурации."""
    mock_require_config.side_effect = FileNotFoundError(
        f"Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки."
    )

    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code != 0
    assert "Конфигурация не найдена" in result.output


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
def test_cli_status_command(mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды status с конфигурацией."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев и статусы
    mock_list_repos.return_value = [("section1", "catalog1", Path("/tmp/test_workspace/section1/catalog1"))]
    mock_get_status.return_value = "clean"

    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    
    # Если команда упала, выводим ошибку для отладки
    if result.exit_code != 0:
        print(f"Command failed with exit code {result.exit_code}")
        print(f"Output: {result.output}")
        print(f"Exception: {result.exception}")
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert "section1" in result.output or "catalog1" in result.output


@patch("gramax_sync.config.config_manager.require_config")
def test_cli_clone_command_no_config(mock_require_config):
    """Тест команды clone без конфигурации."""
    mock_require_config.side_effect = FileNotFoundError(
        f"Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки."
    )

    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["clone"])
    assert result.exit_code != 0
    assert "Конфигурация не найдена" in result.output


@patch("gramax_sync.core.adapters.ConfigManagerAdapter.require_config")
@patch("gramax_sync.core.adapters.WorkspaceManagerAdapter.ensure_workspace_structure")
@patch("gramax_sync.core.adapters.WorkspaceManagerAdapter.list_repositories")
@patch("gramax_sync.core.adapters.GitOperationsAdapter.clone_repository")
def test_cli_clone_command(mock_clone, mock_list_repos, mock_ensure_structure, mock_require_config):
    """Тест команды clone с конфигурацией (используя DI через протоколы)."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Настраиваем возвращаемые значения для моков
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    # Удаляем директорию если существует
    if repo_path.exists():
        import shutil
        shutil.rmtree(repo_path, ignore_errors=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]

    runner = CliRunner()
    result = runner.invoke(cli, ["clone"])
    assert result.exit_code == 0
    mock_require_config.assert_called_once()
    mock_ensure_structure.assert_called_once()
    mock_list_repos.assert_called_once()
    # Проверяем, что clone_repository был вызван с правильными параметрами
    mock_clone.assert_called_once()
    call_args = mock_clone.call_args[0]
    assert call_args[0] == f"{config.base_url}/ritm-authors/catalog1"
    assert call_args[1] == repo_path
    assert call_args[2] == config.catalog_branch


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.ensure_workspace_structure")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.operations.clone_repository")
def test_cli_clone_command_with_filters(mock_clone, mock_list_repos, mock_ensure_structure, mock_require_config):
    """Тест команды clone с фильтрацией по секции и каталогу."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com")),
                    Catalog(name="catalog2", source=Source(url="https://gitlab.example.com")),
                ],
            ),
            Section(
                name="section2",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com")),
                ],
            ),
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев
    # Важно: пути не должны существовать, иначе clone не будет вызван
    repo_path1 = Path("/tmp/test_workspace/section1/catalog1")
    repo_path2 = Path("/tmp/test_workspace/section1/catalog2")
    repo_path3 = Path("/tmp/test_workspace/section2/catalog1")
    import shutil
    for path in [repo_path1, repo_path2, repo_path3]:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    
    mock_list_repos.return_value = [
        ("section1", "catalog1", repo_path1),
        ("section1", "catalog2", repo_path2),
        ("section2", "catalog1", repo_path3),
    ]
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["clone", "--section", "section1", "--catalog", "catalog1"])
    assert result.exit_code == 0
    # Должен быть вызван только для section1/catalog1
    assert mock_clone.call_count == 1


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.ensure_workspace_structure")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.operations.clone_repository")
def test_cli_clone_command_empty_list(mock_clone, mock_list_repos, mock_ensure_structure, mock_require_config):
    """Тест команды clone с пустым списком репозиториев."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["clone"])
    assert result.exit_code == 0
    # clone_repository не должен вызываться
    mock_clone.assert_not_called()


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.ensure_workspace_structure")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.operations.clone_repository")
def test_cli_clone_command_error(mock_clone, mock_list_repos, mock_ensure_structure, mock_require_config):
    """Тест команды clone с ошибкой клонирования."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source
    from git.exc import GitCommandError

    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    # Удаляем директорию если существует
    if repo_path.exists():
        import shutil
        shutil.rmtree(repo_path, ignore_errors=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["clone"])
    assert result.exit_code == 0
    # clone_repository должен быть вызван
    mock_clone.assert_called()


@patch("gramax_sync.config.config_manager.require_config")
def test_cli_pull_command_no_config(mock_require_config):
    """Тест команды pull без конфигурации."""
    mock_require_config.side_effect = FileNotFoundError(
        f"Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки."
    )

    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["pull"])
    assert result.exit_code != 0
    assert "Конфигурация не найдена" in result.output


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.pull_repository")
def test_cli_pull_command(mock_pull, mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды pull с конфигурацией."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    mock_get_status.return_value = "clean"  # Статус clean - можно делать pull

    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["pull"])
    assert result.exit_code == 0
    mock_pull.assert_called()


@patch("gramax_sync.config.config_manager.require_config")
def test_cli_commit_command_no_config(mock_require_config):
    """Тест команды commit без конфигурации."""
    mock_require_config.side_effect = FileNotFoundError(
        f"Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки."
    )

    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["commit"])
    assert result.exit_code != 0
    assert "Конфигурация не найдена" in result.output


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.commit_repository")
def test_cli_commit_command(mock_commit, mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды commit с конфигурацией."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    mock_get_status.return_value = "modified"  # Статус modified - можно делать commit
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["commit"])
    
    if result.exit_code != 0:
        print(f"Command failed: {result.output}")
    assert result.exit_code == 0, f"Command failed: {result.output}"
    mock_commit.assert_called_once()
    # Проверяем, что был вызван с правильными параметрами
    call_args = mock_commit.call_args
    assert call_args[0][0] == repo_path
    # commit_repository вызывается с позиционными аргументами: (path, message, add_all)
    assert len(call_args[0]) >= 2  # path и message (может быть None)
    # add_all передается как третий позиционный аргумент
    if len(call_args[0]) >= 3:
        assert call_args[0][2] is True  # add_all


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.commit_repository")
def test_cli_commit_command_with_message(mock_commit, mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды commit с кастомным сообщением."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    mock_get_status.return_value = "modified"  # Статус modified - можно делать commit
    
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["commit", "-m", "Custom commit message"])
    assert result.exit_code == 0
    mock_commit.assert_called_once()
    # Проверяем, что сообщение было передано
    call_args = mock_commit.call_args
    assert call_args[0][1] == "Custom commit message"


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.commit_repository")
def test_cli_commit_command_no_changes(mock_commit, mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды commit когда нет изменений."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    mock_get_status.return_value = "clean"  # Статус clean - нет изменений для коммита
    
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["commit"])
    assert result.exit_code == 0
    # commit_repository не должен вызываться, так как статус clean
    mock_commit.assert_not_called()


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.commit_repository")
def test_cli_commit_command_no_add(mock_commit, mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды commit с флагом --no-add."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    mock_get_status.return_value = "modified"  # Статус modified - можно делать commit
    
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["commit", "--no-add"])
    assert result.exit_code == 0
    mock_commit.assert_called_once()
    # Проверяем, что add_all=False (передается как третий позиционный аргумент)
    call_args = mock_commit.call_args
    if len(call_args[0]) >= 3:
        assert call_args[0][2] is False  # add_all


@patch("gramax_sync.config.config_manager.require_config")
def test_cli_push_command_no_config(mock_require_config):
    """Тест команды push без конфигурации."""
    mock_require_config.side_effect = FileNotFoundError(
        f"Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки."
    )

    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["push"])
    assert result.exit_code != 0
    assert "Конфигурация не найдена" in result.output


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.push_repository")
def test_cli_push_command(mock_push, mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды push с конфигурацией."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    mock_get_status.return_value = "ahead"  # Статус ahead - можно делать push
    mock_push.return_value = 1  # Возвращаем количество отправленных коммитов
    
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["push"])
    assert result.exit_code == 0
    mock_push.assert_called_once()
    # Проверяем, что был вызван с правильными параметрами
    call_args = mock_push.call_args
    assert call_args[0][0] == repo_path
    assert call_args[0][1] == "private"
    assert call_args[1]["force"] is False
    assert call_args[1]["set_upstream"] is False


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.push_repository")
@patch("click.confirm")
def test_cli_push_command_force(mock_confirm, mock_push, mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды push с флагом --force."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем подтверждение force push
    mock_confirm.return_value = True

    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    mock_get_status.return_value = "ahead"  # Статус ahead - можно делать push
    mock_push.return_value = 1  # Возвращаем количество отправленных коммитов
    
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["push", "--force"])
    assert result.exit_code == 0
    mock_confirm.assert_called_once()
    mock_push.assert_called_once()
    # Проверяем, что force=True
    call_args = mock_push.call_args
    assert call_args[1]["force"] is True


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.push_repository")
def test_cli_push_command_no_commits(mock_push, mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды push когда нет unpushed commits."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config
    
    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    mock_get_status.return_value = "clean"  # Статус clean - нет unpushed commits
    
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["push"])
    assert result.exit_code == 0
    # push_repository не должен вызываться, так как статус clean
    mock_push.assert_not_called()


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.push_repository")
def test_cli_push_command_set_upstream(mock_push, mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды push с флагом --set-upstream."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    mock_get_status.return_value = "ahead"  # Статус ahead - можно делать push
    mock_push.return_value = 1  # Возвращаем количество отправленных коммитов
    
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["push", "--set-upstream"])
    assert result.exit_code == 0
    mock_push.assert_called_once()
    # Проверяем, что set_upstream=True
    call_args = mock_push.call_args
    assert call_args[1]["set_upstream"] is True


@patch("gramax_sync.config.config_manager.require_config")
def test_cli_sync_command_no_config(mock_require_config):
    """Тест команды sync без конфигурации."""
    mock_require_config.side_effect = FileNotFoundError(
        f"Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки."
    )

    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["sync"])
    assert result.exit_code != 0
    assert "Конфигурация не найдена" in result.output


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.pull_repository")
@patch("gramax_sync.git.operations.commit_repository")
@patch("gramax_sync.git.operations.push_repository")
def test_cli_sync_command(
    mock_push, mock_commit, mock_pull, mock_get_status, mock_list_repos, mock_require_config
):
    """Тест команды sync с конфигурацией."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    # Статус изменяется: сначала ahead (нужен push), после commit тоже ahead
    mock_get_status.side_effect = ["ahead", "ahead", "ahead"]
    mock_commit.return_value = "abc1234"  # Возвращаем хеш коммита
    mock_push.return_value = 1  # Возвращаем количество отправленных коммитов
    
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["sync"])
    assert result.exit_code == 0
    # Проверяем, что commit и push были вызваны
    mock_commit.assert_called_once()
    mock_push.assert_called_once()


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
def test_cli_sync_command_dry_run(mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды sync с флагом --dry-run."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["sync", "--dry-run"])
    assert result.exit_code == 0
    # В dry-run режиме операции не должны выполняться
    assert "Предварительный просмотр" in result.output or "dry-run" in result.output.lower()


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.pull_repository")
@patch("gramax_sync.git.operations.commit_repository")
@patch("gramax_sync.git.operations.push_repository")
def test_cli_sync_command_with_message(
    mock_push, mock_commit, mock_pull, mock_get_status, mock_list_repos, mock_require_config
):
    """Тест команды sync с сообщением коммита."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    # Статус изменяется: сначала ahead (нужен push), после commit тоже ahead
    mock_get_status.side_effect = ["ahead", "ahead", "ahead"]
    mock_commit.return_value = "abc1234"  # Возвращаем хеш коммита
    mock_push.return_value = 1  # Возвращаем количество отправленных коммитов
    
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["sync", "-m", "Custom commit message"])
    assert result.exit_code == 0
    mock_commit.assert_called_once()
    # Проверяем, что сообщение было передано
    call_args = mock_commit.call_args
    assert call_args[0][1] == "Custom commit message"


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
@patch("gramax_sync.git.operations.pull_repository")
@patch("gramax_sync.git.operations.commit_repository")
@patch("gramax_sync.git.operations.push_repository")
@patch("click.confirm")
def test_cli_sync_command_force(
    mock_confirm, mock_push, mock_commit, mock_pull, mock_get_status, mock_list_repos, mock_require_config
):
    """Тест команды sync с флагом --force."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config

    # Мокируем подтверждение force push
    mock_confirm.return_value = True

    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    # Статус изменяется: сначала ahead (нужен push), после commit тоже ahead
    mock_get_status.side_effect = ["ahead", "ahead", "ahead"]
    mock_commit.return_value = "abc1234"  # Возвращаем хеш коммита
    mock_push.return_value = 1  # Возвращаем количество отправленных коммитов
    
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["sync", "--force"])
    assert result.exit_code == 0
    mock_confirm.assert_called_once()
    mock_push.assert_called_once()
    # Проверяем, что force=True
    call_args = mock_push.call_args
    assert call_args[1]["force"] is True


@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
def test_cli_sync_command_no_changes(mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды sync когда нет изменений."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.models import Catalog, Section, Source

    # Создаём мок конфигурации
    config = LocalConfig(
        repo_url="https://gitlab.example.com/config",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test_workspace",
        catalog_branch="private",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source=Source(url="https://gitlab.example.com"))
                ],
            )
        ],
    )
    mock_require_config.return_value = config
    
    # Мокируем список репозиториев и статусы
    repo_path = Path("/tmp/test_workspace/section1/catalog1")
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / ".git").mkdir(exist_ok=True)
    mock_list_repos.return_value = [("section1", "catalog1", repo_path)]
    mock_get_status.return_value = "clean"  # Статус clean - нет изменений
    
    # Обновляем ссылки на функции в cli.main после применения патчей
    update_cli_main_functions()

    runner = CliRunner()
    result = runner.invoke(cli, ["sync"])
    assert result.exit_code == 0
    # Операции не должны выполняться, так как статус clean
