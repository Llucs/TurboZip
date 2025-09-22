#!/bin/bash

# Script de instalação para TZP (Turbo Zip)
# Autor: Llucs

set -e

INSTALL_DIR="/usr/local/bin"
TZP_SCRIPT_NAME="tzp_stable.py"
TZP_SCRIPT_PATH="$INSTALL_DIR/$TZP_SCRIPT_NAME"
TZP_COMMAND="tzp"

echo "🚀 Iniciando instalação do TZP (Turbo Zip)..."

# 1. Instalar dependências Python
echo "Instalando dependências Python (lz4, zstandard, numpy)..."
pip3 install lz4 zstandard numpy

# 2. Copiar o script principal para o diretório de instalação
echo "Copiando script principal para $INSTALL_DIR..."
sudo cp "$TZP_SCRIPT_NAME" "$TZP_SCRIPT_PATH"
sudo chmod +x "$TZP_SCRIPT_PATH"

# 3. Criar um wrapper para o comando 'tzp'
echo "Criando comando '$TZP_COMMAND' no $INSTALL_DIR..."
sudo bash -c "cat > $INSTALL_DIR/$TZP_COMMAND <<EOF
#!/usr/bin/env python3
import subprocess
import sys
subprocess.run(['$TZP_SCRIPT_PATH'] + sys.argv[1:])
EOF"
sudo chmod +x "$INSTALL_DIR/$TZP_COMMAND"

# 4. Criar script de descompressão (tzp_decompress)
echo "Criando comando 'tzp_decompress' no $INSTALL_DIR..."
sudo bash -c "cat > $INSTALL_DIR/tzp_decompress <<EOF
#!/usr/bin/env python3
import subprocess
import sys
subprocess.run(['$TZP_SCRIPT_PATH', 'decompress'] + sys.argv[1:])
EOF"
sudo chmod +x "$INSTALL_DIR/tzp_decompress"

# 5. Criar script de compressão (tzp_compress)
echo "Criando comando 'tzp_compress' no $INSTALL_DIR..."
sudo bash -c "cat > $INSTALL_DIR/tzp_compress <<EOF
#!/usr/bin/env python3
import subprocess
import sys
subprocess.run(['$TZP_SCRIPT_PATH', 'compress'] + sys.argv[1:])
EOF"
sudo chmod +x "$INSTALL_DIR/tzp_compress"

echo "\n✅ Instalação do TZP concluída com sucesso!"
echo "Agora você pode usar o comando '$TZP_COMMAND' globalmente."
echo "Exemplos:"
echo "  $TZP_COMMAND compress arquivo.txt arquivo.tzp"
echo "  $TZP_COMMAND decompress arquivo.tzp arquivo.txt"
echo "  $TZP_COMMAND -h"


