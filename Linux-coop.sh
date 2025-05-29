#!/bin/bash
# filepath: /home/mallor/Documentos/GitHub/Linux-Coop/Linux-coop.sh

# INÍCIO DO SCRIPT
# Este script inicia instâncias de um jogo utilizando Proton, InputPlumber e Bubblewrap. 
# Ele lê um perfil com configurações, valida dependências, encontra dispositivos físicos e cria dispositivos virtuais.

# --- Configuração Inicial ---
# Define variáveis de ambiente e diretórios essenciais.
SCRIPT_NAME=$(basename "$0")
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROFILE_DIR="${SCRIPT_DIR}/profiles"
LOG_DIR="$HOME/.local/share/linux-coop/logs"         # Diretório para arquivos de log
PREFIX_BASE_DIR="$HOME/.local/share/linux-coop/prefixes" # Diretório base para Prefixos (Wine)

# --- Funções Auxiliares ---
# Função para registrar mensagens com timestamp.
log_message() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >&2  # Imprime a mensagem com data/hora no stderr
}

# Função para localizar o script do Proton baseado na versão informada.
find_proton_path() {
  local version_string="$1"
  local proton_run_script=""
  local steam_root
  local search_paths=(
    "$HOME/.steam/root" "$HOME/.local/share/Steam" "$HOME/.steam/steam"
    "$HOME/.steam/debian-installation" "/var/mnt/games/messi/Games/Steam"
  )
  log_message "Procurando por Proton: $version_string"
  for steam_path in "${search_paths[@]}"; do
    [ ! -d "$steam_path" ] && continue
    log_message "Verificando diretório Steam: $steam_path"
    steam_root="$steam_path"
    local potential_path=""
    if [[ "$version_string" == "Experimental" ]]; then
      potential_path=$(find "$steam_path/steamapps/common/" -maxdepth 1 -type d -name "Proton - Experimental" 2>/dev/null | head -n 1)
    else
      potential_path=$(find "$steam_path/steamapps/common/" "$steam_path/compatibilitytools.d/" -maxdepth 1 -type d \( -name "Proton $version_string" -o -name "$version_string" \) 2>/dev/null | head -n 1)
    fi
    if [ -n "$potential_path" ] && [ -f "$potential_path/proton" ]; then
      proton_run_script="$potential_path/proton"
      break
    fi
  done
  if [ -z "$proton_run_script" ]; then
    log_message "ERRO: Proton '$version_string' não encontrado."
    return 1
  fi
  log_message "Proton encontrado: $proton_run_script"
  echo "$proton_run_script|$steam_root"
  return 0
}

# Função de limpeza geral (mantida para encerrar instâncias)
cleanup_previous_instances() {
  local proton_cmd_path="$1"
  local exe_path_pattern="$2"
  log_message "Tentando encerrar instâncias anteriores de '$exe_path_pattern'..."
  pkill -f "gamescope.*-- '$proton_cmd_path' run '$exe_path_pattern'" && sleep 1 || true
  pkill -f "'$proton_cmd_path' run '$exe_path_pattern'" && sleep 1 || true
}

# Função que trata a interrupção (Ctrl+C) para finalizar as instâncias.
terminate_instances() {
  log_message "Recebido sinal de interrupção. Encerrando instâncias..."
  if [ ${#PIDS[@]} -gt 0 ]; then
    log_message "Encerrando PIDs das instâncias: ${PIDS[@]}"
    kill "${PIDS[@]}" 2>/dev/null && sleep 2
    kill -9 "${PIDS[@]}" 2>/dev/null
  fi
  log_message "Limpeza concluída."
  exit 0
}

# Nova função para solicitar a senha sudo quando necessário.
prompt_sudo_password() {
  echo "Por favor, insira sua senha de sudo (será solicitada se necessário):"
  sudo -v  # Valida as credenciais sudo
}

# --- Script Principal ---
# Validação de argumentos e carregamento do perfil com as configurações do jogo.
if [ -z "$1" ]; then
  echo "Uso: $SCRIPT_NAME <nome_do_perfil>"  # Exibe mensagem de uso caso nenhum perfil seja informado
  exit 1
fi
PROFILE_NAME="$1"
PROFILE_FILE="$PROFILE_DIR/$PROFILE_NAME.profile"
if [ ! -f "$PROFILE_FILE" ]; then
  echo "Erro: Perfil não encontrado: $PROFILE_FILE"  # Erro se o perfil não existir
  exit 1
fi

log_message "Carregando perfil: $PROFILE_NAME"
source "$PROFILE_FILE"  # Carrega o perfil contendo variáveis de configuração

# Validação das variáveis obrigatórias definidas no perfil
missing_vars=()
[[ -z "$GAME_NAME" ]] && missing_vars+=("GAME_NAME")
[[ -z "$EXE_PATH" ]] && missing_vars+=("EXE_PATH")
[[ -z "$PROTON_VERSION" ]] && missing_vars+=("PROTON_VERSION")
[[ -z "$NUM_PLAYERS" ]] && missing_vars+=("NUM_PLAYERS")
[[ -z "$INSTANCE_WIDTH" ]] && missing_vars+=("INSTANCE_WIDTH")
[[ -z "$INSTANCE_HEIGHT" ]] && missing_vars+=("INSTANCE_HEIGHT")
if [ ${#missing_vars[@]} -gt 0 ]; then
  echo "Erro: Variáveis obrigatórias faltando no perfil:"
  printf " - %s\n" "${missing_vars[@]}"
  exit 1
fi

if [ "$NUM_PLAYERS" -ne 2 ]; then
    log_message "ERRO: Este script está atualmente configurado para exatamente 2 jogadores."
    exit 1
fi

# Verifica se as dependências (gamescope, bwrap, udevadm, busctl) estão instaladas.
log_message "Verificando dependências..."
command -v gamescope &> /dev/null || { echo "Erro: 'gamescope' não encontrado."; exit 1; }
command -v bwrap &> /dev/null || { echo "Erro: 'bwrap' (bubblewrap) não encontrado."; exit 1; }
log_message "Dependências verificadas com sucesso."

prompt_sudo_password  # Solicita a senha do usuário para executar comandos com sudo

# Criação dos diretórios necessários (logs, prefixos)
mkdir -p "$LOG_DIR" || { log_message "ERRO: Não foi possível criar diretório de logs: $LOG_DIR"; exit 1; }
mkdir -p "$PREFIX_BASE_DIR" || { log_message "ERRO: Não foi possível criar diretório de prefixos: $PREFIX_BASE_DIR"; exit 1; }
log_message "Diretórios criados com sucesso."

# Localiza o script do Proton com base na versão informada
proton_result=$(find_proton_path "$PROTON_VERSION" | tail -n 1)
PROTON_CMD_PATH="$(echo "$proton_result" | cut -d'|' -f1)"
STEAM_COMPAT_CLIENT_INSTALL_PATH="$(echo "$proton_result" | cut -d'|' -f2)"
export STEAM_COMPAT_CLIENT_INSTALL_PATH
[ ! -f "$EXE_PATH" ] && { log_message "ERRO: Executável do jogo não existe: $EXE_PATH"; exit 1; }
EXE_NAME=$(basename "$EXE_PATH") 

# Verifica novamente a existência do executável do jogo
if [ ! -f "$EXE_PATH" ]; then
    log_message "ERRO: Executável do jogo não encontrado em: $EXE_PATH";
    exit 1
fi

# Finaliza instâncias anteriores do jogo para evitar conflitos.
cleanup_previous_instances "$PROTON_CMD_PATH" "$EXE_PATH"

# Declaração do array que armazenará os PIDs das instâncias iniciadas
declare -a PIDS=()
# Configura a captura de sinais (Ctrl+C) e direciona para a limpeza
trap terminate_instances SIGINT SIGTERM

log_message "Iniciando $NUM_PLAYERS instância(s) de '$GAME_NAME'..."

# --- Lançamento das Instâncias ---
# Loop que prepara e inicia as instâncias do jogo para cada jogador.
for (( i=1; i<=NUM_PLAYERS; i++ )); do
  instance_num=$i
  log_message "Preparando instância $instance_num..."

  prefix_dir="$PREFIX_BASE_DIR/${PROFILE_NAME}_instance_${instance_num}"
  mkdir -p "$prefix_dir/pfx" || { log_message "Erro ao criar diretório do prefixo: $prefix_dir"; terminate_instances; exit 1; }
  log_message "WINEPREFIX para instância $instance_num: $prefix_dir/pfx"

  # Exporta variáveis de ambiente necessárias para o Proton
  export STEAM_COMPAT_DATA_PATH="$prefix_dir"
  export WINEPREFIX="$prefix_dir/pfx"
  export DXVK_ASYNC="1"
  export PROTON_LOG="1"
  export PROTON_LOG_DIR="$LOG_DIR"

  # Configura o comando gamescope para resolução e tela cheia.
  gamescope_cmd=(
    gamescope
    -W "$INSTANCE_WIDTH" -H "$INSTANCE_HEIGHT" -f
    -- 
  )

  # Define o comando do Proton para executar o jogo.
  proton_cmd=(
    "$PROTON_CMD_PATH" run "$EXE_PATH"
  )

  log_file="$LOG_DIR/${PROFILE_NAME}_instance_${instance_num}.log"
  log_message "Lançando instância $instance_num (Log: $log_file)..."

  # Executa o comando completo unindo gamescope e proton; redireciona a saída para o log.
  "${gamescope_cmd[@]}" "${proton_cmd[@]}" > "$log_file" 2>&1 &
  pid=$!
  PIDS+=($pid)
  log_message "Instância $instance_num iniciada com PID: $pid"
  sleep 5  # Aguarda um breve momento para evitar sobrecarga
done

# Exibe mensagem informando que todas as instâncias foram lançadas e mostra os PIDs.
log_message "Todas as $NUM_PLAYERS instâncias foram lançadas."
log_message "PIDs: ${PIDS[@]}"
log_message "Pressione CTRL+C neste terminal para encerrar todas as instâncias."

# Loop de monitoramento: aguarda o término das instâncias.
while true; do
    all_dead=true
    for pid in "${PIDS[@]}"; do
        [ -e "/proc/$pid" ] && all_dead=false && break
    done
    if $all_dead; then
      log_message "Todas as instâncias parecem ter sido encerradas."
      break
    fi
    sleep 5
done

log_message "Script concluído."
exit 0