"""Утилиты для интерактивного выбора."""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from gramax_sync.config.models import Catalog, Section, Workspace

console = Console()


def display_workspace_structure(workspace: Workspace) -> None:
    """Отобразить структуру workspace в красивом формате.

    Args:
        workspace: Объект Workspace для отображения
    """
    console.print("\n[bold cyan]📋 Найдено конфигураций:[/bold cyan]\n")

    for section in workspace.sections:
        # Подсчитываем количество каталогов
        catalog_count = len(section.catalogs)

        # Создаём таблицу для секции
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            show_edge=False,
        )
        table.add_column(style="cyan", width=2)
        table.add_column(style="white")

        # Добавляем название секции
        table.add_row(
            "📁",
            f"[bold]{section.name}[/bold] [dim]({catalog_count} каталог{'ов' if catalog_count != 1 else ''})[/dim]",
        )

        # Добавляем каталоги
        for catalog in section.catalogs:
            table.add_row("", f"  └─ 📦 [yellow]{catalog.name}[/yellow]")

        console.print(table)
        console.print()  # Пустая строка между секциями


def prompt_selection_mode() -> str:
    """Запросить режим выбора у пользователя.

    Returns:
        Режим: 'all', 'sections', или 'catalogs'
    """
    console.print("\n[bold]Выберите режим загрузки:[/bold]\n")

    options = [
        ("1", "Загрузить все секции и каталоги", "all"),
        ("2", "Выбрать конкретные секции", "sections"),
        ("3", "Выбрать конкретные каталоги", "catalogs"),
    ]

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan", width=3)
    table.add_column(style="white")

    for key, description, _ in options:
        table.add_row(f"[bold]{key}.[/bold]", description)

    console.print(table)

    choice = Prompt.ask(
        "\n[cyan]Ваш выбор[/cyan]",
        choices=["1", "2", "3"],
        default="1",
    )

    return options[int(choice) - 1][2]


def prompt_section_selection(workspace: Workspace) -> list[str]:
    """Интерактивный выбор секций.

    Args:
        workspace: Объект Workspace

    Returns:
        Список выбранных названий секций
    """
    console.print("\n[bold]Выберите секции для загрузки:[/bold]\n")

    sections = []
    for idx, section in enumerate(workspace.sections, 1):
        catalog_count = len(section.catalogs)
        sections.append((section.name, catalog_count))

    # Отображаем список секций
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan", width=3)
    table.add_column(style="white")

    for idx, (name, count) in enumerate(sections, 1):
        table.add_row(
            f"[bold]{idx}.[/bold]",
            f"{name} [dim]({count} каталог{'ов' if count != 1 else ''})[/dim]",
        )

    console.print(table)

    # Запрашиваем выбор
    selected = Prompt.ask(
        "\n[cyan]Введите номера секций через запятую (например: 1,3)[/cyan]",
    )

    try:
        indices = [int(x.strip()) - 1 for x in selected.split(",")]
        selected_sections = [sections[i][0] for i in indices if 0 <= i < len(sections)]
        return selected_sections
    except (ValueError, IndexError):
        console.print("[red]Ошибка: неверный формат ввода[/red]")
        return []


def prompt_catalog_selection(workspace: Workspace) -> list[tuple[str, str]]:
    """Интерактивный выбор каталогов.

    Args:
        workspace: Объект Workspace

    Returns:
        Список кортежей (section_name, catalog_name)
    """
    console.print("\n[bold]Выберите каталоги для загрузки:[/bold]\n")

    catalogs = []
    idx = 1
    catalog_map = {}  # номер -> (section, catalog)

    for section in workspace.sections:
        for catalog in section.catalogs:
            catalog_map[idx] = (section.name, catalog.name)
            catalogs.append((idx, section.name, catalog.name))
            idx += 1

    # Отображаем список каталогов
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan", width=3)
    table.add_column(style="white")

    for num, section_name, catalog_name in catalogs:
        table.add_row(
            f"[bold]{num}.[/bold]",
            f"[dim]{section_name}[/dim] / [yellow]{catalog_name}[/yellow]",
        )

    console.print(table)

    # Запрашиваем выбор
    selected = Prompt.ask(
        "\n[cyan]Введите номера каталогов через запятую (например: 1,3,5)[/cyan]",
    )

    try:
        indices = [int(x.strip()) for x in selected.split(",")]
        selected_catalogs = [
            catalog_map[i] for i in indices if i in catalog_map
        ]
        return selected_catalogs
    except (ValueError, KeyError):
        console.print("[red]Ошибка: неверный формат ввода[/red]")
        return []


def filter_workspace(
    workspace: Workspace,
    mode: str,
    selected_sections: list[str] | None = None,
    selected_catalogs: list[tuple[str, str]] | None = None,
) -> Workspace:
    """Отфильтровать workspace по выбранным секциям/каталогам.

    Args:
        workspace: Исходный workspace
        mode: Режим фильтрации ('all', 'sections', 'catalogs')
        selected_sections: Список выбранных секций (для mode='sections')
        selected_catalogs: Список выбранных каталогов (для mode='catalogs')

    Returns:
        Отфильтрованный workspace
    """
    if mode == "all":
        return workspace

    if mode == "sections" and selected_sections:
        filtered_sections = [
            Section(
                name=section.name,
                catalogs=section.catalogs,
            )
            for section in workspace.sections
            if section.name in selected_sections
        ]
        return Workspace(
            workspace_dir=workspace.workspace_dir,
            sections=filtered_sections,
        )

    if mode == "catalogs" and selected_catalogs:
        # Группируем каталоги по секциям
        section_map: dict[str, list[Catalog]] = {}
        for section_name, catalog_name in selected_catalogs:
            # Находим оригинальный каталог
            for section in workspace.sections:
                if section.name == section_name:
                    for catalog in section.catalogs:
                        if catalog.name == catalog_name:
                            if section_name not in section_map:
                                section_map[section_name] = []
                            section_map[section_name].append(catalog)
                            break

        # Создаём отфильтрованные секции
        filtered_sections = [
            Section(name=section_name, catalogs=catalogs)
            for section_name, catalogs in section_map.items()
        ]

        return Workspace(
            workspace_dir=workspace.workspace_dir,
            sections=filtered_sections,
        )

    return workspace

