# Side Arms MD → SNES

Port nativo **em desenvolvimento** do código de
[rester159/side-arms-MD](https://github.com/rester159/side-arms-MD). Este
repositório é um fork do port MD: o código de referência está na **raiz do
próprio fork** (`src/`, `inc/`, `tools/`, `res/generated/`), sem submódulo.

A ROM deste trabalho é **`snes/sidearms_md_snes.sfc`**. A pasta
`sidearms_snes/` faz parte do repositório e fornece os módulos de áudio `.it`
já extraídos, necessários para o build SNES.

O build MD original continua disponível em **`Makefile.md`** (`make -f
Makefile.md` ou `make md-rom`). O `Makefile` da raiz compila o port SNES.

## Compilar e executar

Requer Python 3 com `numpy` e `Pillow`, PVSnesLib/816-tcc/WLA-DX. Os 27
arquivos do conjunto arcade World em `rom/` e os módulos `.it` de
`sidearms_snes/` acompanham o repositório. Cada arquivo é verificado pelo
SHA-256 do manifesto original.

**Atenção:** esses arquivos são proprietários e foram incluídos para tornar o
fork autocontido. Verifique se você tem direito de redistribuí-los antes de
publicar ou compartilhar o repositório.

```sh
make                       # extrair, converter e compilar
make check                 # bytes da ROM + boot/menu/início de partida/áudio
make check-sections        # entradas nas dez seções e nos doze chefes
make check-frontend        # Home, SRAM após reset, entrada e controle do P2
make check-rush            # Boss Rush até o resultado, com hooks de QA
make check-campaign        # campanha com invulnerabilidade/vidas/auto-hit
make check-audio           # músicas longas e trocas de módulo no SPC700
make check-ending          # chefe final, textos finais, ranking e reset com hooks
make check-render          # sprite parcialmente fora da borda esquerda
make check-options         # opções, controles, Sound Test e persistência
make check-items           # portador -> cápsula -> coleta -> robô e oito tiros
make check-performance     # cadência lógica, quadros pretos e orçamento de VBlank
make check-collision       # 1.500 casos independentes das rotinas 65816 de contato
make check-native          # ticks, ações de contato, sprites, recorte e LRU
make check-ui              # navegação nos menus e introdução com as 15 imagens
make check-parallax        # estrelas por faixas/colunas, caverna e Home ON/OFF
make check-boss-performance # rodas Home e chefe final com disparos repetidos, meta 30/s
make run                   # abrir esta ROM no Snes9x/RetroArch
```

O SDK padrão é `../pvsneslib-sdk-4.6`. Para outro local:
`make PVSNESLIB_HOME=/caminho/do/sdk`. `SIDEARMS_SOURCE` permite selecionar outro
diretório com o conjunto arcade. Os arquivos de áudio utilizados ficam em
`sidearms_snes/res/sfx.it` e `sidearms_snes/music/cmd*.it`.

`tools/prepare_music.py` reorganiza os módulos em `build/music/`, preservando
notas, linhas e destinos dos saltos. Isso é necessário porque os arquivos
fornecidos chegam a 96 padrões, enquanto o SNESMOD possui uma tabela de 64.
Os módulos originais são preservados. Execute uma compilação por vez; os
testes Python podem ser executados separadamente sobre a mesma ROM pronta.
Os efeitos convertidos descartam apenas zeros finais das gravações, mantendo
os demais samples iguais; isso evita invadir a página reservada ao eco do DSP.
`tools/test_music.py` verifica notas, duração, saltos e esse corte de silêncio.

O protótipo **isolado** de SA-1 é compilado e testado com
`python3 tools/sa1_probe.py`. Ele gera `build/sa1_probe/sa1_probe.sfc`, executa
no coprocessador a parte geométrica da colisão dos projéteis com os inimigos
(16 × 18 pares) via I-RAM compartilhada. O SA-1 recebe dois lotes distintos
em sequência sem reiniciar; seus 288 resultados por lote são comparados com o
CPU principal e uma referência independente no Snes9x e no Mesen. Com
`python3 tools/sa1_probe.py --benchmark`, o Mesen mede também os quadros de
varredura usados pela cópia de entrada, pelo cálculo no CPU principal, pelo
SA-1 incluindo acionamento/espera e pela cópia de saída. No lote de teste,
o CPU principal gastou 134 e 132 linhas nos dois cálculos, o SA-1 com
acionamento/espera 57 em cada um; copiar 272 bytes de entrada e 576 bytes
de saída custou cerca de 29 + 36 linhas por chamada.
O ganho de ponta a ponta para **esse lote isolado** é, portanto, de apenas
134 / (29 + 57 + 37) ≈ 1,09×, antes de integrar a rotina ao jogo.
Ao abrir a ROM do protótipo, a tela verde com `SA-1 OK` indica sucesso;
uma tela vermelha indica timeout. O teste também gera
`build/sa1_probe/sa1_probe.png` para conferir a imagem. A ROM principal não é
alterada. Antes do experimento, uma cópia local
da ROM principal foi preservada em
`build/backups/sidearms_md_snes_pre_sa1_565a23b7.sfc` (SHA-256
`565a23b701dff77092ca3d141158a7bbc83a421c7978507c650ce69c3fd6de81`).
O protótipo não altera o jogo: colisões reais dependem da ordem das atualizações,
do estado dos projéteis após cada acerto e da movimentação dos inimigos, não
representados por essa etapa geométrica isolada. O FPS da ROM principal não muda.

## Ghidra

Foi instalada uma cópia local do Ghidra 12.2 em
`tools/local/ghidra_12.2_PUBLIC`. O projeto está em
`build/ghidra/SidearmsMDPort.gpr`; o relatório real de desmontagem e
decompilação estão em `build/analysis/bank0.bin.txt` (CPU principal arcade) e
`build/analysis/sound.bin.txt` (CPU de áudio e tabela de comandos).

`make analyze` repete a importação Z80 com o script
`tools/ghidra/SidearmsPortAudit.java`. É necessário JDK 25; `GHIDRA_HOME` e
`GHIDRA_JAVA_HOME` permitem indicar outras instalações. O JDK 25 local fica
em `tools/local/jdk25`. Os caches são gravados em
`build/` para evitar a quota esgotada do diretório temporário da máquina.

## Implementação e limites atuais

`tools/prepare_snes.py` adapta as fontes C de jogadores, armas, inimigos,
chefes, fases e fluxo do MD. Os módulos nativos em `snes/src/` implementam
PPU, cache de tiles, OAM, controles, SRAM e SPC700. Não há emulação de 68000
ou Z80 no runtime. `build/source_manifest.json` registra as fontes de origem.

O backend mantém as coordenadas lógicas de 320×224 e exibe os 256 pixels
centrais. Os controles padrão são Y para disparar à esquerda, B à direita,
A para trocar arma, L/R para anterior/próxima arma, X para travar disparo
e Start para crédito/início. O mapeamento lógico do MD permanece configurável.

**Este ainda não é um port completo nem certificado como fiel.** O desempenho
atinge 38,69–48,69 atualizações lógicas/s nos 13 cenários de seções/chefes
de referência, mas ainda não mantém 60/s. O HUD precisa de revisão visual integral em 32 colunas.
O áudio usa os módulos locais e uma
tradução parcial dos comandos de efeitos; não reproduz integralmente o driver
YM2612/PSG do MD. A música $38 (demonstração de patches do Sound Test) ainda
excede a RAM do SPC700; a verificação de orçamento impede seu carregamento
para evitar travamento. A cobertura de entradas de fase não substitui uma
partida normal completa e uma comparação com o MD.

Os testes de Home, SRAM após reset e entrada/movimento do segundo jogador
passaram. O Boss Rush alcançou o resultado com os doze chefes usando os hooks
de QA. O teste isolado do chefe final percorreu parabéns e staff, retornou ao
aviso inicial e confirmou o ranking após reset. A campanha completa percorreu
as dez seções e retornou ao aviso com os mesmos hooks de QA: invulnerabilidade,
vidas extras e auto-hit dos chefes. Os JSONs incluem o SHA-256
da ROM para identificar a versão testada.

A verificação da PPU compara o mapa e os tiles de fonte do Sound Test com os
dados preparados, além dos sprites dos dois jogadores e de um cenário. A
rotina `native_offset` em 65816 preserva o avanço de banco em acessos acima de
64 KiB; a expressão de ponteiro equivalente do 816-tcc descartava esse avanço.
Os arrays menores são posicionados integralmente dentro de um banco.

O cenário agora transfere apenas as bordas novas quando a câmera avança um
metatile, mantendo a reconstrução integral para mudanças de zona ou saltos.
O cache de sprites pequenos indexa diretamente código e cor em WRAM e o OAM
usa uma tabela de máscaras em vez de deslocamentos variáveis. A colisão de
projéteis usa limites diretos. Essas mudanças preservaram a bateria de seções,
mas não resolveram o custo total da lógica e da renderização geradas pelo
compilador 816-tcc; atingir 60 atualizações/s ainda requer trabalho substancial
nesses caminhos. O driver de áudio também continua pendente.

O parallax Home foi portado: quatro profundidades de estrelas por faixas,
deslocamento vertical por colunas nas seções 3/6, textura distante da caverna
na seção 5 e variantes Home dos cenários/rodas. As velocidades, as regiões
e a compensação de cortes de câmera seguem os dados do MD. O SNES usa
HDMA no canal 7 para o deslocamento horizontal do BG3; nas colunas, mapas
pré-convertidos para oito fases verticais preservam os pixels e cores sem
renderização de pixels em tempo real. Mapas, scroll e HDMA são comprometidos
no VBlank. As cores do cenário usam CGRAM 64..95, deixando espaço para as
combinações de cores das estrelas no BG3. Arcade e PARALLAX OFF conservam
o movimento simples. Não foram ativadas faixas de montanhas: elas também
estão desativadas na referência MD.

`check-parallax` compara os pixels de estrelas renderizados com a ROM MD,
confere a textura da caverna, paletas, tiles adicionais das rodas e transições
entre os modos, incluindo cortes de câmera e desligamento. Os 12 casos
passaram no Snes9x. A amostra Home de 1.500 quadros por seção (1/3/5/6),
com invulnerabilidade e warps de QA, mediu 47,12 / 46,12 / 38,68 / 30,08
atualizações/s com o efeito ligado, sem quadros pretos, DMA tardio ou overflow.
Com o efeito desligado pelo menu, os quatro cenários mantiveram o modo simples.
Os quatro cenários Home e os 13 cenários Arcade agora exigem pelo menos 30/s
nos testes. Esses ensaios não substituem uma
campanha completa nem testes em hardware real.

A cena de referência da primeira seção alcança **51,04 atualizações/s**,
medidas em 3.000 quadros de vídeo com invulnerabilidade e sem disparo do
jogador. A medição anterior à meta de 30/s era 25,72/s; a inicial, 15,06/s.
A navegação pelos menus, para os mesmos 80 ticks de entrada, passou de
470 para 100 quadros de vídeo (**10,21 para 48 atualizações/s**). A sequência
da Terra na introdução, até entrar na fase após confirmar o nome, passou de
1.753 para 365 quadros (**12,18 para 58,52 atualizações/s**), preservando as
15 imagens e os temporizadores originais. São medições em Snes9x NTSC,
normalizadas a 60 quadros de vídeo/s.

**30/s é a meta das amostras de referência, não um mínimo garantido em toda partida.**
Nos 13 cenários de seções/chefes, os mesmos 8.450 ticks passaram de 24.835
para 11.255 quadros de vídeo. O chefe final com disparos repetidos mediu 30,70/s
em 6.000 quadros, mantendo o chefe ativo. A amostra de gameplay manteve zero
quadros pretos, zero DMA tardio, zero overflow e zero timeout de áudio.

O DMA lê gráficos imutáveis diretamente da ROM e copia dados transitórios
para WRAM. Os lotes respeitam o orçamento restante do VBlank; o laço pode
aproveitar um VBlank iniciado, mantendo no máximo um commit lógico por
VBlank. Os mapas da introdução já estão no formato SNES 32×28 na ROM e
são enviados atomicamente. Os menus redesenham apenas as linhas alteradas;
o HUD usa um índice de glifos validado e um mapa de posições pré-calculado.
Movimento, contato, contagem por faixa, busca/LRU e submissão de sprites
usam caminhos nativos 65816, com os caminhos gerais em C preservados.

As três imagens das rodas gigantes são preparadas durante a construção da ROM.
Os padrões ficam residentes durante o encontro; cada rotação troca apenas o mapa
BG2 de 32×32 células. No ensaio Home da seção 2, com os mesmos 6.000 quadros
e hooks de QA, a vazão passou de 13,34 para 42,78/s. As 104 pausas recorrentes
de 34 quadros desapareceram; resta uma carga inicial dos padrões de 11 quadros.
O DMA pode dividir um descritor entre VBlanks e aproveitar o orçamento restante,
reservando tempo para OAM, paleta e scroll. Os testes diferenciais de memória,
terreno, animações, contatos, armas e desenho comparam os caminhos 65816 com C
ou com os dados de origem. Detalhes em [docs/PERFORMANCE_BOSSES.md](docs/PERFORMANCE_BOSSES.md).
As funções simples de coordenadas são expandidas no ponto de uso.

Os testes comparam 1.500 casos de geometria, cadência, terreno e snapshot de
tiros com uma referência independente; 1.000 ticks/ações de contato e
1.200 submissões de sprites com seus caminhos em C; e 1.200 casos de cache
com a regra original de LRU. A escrita das 1.120 células lógicas do painel
também coincidiu com a implementação C da ROM anterior. Os testes de PPU,
itens, transformação, oito tiros, opções, final e ranking após reset
complementam essas verificações.

As evidências de execução ficam em `build/qa/` e os logs em `build/`. Os testes
de seção usam invulnerabilidade e o hook `dbg_warp` original; suas capturas
não representam uma partida completa sem intervenção.
