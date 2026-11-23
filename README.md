# Diário de atividades

Registra sozinho o que você trabalhou no dia — a partir das sessões do Claude Code e dos commits SVN — e guarda tudo num banco SQLite, para consultar depois e apontar as horas no trabalho. Tem três faces: um conjunto de comandos (`python -m diario`), um widget de desktop (tkinter) e uma skill do Claude Code (`/diario`).

Criado em 27/10/2026 porque reportar atividades e horas à mão não funcionava. A ideia é que o diário se escreva sozinho e a sua parte seja só conferir e completar o que não passou pelo Claude (reunião, ligação, dúvida de colega).

## Sumário

1. [Como funciona](#como-funciona)
2. [Requisitos](#requisitos)
3. [Uso](#uso)
4. [Widget de desktop](#widget-de-desktop)
5. [Skill /diario](#skill-diario)
6. [Tarefas agendadas](#tarefas-agendadas)
7. [Banco de dados](#banco-de-dados)
8. [Regras de coleta](#regras-de-coleta)
9. [Formato do arquivo diário](#formato-do-arquivo-diário)
10. [Configuração](#configuração)
11. [Estrutura do projeto](#estrutura-do-projeto)
12. [Decisões e armadilhas](#decisões-e-armadilhas)
13. [Limitações conhecidas](#limitações-conhecidas)
14. [Manutenção](#manutenção)
15. [Licença](#licença)

## Como funciona

```
 transcritos do Claude Code ──┐                          ┌─► .md por dia (Documents\Diario)
 (~\.claude\projects\*.jsonl) │                          │
                              ├─► coletar ─► SQLite ─────┼─► widget de desktop (tkinter)
 svn log --search <usuário> ──┤   (diario.db)            │
                              │                          └─► skill /diario (Claude Code)
 lançamentos manuais ─────────┘
 (add, widget, /diario)
```

- **O banco é a fonte de verdade.** Os `.md` são só exportação e podem ser regerados a qualquer momento a partir dele. O widget lê o mesmo banco.
- **Três fontes alimentam o banco.** Os pedidos que você fez ao Claude Code (e os instantes de atividade das sessões), os commits SVN do seu usuário e os lançamentos manuais.
- **Duas coisas são guardadas:** `eventos` (o que aconteceu: um pedido, um commit, um lançamento) e `segmentos` (quanto tempo você esteve ativo, em trechos contínuos por projeto).
- **Tudo é idempotente.** Rodar a coleta várias vezes sobre o mesmo período não duplica nada.

## Requisitos

- Windows, com o Python 3.13 em `%LOCALAPPDATA%\Programs\Python\Python313\` (inclui o `tkinter`). O widget usa `pywin32` e `Pillow` para o ícone da bandeja; sem eles ele abre igual, só sem o ícone (e registra o motivo em `widget.log`).
- Opcional, para a coleta do SVN: TortoiseSVN com a linha de comando em `C:\Program Files\TortoiseSVN\bin\svn.exe`, credenciais do SVN já salvas (a coleta não pede senha) e o endereço do repositório em `SVN_URL` (veja [Configuração](#configuração)). Sem isso, o restante funciona e só o SVN fica de fora.
- O Claude Code, porque a fonte principal são os transcritos em `~\.claude\projects\`.

Todos os comandos abaixo rodam a partir da pasta do projeto, com o Python em modo UTF-8 (`-X utf8`, necessário para os acentos no console do Windows):

```powershell
Set-Location <pasta do projeto>
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -X utf8 -m diario <comando>
```

## Uso

### `coletar`

Lê os transcritos do Claude Code e o `svn log` e grava no banco.

```powershell
python -X utf8 -m diario coletar --desde 2026-10-01
python -X utf8 -m diario coletar --desde 2026-10-27 --sem-svn
```

| Opção | Efeito |
|---|---|
| `--desde AAAA-MM-DD` | Primeiro dia a coletar. Padrão: hoje. Arquivos de transcrito não modificados desde essa data são ignorados. |
| `--sem-svn` | Pula o SVN (mais rápido; útil sem VPN). |

- A coleta do SVN leva cerca de 1,5 minuto para um mês inteiro, e segundos para um dia.
- Se o SVN não responder (VPN desligada, tempo esgotado), o comando avisa e termina sem erro. Rode de novo depois com a VPN ligada: os commits que faltavam entram.

### `exportar`

Gera os arquivos `.md` a partir do banco.

```powershell
python -X utf8 -m diario exportar --dia 2026-10-27
python -X utf8 -m diario exportar --desde 2026-10-01 --ate 2026-10-27
python -X utf8 -m diario exportar --desde 2026-10-01 --ate 2026-10-27 --saida C:\teste
```

| Opção | Efeito |
|---|---|
| `--dia` | Um dia só (atalho para `--desde` = `--ate`). |
| `--desde` / `--ate` | Intervalo. Padrão: hoje. Dias sem nenhum registro não geram arquivo. |
| `--saida` | Pasta de destino. Padrão: `SAIDA_MD` do `config.py`. |

### `add`

Lançamento manual, para o que não passou pelo Claude Code.

```powershell
python -X utf8 -m diario add "reunião com CS sobre o #12350" --duracao 1h --projeto "Reunião"
python -X utf8 -m diario add "dúvida de colega sobre sincronismo" --dia 2026-10-26
```

| Opção | Efeito |
|---|---|
| `texto` | Descrição da atividade. Tickets escritos como `#12350` são reconhecidos. |
| `--dia` | Padrão: hoje. |
| `--projeto` | Padrão: `(manual)`. |
| `--categoria` | `trabalho` (padrão) ou `pessoal`. |
| `--duracao` | `30min`, `1h`, `1h30`, `1h 30min`. É só a duração, sem hora de início e fim; ela **soma** ao total do dia. Sem ela entra apenas o texto, sem horas. |

### `contexto` e `resumo`

Servem ao resumo narrativo (veja [Resumo narrativo](#resumo-narrativo)).

```powershell
python -X utf8 -m diario contexto --dia 2026-10-26
python -X utf8 -m diario resumo --dia 2026-10-26 "Portal #12345: ..." --topico "#12345 Guia analisado" --topico "#12346 Commits r20507 e r20513"
```

- `contexto` imprime o material bruto do dia: por projeto, cada pedido com a resposta que o Claude deu, mais os commits e os lançamentos manuais.
- `resumo` grava (ou substitui) o texto do dia; `-` no lugar do texto lê da entrada padrão.

### `widget`

Abre o widget de desktop (veja a seção seguinte).

## Resumo narrativo

Pedidos soltos do começo das conversas ("sim, siga", "agora a documentação") não servem para apontar horas. O que serve é um parágrafo no estilo *"Portal #12301: resolvi o conflito da sincronização com a trunk, ajustei a regra de visualização e testei no servidor de homologação, corrigi o APK..."*, e isso exige entender o trabalho, coisa que o código sozinho não faz.

- **Quem escreve:** o Claude Code, na skill `/diario resumir` (ou "resuma o dia", "resuma a semana"). Ele roda `contexto` para o dia, escreve o parágrafo em primeira pessoa e no passado, e grava com `resumo`. O texto fica na tabela `resumos` e aparece no relatório do widget e no `.md` do dia.
- **Só os botões do widget chamam o modelo:** `[resumir]` e `[atualizar]` (um dia) e `[resumir semana]` (no calendário); a coleta agendada não chama nenhum. Eles (`diario\resumir.py`) coletam, montam o `contexto` de cada dia (sem os projetos de categoria `pessoal`) e rodam `claude -p` sem ferramentas e sem gravar sessão, uma só chamada para todos os dias, que devolve o parágrafo e os tópicos em JSON; quem grava no banco é o próprio código. Sessões abertas em `(home)` contam como trabalho e não dá para separá-las por categoria, então o prompt manda o modelo deixar de fora o que é pessoal pelo conteúdo. Uma semana de 4 dias leva cerca de 3 minutos. Isso exige o `claude` da linha de comando autenticado (`claude /login`); sem o login, ele responde "Not logged in" e o widget mostra "claude não está logado". O estilo do texto está duplicado na constante `INSTRUCAO` e na skill `/diario resumir`; mudando um, mude o outro. Com o login feito, também dá para ligar um `resumir` à tarefa das 18h.
- **Resposta do Claude como matéria-prima:** a coleta guarda, em `eventos.resposta`, o último texto que o Claude deu depois de cada pedido (até 700 caracteres). É ele que diz o que foi feito; o pedido sozinho diz pouco.

## Widget de desktop

Janela pequena, sem borda, que mostra o dia em tempo real. O visual vem de um **tema** que você escolhe no botão `⚙` (veja [Temas do widget](#temas-do-widget)); a descrição abaixo vale para todos.

- **Como abrir:** dois cliques em `abrir_widget.pyw`, ou `python -X utf8 -m diario widget`. Ele também abre sozinho no logon (veja [Tarefas agendadas](#tarefas-agendadas)).
- **No topo:** dia exibido, com o botão `Hoje` logo ao lado da data (só aparece quando você está em outro dia), e os botões `◀` `▶` (trocar de dia), `📅` (calendário), `↻` (coletar agora), `▤` (abrir o relatório do dia no Bloco de Notas) `⚙` (configurações: escolher o tema) e `✕` (fechar). A janela é arrastada pelo título e a posição fica salva em `widget.json`.
- **Ícone na bandeja:** enquanto o widget está aberto, aparece um ícone (lista de três tópicos em azul) na área de notificação do Windows, com a dica "Diário de atividades (aberto)". Um clique nele traz o widget para o primeiro plano, mesmo coberto por outras janelas, com o foco no campo de lançamento. O botão direito abre um menu com a opção **Fechar**, que encerra o widget (útil no papel de parede, que não tem `✕`). Ao fechar o widget (`✕`) o ícone some. No Windows 11 o ícone novo costuma cair no menu `^` de ícones ocultos; arraste-o de lá para a barra para deixá-lo sempre visível. O desenho fica em `diario.ico`, gerado na primeira execução se não existir.
- **Balões de ajuda:** deixar o mouse parado cerca de meio segundo sobre qualquer botão (`Hoje`, `◀`, `📅`, `▶`, `↻`, `▤`, `✕` e as setas do calendário) mostra um balão dizendo o que ele faz; o balão some ao tirar o mouse ou clicar. Os balões são desenhados por `Widget._mostra_balao`, em `diario\widget.py`, com as cores do tema.
- **Calendário (`📅`):** abre um mês logo abaixo do widget (ou acima, se não houver espaço) para escolher o dia exibido. Dias com registro aparecem em verde, o dia exibido em destaque azul, hoje em negrito, e dias futuros são cinza e não respondem ao clique. `◀` `▶` trocam de mês (não passa do mês corrente). Clicar num dia fecha o calendário e mostra o dia; `Esc`, clicar fora, arrastar o widget ou clicar de novo no `📅` também fecham. Escolher um dia passado faz o botão `Hoje` aparecer. Na base do calendário fica o botão **`[resumir semana]`**: pega a semana do dia exibido (segunda até domingo, sem passar de hoje), escreve o resumo só dos dias que não têm resumo ou cujo resumo ficou velho (os demais não vão ao modelo), grava `AAAA-MM-DD_semana.txt` na pasta do mês e o abre no Bloco de Notas, com as horas de trabalho de cada dia (sem sobreposição, as de categoria `pessoal` ficam fora do total), o resumo e os lançamentos manuais. O calendário fecha ao clicar; o andamento aparece na linha de status do widget.
- **Instância única:** só um widget roda por vez (mutex `Local\DiarioAtividadesWidget`, por sessão do Windows). Abrir de novo, por duplo clique, pelo logon ou por `python -m diario widget`, não cria outra janela: a segunda abertura encerra e pede ao widget aberto para vir à frente, como o clique no ícone. Sem `pywin32` não há trava.
- **Tamanho:** depende do tema (Clássico, Jogo retrô e Dino do deserto têm 608 px de largura; Ilha flutuante, 768 px, e Castelo medieval e Argonath, 832 px, com o céu (as telas de calendário e configurações mantêm o tamanho próprio)); a altura acompanha o conteúdo.
- **Tópicos do dia:** uma linha por tópico (até 14), sem horas. Vêm da coluna `topicos` do resumo do dia, escrita pelo Claude Code; os lançamentos manuais aparecem em verde, com a duração. Texto maior que a linha é cortado com reticências, e o texto inteiro aparece na linha de baixo ao passar o mouse. Dia sem tópicos mostra um aviso, as sessões e os commits; ao lado do aviso "Resumo do dia ainda não escrito" fica o botão `[resumir]`, que pede o resumo ao Claude (leva alguns instantes; enquanto isso o botão vira `[resumindo…]`, e o resultado ou o erro aparece na linha de status). Se o dia já tem resumo, mas houve atividade de trabalho depois de ele ser gravado, aparece no fim dos tópicos a linha "Resumo de HH:MM; há atividade até HH:MM" com o botão `[atualizar]`, que refaz o resumo. As horas ficam só no relatório (`▤`).
- **`↻`:** roda a coleta do Claude Code para o dia exibido (não coleta o SVN, que fica para a tarefa agendada). Fora isso, o widget se atualiza sozinho a cada 60 segundos.
- **`▤`:** grava `AAAA-MM-DD_relatorio.txt` na pasta do mês, ao lado do `.md` do dia (`Documents\Diario\AAAA-MM\`), e abre no Bloco de Notas o dia que o widget está mostrando. O texto traz o total do dia (tudo conta como trabalho), o **resumo** em tópicos, as horas por projeto com janela e tickets, os commits SVN e os lançamentos manuais. O resumo não é gerado pelo widget: vem da tabela `resumos`, escrita pelo Claude Code (veja [Resumo narrativo](#resumo-narrativo)); enquanto o dia não tiver resumo, o relatório avisa e mostra o restante. Cada clique regera o arquivo, então edições feitas nele são sobrescritas no clique seguinte; para guardar uma versão ajustada, use "Salvar como".
- **Campo de lançamento:** digite e tecle Enter.

| Você digita | Resultado |
|---|---|
| `1h reunião CS @Reunião #12350` | Lançamento de 1h, projeto `Reunião`, ticket `#12350` |
| `30min revisão do guia` | 30 minutos, projeto `(manual)` |
| `conversa rápida com o suporte` | Só texto, sem duração |

- A duração (`30min`, `1h`, `1h30`...) precisa vir no começo do texto. O `@Projeto` pode estar em qualquer ponto, mas vale uma palavra só (sem espaços).
- Lançamentos feitos pelo widget entram sempre como `trabalho`, e no dia que está exibido. O widget acompanha a virada do dia sozinho, a menos que você tenha voltado a um dia anterior com `◀`. O horário gravado no lançamento é o do relógio na hora em que você digitou.

## Temas do widget

- **Escolher:** botão `⚙` → tela de **Configurações** → clique no tema (a lista tem duas categorias: **Widget** e **Papel de parede**, esta com os temas que marcam `papel = True`). Ele muda na hora e fica salvo em `widget.json` (campo `tema`). Quem nunca escolheu fica com a Ilha flutuante. O calendário e a própria tela de configurações também usam o tema.
- **Temas incluídos:**

| Tema | `id` | Como é |
|---|---|---|
| Ilha flutuante | `ilha` | Placa de madeira e papel creme sobre uma ilha de grama; janela de formato livre (sol, nuvens e flores flutuam na área de trabalho). Pixel art em 2×. |
| Jogo retrô | `retro` | Tela de plataforma 8/16 bits (HUD, colinas, chão de tijolos que rola, herói correndo, bloco `?`) com o menu de RPG embaixo. Pixel art em 2×. |
| Dino do deserto | `dino` | Um dinossauro corre num deserto que rola e pula os cactos sozinho. O cenário tem camadas com parallax (céu, astros, nuvens, pássaros pretos voando, montanhas, colinas, chão e cactos) e a lista fica num cartão de papel sobre a terra. Pixel art em 2×. |
| Castelo medieval | `castelo` | Muralha de pedra com ameias e duas torres de telhado vermelho, com a lista num pergaminho; janela de formato livre, como a Ilha. Um dragão cruza o céu, bandeiras tremulam, tochas piscam, um cavaleiro faz guarda e ilhotas com torre e árvore flutuam ao redor. Os enfeites reagem ao clique: a porta abre e um rei olha para os dois lados antes de fechá-la, o dragão cospe fogo, o cavaleiro levanta a lança, a chama da tocha cresce e o sol pisca (de noite, a lua cintila). Pixel art em 2×. |
| Argonath | `argonath` | As estátuas de Isildur e Anárion guardando o rio Anduin, como na pintura de referência: uma de cada lado, com a lista num quadro de pedra no meio, o céu com nuvens que derivam em cima e o rio embaixo, com três canoas em silhueta: duas levam um humano e dois hobbits, e a terceira, o elfo e o anão. As estátuas e os penhascos vêm da própria referência (`diario
ecursosrgonath.png`, gerado por `arte
eferenciasrgonath\preparar_paredes.py`) e o tronco delas estica com o tamanho da lista. Janela retangular. Pixel art em 2× (blocos de 2×2 no céu, no rio e nas pedras). Os enfeites reagem ao clique: as estátuas viram o rosto para os barcos (clique no rosto: os olhos acendem e cai poeira da mão), cada canoa rema mais forte, o céu muda com a hora (o sol rompe a nuvem de manhã, o sol pulsa à tarde, estrela cadente à noite), a água abre anéis e um peixe salta, e as nuvens soltam chuva. Há dois segredos sem dica: clicar no canto direito da água faz o Gollum aparecer num tronco, e clicar no penhasco da esquerda faz um bando de orcs passar correndo. |
| Argonath (papel de parede) | `argonath-papel` | O mesmo Argonath em **tela cheia, como papel de parede**: a janela cobre o monitor principal e fica atrás de todas as outras. Estátuas dos dois lados, névoa e três cristas de montanha com neve ao fundo, o rio com as canoas e, em primeiro plano, uma margem de grama onde a tábua do diário se apoia, embaixo à direita. O cenário todo usa o mesmo pixel de 3 px da tábua e do texto (a arte está em `argonath_arte.py`), com nuvens como as da pintura (bojo e cauda, tons de areia), água de poucas formas grandes com o reflexo das paredes, do sol e da lua, estátuas ampliadas com Scale2x e retocadas (cabeça com elmo, sobrancelha, nariz, bigode e barba, mãos com dedos, dobras do manto, musgo em tufos e contorno), a da esquerda apoiada numa encosta da mesma rocha que desce ao rio e se funde à névoa, montanhas facetadas (a cadeia mais distante carrega a torre do Olho de Sauron) e uma lua esférica com mares e crateras. Mesmos enfeites e segredos do Argonath da janela, e manhã, tarde e noite. Veja [Papel de parede](#papel-de-parede). |
| Clássico | `classico` | O visual escuro original: cores sólidas e fonte do Windows. |

- **Manhã, tarde e noite:** manhã das 6h às 12h, tarde das 12h às 18h, noite o resto (`periodo_do_horario`, em `diario\temas\base.py`). Ilha, Retrô, Dino, Castelo e Argonath (inclusive o de papel de parede) trocam céu, astros e cores (e bichos, onde há); o Clássico ignora. `DIARIO_PERIODO=manha|tarde|noite` força um período, para testar.
- **Como funciona:** o widget monta um `Estado` (dia, tópicos, status, o que está sob o mouse) e pede ao tema um `Quadro`: a imagem da janela inteira, as regiões clicáveis e o lugar onde fica o campo de texto de verdade. Os temas pixel art (`TemaPixel`) desenham numa grade pequena, com a fonte pixel `recursos\pixel5x7.json` (CC0, sem acentos: `pixel.py` desenha á, ã, é, ç... por cima) e ampliam 2×. Os quadros animados ficam em cache por período e quadro, e só o que muda é redesenhado. Um tema animado também pode ter **efeitos de clique** (`Tema.efeitos`): o tema registra uma região `efeito:<nome>`, o widget conta os quadros desde o clique (`Estado.efeitos`) e o tema desenha a reação; clicar de novo no meio do efeito não o reinicia.
- **Papel de parede:** o tema Argonath (papel de parede) marca `papel = True` e o widget passa a tratar a janela de outro jeito (`diario\papel.py`). Ela cobre o monitor principal, fica atrás de todas as outras janelas, não aparece na barra de tarefas nem no Alt+Tab e não é ativada pelo clique (não rouba o foco). O clique, o hover e as animações funcionam como nos outros temas; **os ícones da área de trabalho ficam cobertos** (o Windows os desenha numa camada abaixo das janelas comuns). No clique, as estátuas viram a cabeça inteira para as canoas (os olhos acendem e cai poeira da mão e do ombro), o Olho de Sauron, fechado em repouso (da cor da torre), abre, olha de um lado ao outro com a pupila seguindo um feixe de luz que varre a paisagem, e fecha, e o Gollum, no canto esquerdo do rio, aparece num tronco. A cena tem 640×360 pixels de arte (16:9) e é ampliada até caber **inteira** no monitor: fator inteiro nas telas 16:9 (3× em 1920×1080, 4× em 2560×1440, 6× em 4K) e fracionário nas outras (2,4× em 1536×960), em que alguns pixels de arte saem uma fração maior que outros. Nada é cortado: o que sobra em cima (telas mais altas que 16:9) é céu, e o que sobra dos lados (telas mais largas) repete a coluna da borda; a tábua fica no canto de baixo à direita. **Troca de monitor:** o vigia confere o tamanho do monitor principal junto com o resto; se ele mudar (monitor ligado ou desligado, resolução trocada), a cena é refeita no tamanho novo e a janela volta ao canto 0,0, sem precisar reabrir o widget. Se a escala do Windows também mudou, o papel de parede cobre a tela mas fica um pouco borrado até o widget ser reaberto (o Windows só atualiza a escala de um programa ao abrir). **Animação só com a tela à mostra:** a cada 0,4 s o widget confere se outra janela cobre a dele por inteiro; coberta, a animação e o redesenho param, e voltam de onde estavam quando ela aparece (Win+D mostra o papel de parede e a animação volta). **Teclado:** como a janela não é ativada, o campo de lançamento abre uma janelinha de digitação por cima dele (Enter lança, Esc ou clicar fora fecha); o ícone da bandeja traz a cena inteira para a frente das outras janelas (a barra de tarefas continua por cima) e abre essa janelinha. A cena volta ao fundo quando a janelinha fecha (Enter, Esc ou um segundo clique no ícone) ou quando você ativa outra janela. A lista mostra no máximo 10 tópicos (o resto vira "… e mais N"), para a tábua não cobrir o rosto da estátua da direita. O calendário e as configurações abrem no meio da tela. Para voltar ao widget comum, escolha outro tema. **Consumo de CPU:** com a tela à mostra o widget usa cerca de 2,6% de um núcleo (era 17,5% antes das otimizações; 12 núcleos lógicos, ou seja, ~0,2% da CPU) e, coberto, cerca de 0,3%. Medido assim (`time.process_time` do processo, em regime, 6 s com o Win+D). O que faz isso: (1) **atualização parcial** (`Tema.partes`): parado, só a faixa do rio com as canoas, as nuvens que andaram e as estrelas que cintilam são refeitas e coladas no Tk; o resto da imagem (6 MB) não é nem refeito nem repintado; (2) **ritmo lento parado**: 280 ms entre quadros, em tempo real (a cena anda na mesma velocidade), e 140 ms só enquanto um efeito de clique roda; as nuvens andam em passos de 2 px e só 10 estrelas cintilam; (3) **prioridade abaixo do normal e modo de economia de energia** (EcoQoS): no Windows 11 o processo roda nos núcleos eficientes e não disputa CPU com o que você usa (o relógio de CPU sobe um pouco, por serem núcleos mais lentos, mas a energia cai); (4) **sem ninguém vendo, zero**: coberto por outra janela, com a sessão bloqueada ou remota ou com o monitor apagado, o timer de animação para de vez, o relógio da cena congela e o vigia passa a conferir a cada 1 s. Não há pausa na bateria.
- **Criar um tema:** o manual passo a passo, com um tema de exemplo completo, está em [docs\criar-um-tema.md](docs/criar-um-tema.md). Em resumo: (1) classe em `diario\temas\`, herdando de `Tema` (ou de `TemaPixel`, que já monta calendário e configurações a partir de `paleta()` e `moldura_dialogo()`); (2) implementar `quadro(estado, t)`; (3) acrescentar em `TEMAS`, em `diario\temas\__init__.py`. O tema aparece sozinho na tela de configurações.
- **Conferir sem abrir janela:** `python tools\previa_temas.py <pasta>` gera PNGs de cada tema e período, do calendário e das configurações, e mede o tempo de cada quadro.
- **Prévia sem mexer no widget do logon:** `DIARIO_PREVIEW=1 python -X utf8 -m diario widget` abre uma instância de teste, sem a trava de instância única e sem ícone na bandeja, que guarda posição e tema em `widget_preview.json`.
- **Rascunhos de arte:** `arte\referencias\` (a ilha flutuante, com a imagem que a inspirou e o gerador dos mockups).

## Barra de tarefas

A tela de **Configurações** tem duas colunas: os temas à esquerda e, à direita, a **Barra de tarefas**, com as opções de aparência que o TranslucentTB oferece. Cada clique muda a barra na hora.

- **Estados da barra:** a lista de cima tem os sete estados do TranslucentTB (Área de trabalho, Janela visível, Janela maximizada, Iniciar aberto, Pesquisa aberta, Visão de tarefas aberta e Economia de bateria), cada um com a aparência em vigor à direita, ou "desligada". Clicar num estado mostra as opções dele logo abaixo. A Área de trabalho vale sempre; os outros só com **Usar esta aparência** marcada e, quando valem, passam por cima dela (por exemplo, acrílico só com uma janela maximizada).
- **Opções de cada estado:** aparência (**Normal**, **Opaca**, **Transparente**, **Desfoque** ou **Acrílico**); **cor**, em oito amostras (preto, branco, azul, verde, vermelho, roxo, laranja e rosa) e cinco opacidades (0%, 25%, 50%, 75% e 100%), que a aparência Normal ignora; **raio do desfoque**, em passos de 0 a 50 (só com Desfoque); **Botão Mostrar área de trabalho** (o canto direito da barra); e **Borda da barra**. Transparente com cor a 0% é a barra totalmente transparente.
- **Ícone do TranslucentTB:** mostra ou esconde o ícone dele na área de notificação (`hide_tray`).
- **Fica de fora** o que precisa de digitação: as regras por janela (`rules`) e a lista de janelas ignoradas (`ignored_windows`), além das opções técnicas (registro, idioma). Para elas, use o menu do TranslucentTB ou edite o `settings.json`.
- **Quem faz é o TranslucentTB** (versão da Microsoft Store, pacote `28017CharlesMilette.TranslucentTB_v826wp6bftszj`). No Windows 11 22H2 em diante a barra é desenhada em XAML dentro do `explorer.exe` e ignora o `SetWindowCompositionAttribute`, que deixava a barra transparente no Windows 10 (testado em 10/11/2026 no build 26300: nenhum efeito). O TranslucentTB resolve por dentro do explorer; o diário (`diario\barra.py`) lê e grava o `settings.json` dele, em `%LOCALAPPDATA%\Packages\<pacote>\RoamingState\`, e o abre pelo atalho `ttb.exe` quando ele não está rodando. O TranslucentTB vigia esse arquivo e recarrega sozinho.
- **A fonte da verdade é o `settings.json`:** o diário não guarda cópia das opções (nada vai para `widget.json`) e relê o arquivo cada vez que a tela de configurações abre, então o que for mudado pelo menu do TranslucentTB aparece ali. O arquivo começa com uma linha de comentário (`// See https://...`) que o JSON do Python não aceita: o diário a separa na leitura e a regrava igual, e mantém a ordem das chaves.
- **Primeira vez:** o TranslucentTB abre uma tela de boas-vindas com a licença e só cria o `settings.json` depois de **Continuar**. Até lá a tela mostra os valores padrão dele, os cliques ficam guardados, a linha de status pede para aceitar a licença e o widget confere a cada 2 s. Quando o arquivo aparece, os cliques guardados são aplicados; se o TranslucentTB fechar sem aceitar, o widget avisa e descarta os cliques.
- **Ao abrir o widget**, se a barra tem alguma aparência diferente de Normal, ele garante que o TranslucentTB está rodando (ele pode não ter sido iniciado com o Windows). Escolher Normal não fecha o TranslucentTB.
- **Sem o TranslucentTB instalado** a coluna mostra só o aviso "Precisa do TranslucentTB, da Microsoft Store".

## Skill /diario

Fica fora do projeto, em `~\.claude\skills\diario\SKILL.md`. Ensina o Claude Code a traduzir pedidos em linguagem natural para os comandos acima.

- `/diario 1h reunião com CS sobre o #12350` — vira um `add` com duração e projeto.
- `/diario` sem argumento, ou "o que fiz hoje" — coleta, exporta e resume o dia.
- "o que fiz na semana" — consolida o período numa tabela Data | Atividade | Horas est.
- A skill nunca inventa horário: sem hora informada, o lançamento entra só com o texto.

## Tarefas agendadas

Duas tarefas no Agendador de Tarefas do Windows:

| Tarefa | Quando | O que faz |
|---|---|---|
| `DiarioAtividades` | Segunda a sexta, 18:00 (se o PC estiver desligado, roda ao ligar) | Executa `agendar\rodar_diario.ps1`: coleta e exporta os últimos 3 dias e registra a saída em `diario.log` |
| `DiarioWidget` | No logon do usuário, com 20 s de atraso | Abre o widget com `pythonw` |

Os 3 dias do script cobrem um dia sem o PC ligado e commits que entram com atraso. Para ajustar a janela, edite `$desde` em `agendar\rodar_diario.ps1`.

```powershell
Get-ScheduledTaskInfo -TaskName DiarioAtividades      # última execução e resultado (0 = sucesso)
Start-ScheduledTask -TaskName DiarioAtividades        # rodar agora
Disable-ScheduledTask -TaskName DiarioWidget          # parar de abrir o widget no logon
Unregister-ScheduledTask -TaskName DiarioAtividades -Confirm:$false   # remover de vez
```

- `Start-ScheduledTask -TaskName DiarioWidget` com o widget já aberto não abre outra janela: a segunda abertura só traz a primeira para a frente (veja a trava de instância única, na seção do widget).
- O `diario.log` só cresce. Apague ou esvazie de tempos em tempos.

## Banco de dados

Arquivo `diario.db`, na raiz do projeto. Três tabelas.

### `eventos`

O que aconteceu. Uma linha por pedido ao Claude, commit ou lançamento manual.

| Coluna | Conteúdo |
|---|---|
| `ref` | Identificador único e estável, que torna a coleta idempotente (veja abaixo). |
| `ts` / `data` | Horário local (`AAAA-MM-DD HH:MM:SS`) e o dia. |
| `origem` | `claude`, `svn` ou `manual`. |
| `projeto` / `categoria` | Projeto e `trabalho`/`pessoal`. |
| `tickets` | Tickets reconhecidos no texto, separados por vírgula (`#12301,#12310`). |
| `texto` | O pedido (até 400 caracteres), a mensagem do commit (`r19596 — RED #12301 - ...`) ou a descrição manual. |
| `minutos` | Só `manual`: a duração informada, quando houver. |
| `resposta` | Só `claude`: último texto do Claude depois do pedido (até 700 caracteres). Serve de base ao resumo narrativo. |

Como `ref` é formado:

- `claude:` + SHA1 de `horário+texto` — o mesmo pedido que aparece em dois arquivos de transcrito (sessão retomada ou copiada) vira uma linha só. Se projeto ou categoria mudaram desde a última coleta, a linha é atualizada.
- `svn:` + número da revisão — inserido uma vez.
- `manual:` + UUID — cada lançamento é novo.

### `segmentos`

Quanto tempo você esteve ativo. Uma linha por trecho contínuo, por projeto e dia.

| Coluna | Conteúdo |
|---|---|
| `origem` | `claude` (calculado) ou `manual` (duração informada em `--duracao`). |
| `data`, `projeto`, `categoria` | Como em `eventos`. |
| `inicio` / `fim` | Limites do trecho (`fim` já inclui a cauda). Num segmento `manual`, `inicio` é a hora em que o lançamento foi feito e `fim` é `inicio` + duração; a janela não é real. |
| `minutos` | `fim - inicio`. |

Os segmentos `claude` de um dia são apagados e recalculados toda vez que a coleta enxerga esse dia. Dias que a coleta não enxerga mais (transcritos que o Claude Code já apagou) ficam intactos. Os segmentos `manual` nunca são tocados pela coleta.

### `resumos`

Um parágrafo por dia, escrito pelo Claude Code.

| Coluna | Conteúdo |
|---|---|
| `data` | Dia (chave). |
| `texto` | O resumo. |
| `gerado_em` | Quando foi gravado. |
| `topicos` | Uma linha curta por tópico (até uns 60 caracteres), separadas por quebra de linha, para o widget. |

Para consultas diretas:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -c "import sqlite3; c=sqlite3.connect('diario.db'); print(c.execute('select data, categoria, sum(minutos) from segmentos group by 1,2').fetchall())"
```

## Regras de coleta

### Projeto de cada sessão

- O projeto vem do **nome da pasta do transcrito** em `~\.claude\projects\`, que é o diretório onde a sessão foi aberta. O nome da pasta é o caminho com tudo que não é letra ou número trocado por `-`; o coletor procura, dentro do arquivo, o `cwd` que gera exatamente esse nome e usa o caminho completo para montar o rótulo.
- Rótulo: com `PASTA_BRANCHES` definida (por exemplo `Branches`), `C:\Branches\<branch>\<produto>\...` vira `<branch>/<produto>`; a pasta pessoal (`C:\Users\<usuário>`) vira `(home)`; qualquer outro caminho vira o nome da última pasta (`meu-app`, `wiki`...).
- Consequência: uma sessão aberta em `(home)` ou numa pasta de documentação agrupa assuntos diferentes sob um só projeto, mesmo que você tenha trabalhado em tickets distintos. Leia os pedidos antes de atribuir horas a um ticket.

### Categoria

Decidida pelo caminho de abertura, na ordem de `CATEGORIAS` em `config.py`: `AndroidStudioProjects` e `PythonProjects` são `pessoal`; todo o resto é `trabalho`. Só o `trabalho` deve entrar no apontamento.

### Pedidos considerados

- Entram as mensagens suas (tipo `user`) de sessões principais. Mensagens de subagentes não geram pedido, mas o tempo que gastam conta como atividade.
- Ficam de fora: resumos de continuação de sessão, carregamento de skill, "request interrupted", imagens soltas, avisos de comando e blocos internos de sistema.
- Os tickets são reconhecidos por `#` seguido de 5 ou 6 dígitos, ou por `tkt`, `ticket`, `chamado`, `redmine` ou `bug` seguido do número (também no plural e em lista, como "tickets 103687 e 103700"). O relatório do widget avisa quando há atividade depois da gravação do resumo do dia.

### Tempo (estimativa)

1. Cada mensagem (sua ou do Claude, inclusive de subagentes) é um "sinal de atividade".
2. Os sinais de um projeto num dia são ordenados; um silêncio maior que `GAP_MIN` (25 min) encerra o trecho e abre outro.
3. Cada trecho recebe `CAUDA_MIN` (5 min) depois do último sinal, para cobrir o trabalho que terminou sem nova mensagem.
4. As horas do dia **por projeto** são a soma dos trechos. O total do dia, por categoria, é a **união** dos intervalos de todos os projetos, sem contar duas vezes o tempo em que duas sessões rodaram ao mesmo tempo, **mais** as durações lançadas à mão, que são somadas como informadas (reunião não sobrepõe sessão por definição).

Por isso a soma das linhas pode passar do total do dia; **o total sem sobreposição é o número confiável**. Tudo isso é estimativa — ajuste antes de apontar.

### Commits SVN

- `svn log --search <SVN_USER>` desde a data pedida; só commits cujo autor é exatamente `SVN_USER` entram. Com `SVN_URL` vazio, a coleta do SVN é pulada.
- Os horários do SVN vêm em UTC e são convertidos para o fuso local.
- Os commits entram como projeto `SVN` e não carregam duração. O branch do commit não é identificado (isso exigiria `svn log -v`, muito mais lento); os tickets vêm da mensagem do commit.

## Formato do arquivo diário

`Documents\Diario\AAAA-MM\AAAA-MM-DD.md`, em UTF-8, um por dia com registro.

```markdown
# Diário — segunda, 26/10/2026

**Tempo ativo estimado (sem sobreposição):** trabalho 4h32

## Resumo

Portal #12345 / #12346 (branch 4321, cliente Exemplo): analisei o guia ... (aparece só quando o dia tem resumo)

| Projeto | Categoria | Tickets | Janela | Horas est. |
|---|---|---|---|---|
| branch_2026.2_chamado_4321/portal | trabalho | #12345, #12346 | 08:27–18:24 | 4h26 |

## branch_2026.2_chamado_4321/portal

Pedidos ao Claude (31):

- 08:27 Neste primeiro momento, analise o chamado #12345 ...
- … e mais 19

## Commits SVN

- 11:40 r20477 — RED #12345 - ...

## Lançamentos manuais

- 14:00 [Reunião] reunião com CS sobre o #12350 (1h00)
```

- A tabela traz um projeto por linha, com a janela (primeira atividade até a última) e a soma dos trechos.
- Cada projeto lista até 12 pedidos (140 caracteres cada) e resume o resto.
- As seções de commits e de lançamentos manuais só aparecem quando há conteúdo.
- O arquivo é sobrescrito a cada exportação; **não edite à mão** — a correção vai no banco (novo `add`) e o arquivo é regerado.

## Configuração

Tudo em `diario\config.py`. Para usar valores próprios sem alterar esse arquivo, crie `diario\config_local.py` (fica fora do Git) só com as constantes que quiser trocar, por exemplo `SVN_URL = "https://svn.exemplo.com/repos/projeto"`.

| Constante | Padrão | Para que serve |
|---|---|---|
| `DB` | `<projeto>\diario.db` | Local do banco. |
| `SAIDA_MD` | `~\Documents\Diario` | Pasta dos `.md`. |
| `PROJETOS_CLAUDE` | `~\.claude\projects` | Onde estão os transcritos. |
| `SVN_EXE` / `SVN_URL` / `SVN_USER` | TortoiseSVN, vazio, usuário do Windows | Coleta do SVN; com `SVN_URL` vazio ela é pulada. |
| `PASTA_BRANCHES` | vazio | Pasta de checkouts de branch cujas sessões ganham o rótulo `<branch>/<produto>` (veja [Projeto de cada sessão](#projeto-de-cada-sessão)). |
| `GAP_MIN` | 25 | Silêncio (min) que fecha um trecho. Menor = estimativa mais conservadora. |
| `CAUDA_MIN` | 5 | Minutos creditados depois do último sinal do trecho. |
| `CATEGORIAS` | pessoal para `AndroidStudioProjects\|PythonProjects`; resto trabalho | Lista de `(regex sobre o caminho, categoria)`; a primeira que casa vence. |

Constantes do widget, em `diario\widget.py`: `REFRESH_MS` (60 s) e `MAX_TOPICOS` (14). Cores e tamanhos ficam em cada tema, em `diario\temas\`.

## Estrutura do projeto

```
diario-widget\
├── README.md              esta documentação
├── LICENSE                licença MIT
├── abrir_widget.pyw       atalho de duplo clique para o widget (roda sem console)
├── diario.db              banco SQLite (fora do OneDrive de propósito)
├── diario.log             saída da tarefa agendada (cresce sem limite)
├── widget.json            posição e tema do widget (criado ao mover/fechar; não vai para o git)
├── arte\
│   └── referencias\       referência do tema Argonath e o script que gera diario\recursos\argonath.png
├── docs\
│   └── criar-um-tema.md   manual: como criar um tema para o widget
├── tools\
│   ├── mcp-server.js      servidor MCP do LibreSprite (para desenhar sprites com o Claude)
│   └── previa_temas.py    renderiza os temas em PNG, sem abrir janela
├── diario.ico             ícone da bandeja (gerado sozinho se faltar)
├── agendar\
│   └── rodar_diario.ps1   script da tarefa DiarioAtividades
└── diario\
    ├── __main__.py        linha de comando (coletar, exportar, add, widget)
    ├── config.py          caminhos, SVN, estimativa de tempo, categorias
    ├── config_local.py    seus valores (opcional, fora do Git): substitui o que quiser do config.py
    ├── db.py              schema, conexão, tickets_em, lancar
    ├── coleta_claude.py   lê os transcritos; gera eventos e segmentos
    ├── coleta_svn.py      lê o svn log; gera eventos
    ├── bandeja.py         ícone do widget na área de notificação (pywin32)
    ├── barra.py           aparência da barra de tarefas: lê e grava o settings.json do TranslucentTB e o abre
    ├── papel.py           janela de papel de parede: fundo, sem ativação, detecta quando algo a cobre (ctypes)
    ├── exporta.py         monta e grava o .md de cada dia
    ├── widget.py          widget de desktop (tkinter): estado, mouse, balões, calendário e configurações
    ├── preferencias.py    lê e grava widget.json (posição e tema)
    ├── pixel.py           fonte pixel 5×7 com acentos, formas e contorno para os temas pixel art
    ├── recursos\          pixel5x7.json (fonte, CC0)
    └── temas\             base.py (contrato), argonath.py, argonath_arte.py, argonath_papel.py, castelo.py, classico.py, dino.py, ilha.py, retro.py, pixeltema.py
```

Fora do projeto: a skill `~\.claude\skills\diario\SKILL.md`, as duas tarefas do Agendador e a nota de memória `project_diario_atividades.md` do Claude Code.

## Decisões e armadilhas

- **O primeiro `cwd` de um transcrito não é confiável.** Uma sessão retomada de outra pasta traz o `cwd` antigo nas primeiras linhas; uma sessão de um branch chegou a aparecer como `trunk`. Por isso o projeto vem da pasta do transcrito, e os `cd` feitos durante a sessão (que fragmentavam um mesmo projeto em `res`, `docs`, `assets`...) são ignorados.
- **Banco fora do OneDrive.** SQLite em pasta sincronizada pelo OneDrive pode corromper. Só os `.md`, que são descartáveis, ficam lá.
- **Os transcritos do Claude Code expiram.** O Claude Code remove transcritos antigos; o banco guarda uma cópia do texto dos pedidos e dos segmentos, e a coleta não apaga dias que ela não vê mais. Quando o banco é a única cópia de um dia, a perda dele é definitiva (veja [Manutenção](#manutenção)).
- **UTF-8 no console.** Sem `-X utf8`, o Windows quebra em acentos e setas. Com `python -I`, `PYTHONIOENCODING` é ignorado, então use `-X utf8` mesmo.
- **`pythonw` não tem `stdout`.** O `main()` só reconfigura a saída se ela existir; sem isso, o widget abriria e morreria em silêncio.
- **SVN lento.** Um mês inteiro leva ~1,5 min. Falhas de rede não derrubam a coleta do Claude Code.
- **Sem `svn log -v`.** Dava para saber o branch de cada commit, mas o custo de tempo era de vários minutos para poucas informações.
- **Horas são estimativa, de propósito.** Não há como saber quanto tempo você realmente passou pensando ou lendo entre uma mensagem e outra; o corte de 25 min e a cauda de 5 min são um acordo razoável, não uma medida.

## Limitações conhecidas

- Só enxerga o que passou pelo Claude Code, pelo SVN ou pelos lançamentos manuais. Reunião, telefone e trabalho em outras ferramentas dependem do lançamento manual.
- Não é possível reclassificar projeto ou categoria de uma linha já coletada pela interface; seria preciso SQL ou um `add` novo.
- Não há coluna "já apontado" nem integração com o sistema de chamados ou de apontamento de horas: o apontamento continua manual, com o diário como apoio.
- O widget lança sempre como `trabalho` e o `@Projeto` não aceita espaços.
- O banco não tem backup automático. Os `.md` mantêm o histórico legível, mas não recriam o banco.
- Projeto, tickets e categoria são inferidos do caminho de abertura e do texto; erros de inferência (ticket no texto que não é o ticket trabalhado) aparecem como estão.

## Manutenção

- **Reprocessar um período:** `coletar --desde <data>` seguido de `exportar --desde <data> --ate <data>`. É seguro repetir.
- **Mudou a regra de categoria ou de rótulo?** Rode `coletar --desde <data>` outra vez: os eventos têm projeto e categoria atualizados e os segmentos do período são recalculados. Eventos de transcritos já apagados mantêm o rótulo antigo.
- **Backup do banco:** copie `diario.db` de vez em quando para um lugar seguro (com o widget fechado, para não pegar um arquivo em escrita). Um backup simples:

```powershell
Copy-Item diario.db "$HOME\Documents\Diario\backup-diario.db"
```

- **Adicionar uma categoria nova:** acrescente uma tupla em `CATEGORIAS` (antes do `.` genérico), rode a coleta do período e exporte.
- **Ver o que a tarefa agendada fez:** `Get-Content diario.log -Tail 20`.
- **Testar sem mexer no banco real:** aponte `diario.config.DB` para uma cópia antes de importar o módulo (foi assim que o widget e o `add` foram testados).

## Licença

MIT (veja [LICENSE](LICENSE)). O `tools/mcp-server.js` é do LibreSprite e continua sob a GPL-2.0, como diz o cabeçalho dele.
