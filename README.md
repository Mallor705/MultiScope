# Linux-Coop

Permite jogar títulos Windows em modo cooperativo local no Linux, rodando múltiplas instâncias do mesmo jogo via Proton e gamescope, com perfis independentes e suporte a controles.

## Funcionalidades

- Executa duas instâncias do mesmo jogo simultaneamente (co-op local).
- Perfis separados para cada jogo, com saves e configurações independentes.
- Seleção de qualquer executável `.exe` e versão do Proton (incluindo GE-Proton).
- Resolução customizável por instância.
- Logs automáticos para depuração.
- Mapeamento de controles físicos para cada jogador.
- Suporte a múltiplos jogos via perfis.

## Status

- Jogos abrem em duas instâncias e saves são separados.
- Coop funcional.
- Desempenho esperado.
- Versão do Proton é selecionável.
- Suporte ao Proton GE.
- Perfis para cada jogo.
- **Problemas conhecidos:**
  - Controles podem não ser reconhecidos em alguns casos (prioridade de correção).
  - Instâncias abrem no mesmo monitor (mover manualmente se necessário).

## Pré-requisitos

- **Steam** instalado e configurado.
- **Proton** (ou GE-Proton) instalado via Steam.
- **Gamescope** instalado ([instruções oficiais](https://github.com/ValveSoftware/gamescope)).
- **Bubblewrap** (`bwrap`).
- Permissões para acessar dispositivos de controle em `/dev/input/by-id/`.
- Bash, utilitários básicos do Linux.

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/Mallor705/Linux-Coop.git
   cd Linux-Coop
   ```
2. Dê permissão de execução ao script:
   ```bash
   chmod +x Linux-coop.sh
   ```

## Como Usar

### 1. Crie um perfil de jogo

Crie um arquivo em `profiles/` com o nome desejado e extensão `.profile`. Exemplo: `MeuJogo.profile`.

Exemplo de conteúdo:
```bash
GAME_NAME="Palworld"
EXE_PATH="/caminho/para/Palworld.exe"
PROTON_VERSION="GE-Proton10-3"
NUM_PLAYERS=2
INSTANCE_WIDTH=1920
INSTANCE_HEIGHT=1080
# (Opcional) Argumentos do jogo
GAME_ARGS="-dx12"
# (Opcional) IDs dos controles físicos
PLAYER_PHYSICAL_DEVICE_IDS=(
  "/dev/input/by-id/usb-Controller1-event-joystick"
  "/dev/input/by-id/usb-Controller2-event-joystick"
)
```

### 2. Execute o script principal

```bash
./Linux-coop.sh MeuJogo
```
- O script irá:
  - Validar dependências.
  - Carregar o perfil.
  - Criar prefixos separados para cada instância.
  - Iniciar duas janelas do jogo via gamescope.
  - Gerar logs em `~/.local/share/linux-coop/logs/`.

### 3. Mapeamento de controles

- Os controles são definidos no perfil ou em arquivos dentro de `controller_config/`.
- Para evitar conflitos, blacklists são criados automaticamente (exemplo: `Player1_Controller_Blacklist`).
- Certifique-se de conectar os controles antes de iniciar o script.

## Dicas e Solução de Problemas

- **Controles não reconhecidos:** Verifique permissões em `/dev/input/by-id/` e IDs corretos no perfil.
- **Proton não encontrado:** Confirme o nome e instalação da versão desejada no Steam.
- **Instâncias no mesmo monitor:** Mova manualmente cada janela para o monitor desejado.
- **Logs:** Consulte `~/.local/share/linux-coop/logs/` para depuração.

## Observações

- Testado com Palworld, mas pode funcionar com outros jogos (pode exigir ajustes no perfil).
- O script atualmente suporta apenas dois jogadores.
- Para jogos que não suportam múltiplas instâncias, pode ser necessário usar sandboxes ou contas Steam separadas.

## Licença

Consulte o arquivo LICENSE (se houver) ou o repositório para detalhes.
