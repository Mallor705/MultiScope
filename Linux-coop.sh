#!/bin/bash

# --- Configuração Inicial ---
# ... (keep previous log, dir settings) ...
INPUTPLUMBER_SERVICE_NAME="inputplumber.service"
INPUTPLUMBER_DBUS_SERVICE="org.shadowblip.InputPlumber"
INPUTPLUMBER_DBUS_PATH="/org/shadowblip/InputPlumber"
# Diretório para configs YAML temporárias do InputPlumber
INPUTPLUMBER_TEMP_YAML_DIR="/tmp/linux-coop-ip-yamls"

# --- Funções Auxiliares ---
log_message() { # ... (keep) ... }
find_proton_path() { # ... (keep) ... }

# --- Funções de Joystick e Propriedades ---
find_joystick_event_nodes() {
    local -n _out_array=$1 # Output array reference
    _out_array=()
    local count=0
    # Encontra symlinks em by-id que contenham '-event-joystick' ou '-event-gamepad'
    # e resolve para o nome do dispositivo eventX real
    while IFS= read -r line; do
        if [[ $count -lt 2 ]]; then
            local real_dev=$(readlink -f "$line")
            if [[ "$real_dev" == /dev/input/event* ]]; then
                _out_array+=("$real_dev")
                ((count++))
                log_message "Joystick $count encontrado: $line -> $real_dev"
            fi
        else
            break
        fi
    done < <(find /dev/input/by-id/ -lname '*event-joystick' -o -lname '*event-gamepad' 2>/dev/null | sort)

    if [[ ${#_out_array[@]} -lt 2 ]]; then
        log_message "ERRO: Menos de 2 joysticks encontrados em /dev/input/by-id/. Verifique se estão conectados."
        return 1
    fi
    return 0
}

get_evdev_property() {
    local event_node="$1" # Ex: /dev/input/event5
    local property_name="$2" # Ex: NAME, PHYS, UNIQ
    local value=$(udevadm info --query=property --name="$event_node" | grep "ID_INPUT_JOYSTICK=1" > /dev/null && \
                  udevadm info --query=property --name="$event_node" | grep "^E: $property_name=" | cut -d'=' -f2)
    # Remove aspas se houver
    value="${value%\"}"
    value="${value#\"}"
    echo "$value"
}

# --- Funções InputPlumber ---

ensure_inputplumber_running() { # ... (keep as before, using systemctl) ... }

# Gera um arquivo YAML de CompositeDevice temporário para UM joystick
# NOTA: A sintaxe é baseada no README, mas pode precisar de ajustes.
generate_composite_yaml() {
    local player_num="$1" # 1 or 2
    local yaml_file="$2"
    local event_node="$3" # Ex: /dev/input/event5
    local match_prop_name="NAME" # Usar o nome do dispositivo para correspondência
    local match_prop_value=$(get_evdev_property "$event_node" "$match_prop_name")
    local virtual_device_name="VirtualCoop_P${player_num}" # Nome para o device uinput

    if [ -z "$match_prop_value" ]; then
        log_message "ERRO: Não foi possível obter a propriedade '$match_prop_name' para $event_node."
        return 1
    fi

    log_message "Gerando YAML para Jogador $player_num ($event_node - Nome: '$match_prop_value') em $yaml_file"

    cat > "$yaml_file" << EOF
# yaml-language-server: \$schema=https://raw.githubusercontent.com/ShadowBlip/InputPlumber/main/rootfs/usr/share/inputplumber/schema/composite_device_v1.json
version: 1
kind: CompositeDevice
# Nome do dispositivo composto (informativo)
name: LinuxCoop_Player_${player_num}_Composite

# Não usar correspondência de DMI, queremos carregar dinamicamente
matches: []

# Dispositivo físico de origem - tenta corresponder pelo nome do evdev
source_devices:
  - group: gamepad # Agrupamento lógico
    evdev:
      # Corresponde ao nome exato do dispositivo evdev físico
      name: "$match_prop_value"
      # Poderia usar phys_path também/em vez, mas é menos estável que o nome:
      # phys_path: "$(get_evdev_property "$event_node" "PHYS")"

# Dispositivo virtual de destino a ser criado
target_devices:
  - gamepad # Cria um dispositivo uinput de gamepad virtual

# ID de um mapa de capacidade (opcional, deixar vazio para espelhamento 1:1)
capability_map_id: ""
EOF

    # Verifica se o arquivo foi criado
    [ ! -f "$yaml_file" ] && { log_message "ERRO: Falha ao criar arquivo YAML $yaml_file"; return 1; }
    return 0
}

# **ASSUNÇÃO CRÍTICA**: Supõe que existe um método D-Bus para carregar uma definição de CompositeDevice
load_composite_device_via_dbus() {
    local yaml_file="$1"
    log_message "Tentando carregar definição de Composite Device via D-Bus: $yaml_file"
    log_message "AVISO: A funcionalidade de carregar Composite Devices dinamicamente via D-Bus é uma ASSUNÇÃO baseada na necessidade, não explicitamente confirmada no README."

    # Comando busctl hipotético. O método real PODE NÃO EXISTIR.
    # A interface pode ser 'org.shadowblip.InputPlumber.Manager' ou outra.
    busctl call $INPUTPLUMBER_DBUS_SERVICE \
        $INPUTPLUMBER_DBUS_PATH \
        org.shadowblip.InputPlumber \
        LoadCompositeDeviceDefinition "s" "$yaml_file"

    # Verificar o código de saída do busctl
    if [ $? -ne 0 ]; then
        log_message "ERRO: Comando busctl (hipotético) para carregar Composite Device falhou para $yaml_file."
        log_message "      Verifique se o InputPlumber suporta carregamento dinâmico ou se o método/interface D-Bus está correto."
        return 1
    fi
    log_message "Solicitação (hipotética) para carregar $yaml_file enviada. Aguardando criação do dispositivo virtual..."
    sleep 4 # Tempo generoso para InputPlumber processar e criar o nó uinput
    return 0
}

# Encontra o nó de dispositivo virtual correspondente criado pelo InputPlumber
find_virtual_device_node() {
    local player_num="$1"
    local expected_name="VirtualCoop_P${player_num}" # Deve corresponder ao 'name' gerado no YAML? Ou ao 'name' do output? Incerto.
                                                    # InputPlumber pode usar um nome diferente.
    local found_path=""
    local attempt=0
    log_message "Procurando por nó de dispositivo virtual com nome contendo '$expected_name'..."

    # InputPlumber pode criar o nó com um nome diferente, vamos procurar por propriedades
    # Tentativa: Listar dispositivos InputPlumber via D-Bus e encontrar o que tem 'kind: target' e 'type: gamepad'
    # Isso é mais robusto, mas complexo de fazer em bash.
    # Abordagem simples por enquanto: procurar em /dev/input
    while [[ $attempt -lt 5 ]]; do
       # Procura por um device node que tenha o nome esperado em suas propriedades udev
       found_path=$(find /dev/input/event* 2>/dev/null | while IFS= read -r ev_node; do
           if udevadm info --query=property --name="$ev_node" | grep -q "NAME=.*$expected_name"; then
               echo "$ev_node"
               break
           fi
       done)

       if [ -n "$found_path" ]; then
           log_message "Dispositivo virtual encontrado para Jogador $player_num: $found_path"
           echo "$found_path"
           return 0
       fi
       log_message "Tentativa $attempt: Dispositivo virtual para Jogador $player_num ainda não encontrado, esperando..."
       sleep 2
       ((attempt++))
    done

    log_message "ERRO: Não foi possível encontrar o nó do dispositivo virtual para Jogador $player_num após várias tentativas."
    return 1
}

# **ASSUNÇÃO CRÍTICA**: Supõe que existe uma forma de descarregar/remover a definição ou que reiniciar o serviço é necessário/suficiente.
unload_composite_definitions() {
    log_message "Tentando descarregar definições de Composite Device..."
    log_message "AVISO: O método para descarregar Composite Devices dinamicamente é uma ASSUNÇÃO."

    # Opção 1: Método D-Bus (Hipotético)
    # for p in 1 2; do
    #   busctl call $INPUTPLUMBER_DBUS_SERVICE $INPUTPLUMBER_DBUS_PATH org.shadowblip.InputPlumber UnloadCompositeDeviceDefinition "s" "LinuxCoop_Player_${p}_Composite"
    # done

    # Opção 2: Remover arquivos e reiniciar/recarregar serviço (mais provável se dinâmico não existe)
    log_message "Removendo arquivos YAML temporários..."
    rm -rf "$INPUTPLUMBER_TEMP_YAML_DIR"
    log_message "Reiniciando serviço $INPUTPLUMBER_SERVICE_NAME para garantir a limpeza..."
    # Usar restart pode interromper outras coisas que usam InputPlumber! Reload pode ser insuficiente.
    sudo systemctl restart "$INPUTPLUMBER_SERVICE_NAME" || log_message "Aviso: Falha ao reiniciar $INPUTPLUMBER_SERVICE_NAME durante a limpeza."
}

# --- Função de Limpeza Geral ---
# (cleanup_previous_instances as before)

terminate_instances() {
  log_message "Recebido sinal de interrupção. Encerrando instâncias..."
  # 1. Matar processos dos jogos/gamescope
  if [ ${#PIDS[@]} -gt 0 ]; then
    log_message "Encerrando PIDs das instâncias: ${PIDS[@]}"
    kill "${PIDS[@]}" 2>/dev/null && sleep 2
    kill -9 "${PIDS[@]}" 2>/dev/null
  fi
  # 2. Descarregar definições do InputPlumber / Reiniciar serviço
  unload_composite_definitions
  log_message "Limpeza concluída."
  exit 0
}


# --- Script Principal ---

# Verificação de Argumentos e Carregamento do Perfil
# ... (load profile, validate vars - ensure VIRTUAL_DEVICE_BASENAME is removed, no longer needed) ...
if [ "$NUM_PLAYERS" -ne 2 ]; then
    log_message "ERRO: Este script está atualmente configurado para exatamente 2 jogadores."
    exit 1
fi

# Verificações de Dependências
# ... (check gamescope, bwrap) ...
command -v udevadm &> /dev/null || { echo "Erro: 'udevadm' não encontrado."; exit 1; }
command -v busctl &> /dev/null || { echo "Erro: 'busctl' não encontrado."; exit 1; }
# ... (check inputplumber service/presence) ...

# Preparação
mkdir -p "$LOG_DIR"
mkdir -p "$PREFIX_BASE_DIR"
mkdir -p "$INPUTPLUMBER_TEMP_YAML_DIR" || { echo "ERRO: Não foi possível criar diretório temporário $INPUTPLUMBER_TEMP_YAML_DIR"; exit 1; }

PROTON_CMD_PATH=$(find_proton_path "$PROTON_VERSION") || exit 1
# ... (check proton/exe path) ...
EXE_NAME=$(basename "$EXE_PATH")

# Encontrar Joysticks Físicos
declare -a PHYSICAL_EVENT_NODES
find_joystick_event_nodes PHYSICAL_EVENT_NODES || exit 1

# Preparar e Ativar Configuração InputPlumber
ensure_inputplumber_running
declare -a TEMP_YAML_FILES
declare -a VIRTUAL_DEVICE_NODES

# Gerar e tentar carregar YAML para cada jogador
for p_idx in 0 1; do # Índices 0 e 1 para 2 jogadores
    player_num=$((p_idx + 1))
    event_node="${PHYSICAL_EVENT_NODES[$p_idx]}"
    yaml_file="$INPUTPLUMBER_TEMP_YAML_DIR/player_${player_num}.yaml"
    TEMP_YAML_FILES+=("$yaml_file")

    generate_composite_yaml "$player_num" "$yaml_file" "$event_node" || { unload_composite_definitions; exit 1; }
    # ** PONTO CRÍTICO DE ASSUNÇÃO **
    load_composite_device_via_dbus "$yaml_file" || { unload_composite_definitions; exit 1; }

    # Encontrar o nó virtual criado
    virt_node=$(find_virtual_device_node "$player_num") || { unload_composite_definitions; exit 1; }
    VIRTUAL_DEVICE_NODES+=("$virt_node")
done

# Verificar se temos 2 nós virtuais
if [ ${#VIRTUAL_DEVICE_NODES[@]} -ne 2 ]; then
   log_message "ERRO: Número incorreto de dispositivos virtuais encontrados (${#VIRTUAL_DEVICE_NODES[@]})."
   unload_composite_definitions
   exit 1
fi

# Limpar instâncias anteriores (depois de configurar InputPlumber e encontrar nós virtuais)
cleanup_previous_instances "$PROTON_CMD_PATH" "$EXE_PATH"

# Configurar Trap para Limpeza
declare -a PIDS=()
trap terminate_instances SIGINT SIGTERM

# --- Lançamento das Instâncias ---
log_message "Iniciando $NUM_PLAYERS instância(s) usando InputPlumber (Composite+YAML) e Bubblewrap..."

for (( i=1; i<=NUM_PLAYERS; i++ )); do
  instance_num=$i
  player_index=$((i-1))
  log_message "Preparando instância $instance_num..."

  prefix_dir="$PREFIX_BASE_DIR/${PROFILE_NAME}_instance_${instance_num}"
  mkdir -p "$prefix_dir/pfx" || { log_message "Erro ao criar diretório do prefixo: $prefix_dir"; terminate_instances; exit 1; }

  # Obter o caminho do dispositivo virtual para este jogador
  current_virtual_device_node="${VIRTUAL_DEVICE_NODES[$player_index]}"
  log_message "Instância $instance_num usará o dispositivo virtual: $current_virtual_device_node"

  # --- Montar Comando Bubblewrap ---
  # (bwrap_cmd as before, using the standard binds)
  bwrap_cmd=(
    bwrap
    # ... (standard --unshare, --proc, --dev, --dev-bind /dev/dri, --dev-bind /dev/snd, sockets, etc.) ...
    --ro-bind /usr /usr
    --bind "$prefix_dir" "$prefix_dir"
    --bind "$HOME" "$HOME" # Ou mais seletivo
    --bind "$(dirname "$EXE_PATH")" "$(dirname "$EXE_PATH")"
    --bind "$(dirname "$PROTON_CMD_PATH")/../../.." "$(dirname "$PROTON_CMD_PATH")/../../.."
    # --- Bind do Dispositivo Virtual InputPlumber ---
    "--dev-bind" "$current_virtual_device_node" "/dev/input/event0" # Mapeia como event0 DENTRO do sandbox
    # --- Variáveis de Ambiente ---
    --setenv STEAM_COMPAT_DATA_PATH "$prefix_dir"
    # ... (WINEPREFIX, DXVK_ASYNC, PROTON_LOG, etc.) ...
  )

  # Comando Gamescope (será executado por bwrap)
  # ... (gamescope_cmd as before, add positioning logic if desired) ...

  # Comando Proton (será executado por gamescope)
  # ... (proton_cmd as before) ...

  log_file="$LOG_DIR/${PROFILE_NAME}_instance_${instance_num}.log"
  log_message "Lançando instância $instance_num (Log: $log_file)..."

  # Combina tudo e executa em background
  "${bwrap_cmd[@]}" "${gamescope_cmd[@]}" "${proton_cmd[@]}" > "$log_file" 2>&1 &
  pid=$!
  PIDS+=($pid)
  log_message "Instância $instance_num iniciada com PID: $pid"
  sleep 5 # Atraso entre lançamentos
done

# --- Conclusão e Espera ---
# ... (wait loop as before) ...

# Limpeza final (se o loop terminar sem Ctrl+C)
unload_composite_definitions
log_message "Script concluído."
exit 0