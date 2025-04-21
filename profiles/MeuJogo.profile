# Nome do Jogo
GAME_NAME="Palworld"

# Caminho do Executável
EXE_PATH="/mnt/games/messi/Games/Steam/steamapps/common/Palworld/Pal/Binaries/Win64/Palworld-Win64-Shipping.exe"

# Versão do Proton
PROTON_VERSION="GE-Proton9-27"

# Número de jogadores/instâncias
NUM_PLAYERS=2

# Resolução por instância
INSTANCE_WIDTH=960
INSTANCE_HEIGHT=1080

# --- Configuração InputPlumber ---
# Nome base para os dispositivos virtuais que serão criados
# (Resultará em: virtual-gamepad-p1, virtual-gamepad-p2)
VIRTUAL_DEVICE_BASENAME="virtual-gamepad-p"

# Array com identificadores PERSISTENTES dos controles FÍSICOS
# Use caminhos de /dev/input/by-id/* ou nomes/IDs únicos
PLAYER_PHYSICAL_DEVICE_IDS=(
  "/dev/input/by-id/usb-Microsoft_Inc._Controller_188A6F4-event-joystick" # Jogador 1
  "/dev/input/by-id/usb-045e_Gamesir-T4w_1.39-event-joystick" # Jogador 2
)
# Garantir que a ordem aqui corresponda à ordem dos jogadores

# (Opcional) Argumentos do jogo
GAME_ARGS="-dx12"
