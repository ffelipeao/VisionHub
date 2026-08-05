# Lançar uma nova versão no GitHub

Este guia descreve a sequência para versionar o VisionHub, enviar a tag e
publicar uma GitHub Release com os instaladores. Execute os comandos na raiz do
repositório.

O workflow `.github/workflows/build-installers.yml` publica automaticamente:

- `VisionHub-VERSAO-Windows-Setup.exe`;
- `VisionHub-VERSAO-macOS.dmg`.

O pacote Linux ainda não faz parte da release automática. Seu processo local
está descrito em [build-linux.md](build-linux.md).

## 1. Escolher a versão

O projeto usa Versionamento Semântico:

- correção compatível: `1.1.1`;
- nova funcionalidade compatível: `1.2.0`;
- alteração incompatível: `2.0.0`;
- versão beta: `1.2.0-beta.1`, `1.2.0-beta.2` e assim por diante.

Nos exemplos abaixo, substitua a versão conforme necessário:

```bash
NEW_VERSION=1.2.0-beta.1
```

Versões que possuem um sufixo, como `-beta.1`, são publicadas automaticamente
como pré-lançamentos. Versões sem sufixo são publicadas como releases estáveis.

## 2. Preparar a branch

Confirme que está na branch principal e atualize o código:

```bash
git switch main
git pull --ff-only origin main
git status --short
```

Antes de continuar, revise qualquer arquivo exibido por `git status`. Todas as
alterações que farão parte da versão devem estar concluídas e testadas.

## 3. Atualizar os arquivos da versão

Altere `visionhub/version.py`:

```python
__version__ = "1.2.0-beta.1"
```

Mantenha também os valores padrão de `installer/windows/VisionHub.iss`
sincronizados. O workflow os sobrescreve durante a publicação, mas os padrões
são usados quando o Inno Setup é executado diretamente:

```iss
#define MyAppVersion "1.2.0-beta.1"
#define MyOutputBaseFilename "VisionHub-1.2.0-beta.1-Windows-Setup"
```

Em `CHANGELOG.md`:

1. mova as alterações de `Não publicado` para uma seção com a nova versão e a
   data do lançamento;
2. mantenha uma seção `Não publicado` vazia no início;
3. atualize os links de comparação no final do arquivo.

Exemplo:

```markdown
## [Não publicado]

## [1.2.0-beta.1] - 2026-08-05

### Adicionado

- Tela de apresentação durante a abertura do programa.

[Não publicado]: https://github.com/ffelipeao/VisionHub/compare/v1.2.0-beta.1...HEAD
[1.2.0-beta.1]: https://github.com/ffelipeao/VisionHub/compare/v1.1.0-beta.2...v1.2.0-beta.1
```

## 4. Validar antes do lançamento

Leia a versão diretamente do código e confirme que ela corresponde à versão
escolhida:

```bash
VERSION=$(python3 -c 'from visionhub.version import __version__; print(__version__)')
test "$VERSION" = "$NEW_VERSION" && echo "Versão correta: $VERSION"
```

Execute as verificações disponíveis:

```bash
python3 -m compileall -q main.py visionhub
git diff --check
git diff
```

Também é recomendável gerar e testar o instalador no sistema local antes de
publicar. Consulte os guias de [macOS](build-macos.md),
[Linux](build-linux.md) e [Windows](build-windows.md).

## 5. Criar o commit da versão

Inclua somente os arquivos desejados, revise o conteúdo preparado e crie o
commit:

```bash
git add visionhub/version.py installer/windows/VisionHub.iss CHANGELOG.md
git diff --cached
git commit -m "chore(release): prepare a versão $NEW_VERSION"
```

Se houver outras mudanças ainda não commitadas que pertençam à release,
inclua-as explicitamente antes do commit. Não use `git add .` sem revisar o
estado do repositório.

## 6. Criar a tag anotada

A tag deve ser exatamente a versão do código precedida por `v`:

```bash
git tag -a "v$NEW_VERSION" -m "VisionHub $NEW_VERSION"
```

Confirme que a tag aponta para o commit correto:

```bash
git show --stat "v$NEW_VERSION"
```

O workflow interrompe o build se, por exemplo, a tag for `v1.2.0-beta.1` e
`visionhub/version.py` contiver outra versão.

## 7. Enviar o commit e a tag

Envie primeiro a branch e depois a tag:

```bash
git push origin main
git push origin "v$NEW_VERSION"
```

O envio da tag inicia o workflow **Gerar instaladores e release**. Executá-lo
manualmente pela aba Actions gera artefatos, mas não cria uma GitHub Release;
a publicação da release depende de uma tag `v*`.

## 8. Acompanhar e verificar a release

Com a GitHub CLI instalada, acompanhe a execução mais recente:

```bash
gh run list --workflow build-installers.yml --limit 5
RUN_ID=$(gh run list --workflow build-installers.yml --limit 1 \
  --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID"
```

Depois que todos os jobs terminarem, verifique a release e seus arquivos:

```bash
gh release view "v$NEW_VERSION"
```

Na interface do GitHub, confirme:

- jobs de Windows, macOS e publicação concluídos;
- `.exe` e `.dmg` anexados à release;
- título e notas da versão corretos;
- release marcada como pré-lançamento quando a versão possuir sufixo.

## 9. Se o workflow falhar

Se o código e a tag estiverem corretos, corrija a configuração necessária e
execute novamente os jobs com falha pela interface do GitHub. O workflow pode
atualizar os arquivos de uma release já criada sem duplicá-la.

Não reutilize silenciosamente uma tag pública para outro commit. Se a versão já
tiver sido disponibilizada aos usuários e exigir mudanças no código, crie uma
nova versão, como `1.2.0-beta.2` ou `1.2.1`, e repita o processo.
