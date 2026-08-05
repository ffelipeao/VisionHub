# Gerar o instalador no macOS

Este processo cria `dist/VisionHub.app` e, em seguida, o instalador
`dist/VisionHub-VERSAO-macOS.dmg`.

## Pré-requisitos

- macOS com Python 3.10 ou superior.
- Ferramentas de linha de comando do Xcode.
- FFmpeg instalado no computador de destino caso o áudio seja utilizado.

Instale as ferramentas necessárias:

```bash
xcode-select --install
brew install python ffmpeg
```

## Preparar o ambiente

Na raiz do projeto:

```bash
python3 -m venv .venv-build
source .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
```

## Limpar e gerar o aplicativo

Remova somente os artefatos de builds anteriores:

```bash
rm -rf build dist VisionHub.spec
```

Gere o aplicativo:

```bash
pyinstaller --noconfirm --clean --windowed --name VisionHub \
  --collect-all cv2 --collect-all keyring main.py
```

Aplique a versão e uma assinatura local ad hoc:

```bash
VERSION=$(python -c 'from visionhub.version import __version__; print(__version__)')
BUILD_VERSION=${VERSION%%-*}
plutil -replace CFBundleShortVersionString -string "$VERSION" \
  dist/VisionHub.app/Contents/Info.plist
plutil -replace CFBundleVersion -string "$BUILD_VERSION" \
  dist/VisionHub.app/Contents/Info.plist
codesign --force --deep --sign - dist/VisionHub.app
```

## Testar o aplicativo

```bash
open dist/VisionHub.app
```

Se o Gatekeeper impedir a primeira abertura, clique com o botão direito no
aplicativo, escolha **Abrir** e confirme. A assinatura ad hoc serve para testes
locais, mas não elimina o aviso de segurança em outros Macs. Uma distribuição
pública sem esse aviso exige certificado **Developer ID Application** e
notarização pela Apple.

## Gerar e testar o DMG

```bash
hdiutil create -volname "VisionHub $VERSION" \
  -srcfolder dist/VisionHub.app -ov -format UDZO \
  "dist/VisionHub-$VERSION-macOS.dmg"
```

Abra o instalador gerado:

```bash
open "dist/VisionHub-$VERSION-macOS.dmg"
```

Arraste `VisionHub.app` para a pasta **Aplicativos** e teste a cópia instalada.

