---
name: criar-tema-widget
description: Continuar um tema do widget do diário de atividades (diario/temas/) em pixel art DEPOIS que o rascunho estático da manhã foi aprovado (a primeira etapa, da ideia ao rascunho, é da skill rascunho-tema-widget): variações de tarde e noite, cenário animado em camadas com parallax, efeitos de clique, registro em TEMAS, README e teste no widget. Use ao alterar um tema existente, ao mexer em diario/temas/*.py ou quando o usuário aprovar o layout do rascunho e pedir para seguir. Traz o padrão de cena em faixas com parallax, a geometria da janela, as armadilhas já pagas e o script que renderiza um tema sem registrá-lo.
---

# Criar um tema do widget

Projeto na raiz deste repositório. Esta skill traz o que o manual não diz; a referência da API (ferramentas de `pixel.py`, atributos, `Estado`, `Quadro`, nomes de região) está em `docs/criar-um-tema.md`, seções 5 e 6: leia só a parte de que precisar. O modelo a copiar é `diario/temas/dino.py` (cena em camadas, janela opaca); `ilha.py` é o modelo de janela de formato livre (transparente) e `retro.py` o do cache por quadro.

## Fluxo combinado com o usuário

1. **Rascunho primeiro, pela skill `rascunho-tema-widget`.** Tema novo nunca vai direto para o app: a ideia vira uma imagem estática da manhã (com as técnicas de `diario/acabamento.py` e a referência de técnicas daquela skill) e o usuário aprova o layout. Só depois entra o que está abaixo: tarde e noite, animação, cliques e registro. Pedido de ajuste depois do rascunho (ex.: "coloque pássaros") entra no rascunho e vale como aprovação para aplicar, se o usuário disse "depois disso, aplique".
2. **Aplicar** só com o ok: registrar, documentar, conferir (ver "Aplicar").
3. **Commit** só quando o usuário pedir. Mensagem em português: título curto e corpo com lista, no estilo do `git log`.

## 1. Ler a referência

Pedir a imagem se não veio. Extrair o que ela tem de verdade, sem chutar cores nem formas:

```python
from PIL import Image
from collections import Counter
im = Image.open(r"<imagem>").convert("RGB")
for c, n in Counter(im.getdata()).most_common(25): print("#%02x%02x%02x" % c, n)   # a paleta
```

- O tamanho do pixel de arte quase nunca é inteiro na imagem (a do dino tinha 1434 px de largura ≈ 239 × 6). Divida por 6 e confira; `gcd` das corridas de cor dá 1 e engana.
- Para copiar a forma de um bicho ou objeto, reduza o recorte com passo 6 e imprima ASCII mapeando cada cor ao caractere mais próximo da paleta. Serve de guia; desenhe o sprite à mão em ASCII (`Tela.spr`) com 1 px de contorno via `contorno()`.
- A imagem é a **manhã** (ou o período dela). Tarde e noite são variações suas na mesma família de cores: tarde quente (roxo, rosa, laranja, verde amarelado), noite azul e roxo escuro com contornos mais escuros e os bichos apagados.
- Decidir o que **muda por período**: céu, astro (sol, sol grande baixo, lua e estrelas piscando), nuvens, montanhas, grama, terra, cactos, cor do papel. O que não muda (contorno, silhueta de pássaro, forma dos sprites) fica fixo.

## 2. Decisões de projeto

| Decisão | Padrão |
|---|---|
| Base | `TemaPixel`: só `paleta()`, `moldura_dialogo()` e `quadro()`; calendário e configurações saem prontos. Herde de `Tema` só se o visual não for pixel art |
| Janela | Opaca: `Quadro(imagem, regioes, entrada, estilo, False, fundo_css)`. Transparente (formato livre) só se a ideia for flutuar na área de trabalho, e aí a cor `(1, 2, 3)` é proibida |
| Largura | `W = 304` pixels de arte (608 na tela, com `Z = 2`), como o Retrô; o Ilha usa 384 |
| Animação | `animacao_ms = 100` com cena que rola; 140 a 220 para movimento calmo. Mais rápido que isso triplica a CPU |
| Layout | Barra superior de 13 px (título + botões) sobre o cenário, cenário, depois cartão da lista, campo de lançamento e status |
| `cores_balao` | É fixo por tema (não varia com o período): use as cores da manhã |

Geometria vertical do layout padrão (pixels de arte; o widget limita a 14 tópicos e os temas reservam no mínimo 3 linhas, para a janela não pular):

```
n = max(len(topicos) + (1 if extra else 0), 3)
cy = CENA_H + 2 ; ch = 11*n + 8            # cartão; linha i em y = cy + 6 + 11*i
ey = cy + ch + 4                           # barra do campo (16 px de altura)
campo = (22, ey + 3, W - 10, ey + 13)      # onde o Entry do Tk fica: 10 px de arte de altura para Consolas 10
sty = ey + 16 + 4 ; H = sty + 7 + 7        # linha de status
```

Botões: `BOTOES` da direita para a esquerda, 8 px cada, região com o nome do botão e `DICAS[nome]`; região `arrastar` cobrindo o título; `hoje` só quando `not e.eh_hoje`; `linha:N` por tópico (dica = texto inteiro quando foi cortado com `cortar`). Nome errado de região = botão morto.

## 3. Padrão de cena animada: faixas com parallax

Não use o cache por `(período, t % N)` do Retrô/Ilha quando as camadas têm velocidades diferentes: o ciclo global exigiria que todas emendassem em N quadros. O padrão do Dino:

- Cada camada que rola é uma **faixa larga** (`L` ≥ `W`, de 300 a 650 px) desenhada **uma vez por período** e guardada em `self._faixas[(per, nome)]` (cache por instância, nunca global de módulo: `Tema.miniatura` e o widget criam instâncias). A cada quadro só se **recorta** `W` px a partir de `int(vel * t) % L`, com a volta emendada (`recorte()`). Assim `t` cresce sem limite e cada camada tem a sua velocidade (nuvens 0,25, montanhas 0,6, colinas 1,5, chão e cactos 3 px por quadro).
- Faixa que dá a volta precisa **emendar**: curvas com `sin(2π·k·x/L)` com `k` inteiro; círculos de nuvem testados com `dx = (x - cx + L//2) % L - L//2`. Dê um valor padrão para a coluna sem círculo, senão aparece uma fenda de 1 px.
- O que depende do tempo e é pequeno (astros que pulsam, estrelas que piscam, pássaros, poeira, o personagem) **não vai para faixa**: desenhe por quadro numa `Tela(W, CENA_H)` e componha. Custa menos de 1 ms.
- Ordem de composição: céu → astros → nuvens → pássaros → montanhas → colinas → chão → cactos → personagem. Sprites com `contorno()` ficam 2 px maiores: o contorno de baixo deve cair na linha do chão (`y = GY - sprite.height`).
- Uma curva de relevo vira silhueta com `[y(x) for x]`; o contorno de 1 px acompanha com `_topo()` (preenche o degrau entre colunas vizinhas, senão fica com buracos). Duas curvas (`y1` e `y1 + 9 + ...`) dão o sombreado claro/escuro sem desenhar textura.
- Transição de faixas de céu "em degraus": 10 linhas alternando as duas cores (`"AABAABABBB"`), como em pixel art de verdade, em vez de degradê.
- UI (barra, cartão, texto) em cache pela chave do estado `(dia, tuple(topicos), extra, status, status_tipo, hover, periodo, eh_hoje)`; só redesenha quando muda.
- Orçamento: o quadro completo (compor 8 camadas, ampliar 2×) deve ficar em 1 a 3 ms; o primeiro quadro de cada período (desenha as faixas) em ~15 ms.

### Personagem que reage ao cenário (pulo do dino)

Calcule tudo em função de `t`, sem estado: o personagem fica parado em x e o mundo anda. Para cada obstáculo, `delta = (cx - vel*t - x_personagem + L//2) % L - L//2`; está no ar quando `|delta| <= vel*Q/2` (Q = quadros no ar), com `u = (meia - delta) / (2*meia)` e altura `4*H*u*(1-u)`. Valide no pior caso **antes** de renderizar: quando `|delta|` for a soma das meias-larguras (obstáculo + personagem), a altura precisa passar do obstáculo mais alto, e a distância entre obstáculos precisa ser maior que `vel*Q` mais folga. Pela conta, o primeiro desenho do pulo (16 quadros, 32 px de altura) não passava do cacto de 27 px com contorno no ponto de maior sobreposição; ficou 20 quadros, 38 px e cactos de 22 px, e o rascunho já saiu certo.

## 4. Pacote de rascunho completo (depois do layout aprovado)

A primeira imagem, estática e só da manhã, é da skill `rascunho-tema-widget`. Quando o usuário aprova o layout, complete o tema (tarde, noite, animação, cliques) em `diario/temas/<id>.py`, ainda **sem registrar em `TEMAS`** (nada de script descartável que depois vira o tema: foi retrabalho), e renderize o pacote com o script desta skill, que carrega a classe por nome. Tarde e noite seguem as mesmas rampas da manhã (sombra fria, luz quente, contorno por selout, `diario/acabamento.py`); à noite, base fria e fontes quentes pontuais (janela, tocha):

```powershell
python -X utf8 .claude\skills\criar-tema-widget\scripts\rascunho.py <modulo>:<Classe> <pasta> --t manha=157,tarde=28,noite=77 --gif
```

Grava `periodos.png` (janela inteira nos três períodos, no quadro escolhido por `--t`), `calendario.png`, `config.png`, os GIFs (`--gif`) e imprime o tempo por quadro. Se a classe tiver `camadas(periodo, t) -> [(nome, descrição, imagem RGBA)]`, grava também `camadas.png` (um painel por camada, em xadrez): vale expor esse método quando o usuário pediu "em camadas", porque é o que ele quer ver. Escolha `--t` de modo que ao menos um período mostre o personagem no ponto interessante (pulando).

- **Olhe as imagens você mesmo** (Read no PNG) antes de mostrar: já pegou nuvem com fenda, pulo atravessando cacto, colinas invisíveis, texto sem contraste.
- No Git Bash, Python do Windows não lê `/c/...`: caminho relativo ou `$(cygpath -w ...)`. Saída em pasta do repo só se for ficar; senão, scratchpad.
- Mostre com `SendUserFile` (render): `periodos.png`, `camadas.png` e um GIF; os outros GIFs ficam na pasta. Descreva em poucas linhas as camadas, o que muda por período, o layout e **o que mudou em relação à referência** (tamanhos, tempos). Uma pergunta só: aprova?
- Guarde a imagem de referência em `arte/referencias/<tema>/referencia_do_usuario.png`; os PNGs e GIFs do rascunho são descartáveis.

## 5. Aplicar

1. `diario/temas/__init__.py`: importar a classe e pôr a instância em `TEMAS` (a ordem é a da tela de configurações; `PADRAO` não muda sem pedido).
2. `README.md`, seção "Temas do widget": linha na tabela (nome, `id`, como é); a frase do tamanho da janela ("têm 608 px de largura"); a frase "Ilha, Retrô e Dino trocam céu, astros, cores e bichos"; a árvore `temas\` no fim do arquivo. Parágrafos e itens em uma linha só, sem quebra manual.
3. `python -X utf8 tools\previa_temas.py <pasta>`: renderiza todos os temas (o novo agora registrado), `*_passado.png` (botão Hoje), calendário e configurações. Conferir também dia vazio e dia com 14 tópicos.
4. Teste no widget de verdade, sem derrubar o do logon:

```powershell
$env:DIARIO_PREVIEW = "1"; $env:DIARIO_PERIODO = "tarde"
python -X utf8 -c "from diario import preferencias; preferencias.salvar(tema='<id>')"
$p = Start-Process python -ArgumentList "-X","utf8","-m","diario","widget" -PassThru -RedirectStandardError "$env:TEMP\t_err.txt" -WorkingDirectory (Get-Location)
Start-Sleep 8; Stop-Process -Id $p.Id -Force; Get-Content "$env:TEMP\t_err.txt"
```

   stderr vazio e processo vivo depois de 8 s = abriu sem erro. Isso **não** testa cliques: diga ao usuário que botões, calendário, arrastar e digitar no campo ficam para ele conferir. O widget do logon só pega o tema depois de `✕` e de reabrir por `abrir_widget.pyw`. `widget_preview.json` fica com o tema gravado (está no `.gitignore`).
5. Atualizar a memória do projeto (`project_widget_pixel_art.md`) com uma linha sobre o tema e o fluxo.

## Efeitos de clique

Enfeite que reage ao mouse (porta que abre, dragão que cospe fogo): `Tema.efeitos = {nome: duração em quadros}`, região `efeito:<nome>` e `Estado.efeitos[nome]` = quadros desde o clique (manual, passo 9). Modelo: `castelo.py` (`ROTEIRO_PORTA`, `_atores`, `_regioes_efeitos`). Ao mexer num enfeite que já existe, **compare o quadro parado antes e depois pixel a pixel** (`ImageChops.difference`): o efeito não pode alterar o desenho em repouso. Teste o clique de verdade criando o `Widget` com `DIARIO_PREVIEW=1` e `event_generate("<ButtonPress-1>")` no centro da região.

## Armadilhas (já custaram tempo)

- Os diálogos do `TemaPixel` saem com `transparente=True`: o `T.cantos(...)` da moldura vira o canto pixelado de verdade (buraco na janela), então chame-o e não pinte o canto com a cor de fundo.
- A miniatura da tela de configurações chama `quadro(estado_exemplo(periodo), 3)` sem banco e sem widget: nada de ler disco, e o primeiro quadro precisa ficar bonito com `t = 3`.
- Fonte pixel sem `ü ñ € emoji`: viram `?`. Acentos do português funcionam.
- Contraste por período, não só na manhã: texto de tinta sobre papel, texto do status sobre a terra, ícones da barra. Olhe a noite.
- Pássaro, sombra e silhueta "pretos" ficam quase invisíveis no céu escuro da noite: confirme na imagem se o usuário pediu preto em todos os períodos.
- Frame de pose que muda de largura (pernas) precisa de `ljust` nas linhas do ASCII para o sprite não desalinhar; conte as colunas com o render ampliado (12×) à vista, não de cabeça.
- Quadro com `t` grande: use `%` só dentro de ciclos curtos (asa, pisca); posição de faixa é `int(vel * t) % L`.
- `id` repetido sobrescreve outro tema em silêncio. `quadro()` lenta trava o mouse: meça com o script antes de dar por pronto.
- Referência que é uma pintura detalhada (estátuas, penhascos) não se redesenha à mão: o primeiro rascunho do Argonath, feito com polígonos, foi recusado. Reduza à grade original (a do Argonath era 160×160, blocos de 4 px), quantize, apague o céu por preenchimento a partir do topo, grave o resultado em `diario/recursos/` e recorte e estique faixas dele no tema; o desenho do que muda por período (céu, nuvens, água) continua em código. Modelo: `argonath.py` e `arte/referencias/argonath/preparar_paredes.py`. Guarde a imagem em `arte/referencias/<tema>/`.
- Nuvem de elipses centradas na linha da base, não em retângulos cortados: base reta e pontas arredondadas (a primeira versão cortava o lado direito). Toda forma desenhada precisa caber na própria tela.
- Janela transparente: alfa < 128 vira buraco, então nada de halo semitransparente (use pontilhado) e nada de sombra. Para ficar "solto", a rocha precisa de contorno escuro e de base afunilada; o usuário testou essa versão (e uma em moldura dourada) e preferiu a retangular, com céu.
- Efeito que mexe numa parte da arte da referência (o rosto de uma estátua): recorte a caixa, desloque e repita a borda para tapar a fresta, em vez de redesenhar. Efeito "segredo" (easter egg): `Regiao("efeito:x", caixa, "", "")`, sem dica e sem cursor de mão. Para testar os cliques de verdade, crie o `Widget` com `DIARIO_PREVIEW=1`, escolha um ponto em que `sup.regiao_em` devolve a região (o centro de uma caixa pode cair em outra), use `event_generate` e avance `w.t` até o efeito sair de `_efeitos_ativos()`.
- Editar README e docs por Python no Windows: `open(caminho, "w")` troca LF por CRLF e o `git diff` mostra o arquivo todo. Use `newline=""` (ou binário) e confira com `git diff --stat` e `git ls-files --eol`.
