# Estrutura do Projeto Linux-Coop Python

```
linux_coop/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management
│   │   ├── logger.py          # Logging utilities
│   │   └── exceptions.py      # Custom exceptions
│   ├── services/
│   │   ├── __init__.py
│   │   ├── proton_service.py  # Proton path detection
│   │   ├── process_service.py # Process management
│   │   └── instance_service.py # Game instance management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── profile.py         # Profile data model
│   │   └── instance.py        # Instance data model
│   └── cli/
│       ├── __init__.py
│       └── commands.py        # CLI interface
├── profiles/                  # Game profiles directory
├── requirements.txt
├── setup.py
└── README.md
```

## Principais Componentes

### 1. **Core Module** - Fundação do sistema
- `config.py`: Gerencia configurações e constantes
- `logger.py`: Sistema de logging centralizado
- `exceptions.py`: Exceções customizadas

### 2. **Services Module** - Lógica de negócio (SOLID)
- `proton_service.py`: Detecção e validação do Proton
- `process_service.py`: Gerenciamento de processos
- `instance_service.py`: Orquestração de instâncias

### 3. **Models Module** - Estruturas de dados
- `profile.py`: Modelo de dados do perfil
- `instance.py`: Modelo de dados da instância

### 4. **CLI Module** - Interface de linha de comando
- `commands.py`: Parser de argumentos e interface CLI

## Benefícios da Arquitetura

- **Single Responsibility**: Cada módulo tem uma responsabilidade específica
- **Open/Closed**: Fácil extensão sem modificar código existente
- **Dependency Inversion**: Abstrações não dependem de detalhes
- **Testabilidade**: Componentes isolados facilitam testes
- **Manutenibilidade**: Código organizado e modular