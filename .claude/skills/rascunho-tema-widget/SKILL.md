---
name: rascunho-tema-widget
description: Rascunho de um tema novo do widget do diário de atividades (diario/temas/), em pixel art. Use SEMPRE que o usuário chegar com uma ideia de tema ("novo tema", "tenho uma ideia de tema", "tema de ...", croqui ou imagem de layout, "rascunho", "o que você sugere para o tema ...", "3 variações da igreja/do personagem"). Entrega UMA imagem estática da manhã, com as técnicas de pixel art pesquisadas aplicadas (luz única, rampas com mudança de matiz, selout, textura em clusters, oclusão), antes de qualquer período, animação, efeito de clique ou registro. Depois do ok do layout, a skill criar-tema-widget continua.
---

# Rascunho de tema do widget

Projeto na raiz deste repositório. Esta skill cobre a primeira metade do trabalho: da ideia até uma **imagem estática da manhã** aprovada. Tarde, noite, animação, efeitos de clique, registro em `TEMAS` e README são da skill `criar-tema-widget`, e só começam depois do ok do usuário.

Antes de desenhar, leia [referencias/tecnicas.md](referencias/tecnicas.md): são as regras de pixel art que o usuário espera ver aplicadas (e o checklist que você passa antes de mostrar). O código das técnicas está em `diario/acabamento.py`.

## Fluxo

1. **Entender a ideia e sugerir antes de desenhar.** Se o usuário só trouxe o tema ("reforma protestante"), responda com uma proposta curta: conceito, layout (em que ele difere dos temas atuais), 4 a 6 elementos do tema, o que cada clique faria, pontos de atenção. Os temas atuais são: Ilha (janela livre), Retrô e Dino (cena em faixa e lista embaixo), Castelo (janela livre), Argonath (retangular, tábua no meio) e o da Reforma (pergaminho central com a catedral ao lado). Um layout novo vale mais que a mesma faixa com outra cena. Pergunte só o que não dá para decidir (por exemplo, se há imagem de referência).
2. **Croqui ou imagem de layout.** Leia a imagem (Read) e diga como a interpretou: cada cor é um papel (quadro central, edifício, personagem, enfeites), a escala da cena e o que ficou de fora. Meça as proporções do croqui e converta para pixels de arte (a largura da janela é o seu `W`; os temas usam 304 a 416). Imagem de referência de pintura: siga `criar-tema-widget` (extrair paleta e reduzir à grade), não redesenhe à mão.
3. **Escrever em `diario/temas/<id>.py` sem registrar em `TEMAS`.** Decisões de projeto (base `TemaPixel`, janela opaca ou livre, mínimo de linhas, geometria da lista) estão em `criar-tema-widget`, seção 2. Defina a paleta só da manhã (os outros períodos vêm depois, mas desenhe já pensando neles: as mesmas chaves, outros valores). Antes de redesenhar um layout que já existe, copie o arquivo para o scratchpad: o tema é um arquivo novo no git e não há como voltar.
4. **Aplicar as técnicas de [tecnicas.md](referencias/tecnicas.md) enquanto desenha**, não só no fim. Escolha a direção da luz e escreva no docstring. Faça uma paleta com rampas por material (`s1 s2 s3 hi sh`, `wd1 wd2 wd3`, `paper paper2`, `ol ol2`). Use as funções de `diario/acabamento.py`: `pedra` (parede e piso), `luz_e_sombra` e `sombra_embaixo` (volume e oclusão), `selout` (sprites), `borda_colorida` (silhueta de peças grandes), `veios` (madeira) e `envelhece` (papel). Contorno preto puro não entra.
5. **Renderizar a imagem estática e olhar.** `python -X utf8 .claude\skills\rascunho-tema-widget\scripts\rascunho_estatico.py <modulo:Classe> <pasta>\rascunho_manha.png --estados`. Grava o estado de exemplo e, ao lado, os estados cheio (14 tópicos e "… e mais 3"), vazio e passado; em tema de janela livre (flutuante, sem céu) acrescente `--fundos` para conferir sobre fundo claro e escuro. Dê Read nas imagens e nos recortes ampliados (`scripts\recorte.py ... --caixa x0,y0,x1,y1 --zoom 8`) dos pontos fracos: rosto do personagem, porta, topo das peças altas. Passe o checklist da seção 8 de `tecnicas.md` e corrija antes de mostrar. Arquivos temporários vão para o scratchpad, não para a raiz.
6. **Mostrar com `SendUserFile`** (`display: render`) só a imagem da manhã (mais a imagem de um estado extremo se ele mudou o layout). Descreva em poucas linhas: como leu o croqui, o que é cada região, decisões, o que você não resolveu. Uma pergunta só: aprova o layout?
7. **Variações pedidas** ("3 versões da igreja", "3 personagens"): o tema lê um atributo de instância (`self.v_igreja = "a"` com valor padrão na classe) e o inclui na chave de cache; `scripts\folha_variantes.py <tema> <saida.png> --atributo v_igreja --valores a,b,c --caixa ... --rotulos "A · ...,B · ...,C · ..."` gera a folha lado a lado no contexto da cena. Mostre a folha e também a cena inteira com cada variante; peças escolhidas independem umas das outras (combine à vontade). Quando o usuário escolher, **apague as variantes descartadas** do código, sem deixar seletor ou ramo morto, e confira que o render ficou idêntico (hash do PNG antes e depois).
8. **Refinar** quando o usuário pedir: pesquise (WebSearch e WebFetch) em vez de chutar; a pesquisa de 30/10/2026 já está resumida em `tecnicas.md`; acrescente nela o que aprender de novo, com a fonte.
9. **Passar adiante.** Aprovado o layout, diga que o próximo passo é `criar-tema-widget` (tarde e noite, animação, cliques, registro) e só então comece.

## Armadilhas já pagas

- No Bash tool, heredoc com aspas ou apóstrofo no meio quebra o comando. Escreva o arquivo com Write e rode o script.
- Peça alta ou larga cobrindo a barra de botões ou o texto da lista. Compare a caixa de cada peça com as regiões clicáveis; a torre da esquerda da catedral tem altura menor por isso.
- `cortar(...)` precisa reservar a largura do botão `[resumir]` na linha em que ele aparece.
- Layout que cresce com a lista: teste `--estados` sempre; o chão ou o fundo da cena tem de acompanhar.
- Sprite com contorno `contorno()` de uma cor só some em fundo da mesma cor: use `selout` e confira o contraste em tamanho real.
- Um sprite posicionado pela mão ou pelo martelo (personagem que bate num prego): calcule a posição a partir do alvo e não ao contrário, ou a pose "bate" erra o prego quando o personagem muda de tamanho.
- Layout flutuante (janela de formato livre): sem céu, o que sobra em volta é buraco. Leia a seção 7b de `tecnicas.md`; o rascunho tem de ser conferido sobre fundo claro e escuro, e o recorte das margens precisa acompanhar o tamanho da lista.
- A janela do rascunho não é registrada: `Tema.miniatura` só roda depois que o tema entra em `TEMAS`.
