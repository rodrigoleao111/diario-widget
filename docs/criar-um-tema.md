# Como criar um tema para o widget

Este manual leva você, passo a passo, da página em branco a um tema novo que aparece na tela de configurações do widget (`⚙`). O exemplo é um tema completo e funcional, o **Terminal** (letras luminosas sobre fundo escuro, com cursor piscando e cores que mudam de manhã, tarde e noite). Ele está inteiro na [seção 4](#4-código-completo-do-tema-terminal) e foi testado: renderiza os três períodos, o calendário e as configurações, e abre no widget de verdade.

O manual não registra o Terminal no projeto. Para ficar com ele, é só seguir os passos; para criar o seu, troque o desenho e mantenha a estrutura.

## Sumário

1. [Como o widget usa um tema](#1-como-o-widget-usa-um-tema)
2. [Escolha a base: `Tema` ou `TemaPixel`](#2-escolha-a-base-tema-ou-temapixel)
3. [Passo a passo](#3-passo-a-passo)
4. [Código completo do tema Terminal](#4-código-completo-do-tema-terminal)
5. [Referência](#5-referência)
6. [Armadilhas](#6-armadilhas)
7. [Checklist antes de dar o tema por pronto](#7-checklist-antes-de-dar-o-tema-por-pronto)

## 1. Como o widget usa um tema

O widget (`diario\widget.py`) **não desenha nada**. Ele só sabe o que existe no dia e quer saber como mostrar. Quem desenha é o tema:

```
banco de dados ──► Widget ──► Estado ──► Tema.quadro(estado, t) ──► Quadro ──► tela
                     ▲                                                │
                     └──── clique na região "fechar", "linha:2"... ◄──┘
```

- **`Estado`** é o que o widget sabe agora: o dia, os tópicos, a mensagem de status, qual região está sob o mouse e o período (manhã, tarde ou noite).
- **`Quadro`** é a resposta do tema: uma imagem RGBA da janela **inteira**, a lista de **regiões** clicáveis e o lugar do campo de texto.
- O widget mostra a imagem num `Canvas`, descobre em qual região o mouse está e executa a ação que o **nome** da região indica (`fechar`, `atualizar`, `dia:2026-10-26`...). Ele nunca pergunta ao tema "onde está o botão X": a caixa de cada região é o contrato.

O tema é chamado de novo **a cada** vez que algo muda: o mouse entra ou sai de uma região, o widget recarrega o banco (a cada 60 s ou ao clicar em `↻`), chega uma mensagem de status e, se o tema anima, a cada `animacao_ms` milissegundos. Por isso `quadro()` precisa ser **rápida** (os temas atuais levam de 2 a 13 ms) e **não pode ler o banco, o disco nem a rede**: só recebe o `Estado`.

Além da janela principal, o tema desenha duas telas pequenas, que o widget abre como diálogos: o **calendário** (`calendario(estado)`) e as **configurações** (`configuracoes(estado, miniaturas)`). No `TemaPixel` elas vêm prontas, a partir de duas coisas que o tema informa: a paleta e a moldura.

## 2. Escolha a base: `Tema` ou `TemaPixel`

| | `TemaPixel` (`diario\temas\pixeltema.py`) | `Tema` (`diario\temas\base.py`) |
|---|---|---|
| Desenho | Numa grade pequena ("pixels de arte"), ampliada `Z` vezes (2) sem borrar | Livre: PIL com fontes do Windows, imagens, o que quiser |
| Calendário e configurações | **Prontos**: você só dá `paleta()` e `moldura_dialogo()` | Você implementa `calendario()` e `configuracoes()` |
| Fonte | Pixel 5×7 embutida (`diario\pixel.py`), com acentos | A que você carregar (`ImageFont`) |
| Exemplos | `ilha.py`, `retro.py` | `classico.py` |
| Use quando | Quer pixel art, com o mínimo de código | Quer outro tipo de visual (vetorial, fotos, fontes de verdade) |

Este manual usa `TemaPixel`. Se for herdar de `Tema`, os mesmos passos valem; a diferença está em implementar o calendário e as configurações (veja `classico.py` e a [seção 5.6](#56-regiões-dos-diálogos)).

## 3. Passo a passo

### Passo 1. Crie o arquivo e a classe

Crie `diario\temas\terminal.py` (o nome do arquivo é livre) com o cabeçalho e a classe vazia:

```python
from ..pixel import Tela, cortar, hx, icone, mix
from .base import BOTOES, DIAS_SEMANA, DICAS, Estado, Quadro, Regiao
from .pixeltema import TemaPixel


class Terminal(TemaPixel):
    id = "terminal"
    nome = "Terminal"
    descricao = "Letras luminosas sobre fundo escuro, com cursor piscando."
```

- **`id`**: identificador curto, sem espaços e **único**. É o que fica salvo em `widget.json` (campo `tema`). Dois temas com o mesmo `id` não dão erro: o último a ser registrado vence, em silêncio.
- **`nome`** e **`descricao`**: aparecem na tela de configurações. A descrição é quebrada em até 3 linhas e cortada com reticências, então fique em uma frase curta.

### Passo 2. Defina as cores por período

O widget passa o período em `estado.periodo`: `"manha"` (6h às 12h), `"tarde"` (12h às 18h) ou `"noite"` (o resto). Um tema que quer mudar com a hora guarda uma paleta por período:

```python
COR = {  # uma paleta por período
    "manha": dict(fundo=hx("#06140a"), texto=hx("#7dff9a"), dim=hx("#3f9a58"), alerta=hx("#ffd84a")),
    "tarde": dict(fundo=hx("#140e04"), texto=hx("#ffb454"), dim=hx("#9a6a2a"), alerta=hx("#ffe58a")),
    "noite": dict(fundo=hx("#04080f"), texto=hx("#7fb8ff"), dim=hx("#3f6a9a"), alerta=hx("#ffd84a")),
}
```

`hx("#rrggbb")` devolve a cor no formato que as ferramentas de desenho esperam, `(r, g, b, 255)`. Um tema que **não** muda com a hora usa uma paleta só e ignora `estado.periodo`. Os nomes das chaves (`fundo`, `texto`...) são seus; só a paleta dos diálogos (passo 3) tem nomes fixos.

### Passo 3. Dê a paleta e a moldura dos diálogos

Estes dois métodos são o que o `TemaPixel` usa para desenhar o calendário e as configurações no seu estilo.

**`paleta(per)`** devolve um dicionário com **exatamente** estas chaves:

| Chave | Para quê |
|---|---|
| `texto` | Texto normal |
| `dim` | Texto secundário (dias futuros, descrições, setas) |
| `ok` | Verde de "tem registro" e do tema em uso |
| `acc` | Títulos de seção ("Tema") |
| `sel_fundo`, `sel_texto` | Fundo e texto do dia escolhido no calendário |
| `linha` | Separadores e fundo de item sob o mouse |
| `hover` | Cor dos botões sob o mouse |

```python
    def paleta(self, per):
        c = COR[per]
        return dict(texto=c["texto"], dim=c["dim"], ok=c["texto"], acc=c["alerta"], sel_fundo=c["dim"],
                    sel_texto=c["fundo"], linha=mix(c["fundo"], c["dim"], .35), hover=c["alerta"])
```

`mix(a, b, t)` mistura duas cores (`t` de 0 a 1), útil para derivar tons sem escolher cada um.

**`moldura_dialogo(T, w, h, titulo, per, hover_fechar)`** desenha, na tela `T` de `w × h` pixels de arte, a borda, o fundo e a barra de título do diálogo, e **devolve a caixa do botão de fechar** `(x0, y0, x1, y1)`. O `TemaPixel` desenha o conteúdo (dias, temas, miniaturas) por cima do que a moldura deixou. A barra de título tem `self.TITULO_H` pixels (15) de altura; o conteúdo começa abaixo dela.

```python
    def moldura_dialogo(self, T, w, h, titulo, per, hover_fechar):
        c = COR[per]
        T.rect(0, 0, w, h, c["dim"])
        T.rect(1, 1, w - 2, h - 2, c["fundo"])
        T.cantos(0, 0, w, h)
        T.texto(6, 5, titulo, c["texto"])
        T.put(icone("fechar", c["alerta"] if hover_fechar else c["texto"]), w - 11, 5)
        T.rect(1, self.TITULO_H - 1, w - 2, 1, c["dim"])
        return (w - 16, 1, w - 2, self.TITULO_H)  # caixa do botão de fechar
```

`T.cantos(...)` "come" os quatro cantos do retângulo, o contorno pixelado clássico. Num tema transparente (o `TemaPixel` é) os cantos viram buraco na janela; num tema opaco eles ficam na cor de fundo.

### Passo 4. Desenhe a janela principal em `quadro()`

Este é o coração do tema. A assinatura é sempre `quadro(self, e: Estado, t: int) -> Quadro`, onde `e` é o `Estado` e `t` é o número do quadro de animação (começa em 0 e cresce; um tema sem animação o ignora).

**4.1. Calcule a geometria.** A altura da janela depende de quantos tópicos há. Os outros temas reservam no mínimo 3 linhas, para a janela não pular de tamanho quando o dia está vazio. Todas as medidas são em **pixels de arte** (cada um vira 2×2 pixels na tela):

```python
    def quadro(self, e: Estado, t: int) -> Quadro:
        c = COR[e.periodo]
        linhas = list(e.topicos) or [("Nada registrado neste dia.", "aviso")]
        n = max(len(linhas) + (1 if e.extra else 0), 3)
        ey = 20 + 11 * n + 4  # topo do campo de lançamento
        sy = ey + 18  # linha de status
        H = sy + 13
        T = Tela(W, H)
```

- `e.topicos` é uma lista de `(texto, tipo)`, com `tipo` igual a `""` (tópico do resumo), `"manual"` (lançamento manual, mostre em destaque) `"aviso"` (mensagem do sistema, mostre apagada) ou `"resumir"` (o aviso "Resumo do dia ainda não escrito": mostre apagado, como o `"aviso"`, e desenhe o botão `[resumir]` ao lado, com a região `"resumir"` registrada **antes** da região da linha; `e.resumindo` troca o rótulo para `[resumindo…]` e tira a região, e `e.refazer` troca para `[atualizar]` (resumo já escrito, mas velho; a dica passa a ser `DICAS["refazer"]`); nos temas em pixel art, `botao_resumir` de `pixeltema.py` faz isso). O widget entrega no máximo 14 e põe em `e.extra` quantos não couberam.
- `Tela(W, H)` cria uma camada RGBA **transparente** onde você desenha. `W` é uma constante do módulo (`W = 240`).
- Cada linha tem 11 pixels de altura: 7 da fonte, mais respiro.

**4.2. Desenhe o fundo.**

```python
        T.rect(0, 0, W, H, c["dim"])
        T.rect(1, 1, W - 2, H - 2, c["fundo"])
        T.cantos(0, 0, W, H)
        regs = []
```

`regs` vai juntar as regiões clicáveis (passos seguintes).

**4.3. Título e botões.** O título mostra o dia; `DIAS_SEMANA` vem de `base.py`. O `T.texto(...)` devolve o `x` onde o texto terminou, o que permite pendurar o cursor piscando logo depois:

```python
        fim = T.texto(6, 5, f"> diario {DIAS_SEMANA[e.dia.weekday()]} {e.dia:%d/%m}", c["texto"])
        if t % 2 == 0:
            T.rect(fim + 2, 11, 5, 2, c["alerta"])
```

Os botões vêm de `BOTOES` (`anterior`, `calendario`, `proximo`, `atualizar`, `relatorio`, `config`, `fechar`, nesta ordem, da esquerda para a direita). Desenhe da direita para a esquerda e, para cada um, registre uma `Regiao` com o **nome do botão**, a caixa e a dica do balão (`DICAS[nome]`). O widget troca a cor do botão sob o mouse porque você mesmo olha `e.hover`:

```python
        x = W - 4
        for nome in reversed(BOTOES):
            x -= 9
            ic = icone(nome, c["alerta"] if e.hover == nome else c["texto"])
            T.put(ic, x + (9 - ic.width) // 2, 8 - ic.height // 2)
            regs.append(Regiao(nome, (x, 1, x + 9, 15), DICAS[nome]))
```

O botão `Hoje` só existe quando `e.eh_hoje` é falso (o usuário está olhando outro dia) e fica logo depois do título com a data, na mesma linha (posição pela largura do título, `largura(titulo)`). A região se chama `"hoje"`. E a **região `"arrastar"`** é a faixa que o usuário puxa para mover a janela; ela perde para qualquer outra região no mesmo ponto, então pode cobrir o título inteiro:

```python
        if not e.eh_hoje:
            T.texto(x - 28, 5, "hoje", c["alerta"] if e.hover == "hoje" else c["texto"])
            regs.append(Regiao("hoje", (x - 30, 1, x - 2, 15), DICAS["hoje"]))
        regs.append(Regiao("arrastar", (0, 0, W, 15), "", ""))
```

Os ícones são de `pixel.py` (5×5, e 7×7 o da engrenagem). O quarto argumento de `Regiao` (`""`) é o cursor: `"hand2"` é o padrão (mãozinha); vazio deixa o cursor normal, o que convém à região de arrastar.

**4.4. A lista de tópicos.** Uma região `linha:N` por tópico, com `N` começando em 0. Se o texto não cabe, ele é cortado com `cortar(texto, largura_em_pixels_de_arte)` e a região leva o texto inteiro como `dica`, que o widget mostra num balão:

```python
        for i, (txt, tipo) in enumerate(linhas):
            y = 20 + i * 11
            cor = {"manual": c["alerta"], "aviso": c["dim"]}.get(tipo, c["texto"])
            if e.hover == f"linha:{i}":
                T.rect(3, y - 2, W - 6, 11, mix(c["fundo"], c["dim"], .35))
            curto = cortar(txt, W - 26)
            T.texto(8, y, "-", cor)
            T.texto(16, y, curto, cor)
            regs.append(Regiao(f"linha:{i}", (1, y - 2, W - 1, y + 9), txt if curto != txt else ""))
        if e.extra:
            T.texto(16, 20 + len(linhas) * 11, f"… e mais {e.extra}", c["dim"])
```

Se preferir que o texto inteiro apareça na linha de status em vez de num balão, ponha `hover_no_status = True` na classe e use `e.status`, que o widget já troca pelo tópico sob o mouse (é o que o tema Clássico faz).

**4.5. O campo de lançamento.** O campo onde o usuário digita **não é desenhado**: é um `Entry` de verdade do Tk, que o widget põe por cima da caixa que você indicar. Você desenha só a moldura em volta e devolve a caixa interna em `campo`:

```python
        T.rect(4, ey, W - 8, 14, c["dim"])
        T.rect(5, ey + 1, W - 10, 12, c["fundo"])
        T.texto(8, ey + 4, ">", c["texto"])
        campo = (18, ey + 2, W - 6, ey + 12)
```

**4.6. A linha de status.** Quando o status é `"dica"` (nada a dizer), mostre a dica de uso. Nos demais (`ok`, `info`, `erro`), mostre a mensagem na cor correspondente:

```python
        msg = e.status if e.status and e.status_tipo != "dica" else DICA
        cor = {"ok": c["texto"], "info": c["alerta"], "erro": hx("#ff6060")}.get(e.status_tipo, c["dim"])
        T.texto(6, sy, cortar(msg, W - 12), cor)
```

**4.7. Entregue o quadro.** O `TemaPixel._finaliza` amplia a camada `Z` vezes, converte as caixas de todas as regiões e do campo para pixels da tela e monta o `Quadro`. O dicionário de estilo do `Entry` **precisa** das quatro chaves: `bg`, `fg`, `cursor` e `fonte`:

```python
        estilo = dict(bg=css(c["fundo"]), fg=css(c["texto"]), cursor=css(c["alerta"]), fonte=("Consolas", 10))
        return self._finaliza(T, regs, campo, estilo)
```

`css(cor)` é uma função pequena do módulo que converte a cor em `"#rrggbb"`, formato que o Tk entende:

```python
def css(cor):
    return "#%02x%02x%02x" % cor[:3]
```

### Passo 5. Registre o tema

Em `diario\temas\__init__.py`, importe a classe e acrescente uma instância ao dicionário `TEMAS`:

```python
from .classico import Classico
from .ilha import Ilha
from .retro import Retro
from .terminal import Terminal

TEMAS = {t.id: t for t in (Ilha(), Retro(), Classico(), Terminal())}
PADRAO = "ilha"
```

- A **ordem** da tupla é a ordem dos temas na tela de configurações.
- `PADRAO` é o tema de quem ainda não escolheu nenhum (e o de reserva se o `id` salvo em `widget.json` não existir mais). Só troque se a ideia for mudar o tema padrão do app.
- Não é preciso mexer em `widget.py`: o tema aparece sozinho na tela de configurações, com uma miniatura gerada por ele mesmo (`Tema.miniatura`, que chama o seu `quadro()` com dados de exemplo).

### Passo 6. Confira sem abrir janela

```powershell
python -X utf8 tools\previa_temas.py C:\temp\previa
```

O script renderiza **todos** os temas registrados, em manhã, tarde e noite, mais o calendário, as configurações e um dia passado, e grava PNGs (`terminal_manha.png`, `terminal_calendario.png`, `terminal_config.png`...). Ele também imprime quanto tempo cada quadro levou. Abra os PNGs e confira:

- o texto está legível nos três períodos?
- nada sobrepõe o campo de lançamento ou a linha de status?
- o tema aparece na tela de configurações, com a miniatura e o "em uso" quando selecionado?
- o tempo por quadro está na casa de 2 a 15 ms? Bem acima disso, veja o [passo 8](#passo-8-se-animar-guarde-quadros-em-cache).

### Passo 7. Confira na janela de verdade

Use a **instância de teste**: ela não derruba o widget que abre no logon (sem a trava de instância única, sem o ícone da bandeja) e guarda posição e tema em `widget_preview.json`, sem tocar em `widget.json`.

```powershell
$env:DIARIO_PREVIEW = "1"
python -X utf8 -m diario widget
```

Clique em `⚙` e escolha o Terminal. Confira, com o mouse:

- passar o mouse nos botões muda a cor e, depois de meio segundo, mostra o balão;
- clicar em cada botão faz o que deve (dia anterior/seguinte, calendário, `↻`, `▤`, `⚙`, `✕`);
- clicar num dia do calendário muda o dia; ao ir para um dia passado, o `Hoje` aparece e funciona;
- o campo de lançamento recebe o foco e aceita digitação, com as cores do seu tema (a instância de teste grava no mesmo `diario.db`, então só tecle Enter se quiser mesmo lançar a atividade);
- arrastar pelo título move a janela e a posição fica salva;
- um dia com muitos tópicos (volte em `◀` até um dia cheio) corta o texto e mostra "… e mais N".

Para ver os outros períodos sem esperar a hora passar, force um:

```powershell
$env:DIARIO_PERIODO = "noite"   # manha, tarde ou noite
```

Para abrir já com o seu tema, sem passar pela tela de configurações: `python -X utf8 -c "from diario import preferencias; preferencias.salvar(tema='terminal')"` com `DIARIO_PREVIEW=1` definido na mesma sessão.

**O widget do logon não pega o tema novo sozinho**: ele carrega o código ao abrir. Para vê-lo, feche o widget (`✕`) e abra de novo por `abrir_widget.pyw`.

### Passo 8. Se animar, guarde quadros em cache

Para animar, defina `animacao_ms` (intervalo entre quadros) na classe. O Terminal usa `500`, o suficiente para o cursor piscar; as animações do Ilha e do Retrô usam 220 e 140.

```python
    animacao_ms = 500  # um quadro a cada meio segundo: é o que pisca o cursor
```

O widget incrementa `t` a cada intervalo e chama `quadro(estado, t)`. Cuidados:

- **`t` cresce sem parar.** Use o resto da divisão (`t % N`) para ciclos. O Terminal só olha `t % 2`.
- **Faça o ciclo emendar.** Se a animação tem `N` quadros, o quadro `N` precisa ser igual ao quadro 0, ou haverá um pulo a cada volta. No Retrô, o chão rola 4 px por quadro e se repete a cada 128 px; por isso são 32 quadros.
- **Guarde em cache o que é caro.** O Ilha e o Retrô desenham o cenário uma vez por `(período, quadro)` e guardam num dicionário; só a parte do texto e dos botões, que muda com o mouse, é refeita. O Terminal é tão leve (1,6 ms) que dispensa cache. Se a sua cena demora, siga o padrão de `ilha.py` (`_camada`, `_interface`): o que depende do **tempo** num cache por quadro, o que depende do **estado** num cache pela chave do estado.
- **Não anime demais.** Cada quadro redesenha a janela inteira e recria a imagem no Tk. Os temas atuais usam de 2% a 4% de um núcleo; um intervalo de 50 ms triplicaria isso.

Sem `animacao_ms` (o padrão é `None`), o tema só é redesenhado quando o estado muda.

**Animação barata (opcional, para temas grandes).** Um tema que ocupa a tela toda (o Argonath de papel de parede) não pode refazer e repintar 6 MB a cada quadro. Dois ganchos permitem isso. `animacao_ociosa_ms` faz o tema andar em tempo real: `t` passa a contar quadros de `animacao_ms` pelo relógio, e o widget só o chama a cada `animacao_ociosa_ms` enquanto nenhum efeito de clique roda (com um efeito, volta a `animacao_ms`). `partes(e, t)` devolve `[(imagem RGB, x, y)]` com só os pedaços da última imagem que mudaram, ou `None` para pedir um `quadro()` inteiro; o tema guarda o que o último quadro mostrou e responde `None` quando o estado do diário mudou ou há efeito de clique. O widget cola os pedaços no Tk (`Superficie.cola`), que repinta só essas áreas. Confira sempre que os pedaços colados sobre o quadro anterior dão exatamente, pixel a pixel, o `quadro()` inteiro do mesmo `t`, em todos os períodos. Cada remendo, por menor que seja, custa ~1 ms de colagem: junte o que puder.

### Passo 9. Se quiser, faça os enfeites reagirem ao clique

Um tema animado pode deixar elementos do cenário reagirem ao mouse (a porta do Castelo abre, o dragão cospe fogo). O widget só guarda **quando** o clique aconteceu; o desenho é todo do tema:

1. Declare os efeitos na classe, com a duração em quadros: `efeitos = {"porta": 16, "dragao": 12}`.
2. Em `quadro()`, devolva uma `Regiao` chamada `efeito:<nome>` sobre o enfeite (`Regiao("efeito:porta", caixa, "Bater na porta")`). Ela **não** deve entrar no cache da interface se a caixa se mexe com `t`, como a do dragão.
3. Quando o clique cai nela, o widget grava o quadro atual e passa a entregar `e.efeitos = {"porta": f}`, onde `f` é 0 no quadro do clique, 1 no seguinte, e assim até `duração - 1`. Depois some. Desenhe a reação em função de `f` (`ROTEIRO_PORTA[f]`, `LANCA_SOBE[f]`...); sem `f` no dicionário, desenhe o enfeite parado, **idêntico** ao de antes.
4. Clicar de novo no meio do efeito não o reinicia, e trocar de tema cancela os que estavam rodando.

Cuidados: a primeira região que casa com o mouse vence, então o que está na frente do cenário (o dragão sobre o sol) deve vir antes na lista; regiões de botões e de linhas da lista, que o tema põe antes, continuam ganhando de qualquer efeito. O que reage ao clique precisa sair do cache por `t % N` (ou ter um cache por `f`), senão o efeito não aparece. O `castelo.py` é o exemplo completo: porta (cache por quadro do efeito), tochas e cavaleiro (por quadro, em `_atores`), dragão (`labareda`) e astros (`rosto_sol`, `cintila`).

### Passo 9. Documente

Acrescente o tema na tabela "Temas incluídos" do `README.md` (seção "Temas do widget") com o `id` e uma frase sobre como ele é. Se ele tem alguma particularidade (por exemplo, não muda com a hora), diga ali.

## 4. Código completo do tema Terminal

Todo o `diario\temas\terminal.py`, reunindo os passos 1 a 8:

```python
"""Tema Terminal: letras luminosas sobre fundo escuro, com cursor piscando. A cor muda de manhã, tarde e noite."""
from ..pixel import Tela, cortar, hx, icone, mix
from .base import BOTOES, DIAS_SEMANA, DICAS, Estado, Quadro, Regiao
from .pixeltema import TemaPixel

W = 240  # largura em pixels de arte; na tela são W * Z = 480 pixels
DICA = "Enter lança · 1h30 reunião @Projeto"
COR = {  # uma paleta por período
    "manha": dict(fundo=hx("#06140a"), texto=hx("#7dff9a"), dim=hx("#3f9a58"), alerta=hx("#ffd84a")),
    "tarde": dict(fundo=hx("#140e04"), texto=hx("#ffb454"), dim=hx("#9a6a2a"), alerta=hx("#ffe58a")),
    "noite": dict(fundo=hx("#04080f"), texto=hx("#7fb8ff"), dim=hx("#3f6a9a"), alerta=hx("#ffd84a")),
}


def css(cor):
    return "#%02x%02x%02x" % cor[:3]


class Terminal(TemaPixel):
    id = "terminal"
    nome = "Terminal"
    descricao = "Letras luminosas sobre fundo escuro, com cursor piscando."
    cores_balao = ("#06140a", "#7dff9a", "#3f9a58")  # fundo, texto e borda dos balões de ajuda
    animacao_ms = 500  # um quadro a cada meio segundo: é o que pisca o cursor

    def paleta(self, per):
        c = COR[per]
        return dict(texto=c["texto"], dim=c["dim"], ok=c["texto"], acc=c["alerta"], sel_fundo=c["dim"],
                    sel_texto=c["fundo"], linha=mix(c["fundo"], c["dim"], .35), hover=c["alerta"])

    def moldura_dialogo(self, T, w, h, titulo, per, hover_fechar):
        c = COR[per]
        T.rect(0, 0, w, h, c["dim"])
        T.rect(1, 1, w - 2, h - 2, c["fundo"])
        T.cantos(0, 0, w, h)
        T.texto(6, 5, titulo, c["texto"])
        T.put(icone("fechar", c["alerta"] if hover_fechar else c["texto"]), w - 11, 5)
        T.rect(1, self.TITULO_H - 1, w - 2, 1, c["dim"])
        return (w - 16, 1, w - 2, self.TITULO_H)  # caixa do botão de fechar

    def quadro(self, e: Estado, t: int) -> Quadro:
        c = COR[e.periodo]
        linhas = list(e.topicos) or [("Nada registrado neste dia.", "aviso")]
        n = max(len(linhas) + (1 if e.extra else 0), 3)
        ey = 20 + 11 * n + 4  # topo do campo de lançamento
        sy = ey + 18  # linha de status
        H = sy + 13
        T = Tela(W, H)
        T.rect(0, 0, W, H, c["dim"])
        T.rect(1, 1, W - 2, H - 2, c["fundo"])
        T.cantos(0, 0, W, H)
        regs = []

        # título com cursor piscando e botões da direita para a esquerda
        fim = T.texto(6, 5, f"> diario {DIAS_SEMANA[e.dia.weekday()]} {e.dia:%d/%m}", c["texto"])
        if t % 2 == 0:
            T.rect(fim + 2, 11, 5, 2, c["alerta"])
        x = W - 4
        for nome in reversed(BOTOES):
            x -= 9
            ic = icone(nome, c["alerta"] if e.hover == nome else c["texto"])
            T.put(ic, x + (9 - ic.width) // 2, 8 - ic.height // 2)
            regs.append(Regiao(nome, (x, 1, x + 9, 15), DICAS[nome]))
        if not e.eh_hoje:
            T.texto(x - 28, 5, "hoje", c["alerta"] if e.hover == "hoje" else c["texto"])
            regs.append(Regiao("hoje", (x - 30, 1, x - 2, 15), DICAS["hoje"]))
        regs.append(Regiao("arrastar", (0, 0, W, 15), "", ""))

        # lista de tópicos
        for i, (txt, tipo) in enumerate(linhas):
            y = 20 + i * 11
            cor = {"manual": c["alerta"], "aviso": c["dim"]}.get(tipo, c["texto"])
            if e.hover == f"linha:{i}":
                T.rect(3, y - 2, W - 6, 11, mix(c["fundo"], c["dim"], .35))
            curto = cortar(txt, W - 26)
            T.texto(8, y, "-", cor)
            T.texto(16, y, curto, cor)
            regs.append(Regiao(f"linha:{i}", (1, y - 2, W - 1, y + 9), txt if curto != txt else ""))
        if e.extra:
            T.texto(16, 20 + len(linhas) * 11, f"… e mais {e.extra}", c["dim"])

        # campo de lançamento: o Entry do Tk fica por cima da caixa "campo"
        T.rect(4, ey, W - 8, 14, c["dim"])
        T.rect(5, ey + 1, W - 10, 12, c["fundo"])
        T.texto(8, ey + 4, ">", c["texto"])
        campo = (18, ey + 2, W - 6, ey + 12)

        # linha de status
        msg = e.status if e.status and e.status_tipo != "dica" else DICA
        cor = {"ok": c["texto"], "info": c["alerta"], "erro": hx("#ff6060")}.get(e.status_tipo, c["dim"])
        T.texto(6, sy, cortar(msg, W - 12), cor)

        estilo = dict(bg=css(c["fundo"]), fg=css(c["texto"]), cursor=css(c["alerta"]), fonte=("Consolas", 10))
        return self._finaliza(T, regs, campo, estilo)
```

## 5. Referência

### 5.1. Ferramentas de desenho (`diario\pixel.py`)

Tudo desenha em **pixels de arte**, sem suavização. A origem `(0, 0)` é o canto superior esquerdo; `y` cresce para baixo.

| Ferramenta | O que faz |
|---|---|
| `Tela(w, h)` | Camada RGBA transparente de `w × h`; `T.im` é a imagem PIL, `T.d` o `ImageDraw` |
| `T.px(x, y, cor)` | Um pixel (ignora o que sai da tela) |
| `T.rect(x, y, w, h, cor)` | Retângulo cheio de largura `w` e altura `h` |
| `T.ell(x0, y0, x1, y1, cor)` | Elipse cheia dentro da caixa |
| `T.poly(pontos, cor)` / `T.line(pontos, cor, w)` | Polígono cheio / linha |
| `T.put(imagem, x, y)` | Cola uma imagem RGBA (respeita o alfa; corta o que sai da tela) |
| `T.spr(x, y, linhas, paleta)` | Desenha um sprite a partir de texto: cada caractere de `linhas` é um pixel e `paleta` mapeia o caractere à cor (`"#": hx("#fff")`); caracteres fora da paleta ficam transparentes |
| `T.texto(x, y, texto, cor, k=1)` | Escreve com a fonte pixel e devolve o `x` do fim; `k` amplia o texto |
| `T.cantos(x, y, w, h)` | Apaga os 4 cantos de um retângulo (contorno pixelado) |
| `hx("#rrggbb")` | Cor `(r, g, b, 255)` |
| `mix(a, b, t)` | Mistura duas cores |
| `rampa(cor)` | `(escuro, base, claro)` com sombra puxando para o roxo e luz para o amarelo |
| `esfera(T, x0, y0, x1, y1, rampa)` | Elipse com sombra embaixo e brilho em cima |
| `contorno(imagem, cor)` | Devolve a imagem com 1 pixel de contorno (2 pixels maior em cada eixo) |
| `icone(nome, cor)` | Ícone de botão (`anterior`, `proximo`, `calendario`, `atualizar`, `relatorio`, `fechar`, `config`) |
| `largura(texto, k=1)` | Largura do texto em pixels de arte |
| `cortar(texto, px)` | Corta com reticências para caber em `px` pixels de arte |
| `glifo(caractere)` | Linhas do caractere na fonte (para desenhos especiais) |

**Fonte pixel:** 5×7, letras de tamanho único (6 pixels de avanço por caractere). Tem letras, dígitos e a pontuação `! " # $ % & ' ( ) * + , - . / : ; < = > ? @ [ \ ] ^ _ ` { | } ~ · — • …`. Os acentos `á à ã â é ê í ó õ ô ú ç` (e as maiúsculas) são desenhados por cima da letra-base. **Qualquer outro caractere aparece como `?`** (por exemplo `ü`, `ñ`, `€`, emojis). Para texto sempre em caixa alta, como no Retrô, faça `texto.upper()` antes de desenhar (o `TemaPixel` tem a ajuda `_t()` e o atributo `CAIXA_ALTA`).

### 5.2. Atributos que o tema pode definir

| Atributo | Padrão | Efeito |
|---|---|---|
| `id`, `nome`, `descricao` | (obrigatórios) | Identidade do tema na tela de configurações |
| `animacao_ms` | `None` | Intervalo entre quadros de animação; sem ele, só redesenha quando o estado muda |
| `animacao_ociosa_ms` | `None` | Tema em tempo real: intervalo entre quadros enquanto nenhum efeito de clique roda (ver "Animação barata") |
| `cores_balao` | cinza-azulado escuro | `(fundo, texto, borda)` dos balões de ajuda, em `"#rrggbb"` |
| `hover_no_status` | `False` | `True`: o texto inteiro do tópico sob o mouse aparece na linha de status, em vez de num balão |
| `efeitos` | `{}` | `{nome: duração em quadros}` dos efeitos que o clique dispara (ver o passo 9) |
| `Z` (`TemaPixel`) | `2` | Quantos pixels da tela vale cada pixel de arte |
| `PAD` (`TemaPixel`) | `8` | Margem interna dos diálogos, em pixels de arte |
| `TITULO_H` (`TemaPixel`) | `15` | Altura da barra de título dos diálogos |
| `CAIXA_ALTA` (`TemaPixel`) | `False` | Título e rótulos dos diálogos em maiúsculas |

### 5.3. O `Estado` que o tema recebe

| Campo | Significado |
|---|---|
| `dia` | O dia exibido (`date`) |
| `eh_hoje` | `False` quando está vendo outro dia: mostre o botão `Hoje` |
| `topicos`, `extra` | `[(texto, tipo)]` (até 14) e quantos não couberam |
| `status`, `status_tipo` | Mensagem e tipo (`dica`, `ok`, `info`, `erro`); `dica` com `status` vazio significa "mostre a dica de uso" |
| `hover` | Nome da região sob o mouse, ou `""` |
| `periodo` | `manha`, `tarde` ou `noite` |
| `cal_mes`, `cal_dias` | (calendário) primeiro dia do mês exibido e o conjunto de dias `AAAA-MM-DD` com registro |
| `temas`, `tema_atual` | (configurações) lista `(id, nome, descricao)` de todos os temas e o `id` do que está em uso |
| `barra` | (configurações) itens `(tipo, regiao, rotulo, valor, ativo)` da coluna **Barra de tarefas**, desenhados de cima para baixo à direita dos temas; os tipos (`titulo`, `sub`, `texto`, `espaco`, `estado`, `marca`, `opcao`, `cores`, `alfas`, `passo`) estão no comentário `ITENS_BARRA` de `base.py`. Lista vazia: a janela fica só com os temas |
| `efeitos` | `{nome: quadros desde o clique}` dos efeitos em andamento; vazio quando nada foi clicado |

### 5.4. O `Quadro` que o tema devolve

| Campo | Significado |
|---|---|
| `imagem` | RGBA do tamanho **exato** da janela. O widget redimensiona a janela para o tamanho da imagem, então ele pode mudar de um quadro para o outro (a altura acompanha o conteúdo) |
| `regioes` | Lista de `Regiao(nome, caixa, dica, cursor)`. `caixa` é `(x0, y0, x1, y1)` em pixels da **tela** (o `TemaPixel._finaliza` já converte) |
| `entrada` | Caixa onde fica o campo de texto do Tk, ou `None` se o quadro não tem campo (diálogos) |
| `estilo_entrada` | `bg`, `fg`, `cursor` (cor do cursor de texto) e `fonte` (`("Consolas", 10)`): as quatro chaves são obrigatórias |
| `transparente` | `True`: pixels com alfa abaixo de 128 viram buraco na janela e deixam o clique passar (formato livre) |
| `fundo` | Cor de fundo da janela quando o quadro não é transparente |

### 5.5. Regiões da janela principal

O widget só reage a estes nomes; qualquer outro é ignorado (o mouse passa por cima sem efeito).

| Nome | Ação do widget |
|---|---|
| `anterior`, `proximo` | Dia anterior e seguinte (não passa de hoje) |
| `hoje` | Volta para o dia de hoje |
| `calendario` | Abre o calendário |
| `atualizar` | Coleta as sessões do Claude Code do dia |
| `relatorio` | Gera e abre o relatório do dia |
| `config` | Abre as configurações |
| `fechar` | Fecha o widget |
| `linha:N` | Nenhuma ação: serve ao realce e ao balão do tópico `N` |
| `arrastar` | Arrastar a janela (só vale onde nenhuma outra região está) |

### 5.6. Regiões dos diálogos

No `TemaPixel` elas já estão prontas. Se você herdar de `Tema` e escrever o calendário e as configurações, devolva estas:

| Diálogo | Região | Ação |
|---|---|---|
| Calendário | `cal_fechar`, `cal_ant`, `cal_prox` | Fechar; mês anterior; mês seguinte |
| Calendário | `dia:AAAA-MM-DD` | Escolher o dia (só para dias que não são futuros) |
| Calendário | `cal_semana` | Resumir a semana do dia exibido (dica: `base.dica_semana(e.dia)`; rótulos em `base.SEMANA` e `base.SEMANA_ROTULO`; com `e.resumindo` o botão vira `[resumindo…]` e a região some) |
| Configurações | `cfg_fechar` | Fechar |
| Configurações | `tema:<id>` | Trocar para o tema `<id>` |
| Configurações | `barra:...` | A região que vem em cada item de `e.barra` (no `passo`, `<regiao>:-` e `<regiao>:+`); o widget interpreta |
| Ambos | `arrastar` | Mover o diálogo |

A lista de temas da tela de configurações tem duas categorias, **Widget** e **Papel de parede**; o tema que tem `papel = True` cai na segunda. Em `configuracoes(estado, miniaturas)`, itere `base.grupos_de_temas(estado)`, que devolve `[(título, [(id, nome, descrição)])]` já separado (sem grupo vazio), e desenhe um título por grupo. `miniaturas` é um dicionário `{id: imagem PIL RGB de 160 px de largura}` com a prévia de cada tema; cole a de cada um ao lado do nome. Os diálogos abrem logo abaixo do widget, `Esc` fecha, e a largura deles é você que decide (no `TemaPixel` são fixas: 149 pixels de arte o calendário e 190 as configurações).

### 5.7. Janela de formato livre (`transparente=True`)

Só vale para a janela inteira e funciona por uma cor-chave: o widget pinta de `(1, 2, 3)` os pixels com alfa abaixo de 128 e pede ao Windows que trate essa cor como transparente. Daí:

- **Não use** a cor `(1, 2, 3)` no desenho.
- **Sem meio-termo:** um pixel com alfa 100 vira buraco e um com alfa 200 vira opaco. Sombras translúcidas e bordas suavizadas ficam serrilhadas ou somem. Em pixel art isso não importa; em desenho suave, prefira um tema opaco (`transparente=False` e `fundo` definido), como o Clássico faz.
- O clique **atravessa** os buracos para a janela de trás.

## 6. Armadilhas

- **Nome de região errado = botão morto.** `"fechar"` funciona; `"Fechar"` ou `"close"` não. Confira a tabela da seção 5.5.
- **Caixa em pixels da tela, desenho em pixels de arte.** No `TemaPixel`, você monta as caixas em pixels de arte e o `_finaliza` as multiplica por `Z`. Se montar o `Quadro` à mão (como o Retrô faz, que usa janela opaca), multiplique você.
- **`estilo_entrada` incompleto** dá `KeyError` ao abrir o widget: precisa de `bg`, `fg`, `cursor` e `fonte`.
- **Campo mal posicionado.** O `Entry` ocupa exatamente a caixa `entrada`; se ela for maior que a moldura que você desenhou, o campo "vaza". Com `Consolas` 10, a caixa precisa de cerca de 20 pixels da tela de altura (10 pixels de arte com `Z = 2`).
- **Texto que não cabe.** Sempre passe pelo `cortar(texto, largura)`; uma linha longa desenhada direto atravessa a janela, e com `W` fixo ela some do lado de fora ou invade os botões.
- **Janela que "pula".** Se a altura depende do número de tópicos, fixe um mínimo (como as 3 linhas dos temas atuais) e limite o crescimento; o widget já limita a 14 tópicos.
- **Quadro lento.** O tema é chamado a cada movimento de mouse que troca de região. Desenhar sprites grandes ou gerar ruído aleatório a cada chamada trava a interface. Guarde em cache o que não muda e use `random.Random(semente)` com semente fixa para o desenho ficar igual de um quadro a outro.
- **Ler o banco ou o disco dentro de `quadro()`.** Não faça: o tema recebe tudo no `Estado`, e a miniatura da tela de configurações chama `quadro()` com dados de exemplo, sem banco.
- **`id` repetido** sobrescreve o outro tema sem avisar.
- **Tema removido.** Se alguém apagar o tema que está salvo em `widget.json`, o widget abre no `PADRAO` sem erro.
- **Translucidez total.** O widget aplica um `alfa` de 0,97 só ao tema de `id` `classico` (ele está fixo em `Widget.redesenha`). Um tema novo que queira a janela levemente translúcida precisa de uma pequena mudança ali.
- **Fontes de verdade** (temas que herdam de `Tema`): use `base.ESCALA`, o fator de DPI do Windows, para dimensionar fontes e margens; sem isso, em telas com 125% ou 150% o texto sai pequeno.
- **Barras invertidas no PowerShell/Git Bash:** ao escrever caminhos do Windows em scripts que geram arquivos, `\t`, `\n` e `\r` viram tabulação, quebra de linha e retorno. Em Python use `r"C:\caminho"` ou `/`.

## 7. Checklist antes de dar o tema por pronto

- [ ] `id` único, `nome` e `descricao` curtos
- [ ] `quadro()`, `paleta()` e `moldura_dialogo()` implementados (ou `quadro()`, `calendario()` e `configuracoes()`, se a base é `Tema`)
- [ ] Registrado em `TEMAS`, no `diario\temas\__init__.py`
- [ ] `python -X utf8 tools\previa_temas.py <pasta>` roda sem erro e os PNGs de manhã, tarde e noite estão legíveis
- [ ] Dia vazio, dia com 14 tópicos (e "… e mais N") e dia passado (com `Hoje`) conferidos
- [ ] Tempo por quadro de poucos milissegundos
- [ ] Testado na instância de teste (`DIARIO_PREVIEW=1`): balões, botões, calendário, configurações, arrastar e digitar no campo
- [ ] Linha nova na tabela de temas do `README.md`
