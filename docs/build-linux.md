# Gerar o instalador no Linux

Este guia usa Ubuntu ou Debian para criar a aplicação independente e um pacote
local `dist/VisionHub-VERSAO-amd64.deb`.

## Pré-requisitos

Instale Python, Tkinter, FFmpeg e as ferramentas de empacotamento:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-tk ffmpeg dpkg-dev
```

O projeto deve conter o ícone principal `assets/icon.png` e as versões de
16 a 512 pixels em `assets/linux/`.

## Preparar o ambiente

Na raiz do projeto:

```bash
python3 -m venv .venv-build
source .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
```

## Limpar e gerar a aplicação

```bash
rm -rf build dist VisionHub.spec package
pyinstaller --noconfirm --clean --windowed --name VisionHub \
  --icon assets/icon.png \
  --add-data assets/VisuonHub.png:assets \
  --collect-all cv2 --collect-all keyring main.py
```

No Linux, a exibição do ícone no menu de aplicativos é definida pelo pacote
`.deb`; por isso, os PNGs também serão copiados para o tema de ícones do sistema.
O parâmetro `--add-data` inclui a imagem exibida na abertura do programa.

Teste antes de empacotar:

```bash
./dist/VisionHub/VisionHub
```

## Gerar o pacote `.deb`

Monte a estrutura do pacote:

```bash
VERSION=$(python -c 'from visionhub.version import __version__; print(__version__)')
mkdir -p package/DEBIAN package/opt/visionhub package/usr/bin \
  package/usr/share/applications
cp -a dist/VisionHub/. package/opt/visionhub/
ln -s /opt/visionhub/VisionHub package/usr/bin/visionhub

for size in 16 24 32 48 64 128 256 512; do
  mkdir -p "package/usr/share/icons/hicolor/${size}x${size}/apps"
  cp "assets/linux/icon-${size}.png" \
    "package/usr/share/icons/hicolor/${size}x${size}/apps/visionhub.png"
done
```

Crie `package/usr/share/applications/visionhub.desktop` com este conteúdo:

```ini
[Desktop Entry]
Type=Application
Name=VisionHub
Comment=Visualizador de câmeras RTSP
Exec=visionhub
Icon=visionhub
Terminal=false
Categories=AudioVideo;Video;Security;
```

O valor `Icon=visionhub` referencia os PNGs copiados para o tema `hicolor`, sem
extensão ou caminho absoluto.

Crie `package/DEBIAN/control` com o conteúdo abaixo, substituindo `VERSAO` pelo
valor exibido pelo comando `echo "$VERSION"`:

```text
Package: visionhub
Version: VERSAO
Section: video
Priority: optional
Architecture: amd64
Maintainer: ffelipeao
Depends: ffmpeg
Description: Visualizador desktop de cameras RTSP
```

O campo `Version` do Debian não aceita todos os formatos de pré-lançamento. Se
a versão possuir hífen, como `1.1.0-beta.2`, use `1.1.0~beta.2` no arquivo
`control`; o nome do artefato pode manter a versão original.

Gere o pacote:

```bash
dpkg-deb --build --root-owner-group package \
  "dist/VisionHub-$VERSION-amd64.deb"
```

## Instalar e testar

```bash
sudo apt install "./dist/VisionHub-$VERSION-amd64.deb"
visionhub
```

Para remover a instalação de teste:

```bash
sudo apt remove visionhub
```

O pacote acima é destinado a computadores `amd64`. Em outra arquitetura,
ajuste o campo `Architecture` e o nome do arquivo.
