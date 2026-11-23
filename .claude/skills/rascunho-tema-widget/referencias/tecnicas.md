# Técnicas de pixel art para os temas do widget

Resumo da pesquisa feita em 30/10/2026 (fontes no fim) já traduzido para o que o projeto usa. O código das técnicas genéricas está em `diario/acabamento.py`; as peças de cada tema (janela, flecha, porta) ficam no tema.

## 1. Luz

- Uma luz só por cena. O padrão é vir de cima e da esquerda; mantenha em tudo (fachada, sprites, chão, sombras projetadas). Luz de baixo só para fogo ou terror.
- Escreva a direção da luz no docstring do tema e confira no fim: "de onde vem a luz?". Se não souber responder, é pillow shading (borda escura em volta de tudo e miolo claro), o erro mais comum.
- Face que olha para a luz: fio claro de 1 a 2 px na borda do lado da luz (`luz_e_sombra`). Face oposta: sombra em três passos, dois lisos e um pontilhado de transição.
- Sombra projetada: curta, para o lado oposto à luz e um pouco para baixo. Sprite em frente a uma parede projeta a silhueta deslocada uns 4 px à direita e 1 abaixo, só onde há parede ou chão (veja `_lutero` em `reforma.py`).
- Oclusão: duas linhas escuras sob cornijas, beirais, ameias e vãos, e um zócalo escuro no pé das paredes (`sombra_embaixo`).

## 2. Cor

- Rampa por material, de 3 a 5 tons: sombra funda, sombra, base, luz, realce. A sombra puxa para o frio e ganha saturação; a luz puxa para o quente e perde saturação. Escurecer só por brilho deixa tudo lavado e sujo.
- Em peças pequenas a diferença de luminosidade faz quase todo o trabalho (a sombra mediana é uns 16 pontos de L mais escura); a mudança de matiz compensa a partir de 3 tons por rampa, em peças maiores.
- Matiz que sobe com o brilho (Slynyrd usa cerca de +20° por passo) esquenta o que clareia, o que dá cores naturais.
- Contrastes: evite saturação alta com brilho alto, que fica áspero. Tons escuros aguentam mais saturação.
- Paleta enxuta e reaproveitada: o mesmo `sh` e `hi` tingem pedra, madeira, pele e papel. Peças de cor viva (vitral, ouro, vermelho) são o foco e ficam em poucos pontos.
- Noite: base fria (azul ou índigo escuro), fontes quentes pontuais (janela, tocha) como foco. Nada de preto puro.
- No código: chaves `s1 s2 s3 hi sh` (pedra), `wd1 wd2 wd3` (madeira), `paper paper2`, `ol ol2`, `vidro vidro2 vidro_hi`, em um dicionário por período. Veja `PER` e `_RAMPAS` em `reforma.py`.

## 3. Contorno

- Preto puro deixa o desenho "de desenho animado" e recorta cada peça. Use selout: o contorno é um tom do próprio objeto, mais escuro, mais claro onde a luz bate (alto e esquerda) e mais escuro embaixo e à direita.
- O contorno tem de ser mais escuro que o objeto e que o fundo. Confira em tamanho real: dois tons vizinhos precisam se distinguir; se não, escureça o contorno ou troque por uma sombra.
- Linhas internas: um tom abaixo da área em que estão; mais escuras para parecer mais grossas. Entre duas cores, use a da peça que está mais perto; entre duas partes da mesma superfície, omita a linha ou use a mais escura.
- No código: `selout(im, c)` para sprites (devolve a imagem 2 px maior) e `borda_colorida(im, linha, c)` para recolorir o contorno externo de uma peça grande desenhada com retângulos de uma cor `linha`. Desenhe a peça com um `c` cujo `ol` seja a linha interna suave e chame `borda_colorida` no fim.

## 4. Pedra, tijolo e outras texturas

- Monte a textura com poucos aglomerados (clusters) simples, repetidos em arranjos diferentes. Textura uniforme parece falsa e ocupada; detalhe em umas áreas e vazio em outras.
- Tijolo e pedra: desenhe primeiro as juntas, depois os blocos, depois o desgaste. Não contorne bloco por bloco (fica ocupado): junta de 1 px um tom abaixo da pedra, tom ligeiramente diferente por bloco, brilho ou sombra em alguns blocos, uma lasca de vez em quando, uns blocos mais fundos ou mais salientes.
- Largura de bloco variável (10 a 18 px) e fiadas deslocadas; altura constante (7 px) deixa a leitura limpa.
- Madeira: contraste médio, claro e escuro seguindo o veio, traços curtos e poucos realces; tábuas de tons diferentes e emendas. Metal: contraste alto, 1 ou 2 px de realce. Tecido: sombra macia que segue as dobras. Vidro: degradê, claro no alto, e um reflexo.
- Evite pixel solto (órfão), a menos que leia como parte da textura.
- No código: `pedra`, `veios`, `envelhece`, `janela` e `flecha` (esta no tema).

## 5. Pontilhado, bandas e serrilhado

- Pontilhado com parcimônia: para unir dois tons sem criar cor nova, em áreas grandes lisas (céu) ou em texturas ásperas (terra). A transição de uma sombra usa uma fileira pontilhada, não um degradê inteiro.
- Faixas de céu em "degraus": 10 linhas alternando as duas cores (`AABAABABBB`).
- Banding (segmentos que se alinham e empilham em escada) e serrilhado irregular (degraus de comprimentos misturados, como 2:1 e 3:1) denunciam amadorismo: faça degraus que crescem ou encolhem de forma regular.

## 6. Sprites pequenos (30 a 50 px)

- Silhueta primeiro: preenchido de preto, o personagem tem de ser reconhecível. A forma decide mais que o detalhe.
- No rosto, olho de 1 a 3 px, sobrancelha de 1 a 2 px e um traço de boca; mover um pixel muda a expressão. Pele com um lado ao sol (`L`) e outro na sombra (`F`).
- Use cor, não contorno, para separar partes; o contorno custa espaço de sombreado.
- Detalhes que identificam (tonsura, hábito, martelo, gola de pele) valem mais que acabamento.

## 7. Cena

- Cobertura entre elementos: quem fica em frente de uma região clicável (botões, linhas da lista) a esconde. Confira que torres, flechas e props não cobrem título e botões do quadro central (aconteceu com a torre da esquerda da catedral).
- Escalas coerentes: porta com 3 a 4 vezes a altura de um personagem, janelas proporcionais; se uma peça parece pequena demais, aumente a peça, não o detalhe.
- Camadas atmosféricas: o que está longe (casas ao longe) fica mais claro e menos contrastado que o que está perto.

## 7b. Layout flutuante (janela de formato livre)

- Sem céu nem fundo: `Quadro(..., transparente=True)`. O que não é desenhado é buraco e o clique atravessa; alfa abaixo de 128 vira buraco e o resto, opaco (sem halo, sem sombra translúcida); a cor `(1, 2, 3)` é proibida. Confira com `rascunho_estatico.py --fundos`: o rascunho sai sobre uma área de trabalho de teste e, ao lado, sobre fundo claro e escuro.
- Tudo precisa de contorno próprio, porque o fundo é desconhecido: `selout` em sprites, astros e nuvens; `borda_colorida` em peças grandes. Nuvem branca sem contorno some num fundo claro.
- Dar a ideia de "flutuando": o chão é uma laje solta, sem nada embaixo. Em cima as lajes vistas de cima (o topo pega a luz); na frente a espessura em três fiadas de blocos, mais escura que o topo e ainda mais na base, com a borda de baixo lascada. O contorno só existe nos lados e embaixo; em cima a laje encosta nas peças que estão sobre ela. Veja `calcada` em `reforma.py`. A alternativa mais pesada, uma rocha de terra que afina como cúpula virada, com estalactites e musgo, foi feita e o usuário preferiu só a calçada de blocos: não a ofereça de saída.
- Margens: recorte a imagem no que tem conteúdo (`JANELA` em `reforma.py`) e desloque as regiões clicáveis e a caixa do campo na mesma medida; com a lista cheia o recorte de cima precisa descer, senão corta o que sobe com o pergaminho.
- Equilíbrio: o peso visual tem de se distribuir em volta do quadro central. Uma peça alta de um lado (torre) pede outra massa do outro; o que fica no alto (astro, nuvens, emblema) pesa menos que a base, então a laje larga embaixo segura a cena. Meça as margens: conteúdo a cerca de 10 px de cada ponta da laje, dos dois lados. O usuário também descartou uma árvore usada como contrapeso: prefira reposicionar o que já existe a acrescentar elementos.

## 8. Checklist antes de mostrar

1. Fixei a direção da luz e todas as peças obedecem (fio claro de um lado, sombra do outro, sombra projetada)?
2. Há contorno preto puro em alguma peça? Troquei por selout ou por um tom escuro do próprio material?
3. A pedra, a madeira e o papel têm textura em poucos clusters, sem contornar cada bloco e sem uniformidade?
4. Há oclusão sob cornijas, beirais e no pé das paredes?
5. As rampas esquentam na luz e esfriam na sombra, sem escurecer só por brilho?
6. Olhei a imagem em tamanho real e ampliada 4x nos pontos fracos (personagem, porta, topo das torres)?
7. Nada cobre botões, título ou linhas da lista? O texto cortado ainda lê bem? O estado com 14 tópicos e o dia vazio fecham?
8. A silhueta do personagem principal lê de longe?
9. Janela livre: tudo tem contorno e lê sobre fundo claro e escuro (`--fundos`)? Não há alfa intermediário nem a cor-chave? A ilha parece flutuar? O layout está equilibrado nos dois lados?

## Fontes

- [Pixelblog 1: Color Palettes, Slynyrd](https://www.slynyrd.com/blog/2018/1/10/pixelblog-1-color-palettes)
- [Pixelblog 2: Texture, Slynyrd](https://slynyrd.com/blog/2018/2/15/pixelblog-2-texture)
- [Pixelblog 45: Bricks, Walls, Doors and More, Slynyrd](https://slynyrd.com/blog/2023/7/21/pixelblog-45-bricks-walls-doors-and-more)
- [Pixel art outlines, parte 2: using color, Lospec](https://lospec.com/articles/pixel-art-outlines-part-2-using-color)
- [Shading and Lighting, pixnote](https://pixnote.net/en/learn/shading)
- [Pixel Art Tutorial, Derek Yu](https://www.derekyu.com/makegames/pixelart.html)
