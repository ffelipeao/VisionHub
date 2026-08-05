# Build e instaladores locais

Os guias desta pasta descrevem como gerar uma aplicação independente e um
instalador local em cada sistema operacional suportado:

- [macOS: aplicativo `.app` e instalador `.dmg`](build-macos.md)
- [Linux: aplicação e pacote `.deb`](build-linux.md)
- [Windows: aplicação e instalador `.exe`](build-windows.md)

O build deve ser executado no próprio sistema de destino. O PyInstaller não
gera binários para outro sistema operacional: o `.dmg` deve ser criado no
macOS, o `.deb` no Linux e o `.exe` no Windows.

Todos os comandos partem da raiz do repositório. A versão usada nos nomes dos
artefatos é lida de `visionhub/version.py`.

