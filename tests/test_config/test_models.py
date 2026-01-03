"""Тесты для Pydantic моделей."""

from gramax_sync.config.models import Catalog, Section, Source, Workspace


def test_source_model():
    """Тест модели Source."""
    source = Source(url="https://gitlab.example.com")
    assert source.url == "https://gitlab.example.com"


def test_catalog_model():
    """Тест модели Catalog."""
    source = Source(url="https://gitlab.example.com")
    catalog = Catalog(name="test-catalog", source=source)
    assert catalog.name == "test-catalog"
    assert catalog.source.url == "https://gitlab.example.com"


def test_section_model():
    """Тест модели Section."""
    source = Source(url="https://gitlab.example.com")
    catalog = Catalog(name="test-catalog", source=source)
    section = Section(name="test-section", catalogs=[catalog])
    assert section.name == "test-section"
    assert len(section.catalogs) == 1
    assert section.catalogs[0].name == "test-catalog"


def test_workspace_model(sample_workspace_data):
    """Тест модели Workspace."""
    workspace = Workspace(**sample_workspace_data)
    assert workspace.workspace_dir == "/tmp/test_workspace"
    assert len(workspace.sections) == 1
    assert workspace.sections[0].name == "section1"
