# Chefes grandes e meta de 30 atualizações/s

ROM validada: `snes/sidearms_md_snes.sfc`.
SHA-256: `db4ffc5c5eaa3449e45eb139bdc248de79c0b1c0d2a6e4a43500faa02e20ec7a`.

## Correção das pausas

As rodas reconstruíam o mapa BG2 em C a cada troca de imagem. No ensaio
Home da seção 2 isso causava 104 intervalos de 34 quadros em 6.000 quadros
de vídeo. O gerador `tools/build_wheels.py` agora prepara as três imagens
de cada variante Arcade/Home e a união de seus padrões. O runtime carrega
esses padrões uma vez e envia um mapa de 2.048 bytes por troca de imagem.
O mapa e o scroll são aplicados no VBlank, junto da configuração do parallax.

O cenário comum também ganhou lookup de metatiles, LRU e expansão de células
em 65816. A fila de DMA divide descritores grandes para aproveitar o orçamento
disponível sem ultrapassar o VBlank. Dados transitórios continuam tendo uma
cópia própria na fila; mapas persistentes só mudam antes do respectivo flush.

Os caminhos comuns de atualização e desenho de inimigos, tiros e segmentos do
chefe final usam 65816. Os controles de animação e callbacks da IA continuam
seguindo os dados originais. A lista de tiros usada pelos chefes é montada por
atualização e revalida os tiros consumidos antes de cada consulta. O contato
confere novamente o estado dos jogadores antes de aplicar dano.

## Resultados reproduzíveis

Snes9x NTSC, resultados normalizados a 60 quadros de vídeo/s. Os testes usam
warps e invulnerabilidade de QA; os chefes permanecem ativos, sem auto-hit
nos ensaios de desempenho. O disparo repetido alterna o botão a cada dois
ticks lógicos para gerar novos tiros.

- Roda Home, seção 2, 6.000 quadros: **13,34 → 42,78 atualizações/s**.
  Nenhuma pausa recorrente de 34 quadros; uma carga inicial de 11 quadros.
- Roda Home, seção 8, 6.000 quadros: **37,10/s**, maior intervalo de 5 quadros.
- Chefe final, disparos repetidos, 6.000 quadros: **30,70/s**,
  maior intervalo de 3 quadros, chefe ainda ativo ao final.
- Home com parallax, seções 1/3/5/6, 1.500 quadros por seção:
  **47,12 / 46,12 / 38,68 / 30,08/s**.
- Home com parallax desligado pelo menu, mesmas seções:
  **32,48/s ou mais**.
- Treze entradas de seção/chefe, 650 ticks por caso:
  **38,69–48,69/s**, total de 11.255 quadros para 8.450 ticks.
- Referência Arcade, primeira seção, 3.000 quadros: **51,04/s**.
- Menu: **48/s**. Intro: **58,52/s**, preservando suas 15 imagens.

Essas amostras apresentaram zero DMA tardio e zero overflow. Os ensaios Home
e da primeira fase também verificam ausência de quadros pretos. Os testes do
parallax comparam pixels, cores e transições com os dados MD; os testes nativos
comparam memória e efeitos das rotinas com C ou modelos independentes.

## Comandos e evidências

```sh
make all
make check-native
make check-boss-performance
make check-sections check-performance check-parallax check-ui
make check-items check-player-bounds check-options check-frontend
make check-audio check-ending check-campaign check-rush
```

Relatórios em `build/qa/`: `boss-performance.json`,
`boss2-before-matched.json`, `boss2-after-matched.json`, `sections.json`,
`parallax-home-on.json`, `parallax-home-off.json`, `performance-after.json`,
`ui-menu-after.json`, `ui-intro-after.json` e os relatórios diferenciais
`*-native.json`, `enemy-pool.json`, `weapon-update.json`.

Os testes de campanha, final e Boss Rush usam também vidas e/ou auto-hit,
conforme registrado em seus JSONs. Eles verificam progressão, não desempenho
de uma partida sem auxílio. Os limites acima são médias dos cenários
descritos: ainda pode haver atualizações acima de dois quadros em combates
mais carregados e cargas de gráficos nas transições. Não há certificação
de 30/s em toda combinação de inimigos/armas nem validação em hardware real.
