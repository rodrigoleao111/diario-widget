# tools/

## mcp-server.js

Servidor MCP do LibreSprite, para o Claude desenhar pixel art no programa. É uma cópia de `data/scripts/mcp-server.js` do LibreSprite `master` (build `1.3-dev (20bd251)`, GPL-2.0, "LibreSprite contributors"), com acréscimos marcados com `[diario]`. A v1.3 estável **não** roda este script: precisa de um build do master (`net.serve`).

Acréscimos em relação ao original:

- `sprite_open` abre um PNG ou `.aseprite` e o torna o documento ativo (a CLI não cria sprite do zero; gerar um PNG transparente do tamanho desejado com Pillow resolve).
- `draw_grid` desenha uma grade de texto (um caractere por pixel) com uma paleta `caractere -> cor`. Valida tudo antes de escrever e cria o cel de um quadro vazio.
- `sprite_info` usa `sprite.totalFrames` (o original contava só quadros com cel, e errava depois de `NewFrame` com `content: "empty"`).

### Subir

```bash
libresprite.exe -b --set port=9411 --script tools/mcp-server.js
```

Escuta em `http://127.0.0.1:9411/mcp`. Sem interface, a permissão `net.serve` é concedida sozinha.

### Limites

- A API de script não alcança **duração de quadro** nem **tags de animação** (`Sprite` só expõe largura, altura, camadas, `totalFrames`, paleta, `save*` e `resize`; `FrameProperties` e `FrameTagProperties` abrem janela). Os tempos e os nomes das animações ficam num JSON ao lado do sprite, escrito por nós.
- Exportar a folha de sprites é pela CLI, depois de `sprite_save_as`:
  `libresprite.exe -b arte.aseprite --sheet arte.png --data arte.json --format json-array --sheet-type horizontal`
- Edições feitas pelo servidor não se desfazem: salvar uma cópia antes de mudanças grandes.
- Só RGB em `draw_grid`.
