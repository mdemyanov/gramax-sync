"""Тесты для утилит интерактивного выбора."""

from unittest.mock import MagicMock, patch

import pytest

from gramax_sync.config.models import Catalog, Section, Workspace
from gramax_sync.utils.selection import (
    display_workspace_structure,
    prompt_selection_mode,
    prompt_section_selection,
    prompt_catalog_selection,
    filter_workspace,
)


@pytest.fixture
def sample_workspace():
    """Фикстура для создания тестового workspace."""
    return Workspace(
        workspace_dir="/tmp/test",
        sections=[
            Section(
                name="section1",
                catalogs=[
                    Catalog(name="catalog1", source={"url": "https://example.com"}),
                    Catalog(name="catalog2", source={"url": "https://example.com"}),
                ],
            ),
            Section(
                name="section2",
                catalogs=[
                    Catalog(name="catalog3", source={"url": "https://example.com"}),
                ],
            ),
        ],
    )


@patch("gramax_sync.utils.selection.console")
def test_display_workspace_structure(mock_console, sample_workspace):
    """Тест отображения структуры workspace."""
    display_workspace_structure(sample_workspace)
    
    # Проверяем, что console.print был вызван
    assert mock_console.print.called


@patch("gramax_sync.utils.selection.console")
@patch("gramax_sync.utils.selection.Prompt")
def test_prompt_selection_mode_all(mock_prompt, mock_console):
    """Тест выбора режима 'all'."""
    mock_prompt.ask.return_value = "1"
    
    result = prompt_selection_mode()
    
    assert result == "all"
    mock_prompt.ask.assert_called_once()


@patch("gramax_sync.utils.selection.console")
@patch("gramax_sync.utils.selection.Prompt")
def test_prompt_selection_mode_sections(mock_prompt, mock_console):
    """Тест выбора режима 'sections'."""
    mock_prompt.ask.return_value = "2"
    
    result = prompt_selection_mode()
    
    assert result == "sections"


@patch("gramax_sync.utils.selection.console")
@patch("gramax_sync.utils.selection.Prompt")
def test_prompt_selection_mode_catalogs(mock_prompt, mock_console):
    """Тест выбора режима 'catalogs'."""
    mock_prompt.ask.return_value = "3"
    
    result = prompt_selection_mode()
    
    assert result == "catalogs"


@patch("gramax_sync.utils.selection.console")
@patch("gramax_sync.utils.selection.Prompt")
def test_prompt_section_selection(mock_prompt, mock_console, sample_workspace):
    """Тест выбора секций."""
    mock_prompt.ask.return_value = "1,2"
    
    result = prompt_section_selection(sample_workspace)
    
    assert len(result) == 2
    assert "section1" in result
    assert "section2" in result


@patch("gramax_sync.utils.selection.console")
@patch("gramax_sync.utils.selection.Prompt")
def test_prompt_section_selection_empty(mock_prompt, mock_console, sample_workspace):
    """Тест выбора пустого списка секций."""
    mock_prompt.ask.return_value = ""
    
    result = prompt_section_selection(sample_workspace)
    
    assert result == []


@patch("gramax_sync.utils.selection.console")
@patch("gramax_sync.utils.selection.Prompt")
def test_prompt_section_selection_invalid(mock_prompt, mock_console, sample_workspace):
    """Тест обработки неверного формата ввода."""
    mock_prompt.ask.return_value = "invalid"
    
    result = prompt_section_selection(sample_workspace)
    
    assert result == []


@patch("gramax_sync.utils.selection.console")
@patch("gramax_sync.utils.selection.Prompt")
def test_prompt_catalog_selection(mock_prompt, mock_console, sample_workspace):
    """Тест выбора каталогов."""
    mock_prompt.ask.return_value = "1,2"
    
    result = prompt_catalog_selection(sample_workspace)
    
    assert len(result) == 2
    assert ("section1", "catalog1") in result
    assert ("section1", "catalog2") in result


@patch("gramax_sync.utils.selection.console")
@patch("gramax_sync.utils.selection.Prompt")
def test_prompt_catalog_selection_empty(mock_prompt, mock_console, sample_workspace):
    """Тест выбора пустого списка каталогов."""
    mock_prompt.ask.return_value = ""
    
    result = prompt_catalog_selection(sample_workspace)
    
    assert result == []


@patch("gramax_sync.utils.selection.console")
@patch("gramax_sync.utils.selection.Prompt")
def test_prompt_catalog_selection_invalid(mock_prompt, mock_console, sample_workspace):
    """Тест обработки неверного формата ввода."""
    mock_prompt.ask.return_value = "invalid"
    
    result = prompt_catalog_selection(sample_workspace)
    
    assert result == []


def test_filter_workspace_all(sample_workspace):
    """Тест фильтрации workspace в режиме 'all'."""
    result = filter_workspace(sample_workspace, "all")
    
    assert result == sample_workspace
    assert len(result.sections) == 2


def test_filter_workspace_sections(sample_workspace):
    """Тест фильтрации workspace по секциям."""
    result = filter_workspace(sample_workspace, "sections", selected_sections=["section1"])
    
    assert len(result.sections) == 1
    assert result.sections[0].name == "section1"


def test_filter_workspace_catalogs(sample_workspace):
    """Тест фильтрации workspace по каталогам."""
    result = filter_workspace(
        sample_workspace,
        "catalogs",
        selected_catalogs=[("section1", "catalog1")],
    )
    
    assert len(result.sections) == 1
    assert result.sections[0].name == "section1"
    assert len(result.sections[0].catalogs) == 1
    assert result.sections[0].catalogs[0].name == "catalog1"


def test_filter_workspace_no_selection(sample_workspace):
    """Тест фильтрации workspace без выбора."""
    result = filter_workspace(sample_workspace, "sections", selected_sections=None)
    
    assert result == sample_workspace

