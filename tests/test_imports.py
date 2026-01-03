"""Тесты для проверки импортов всех модулей."""


def test_import_main_modules():
    """Проверка импорта основных модулей."""
    import gramax_sync
    import gramax_sync.cli
    import gramax_sync.config
    import gramax_sync.config.models
    import gramax_sync.config.parser
    import gramax_sync.git
    import gramax_sync.git.operations
    import gramax_sync.git.status
    import gramax_sync.utils
    import gramax_sync.utils.output
    import gramax_sync.workspace
    import gramax_sync.workspace.manager

    assert gramax_sync.__version__ == "0.1.0"
