# Nome do Jogo
GAME_NAME="Palworld"

# Caminho do Executável
EXE_PATH="/mnt/games/messi/Games/Steam/steamapps/common/Palworld/Palworld.exe"

# Versão do Proton
PROTON_VERSION="GE-Proton10-3"

# Número de jogadores/instâncias
NUM_PLAYERS=2

# Resolução por instância
INSTANCE_WIDTH=1920
INSTANCE_HEIGHT=1080

# Joystick para jogador 1, nenhum para jogador 2
PLAYER_PHYSICAL_DEVICE_IDS=(
    "/dev/input/by-id/usb-8BitDo_8BitDo_Ultimate_wireless_Controller_for_PC_4057CAD817E4-event-joystick" # Jogador 1
    "/dev/input/by-id/usb-045e_Gamesir-T4w_1.39-event-joystick" # Jogador 2
)

# Mouse para jogador 1, mouse para jogador 2
PLAYER_MOUSE_EVENT_PATHS=(
    "" # Jogador 1
    "/dev/input/by-id/usb-04d9_USB_Gaming_Mouse-event-mouse" # Jogador 2
)

# Teclado para jogador 1, teclado para jogador 2
PLAYER_KEYBOARD_EVENT_PATHS=(
    "" # Jogador 1
    "/dev/input/by-id/usb-Evision_RGB_Keyboard-event-kbd" # Jogador 2
)

# Garanta que a ordem aqui corresponda à ordem dos jogadores

# (Opcional) Argumentos do jogo
GAME_ARGS="-dx12"
