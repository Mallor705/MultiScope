"""Testes básicos para o projeto Twinverse."""


def test_import_main_module():
    """Testa se o módulo principal pode ser importado."""
    try:
        import twinverse  # noqa: F401

        assert True  # Se chegou até aqui, a importação funcionou
    except ImportError:
        raise AssertionError("Falha ao importar o módulo twinverse")
