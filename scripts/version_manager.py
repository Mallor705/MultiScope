#!/usr/bin/env python3
"""
Script para gerenciar o versionamento do MultiScope.

Este script atualiza automaticamente a versão em todos os arquivos necessários
quando uma nova versão é definida.
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime


def update_version_in_file(file_path, old_version, new_version):
    """Atualiza a versão em um arquivo específico."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Substituições específicas para diferentes formatos de versão
    updated_content = content

    # Atualiza versão em formato "x.y.z"
    updated_content = re.sub(
        rf'(["\']){re.escape(old_version)}(["\'])',
        rf'\g<1>{new_version}\g<2>',
        updated_content
    )

    # Atualiza versão em formato de data no metainfo.xml
    if 'metainfo.xml' in str(file_path):
        current_date = datetime.now().strftime('%Y-%m-%d')
        # Atualiza a data da release no metainfo.xml
        updated_content = re.sub(
            r'<release version="[^"]+" date="[^"]+">',
            f'<release version="{new_version}" date="{current_date}">',
            updated_content
        )

    # Atualiza a badge de versão no README
    if 'README' in str(file_path):
        updated_content = re.sub(
            r'Version-[0-9]+\.[0-9]+\.[0-9]+',
            f'Version-{new_version}',
            updated_content
        )

    if content != updated_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print(f"✓ Atualizado: {file_path}")
        return True

    return False


def get_current_version():
    """Obtém a versão atual do arquivo version."""
    version_file = Path("version")
    if version_file.exists():
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None


def set_new_version(new_version):
    """Define uma nova versão e atualiza todos os arquivos relevantes."""
    old_version = get_current_version()

    if not old_version:
        print("Erro: Arquivo version não encontrado ou vazio")
        return False

    if old_version == new_version:
        print(f"A versão já é {new_version}")
        return True

    # Atualiza o arquivo version
    with open("version", 'w', encoding='utf-8') as f:
        f.write(new_version)

    print(f"Atualizando versão de {old_version} para {new_version}")

    # Lista de arquivos que contêm a versão
    files_to_update = [
        "scripts/package-appimage.sh",
        "share/metainfo/io.github.mallor.MultiScope.metainfo.xml",
        "README.md",
        "docs/README.pt-br.md",
        "docs/README.es.md",
        "io.github.mallor.MultiScope.yaml",  # Embora não contenha versão diretamente, pode conter referências
        "scripts/package-flatpak.sh",
    ]

    updated_files = []

    for file_path in files_to_update:
        file_obj = Path(file_path)
        if file_obj.exists():
            if update_version_in_file(file_obj, old_version, new_version):
                updated_files.append(file_path)


    print(f"\n✓ Versão atualizada com sucesso de {old_version} para {new_version}")
    print(f"Arquivos atualizados: {len(updated_files)}")
    for file in updated_files:
        print(f"  - {file}")

    return True


def main():
    if len(sys.argv) != 2:
        current_version = get_current_version()
        if current_version:
            print(f"Uso: python {sys.argv[0]} <nova_versao>")
            print(f"Versão atual: {current_version}")
        else:
            print(f"Uso: python {sys.argv[0]} <nova_versao>")
            print("Nenhuma versão atual encontrada")
        return 1

    new_version = sys.argv[1]

    # Valida o formato da versão (x.y.z)
    version_pattern = r'^[0-9]+\.[0-9]+\.[0-9]+$'
    if not re.match(version_pattern, new_version):
        print(f"Erro: Formato de versão inválido. Use o formato x.y.z (ex: 1.0.0)")
        return 1

    if not set_new_version(new_version):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
