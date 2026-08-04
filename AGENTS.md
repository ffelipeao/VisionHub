# Instruções para agentes

## Sugestão de commit

Sempre que fizer qualquer alteração em código, configuração ou documentação,
inclua ao final da resposta uma sugestão de commit no padrão Conventional
Commits. Apenas sugira a mensagem; não crie o commit sem solicitação explícita
do usuário.

Use o formato:

```text
tipo(escopo opcional): descrição curta
```

Tipos permitidos:

- `feat`: nova funcionalidade
- `fix`: correção de comportamento ou erro
- `docs`: alteração exclusivamente em documentação
- `style`: formatação sem mudança de comportamento
- `refactor`: reorganização sem nova funcionalidade ou correção
- `perf`: melhoria de desempenho
- `test`: criação ou alteração de testes
- `build`: dependências ou processo de build
- `ci`: integração e entrega contínuas
- `chore`: manutenção que não se encaixa nos tipos anteriores
- `revert`: reversão de uma alteração anterior

Regras para a descrição:

- Escreva em português.
- Use letras minúsculas e verbo no imperativo.
- Seja objetiva e não termine com ponto.
- Prefira no máximo 72 caracteres na primeira linha.
- Use `!` antes dos dois-pontos e inclua `BREAKING CHANGE:` no corpo quando
  houver uma mudança incompatível.
- Quando houver alterações independentes, sugira commits separados.

Exemplo de apresentação ao usuário:

```text
Sugestão de commit: feat(player): adicione visualização em tela cheia
```
