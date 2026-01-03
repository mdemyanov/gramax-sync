"""Тесты для парсера workspace.yaml."""

from pathlib import Path

import pytest
import yaml

from gramax_sync.config.parser import load_workspace, load_workspace_from_string


def test_load_workspace_success(tmp_path):
    """Тест успешной загрузки workspace.yaml."""
    workspace_file = tmp_path / "workspace.yaml"
    workspace_data = {
        "workspace_dir": "/tmp/test",
        "sections": [
            {
                "name": "section1",
                "catalogs": [
                    {
                        "name": "catalog1",
                        "source": {"url": "https://gitlab.example.com"},
                    }
                ],
            }
        ],
    }
    workspace_file.write_text(yaml.dump(workspace_data), encoding="utf-8")
    
    workspace = load_workspace(workspace_file)
    
    assert workspace.workspace_dir == "/tmp/test"
    assert len(workspace.sections) == 1
    assert workspace.sections[0].name == "section1"


def test_load_workspace_not_found(tmp_path):
    """Тест загрузки несуществующего файла."""
    workspace_file = tmp_path / "nonexistent.yaml"
    
    with pytest.raises(FileNotFoundError, match="Файл не найден"):
        load_workspace(workspace_file)


def test_load_workspace_empty_file(tmp_path):
    """Тест загрузки пустого файла."""
    workspace_file = tmp_path / "workspace.yaml"
    workspace_file.write_text("", encoding="utf-8")
    
    with pytest.raises(ValueError, match="пуст"):
        load_workspace(workspace_file)


def test_load_workspace_invalid_yaml(tmp_path):
    """Тест загрузки невалидного YAML."""
    workspace_file = tmp_path / "workspace.yaml"
    workspace_file.write_text("invalid: yaml: content: [", encoding="utf-8")
    
    with pytest.raises(yaml.YAMLError):
        load_workspace(workspace_file)


def test_load_workspace_from_string_success():
    """Тест загрузки workspace из строки."""
    content = """
workspace_dir: /tmp/test
sections:
  - name: section1
    catalogs:
      - name: catalog1
        source:
          url: https://gitlab.example.com
"""
    workspace = load_workspace_from_string(content)
    
    assert workspace.workspace_dir == "/tmp/test"
    assert len(workspace.sections) == 1


def test_load_workspace_from_string_empty():
    """Тест загрузки пустой строки."""
    with pytest.raises(ValueError, match="пусто"):
        load_workspace_from_string("")


def test_load_workspace_from_string_invalid_yaml():
    """Тест загрузки невалидного YAML из строки."""
    with pytest.raises(yaml.YAMLError):
        load_workspace_from_string("invalid: yaml: [")
