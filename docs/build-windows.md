# Gerar o instalador no Windows

Este processo cria `dist\VisionHub\VisionHub.exe` e o instalador
`installer\output\VisionHub-VERSAO-Windows-Setup.exe`.

Execute os comandos no PowerShell, a partir da raiz do projeto.

## Pré-requisitos

- Windows 11 de 64 bits.
- Python 3.10 ou superior disponível no `PATH`.
- [Inno Setup 6](https://jrsoftware.org/isinfo.php).
- FFmpeg disponível no `PATH` do computador de destino caso o áudio seja
  utilizado.

## Preparar o ambiente

```powershell
py -m venv .venv-build
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
```

## Limpar e gerar a aplicação

```powershell
Remove-Item build, dist, VisionHub.spec -Recurse -Force -ErrorAction SilentlyContinue
pyinstaller --noconfirm --clean --windowed --name VisionHub `
  --collect-all cv2 --collect-all keyring main.py
```

Teste a aplicação antes de gerar o instalador:

```powershell
.\dist\VisionHub\VisionHub.exe
```

## Gerar o instalador `.exe`

```powershell
$version = python -c "from visionhub.version import __version__; print(__version__)"
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" `
  "/DMyAppVersion=$version" `
  "/DMyOutputBaseFilename=VisionHub-$version-Windows-Setup" `
  "installer\windows\VisionHub.iss"
```

O instalador será criado em:

```text
installer\output\VisionHub-VERSAO-Windows-Setup.exe
```

## Instalar e testar

Abra o arquivo gerado pelo Explorador de Arquivos ou pelo PowerShell:

```powershell
Start-Process ".\installer\output\VisionHub-$version-Windows-Setup.exe"
```

Conclua o assistente, abra o VisionHub pelo Menu Iniciar e confirme que a tela
de configuração inicial é exibida. O instalador local não possui assinatura de
código; por isso, o Windows SmartScreen pode apresentar um aviso. Distribuições
públicas devem ser assinadas com um certificado de assinatura de código.

