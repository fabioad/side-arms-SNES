# Progresso — fidelidade do Side Arms para SNES

Atualizado em **08/11/2026**, durante a sessão de implementação.

## Atualização: exportação completa das músicas recuperáveis

Com Ghidra foi percorrida a tabela completa de dispatch e auditados o vetor e
os 25 cabeçalhos dos comandos `0x20`–`0x38` em `a_04k.rom`. Dezenove têm notas
e foram exportados em pares `.mid`/`.it` (`stage1`, `cmd21`–`cmd29`, `cmd2a`,
`cmd2c`, `cmd2e`, `alt`, `cmd33`–`cmd36`, `cmd38`); seis (`0x2B`, `0x2D`,
`0x2F`, `0x30`, `0x31`, `0x37`) são stubs sem notas. A comparação confirma
13.962 eventos YM2203 capturados nos seis canais; os comandos `0x25`, `0x28` e
`0x35` usam key-ons/key-offs medidos no MAME. Todos os 19 ITs renderizam áudio
no FFmpeg. Evidências Ghidra e arquivos estão em
`sidearms_snes/docs/ghidra/evidence/music/`, `sidearms_snes/docs/MUSIC.md` e
`sidearms_snes/music/`. A cobertura do sequenciador foi concluída; isso não declara fidelidade integral
do áudio, pois a síntese FM foi adaptada para samples. O alvo `audio-from-rom`
regenerou banco e SPCs; `make` recompilou a ROM sem avisos e a regressão natural
confirmou POW, coleta, shotgun, SFX 0x01 e música simultânea durante os tiros.

## Disco azul sem tiles faltando

- O disco usava quatro quadrantes de 16×16 no arcade, mas o port desenhava
  apenas o primeiro. As quatro animações usadas (`1728`, `1730`, `1744`,
  `1750`) agora têm seus quatro códigos no atlas e ocupam quatro células
  da OAM. Para manter o banco de ROM dentro do limite, foram retirados
  14 códigos não usados da faixa `376..389`; o atlas passou de 438 para
  436 glifos, sem reduzir os 48 slots de cache da VRAM.
- A cor também estava incorreta: passar uma expressão ternária sem
  parênteses à macro `OAM_ATTR` escolhia outra paleta. O argumento foi
  agrupado no `DRAW`, incluindo os outros sprites que usam seleção
  condicional de paleta. No Mesen, a regressão verifica a paleta OBJ 4
  e pixels visíveis em **cada um dos quatro quadrantes**, além dos
  códigos presentes no cache e das posições na OAM.

## Puladores, formações aéreas e inimigos do stage 1

- O extrator passou a ler **183 eventos de inimigos** do script arcade
  `a_14e.rom:815C..84D0`, além dos 11 eventos de itens/andarilhos já
  implementados. Até o gatilho atual do chefe (`bg_px=3000`), há 115
  voadores comuns sem POW (`AD32..AD42`), 30 puladores (`8314..8320`),
  dois discos (`5523`) e 13 entradas de esquadrões (`A4DA..A4EA`).
  As formações genéricas inventadas após a primeira onda foram retiradas;
  a primeira onda antiga permanece para não deixar a entrada sem inimigos.
- Os voadores comuns usam o controlador de voo já portado para os
  portadores de POW, **mas não soltam item**. Os puladores descem, pousam,
  saltam novamente e podem ser atingidos. Discos e esquadrões recebem
  sprites próprios, com animação, tiros e colisão. Os gráficos vêm da
  ROM original; a paleta arcade 12 dos discos ocupa temporariamente o
  grupo OBJ 4, restaurado para a paleta 14 quando começa o chefe.
- O teste nativo exercita os spawns e movimento; o Mesen confirma OAM,
  cache VRAM, cores renderizadas das quatro famílias, paleta do disco e
  destruição de pulador por tiro. Uma execução adicional percorre o stage
  **sem forçar câmera ou criar inimigos** até vê-los surgir nos scrolls
  213, 1812, 1876 e 2071. Nessa execução, a invulnerabilidade é mantida
  pelo teste para evitar game over; ela não demonstra uma partida
  inteiramente natural até o chefe.
- **Não é um port integral do stage:** as trajetórias de puladores,
  discos e esquadrões ainda são aproximações; outros comandos do script
  (`8A57`, `A905`, entre outros) permanecem sem rotina própria. Há limite
  de 12 atores simultâneos e, para preservar a jogabilidade, os voadores
  comuns deixam de entrar quando oito slots já estão ocupados. Eventos
  posteriores ao gatilho atual do chefe não são executados. Trechos
  carregados continuam abaixo de 60 atualizações/s.
- A correção da paleta revelou que `dmaCopyCGram` recebe índices de cores,
  não offsets em bytes. O destino da atualização das paletas OBJ 2–4 foi
  corrigido; assim a paleta 12 dos discos é substituída pela 14 na entrada
  do chefe sem sobrescrever a paleta do jogador.

## Derrota no chefe sem ending; vitória com stage clear e ending

- O sinal `ending_pending` agora é zerado no início de cada partida e na
  derrota final de P1. O loop só solicita o ending se o estado atual for
  `STAGE CLEAR`; durante esse estado, um acerto tardio não converte vitória
  em game over. A derrota pela última vida mostra GAME OVER (ou ranking
  quando há classificação) e depois retorna ao título, sem o ending.
- Uma regressão nativa cobre vitória, reinício da partida, derrota durante
  o chefe e nova vitória. No Mesen, `test_boss_ending.py` exercita os dois
  resultados em partidas consecutivas: `STAGE CLEAR` → planeta do ending
  → título, e última vida perdida no chefe → GAME OVER → título, sem
  apresentar o planeta. As telas são verificadas em pixels após o atraso
  de apresentação, não apenas pela RAM ou pelo mapa do PPU.
- O teste Mesen injeta apenas o estado necessário para colocar o chefe e
  o projétil em cada resultado; ainda falta uma partida inteira que alcance
  ambos naturalmente. Build sem avisos, demais regressões de gameplay,
  combate, abertura, transição, emulador, itens e música passaram. ROM de
  1 MB, MD5 `f15d2233f71866960dd38fcf12fc7f38`. A emenda da abertura
  ainda mostrou três quadros pretos nesta compilação.

## Arma equipada na coleta e tiro comum do robô grande

- Coletar um POW de arma agora equipa imediatamente sua munição para o
  jogador que o apanhou, inclusive o Auto especial. X ainda percorre as
  armas já adquiridas; itens de velocidade, vida e pontos não trocam arma.
  Ao trocar de tipo, apenas os tiros antigos do mesmo jogador são limpos.
  Essa seleção imediata foi solicitada como escolha de jogabilidade: a
  rotina arcade `2617` confirma o upgrade, mas não demonstra essa troca
  automática da arma selecionada.
- Alpha/Beta continuam disparando os oito projéteis alternados dos descritores
  `927F/92BF` e `92FF/933F`; durante a fusão, a arma equipada pelo atirador
  também dispara com sua cadência e seus limites próprios. O MAME mostrou
  no mesmo estado Alpha um projétil comum de código 22 e oito tiros em leque.
  O teste Mesen confirmou a coexistência, OAM e pixels visíveis do disparo
  comum; o papel separado do piloto/atirador em 2P tem teste nativo, não uma
  partida cooperativa integral no emulador.
- Build e regressões de gameplay, combate, abertura, transição, cenário e
  música passaram. O teste de controles desde o boot confirmou que coletar o
  POW já ativa a shotgun sem pressionar X. A emenda para o gameplay mostrou
  **três frames pretos** nesta ROM, um a mais que antes; permanece pendente
  reduzir essa interrupção, sem afirmar continuidade perfeita. ROM de 1 MB,
  MD5 `c002f659e826c3144265af47619c94b0` naquela compilação.

## Entrega prioritária mais recente — itens, robô, andarilhos e músicas

As adições pedidas pelo usuário foram implementadas antes das demais pendências
listadas na auditoria. Detalhes e endereços estão em
[IMPLEMENTACAO_ITENS_ANDARILHOS_AUDIO.md](sidearms_snes/docs/IMPLEMENTACAO_ITENS_ANDARILHOS_AUDIO.md).

- Itens ocultos revelados por tiros; benefício de pontos, vida extra e
  transformação Alpha/Beta, além do sistema de armas e velocidade existente.
- Itens e quatro entradas de andarilhos posicionados pelos registros originais
  do script do stage 1; animações e dois tiros dos andarilhos recuperados da ROM.
- Corpo combinado 32×48, seis sprites, sequência de transformação, proteção,
  separação e dois padrões alternados de oito tiros por modelo.
- Em 2P, o coletor pilota e o parceiro atira, conforme `8D14`.
- As 19 faixas com notas foram verificadas contra 13.962 eventos capturados do
  YM2203; seis comandos sem notas foram confirmados como stubs. O módulo
  integrado mantém 37 padrões dentro do limite de 64 do
  snesmod; os SPCs independentes de stage e chefe reproduzem áudio por 40
  segundos, incluindo a repetição após a primeira volta.
- `make` agora tem `all` como alvo padrão e termina a ligação da ROM.
- A partida normal agora tem uma regressão sem injetar estado no WRAM:
  `test_natural_items.py` destrói o portador, confirma o POW ativo e visível
  na OAM e na captura, acompanha seu ciclo, coleta a arma e dispara a shotgun.
  O rastreio anterior mostrou uma remoção indevida pelo caminho do P2 quando
  inativo; a ROM recompilada com esse caminho protegido passou duas execuções
  completas. O comando do tiro comum carrega o sample `0x01` (SRCN 64 no SPC),
  com vozes de música ativas simultaneamente ao efeito; isso não prova
  equivalência de timbre/volume com o YM2203 original.
- A variável temporária que registrava o motivo de remoção do item foi
  retirada. A ROM foi religada e a partida natural voltou a passar sem
  instrumentação; o MD5 final da ROM de 1 MB é
  `1907c9410fa79f2be5864d7e9820bc43` naquela compilação.
- As referências de QA da abertura foram alinhadas à alteração dos slots de
  NAMING e à fonte sombreada instalada na VRAM durante a transição; combate,
  abertura e transição voltaram a passar na ROM atual sem relaxar as
  verificações de pixels/VRAM.

A revisão anterior abaixo é histórica: suas referências a fusão ausente e ao
backend antigo de música foram superadas por esta entrega. Permanecem as
pendências gerais de ondas/IA comum, câmera, terreno e auxiliares do chefe.
Não declarar fidelidade completa por causa destas adições.

## Revisão mais recente — stage 1 com Ghidra

A auditoria detalhada está em
[STAGE1_FIDELIDADE.md](sidearms_snes/docs/STAGE1_FIDELIDADE.md), com nova
exportação do Ghidra, conferência dos bytes das ROMs, endereços e critérios
para fechar cada diferença. Essa revisão prevalece sobre atribuições antigas
da câmera: `700B` não foi demonstrado como controlador normal do percurso.
Também foram corrigidos os eixos da estrutura de entidades em `docs/GHIDRA.md`.

Prioridades: scripts reais de ondas/IA e câmera; máscara de colisão do terreno
(`84B5`); schedulers completos do chefe (`3522/36B6`) e pós-morte (`6B71/3916`);
regras de itens/RNG e comandos de som; cadência e apresentação.
O tiro contínuo permanece como escolha de jogabilidade já registrada.

Na revisão, `make` e o combate no Mesen passaram. `make check-gameplay`
também passou após incluir `hiscore.c` na ligação do harness nativo.
Não foram implementadas novas ondas nem declarada fidelidade completa.

## Objetivo e situação

O objetivo continua sendo aproximar o stage 1 e sua abertura do arcade usando
engenharia reversa, assets da ROM e áudio SPC700. **O port ainda não deve ser
classificado como 100% fiel nem como jogo completo.** Há mudanças concretas e
testadas em relação ao protótipo, mas as ondas e a IA dos inimigos comuns ainda
contêm aproximações e há quedas de frequência em trechos pesados.

A ROM executável está em `sidearms_snes/sidearms.sfc`. O projeto usa PVSnesLib,
HiROM/FastROM e ROM de 1 MB. Não foi adotado MSU-1. O áudio permanece nativo
SPC700, como solicitado.

## O que já foi implementado nesta continuação

### Armas, jogador e itens

- Cinco famílias de armas substituíram os três padrões inventados do protótipo.
- Os descritores de tiro são extraídos de `a_12e.rom`, endereços Z80
  `0x90DF..0x927E`: sprite, posição, velocidade e parâmetros de colisão.
- Shotgun com 3/5/7 projéteis; laser segmentado com atrasos entre segmentos;
  tiro de três direções; Auto normal e variante especial; arma inicial com
  satélites e tiros próprios.
- Segurar A/B/Y agora repete o disparo para 1P e 2P após o cooldown, sem
  precisar soltar e apertar de novo. Isso é uma escolha de jogabilidade
  **diferente do latch observado no arcade** para as armas comuns; a variante
  especial Auto preserva sua cadência própria. Direção esquerda tem
  prioridade quando os dois botões estão pressionados.
- X percorre as armas coletadas e limpa os projéteis antigos do jogador,
  reproduzindo a regra identificada na rotina `0x1E03`.
- Movimento e seus três níveis vêm das tabelas `0x864C`, `0x866C`, `0x868C`:
  4/5/6 px nos eixos e 3/4/5 px nas diagonais.
- Os limites de upgrade vêm da rotina `0x2617`: 3/3/2/2 e estados `0x10/0x11`
  para Auto. Os itens de velocidade respeitam os limites 1..3.
- As formas do corpo do jogador usam os sprites originais de cada arma,
  orientação e recuo; há um cache separado por jogador. O laser tem o cano
  adicional. Os satélites seguem os 32 pontos originais de `0x1F56`, atualizados
  conforme `0x85EF`.
- O POW usa os estados identificados em `0x4DCF..0x513C`: alternância entre
  velocidade e armas, armas intermediárias com três acertos para mudar,
  POW negativo com 14 acertos e uma forma final de Auto. Há transições de
  animação, evitando vários avanços indevidos no mesmo quadro.
- Ícones e animações dos itens vêm da ROM; os números provisórios foram
  substituídos pelos gráficos originais.

### Gráficos e cache de sprites

- Objetos de 32×32 respeitam o passo de 16 tiles por linha do SNES.
- Projéteis, itens e explosões usam gráficos completos de 16×16, sem os antigos
  recortes de 8×8.
- Um cache de 48 células de 16×16 carrega os gráficos necessários em VBlank.
  Os corpos do jogador também são atualizados por pacote de DMA. Isso permite
  usar mais gráficos originais sem ultrapassar a página de OBJ da VRAM.
- Os projéteis ativos usam uma lista compacta; a rotina não percorre todos os
  slots vazios em todos os passos. Também foram removidas verificações e
  transferências de OAM redundantes.
- O starfield procedural foi substituído por um padrão extraído de
  `b_11j.rom`, usando a lógica do driver MAME local. A posição das estrelas em
  uma faixa limpa da captura de referência foi comparada e coincidiu.
- O padrão do starfield é original, mas seu movimento em gameplay ainda usa
  scroll/parallax simplificado; não foi portada toda a dinâmica dos contadores
  e latches do circuito de estrelas.

### Abertura

- Há 737 capturas consecutivas do arcade em
  `tools/capture/intro_full.zip`, correspondentes aos frames 104..840.
- A sequência de pacotes vai dos frames arcade 104..747: **644 frames do
  arcade → 635 frames NTSC SNES**, ajustando 61,035 Hz para aproximadamente
  60,099 Hz. Os frames 740..747 também usam os pacotes originais.
- A conversão preserva as cores RGB das capturas no passo de indexação; a
  redução de cor é a conversão física para BGR555. A largura é adaptada de
  384 para 256 por nearest-neighbor.
- O gerador pré-carrega tiles futuros e verifica a reconstrução de todos os
  quadros. Um leitor de pacotes em assembly executa os DMAs em VBlank.
- Na configuração verificada, o pico foi 3.264 bytes e 15 chamadas de DMA por
  pacote; o pacote inicial maior é carregado com a tela desligada.
- O teste no Mesen verificou VRAM, CGRAM, pixels renderizados e avanço de um
  quadro por atualização NTSC. A comparação de pixels considera a adaptação
  espacial e a conversão BGR555, não significa 384×224 nativos no SNES.
- A validação de pixels passou a considerar a latência de 1–3 quadros entre
  a VRAM recém-atualizada e a captura da imagem apresentada pelo Mesen.
- A música do stage começa no Start, como o comando arcade `0x20`, e não é
  reiniciada ao terminar a abertura.
- O efeito `0x0C` foi isolado com duas execuções determinísticas do MAME
  (`0x0C` e controle `0xFF`), reamostrado para 4 kHz e carregado como sétimo
  efeito SPC700. O Mesen confirmou atividade das vozes de efeitos na abertura.
  O disparo no Start ainda precisa de comparação temporal com o comando arcade.
- A tentativa de estender os pacotes de vídeo até o frame 840 falhou no frame
  SNES 640: faltaram 225 tiles, com orçamento de apenas 16 tiles por VBlank.
  A passagem agora usa **Mode 3 com duas camadas nativas**: BG1 guarda tiles
  8bpp da cidade/mar e avança por scroll horizontal; BG2 mantém céu, estrelas
  e HUD imóveis, com duas variantes para a piscada de NAMING. O gerador
  `tools/build_transition.py` extrai os dados das capturas 748..840; são
  91 atualizações NTSC, sem streaming de novos tiles da cidade por quadro.
- O teste `tools/test_transition.py` verifica tiles/mapas em VRAM, CGRAM, modo
  e scroll do PPU e compara capturas renderizadas com o arcade. Nos frames
  amostrados, a igualdade dos pixels adaptados ficou entre **88,1% e 97,4%**.
  A diferença inclui a amostragem horizontal fracionária (384→256), estrelas
  estáticas na camada fixa e pixels do cenário ainda simplificados.
- Os 16 KB iniciais de OBJ são enviados em 16 VBlanks durante a passagem.
  A inicialização do jogo é preparada com a última imagem ainda visível.
  O primeiro cenário nativo começa com câmera x=192/y=16 para aproximar a
  silhueta da cidade. A troca para os gráficos de gameplay ainda produz
  **até três frames pretos na ROM atual** (antes eram dois) e a última
  imagem fica retida alguns frames;
  portanto a emenda final não é perfeitamente contínua nem bit a bit fiel.
- O layout da VRAM do gameplay foi corrigido: a BG2 agora inicia em 0x5000
  (alinhamento de hardware) e a fonte da BG3 foi movida para 0x5800. Antes
  disso a BG2 lia tiles da fonte e poluía o cenário com caracteres.
- O topo do HUD nativo agora usa os 32 tiles de 8×8 extraídos do frame arcade
  748, com paleta própria; as letras e o HI 100000 coincidem em pixels com a
  abertura adaptada. A pontuação é composta em VRAM por dígitos reamostrados
  para 5 px. O rodapé de gameplay ainda contém WPN/LIFE nativos, não a
  piscada de NAMING da abertura.
- Um OBJ grande escondido em y=240 reaparecia no canto superior esquerdo por
  wrap vertical. Agora o ocultamento usa y=224 e preserva os bits de tamanho
  da OAM. A limpeza só reescreve slots que estavam visíveis; ocultar os 128
  sprites em todas as atualizações reduzia sensivelmente a cadência do jogo.
- Regressão após ajustar a câmera: começar em x=192 e pular as duas primeiras
  ondas deixava centenas de quadros sem inimigos. Agora apenas a onda em x=0
  é ignorada; a onda x=180 entra logo após a transição. Os tiros eram criados,
  mas descartados na rotina de colisão com itens mesmo com `power_count=0`;
  a varredura de itens/inimigos só ocorre quando há entidades ativas. O teste
  nativo e o cenário do Mesen verificam a onda, o projétil persistente e as
  entradas visíveis na OAM.
- A colisão foi ajustada para comparar diretamente os limites das caixas e
  separar as verificações de entidade ativa, invulnerabilidade e presença do
  P2. Antes, uma entrada inativa acusava contato com o jogador distante, e o
  caminho de P2 descartava tiros inimigos mesmo sem segundo jogador. Em
  `tools/test_combat.py`, o jogador mira e acerta a primeira onda (HP cai de
  6 a 0, +300 pontos); o tiro inimigo permanece ativo, tem sprite na OAM e
  pixels visíveis na captura antes de atingir o jogador. A primeira vida só
  é perdida quando o projétil de fato se aproxima. Isso não valida ainda
  todos os padrões de tiro ou as colisões com cenário do arcade.

### Chefe do stage 1

- A composição correta é 128×64, usando oito blocos de 32×32. Os dados anteriores
  tratavam partes espaciais da nave como quadros de animação.
- Há 128 frames de entrada, flashes de transição de 12 frames e sequência de
  morte de 80 frames.
- A resistência foi corrigida para **três fases de 20 acertos**, total 60.
  O byte `0x50` do template não devia ter sido interpretado como 80 HP.
- O controle vertical foi recuperado de `0x6A17..0x6B70`: comparação com a posição
  do jogador, passos de oito frames e limites verticais. Foi removido o seno
  inventado do protótipo.
- O disparo principal usa oito segmentos: pares superior, centrais e inferior,
  sprites 288..293, velocidades horizontais -4/-5 e verticais -2/0/+2.
- A primeira emissão e o intervalo observado de 96 frames foram reproduzidos a
  partir da captura de referência. O teste nativo confere movimento inicial e
  os descritores do disparo.
- **Ainda faltam os controladores auxiliares que liberam outros inimigos durante
  a luta**, e a validação de todas as variantes da cadência nas fases restantes.
  A posição horizontal no viewport SNES também continua sendo uma adaptação.

### Música

- O pipeline continua: ROM → MIDI e JSON com os mesmos eventos → IT → `smconv`
  → soundbank SPC700 e arquivos SPC independentes.
- Os timbres genéricos do template foram substituídos por samples dos nove
  patches FM efetivamente usados pelo stage 1 e pelo chefe.
- As referências foram sintetizadas no MAME a partir dos bytes originais do
  instrumento, com YM2203 a 4 MHz. Estão em `tools/capture/fm/`.
- A resolução temporal do IT passou de 12 para 3 ticks do sequenciador por linha.
  As seções agora saltam para o loop após a intro, em vez de repetir toda a intro.
- As ordens iniciais são geradas em `src/generated/music_orders.h`; não devem
  ser fixadas manualmente em `sound.c`.
- `music/stage1.spc` e `music/boss.spc` foram regenerados.
- O teste da abertura também verificou atividade das vozes de música no DSP.
- **Ainda é uma adaptação para SPC700**, não emulação FM bit a bit: samples têm
  uma nota de referência, sustain congelado e envelopes/timbres não são
  idênticos ao YM2203 em todas as notas. A quantização do tracker e seu clock
  também introduzem pequenas diferenças temporais.

## Arquivos principais para retomar

- `sidearms_snes/src/game.c`: armas, itens, cache OBJ, colisões, chefe e gameplay.
- `sidearms_snes/src/main.c`: título, abertura, carregamento e loop principal.
- `sidearms_snes/src/intro_dma.asm`: leitor rápido dos pacotes de DMA; também
  usado para as atualizações do cache de sprites.
- `sidearms_snes/src/game.h`: layout da VRAM e índices de corpos fixos.
- `sidearms_snes/src/sound.c`: integração SPC e ordens geradas.
- `sidearms_snes/tools/extract_gameplay.py`: tabelas de movimento, tiros,
  satélites e animações dos itens extraídas da ROM.
- `sidearms_snes/tools/build_object_atlas.py`: corpos fixos, gráficos dinâmicos,
  formas do jogador e paletas originais.
- `sidearms_snes/tools/build_intro.py`: indexação, cache com pré-carregamento,
  pacotes de vídeo e verificação offline da abertura.
- `sidearms_snes/tools/build_transition.py` e `tools/test_transition.py`:
  camadas nativas, cadência da câmera e comparação no Mesen.
- `sidearms_snes/tools/build_hud.py`: extrai o cabeçalho do frame 748 e
  prepara dígitos reamostrados para o placar nativo.
- `sidearms_snes/tools/test_combat.py`: acerto real na primeira onda, sprite
  e pixels do tiro inimigo, HUD comparado com a abertura, disparo segurado
  e instante de perda de vida no Mesen.
- `sidearms_snes/tools/extract_intro_sfx.py`: captura diferencial do efeito
  `0x0C` no MAME e conversão para WAV de 4 kHz.
- `sidearms_snes/tools/capture_fm.py`, `tools/fm_bank.py` e `tools/midi_to_it.py`: samples FM e módulo IT.
- `sidearms_snes/tools/mame/`: capturas e probes do arcade.
- `sidearms_snes/tools/ghidra/SidearmsFidelity.java`: exportação de instruções
  das rotinas investigadas; ainda pode ser generalizada para selecionar faixas.

## Comandos de build e validação

Executar dentro de `sidearms_snes/`:

```sh
make
make check-gameplay
python3 tools/test_intro.py --out /tmp/sidearms-intro-qa
python3 tools/test_transition.py --out /tmp/sidearms-transition-qa
python3 tools/test_combat.py --out /tmp/sidearms-combat-qa
python3 tools/test_emulator.py --out /tmp/sidearms-game-qa
```

Regeneração dos dados:

```sh
make assets-from-rom
make intro-assets
python3 tools/extract_intro_sfx.py
python3 tools/make_sfx_it.py
make audio-from-rom
make
```

O teste `test_emulator.py` concede invulnerabilidade e adianta o scroll para
exercitar o chefe. São condições de teste, não alterações de cheat na ROM.
Os testes consultam os endereços no `.sym` da build; não reutilizar endereços
fixos de dumps antigos após mudanças no layout da WRAM.

### Testes confirmados na sessão

- Build sem avisos ou erros nas últimas compilações verificadas.
- Regressões nativas: colisões, dano, placar, coleta, seleção, níveis,
  velocidades, tiro para ambos os lados, segmentação do laser, shotgun,
  repetição ao segurar disparo, cache de gráficos e movimento inicial do chefe.
- Teste de layout de objetos 32×32 do SNES.
- Mesen: inimigos e tiros visíveis logo após a transição, tiro esquerdo,
  nascimento do chefe e capturas dos cenários. Combate sem invulnerabilidade
  artificial: dano ao inimigo, tiro inimigo em movimento/pixels/OAM e perda
  de vida somente após o projétil alcançar o jogador. Topo do HUD comparado
  pixel a pixel com a abertura e ausência do OBJ fantasma no canto.
- Abertura: igualdade dos pixels adaptados, VRAM e CGRAM; um avanço por frame
  NTSC; atividade das vozes de música e do efeito `0x0C`. Entrada do cenário:
  mapas/scroll nativos, sprites pré-carregados e comparação de frames no Mesen.

Os últimos logs de cenário mostraram trechos de 60 atualizações/s, mas ainda
há trechos próximos de 48–53 atualizações/s. **Não declarar 60 fps constantes
para todo o gameplay.**

## Diferenças que impedem chamar o port de totalmente fiel

1. Ondas e IA dos inimigos comuns ainda usam a tabela `waves[]` e movimentos
   simplificados do protótipo. É necessário portar os scripts/threads reais,
   a câmera e as colisões com o cenário.
2. Faltam os inimigos auxiliares liberados pelo chefe e a validação das fases
   restantes de seus controladores de ataque.
3. A entrada por scroll foi portada, mas a emenda final ainda apresenta até
   três frames pretos na ROM atual e o ajuste 384→256 não é idêntico em cada pixel.
   O efeito `0x0C` já toca no SPC, mas o banco de sete SFX e seu mapeamento
   ainda são incompletos; não declarar que todos os eventos já são fiéis.
4. Fusão Alpha/Beta e benefícios especiais foram adicionados nesta entrega.
   Falta comparação integral do modo cooperativo e refinamento da aproximação
   do parceiro; consultar o registro prioritário acima.
5. Ainda há quedas de frequência; é preciso medir os trechos pesados e otimizar
   simulação/renderização sem alterar as regras originais.
6. O movimento do starfield usa parallax simplificado, embora seu padrão seja
   extraído da ROM.
7. Há limitações de paletas simultâneas: dois bancos podem ser usados por itens
   em 1P, um deles fica reservado ao P2 quando ele está ativo. Se houver mais
   grupos de cor concorrentes do que bancos disponíveis, existe fallback de cor.
8. O áudio SPC é uma adaptação por samples; não é FM bit a bit.
9. Somente o stage 1 é jogável; não é um port completo de todos os estágios.

## Preferência visual pendente

Foi perguntado ao usuário se prefere adaptar 384×224 para 256×224, recortar
mantendo os pixels ou usar alta resolução com margens. Não houve resposta até
a criação deste arquivo. Por enquanto foi mantida a adaptação 256×224 existente;
não interpretar silêncio como aprovação de uma mudança de arquitetura.

## Evidências e ferramentas locais

A cópia completa do driver MAME está em
`sidearms_snes/docs/mame/sidearms.cpp`; ela contém a lógica de vídeo e do
starfield, não apenas o mapa de memória.

Os dados extraídos e probes duráveis estão em
`sidearms_snes/tools/capture/fidelity/` e as referências FM em
`sidearms_snes/tools/capture/fm/`.

Durante esta sessão o Ghidra/projeto estavam em:

- `/tmp/opencode/ghidra_install/ghidra_12.2_PUBLIC/`
- `/tmp/opencode/ghidra_proj/sidearms.gpr`
- `/tmp/opencode/ghidra_out/decompiled_bank2.c`
- JDK: `/tmp/opencode/jdk25`

Esses caminhos em `/tmp` podem não persistir. O script de análise e os assets
extraídos estão no projeto. Para executar o Ghidra com cache gravável nesta
sandbox, foi usado `JAVA_TOOL_OPTIONS=-Duser.home=/tmp/sidearms-ghidra-home`,
criando esse diretório previamente, e `JAVA_HOME=/tmp/opencode/jdk25`.

## Próxima sequência recomendada

1. Reexecutar os testes na ROM atual antes de novos trabalhos.
2. Refinar a emenda final da passagem (três frames pretos na ROM atual) e a amostragem
   horizontal fracionária; manter o scroll nativo em vez de voltar ao cache
   de vídeo que excede o VBlank.
3. Recuperar os scripts das ondas do stage 1 e os controladores auxiliares do
   chefe; evitar adicionar novas aproximações baseadas em seno ou aleatoriedade.
4. Usar os probes do arcade como oráculo para comparar posições, sprites,
   acertos e intervalos frame a frame.
5. Medir os frames lentos com callbacks de execução do Mesen e otimizar os
   trechos responsáveis. A lista compacta de projéteis já foi implementada.
6. Validar 2P, fusão e itens especiais separadamente; não concluir fidelidade
   completa apenas porque a ROM compila ou porque um cenário acelerado passou.
