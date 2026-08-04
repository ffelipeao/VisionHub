# VisionHub

VisionHub é um reprodutor desktop pensado para capturar e exibir imagens de
quaisquer câmeras de segurança compatíveis com o protocolo RTSP. Inicialmente,
o projeto utiliza um mosaico 2×2 para quatro câmeras, mas pode ser expandido
para oito ou dezesseis câmeras, conforme a necessidade. O programa permite
ampliar uma câmera, entrar em tela cheia, reproduzir o áudio de um canal por vez
e controlar o volume individualmente.

O vídeo é processado pelo OpenCV e o áudio é reproduzido pelo `ffplay`. As
credenciais e demais configurações ficam em um arquivo `.env`, sem necessidade
de alterar o código-fonte.

## Recursos

- Visualização simultânea de quatro canais RTSP.
- Modo ampliado para uma câmera.
- Tela cheia com restauração do tamanho e da posição anteriores.
- Redimensionamento das imagens sem distorção.
- Reprodução de áudio iniciada no modo silencioso.
- Controle de volume por câmera.
- Apenas uma câmera com áudio ativo por vez, evitando sobreposição.
- Reconexão automática com espera progressiva.
- Indicação de câmera online, desconectada ou em reconexão.
- Logs repetitivos do FFmpeg suprimidos quando uma câmera está ausente.

## Requisitos

- Python 3.10 ou superior.
- Tkinter, normalmente incluído na instalação do Python.
- FFmpeg com o executável `ffplay`, necessário para o áudio.
- NVR ou câmeras acessíveis pela rede e com RTSP habilitado.

### Instalando o FFmpeg

No macOS com Homebrew:

```bash
brew install ffmpeg
```

No Ubuntu ou Debian:

```bash
sudo apt update
sudo apt install ffmpeg python3-tk
```

No Windows, instale o FFmpeg e adicione a pasta que contém `ffplay.exe` à
variável `PATH`. Como alternativa, informe seu caminho completo em
`FFPLAY_PATH` no `.env`.

Confirme a instalação:

```bash
ffplay -version
```

## Instalação

Clone ou abra o projeto e entre em sua pasta:

```bash
cd visuonhub
```

Crie um ambiente virtual:

```bash
python3 -m venv .venv
```

Ative o ambiente no macOS ou Linux:

```bash
source .venv/bin/activate
```

No Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

## Configuração

Crie o `.env` a partir do modelo:

```bash
cp .env.example .env
```

No Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edite o `.env` com os dados do equipamento:

```env
NVR_IP=192.168.1.100
NVR_RTSP_PORT=554
NVR_USER=admin
NVR_PASSWORD=troque_por_sua_senha
NVR_STREAM=1

WINDOW_WIDTH=1280
WINDOW_HEIGHT=720
WINDOW_SCALE=0.92
IMAGE_FIT=cover
UI_FPS=15
AUDIO_VOLUME=50
RECONNECT_SECONDS=3.0
RECONNECT_MAX_SECONDS=60.0
```

O `.env` está ignorado pelo Git e não deve ser enviado ao repositório, pois
contém as credenciais do NVR.

### Variáveis disponíveis

| Variável | Obrigatória | Padrão | Descrição |
| --- | --- | --- | --- |
| `NVR_IP` | Sim | — | Endereço IP ou nome do NVR. |
| `NVR_RTSP_PORT` | Não | `554` | Porta do serviço RTSP. |
| `NVR_USER` | Sim | — | Usuário com acesso aos canais. |
| `NVR_PASSWORD` | Sim | — | Senha do usuário. |
| `NVR_STREAM` | Não | `1` | `0` para stream principal ou `1` para substream. |
| `WINDOW_WIDTH` | Não | `1280` | Largura usada para calcular a proporção da janela. |
| `WINDOW_HEIGHT` | Não | `720` | Altura usada para calcular a proporção da janela. |
| `WINDOW_SCALE` | Não | `0.92` | Fração da tela utilizada pela janela, entre `0.5` e `1.0`. |
| `IMAGE_FIT` | Não | `cover` | `cover` preenche o quadro; `contain` preserva toda a imagem. |
| `UI_FPS` | Não | `15` | Frequência máxima de atualização da interface. |
| `AUDIO_VOLUME` | Não | `50` | Volume inicial, entre `0` e `100`. |
| `FFPLAY_PATH` | Não | Detectado no `PATH` | Caminho completo do executável `ffplay`. |
| `RECONNECT_SECONDS` | Não | `3.0` | Espera inicial antes de tentar reconectar. |
| `RECONNECT_MAX_SECONDS` | Não | `60.0` | Espera máxima entre novas tentativas. |

### Canais e URL RTSP

Por padrão, o VisionHub cria os canais 1, 2, 3 e 4. O endereço de cada canal é
montado no seguinte formato:

```text
rtsp://usuario:senha@ip:porta/avstream/channel=CANAL/stream=STREAM.sdp
```

Para alterar nomes, quantidade ou números dos canais, edite a lista `CAMERAS`
em `visionhub/config.py`:

```python
CAMERAS = [
    CameraConfig("Entrada", 1),
    CameraConfig("Garagem", 2),
    CameraConfig("Sala", 3),
    CameraConfig("Quintal", 4),
]
```

## Executando

Com o ambiente virtual ativado:

```bash
python main.py
```

O áudio começa fechado. O VisionHub não abre nenhuma reprodução de áudio até
que o botão de alto-falante de uma câmera seja acionado.

## Controles

### Controles dos painéis

- **Ampliar:** faz a câmera preencher toda a área da janela.
- **Mosaico:** devolve a câmera ampliada ao quadro original no mosaico 2×2.
- **Tela cheia:** abre a câmera escolhida ocupando toda a tela.
- **Restaurar:** sai da tela cheia e recupera a visualização anterior.
- **Áudio:** ativa ou silencia o áudio da câmera correspondente.
- **Volume:** ajusta o volume daquela câmera de `0` a `100`.
- **Duplo clique:** alterna entre câmera ampliada e mosaico.

Ao ativar o áudio de outra câmera, o canal anterior é silenciado
automaticamente.

### Atalhos de teclado

| Atalho | Ação |
| --- | --- |
| `F11` | Alterna a tela cheia preservando a visualização atual. |
| `Command + F` | Alterna a tela cheia no macOS. |
| `Esc` | Sai da tela cheia ou retorna uma câmera ampliada ao mosaico. |
| `Enter` ou `Espaço` | Aciona um botão vetorial que esteja com foco. |

## Ajuste da imagem

O modo `cover` preenche todo o painel sem deformar a imagem. Dependendo da
proporção da câmera, uma pequena parte das bordas pode ser recortada:

```env
IMAGE_FIT=cover
```

Para sempre mostrar o quadro completo, aceitando possíveis bordas pretas:

```env
IMAGE_FIT=contain
```

## Estrutura do projeto

```text
.
├── main.py                 # Ponto de entrada
├── requirements.txt        # Dependências Python
├── .env.example            # Modelo de configuração
└── visionhub/
    ├── __init__.py         # Interface pública do pacote
    ├── app.py              # Janela, mosaico e interações
    ├── config.py           # Ambiente, validações e câmeras
    ├── media.py            # Vídeo RTSP e áudio
    └── widgets.py          # Painéis, controles e ícones
```

## Solução de problemas

### A câmera mostra “Sem conexão”

Verifique:

- Se o NVR e a câmera estão ligados e acessíveis na rede.
- Se o canal está online no painel do NVR.
- Se a porta RTSP está habilitada e corresponde a `NVR_RTSP_PORT`.
- Se usuário e senha possuem acesso à visualização ao vivo.
- Se o número configurado em `CAMERAS` corresponde ao canal real.

O VisionHub continuará tentando conectar com intervalos progressivos, sem
imprimir o mesmo erro constantemente.

### Erro `DESCRIBE failed: 500 Internal Server Error`

Esse retorno normalmente indica que o NVR recebeu a solicitação, mas rejeitou o
canal ou stream. Teste se o canal está online e alterne temporariamente entre:

```env
NVR_STREAM=0
```

e:

```env
NVR_STREAM=1
```

### A imagem aparece, mas não há áudio

- Confirme que a câmera transmite áudio no mesmo fluxo RTSP.
- Verifique se `ffplay -version` funciona no terminal.
- Confirme que o botão de alto-falante da câmera está ativo.
- Aumente o controle de volume do painel e o volume do sistema operacional.
- Se necessário, defina `FFPLAY_PATH` com o caminho completo do executável.

### O `ffplay` não foi encontrado

Localize o executável:

```bash
command -v ffplay
```

Depois informe o resultado no `.env`, por exemplo:

```env
FFPLAY_PATH=/opt/homebrew/bin/ffplay
```

### Tkinter não está disponível no Linux

Em distribuições baseadas em Ubuntu ou Debian:

```bash
sudo apt install python3-tk
```

## Segurança

- Não publique o arquivo `.env`.
- Use um usuário do NVR com apenas as permissões necessárias.
- Evite expor a porta RTSP diretamente à internet.
- Prefira executar o VisionHub na mesma rede local ou por uma VPN confiável.
