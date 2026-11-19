# Diagnóstico trimestral de turnover (RH, Vantel Serviços)

Projeto de análise de dados de RH. A cada trimestre o usuário atualiza os CSVs em `DADOS/` e pede **"roda o diagnóstico do trimestre"**. A entrega é um dashboard para a diretoria, um relatório de diagnóstico e as listas de apoio, tudo arquivado em `ENTREGAS/<período>/`.

Idioma de trabalho: português do Brasil, em tudo (respostas, HTML, comentários). A base é sintética (empresa fictícia), e os HTMLs avisam isso no cabeçalho. Se o usuário disser que passou a usar dados reais, remover "base sintética" dos dois templates.

## Quando o usuário disser "roda o diagnóstico do trimestre"

Execute estes passos, nesta ordem, sem pedir confirmação (só pergunte se algo bloquear):

1. **Confirmar que os dados novos estão em `DADOS/`.** São 5 CSVs com os mesmos nomes de sempre, cumulativos desde jan/2023 (não só o trimestre novo). Se o último mês do `historico_mensal.csv` for igual ao da última entrega em `ENTREGAS/`, avise que parece não ter dado novo e pergunte antes de seguir.
2. **Rodar o pipeline**, da raiz do projeto (a pasta tem espaço no caminho, use aspas):
   ```
   python3 -I src/rodar_diagnostico.py
   ```
   Ele confere os brutos, trata, calcula, gera os dois HTMLs e arquiva em `ENTREGAS/<período>/` (por exemplo `2026-T3`). Se parar com erro, **leia a mensagem e conserte a causa**: não contorne, não apague checagem, não force. As causas típicas estão em "Quando o pipeline para".
3. **Ler o resultado**: `comparativo.md` (variação contra o trimestre anterior e mudanças qualitativas), `log_limpeza.csv` (o que foi corrigido), `resumo.json` e os avisos que o script imprimiu.
4. **Fazer a revisão de julgamento** (seção "O que exige julgamento a cada trimestre").
5. **Verificar os HTMLs** renderizados no Chrome, sem erro de JavaScript e sem `undefined` ou `NaN` no texto (comando em "Verificação dos HTMLs").
6. **Responder ao usuário** com: período coberto, os números principais e a variação contra o trimestre anterior, o que mudou de qualitativo (gestores, área crítica, fatores), avisos e regras novas de tratamento, e onde estão os arquivos. Estilo na seção "Como responder".

Não faça commit nem push sem o usuário pedir, e não publique como Artifact a menos que ele peça (a entrega padrão são arquivos locais). Este projeto é um repositório Git (`github.com/ricardopjm/analise-turnover-rh`, portfólio público). Para publicar um novo trimestre, o usuário pede, e o commit leva `DADOS/`, `ENTREGAS/<período>/` e `docs/`.

## Estrutura de pastas

```
CLAUDE.md
README.md, LICENSE, .gitignore
DADOS/               entrada: 5 CSVs brutos. NUNCA editar. O dicionário completo (local, não versionado) também fica aqui
DADOS_TRATADOS/      saída da limpeza (regerada a cada execução, fora do Git)
RESULTADOS/          JSONs e HTMLs de trabalho (regerados a cada execução, fora do Git)
ENTREGAS/<período>/  arquivo permanente de cada trimestre (não apagar)
docs/                páginas do GitHub Pages (cópia mais recente dos 2 HTMLs, index.html), dicionario_de_dados.md público, img/
src/                 código (Python padrão, sem pandas/numpy)
src/legado/          versão antiga, fora do pipeline e do Git
src/utilitarios/     ferramentas de teste
```

Ignore os arquivos `._*` (metadados do macOS em disco exFAT). Não os liste nem os copie.

`ENTREGAS/<período>/` contém: `dashboard_turnover.html`, `relatorio_turnover.html`, `abaixo_do_piso.csv`, `comparativo.md`, `resumo.json`, `log_limpeza.csv`, `rejeitados.csv`, `log_execucao.txt` e `dados_brutos/` (cópia dos CSVs daquela execução, para reproduzir; essa subpasta fica fora do Git). O pipeline também copia os dois HTMLs para `docs/`, que alimenta o GitHub Pages. As imagens `docs/img/*.png` do README são capturas dos HTMLs em tema claro e precisam ser refeitas à mão quando o visual mudar. O nome do período é `AAAA-T1..T4` quando o último mês fecha um trimestre, senão `AAAA-MM`.

## Dados de entrada

Todos usam `;` como separador. A chave de ligação é `colaborador_id`.

| Arquivo | Uma linha é | O que traz |
|---|---|---|
| `colaboradores.csv` | uma pessoa (foto atual) | área, cargo, nível, gestor, admissão, desligamento (vazio = ativo), salário atual, modalidade, cidade/UF, nascimento, data da última promoção |
| `historico_mensal.csv` | uma pessoa em um mês | `horas_extras`, `faltas_dias`. Só existe nos meses em que a pessoa estava na empresa. O último mês de quem saiu é o mês do desligamento |
| `pesquisa_clima.csv` | uma resposta em uma rodada (jun e dez) | `enps` (0 a 10), satisfação com gestor, salário e carreira (1 a 5). Cerca de 72% respondem |
| `desligamentos.csv` | uma saída | tipo (Voluntario/Involuntario), motivo, aviso prévio |
| `faixas_salariais.csv` | um cargo + nível (9 linhas) | piso, média e teto da faixa |

Relações: cadastro 1:1 com desligamentos (as pessoas com data de desligamento no cadastro são exatamente as do arquivo de desligamentos); cadastro 1:N com histórico e com pesquisa; faixas ligam por **cargo + nível**.

**O que a base não responde**: causa (só associação), evolução salarial ou reajustes, desempenho individual, custo real de reposição, movimentações internas, diversidade, hierarquia acima dos gestores (os `G###` não são colaboradores), e quem saiu antes do primeiro mês do histórico.

`DADOS/dicionario_de_dados_rh.md` (só local, não versionado) descreve as colunas, mas **também traz material de referência com as respostas esperadas da análise**. Use só a descrição das colunas. Não use esse material como fonte de verdade nem para direcionar conclusões: todo número deve vir dos dados, e onde a análise divergir dele, vale a análise. A versão pública, só com a descrição das colunas, é `docs/dicionario_de_dados.md`: **nunca publique o arquivo completo, nem cite o conteúdo desse material no README, nos HTMLs ou em commits**.

## Regras de tratamento (`src/limpeza_rh.py`)

O script lê `DADOS/` (detecta UTF-8 ou ISO-8859-1), grava `DADOS_TRATADOS/` em UTF-8 e registra tudo em `log_limpeza.csv`. Linhas descartadas vão para `rejeitados.csv`.

| Arquivo | Regra |
|---|---|
| colaboradores | remove linhas duplicadas exatas; salário em texto (`R$ 4.500,00`) vira número; área `TI`/`T.I.` vira `Tecnologia`, `Operações` vira `Operacoes`; cargo em Title Case sem espaços; modalidade padronizada em `Presencial`/`Hibrido`/`Remoto` (`Home Office` = Remoto); gestor em branco vira `gestor_id = NI` e `gestor = Nao informado`; datas para AAAA-MM-DD |
| colaboradores | se a data de desligamento do cadastro diverge da de `desligamentos.csv`, **vale o arquivo de desligamentos** (resolveu desligamento anterior à admissão) |
| historico_mensal | mês misto (`2024-03`, `abr/24`) vira `AAAA-MM`; `faltas_dias` em texto (`2 dias`) vira inteiro; remove duplicatas; remove linhas de colaborador que não existe no cadastro (vão para `rejeitados.csv`); **horas extras negativas viram vazio**, mantendo a linha para não perder as faltas |
| pesquisa_clima | `enps` em texto (`8 - nota 8`) vira inteiro; `satisfacao_gestor` em rótulo vira 1 a 5 (Discordo totalmente = 1, Discordo = 2, Neutro = 3, Concordo = 4, Concordo totalmente = 5); `satisfacao_carreira` em branco **fica em branco** (sem imputar) |
| desligamentos | `tipo` padronizado em `Voluntario`/`Involuntario`; datas para AAAA-MM-DD |
| faixas | copiada sem alteração |

Outliers de horas extras (acima de 60 h/mês) são mantidos. Calcular médias com atenção a eles.

**Valores novos nunca são adivinhados.** Se aparecer uma modalidade, área, rótulo de satisfação ou formato de data que a regra não conhece, o script falha de propósito. Estenda a regra em `limpeza_rh.py`, rode de novo, e registre a decisão em "Histórico de decisões" abaixo. O orquestrador também avisa quando surge uma área nova.

## Definições (valem em todos os scripts)

- **Período**: do primeiro ao último mês do `historico_mensal.csv` tratado. Nada de datas fixas no código: o período, os anos e a data de referência (último dia do último mês) vêm de `src/periodo.py`.
- **Headcount do mês**: pessoas ativas no início e no fim do mês, e a média das duas.
- **Turnover** = saídas ÷ headcount médio, anualizado (× 12 ÷ número de meses do recorte). Anos parciais, como o ano corrente no meio do ano, são anualizados pelos meses que existem e rotulados "(N meses)".
- **Voluntário** = pedido de demissão (`tipo = Voluntario`). **Involuntário** = o restante.
- **Custo estimado das saídas** = **3 vezes o último salário** de cada pessoa desligada (premissa do usuário para reposição). É estimativa, nunca custo contábil, e isso deve estar escrito onde aparecer.
- **eNPS** = % promotores (9 e 10) − % detratores (0 a 6), por rodada. O "eNPS geral" do dashboard é o da rodada mais recente.
- **Abaixo do piso** = salário atual menor que `faixa_min` do cargo + nível.
- **Inversão salarial** = entre ativos, comparar quem tem menos de 1,5 ano de casa com quem tem mais de 4 anos, no mesmo cargo e nível (mediana do salário ÷ faixa média).
- **Eventos medidos antes da saída**: o modelo de risco usa um painel pessoa-mês e só fatores observáveis antes do mês da saída (horas extras e faltas dos 3 meses anteriores; eNPS da pesquisa mais recente, até 200 dias antes).
- **Saída em 6 meses após a pesquisa** (gráfico eNPS × desligamento do dashboard): só entram respostas com 183 dias completos de acompanhamento até a data de referência.
- **Gestor crítico** (regra automática): saídas voluntárias pelo menos 1,5× o esperado para a área **e** chance de acaso (Poisson) abaixo de 5%. A lista não é digitada: muda sozinha a cada execução. O teste mais rigoroso (corrigido por comparar todos os gestores) é sinalizado em `bonf`.
- **Área crítica**: a de maior taxa anual no período (hoje Atendimento).
- **Classificação de fator** (modelo com todos os fatores juntos, razão de chances com IC 95%): **forte** se o limite inferior do IC é ≥ 1,4; **moderado** se o IC exclui 1; **protetor** se o IC fica todo abaixo de 1; **sem efeito claro** se o IC cruza 1.
- **Tendência**: taxa dos últimos 12 meses contra os 12 anteriores. Diferença menor que 1,5 ponto percentual é "estável".

## O que cada script faz

Executados nesta ordem pelo `src/rodar_diagnostico.py`:

| Script | Faz |
|---|---|
| `periodo.py` | caminhos e período, derivados dos dados. A variável de ambiente `DIAG_RAIZ` troca a pasta raiz (uso em testes) |
| `limpeza_rh.py` | tratamento (acima) |
| `turnover.py` | headcount e saídas por mês, por tipo, por área e por modalidade, e modalidade dentro e fora da área crítica. Gera `RESULTADOS/turnover.json` |
| `salario_faixa.py` | inversão salarial, posição na faixa e relação do piso com demissão voluntária. Imprime o diagnóstico e grava `abaixo_do_piso.csv` |
| `base_analitica.py` | monta o painel pessoa-mês (usado pelos dois geradores abaixo) |
| `modelo.py` | regressão logística em Python puro |
| `dados_relatorio.py` | todos os números do relatório: gestores, fatores, excesso atribuível, piso, eNPS, quadro atual |
| `gerar_relatorio.py` | injeta os números em `relatorio_template.html` e grava `relatorio_turnover.html` |
| `dados_dashboard.py` | números do dashboard: KPIs, mensal, área, modalidade, gestores, salários por faixa, eNPS |
| `gerar_dashboard.py` | injeta em `dashboard_template.html` e grava `dashboard_turnover.html` |
| `rodar_diagnostico.py` | orquestra, confere, compara com o trimestre anterior e arquiva |

Os dois HTMLs são **arquivos únicos**, com dados embutidos e sem dependência de internet (o relatório usa fontes do Google se houver rede, e cai para a fonte do sistema se não houver).

## Entregáveis

1. **`dashboard_turnover.html`**, para apresentar à diretoria de RH. Topo: headcount atual, turnover do período, turnover voluntário, custo estimado das saídas (3× salário) e eNPS geral. Depois: evolução mensal, turnover por área, comparação entre modalidades (com filtro que separa a área crítica), ranking de gestores com maior saída do time, salários contra as faixas do cargo (um ponto por pessoa ativa) e eNPS × desligamento. Nenhum nome de colaborador aparece (só gestores).
2. **`relatorio_turnover.html`**, diagnóstico com os achados: dimensão, quanto cada fator multiplica o risco, quantas saídas cada fator explica, achados com evidência, peso e ação, o que é fraco ou coincidência, prioridades e limitações.
3. **`abaixo_do_piso.csv`**: lista **nominal** das pessoas ativas abaixo do piso. Contém dados pessoais e salários: tratar com cuidado, e não colar na conversa mais do que o necessário.
4. **`comparativo.md`**, **`resumo.json`**, logs e `dados_brutos/`.

**Como o usuário abre**: dois cliques no HTML, que abre no navegador (Chrome, Safari ou Edge). Para apresentar, tela cheia (no Mac, Ctrl+Cmd+F). Para PDF, Cmd+P e "Salvar como PDF" (os botões de filtro somem na impressão). Para enviar, anexar o arquivo ao e-mail.

## O que exige julgamento a cada trimestre

O pipeline gera texto e tags a partir dos números, mas estes pontos precisam do seu olho antes de responder:

1. **Gestores que entraram ou saíram da lista crítica** (`comparativo.md`). Times têm cerca de 20 a 35 pessoas, então um gestor novo na lista pode ser acaso. Conferir se passa no teste mais rigoroso e se há evidência convergente (satisfação com o gestor, motivo "Relação com a gestão").
2. **Fator que mudou de classificação** (forte, moderado, sem efeito). Dizer ao usuário, com o número antes e depois. Não "suavizar" para manter a história do trimestre passado.
3. **Ações padrão dos cards e das prioridades** são genéricas (conversa individual, investigação de campo, corrigir o piso por equidade). Se o quadro mudou (por exemplo, o custo de corrigir o piso passou a compensar, ou não há mais gestor crítico), conferir se o texto ainda faz sentido. Os templates tratam alguns desses casos, mas confira.
4. **Bases pequenas**: áreas ou modalidades com menos de 15 pessoas, ou menos de 5 saídas, oscilam muito. Não tire conclusão de variação nelas.
5. **Ano parcial**: a taxa de um ano com poucos meses é ruidosa. Compare pelos "últimos 12 meses contra os 12 anteriores", que é o que os HTMLs usam.
6. **Fatores fracos**: o relatório lista os que "parecem ter efeito mas somem com controles". Esperam-se falsos positivos (cerca de 5% dos fatores testados), então não promover um fator fraco a achado.
7. **Pessoa nova em categoria** (área, modalidade, cargo, nível sem faixa salarial): o orquestrador avisa ou para. Decidir a regra com o usuário.
8. **Premissa do custo (3× o salário)**: mantê-la fixa entre trimestres, para os números serem comparáveis. Só mude se o usuário mandar.

## Quando o pipeline para

| Mensagem | Causa provável | O que fazer |
|---|---|---|
| "colunas diferentes do esperado" | o sistema de origem mudou o layout | mostrar ao usuário a diferença e ajustar `ESPERADO` em `rodar_diagnostico.py` e a leitura em `limpeza_rh.py` |
| "arquivo ausente" | falta um dos 5 CSVs | pedir o arquivo |
| `KeyError` em `limpeza_rh.py` | rótulo novo (modalidade, satisfação etc.) | estender a regra e registrar a decisão |
| "cadastro e desligamentos não batem" | alguém saiu sem registro, ou o inverso | listar as pessoas e perguntar ao usuário |
| "cargo/nível sem faixa salarial" | cargo novo | pedir a faixa salarial |
| "histórico mensal tem meses faltando" | extração incompleta | pedir novo arquivo |
| "headcount do cadastro difere do último mês" | inconsistência de datas | investigar antes de seguir |

O pipeline para **antes de arquivar**, então uma falha nunca deixa uma entrega pela metade em `ENTREGAS/`.

## Verificação dos HTMLs

Não há Node nem pandas. Use o Chrome em modo headless:

```
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
  --virtual-time-budget=3000 --enable-logging=stderr --v=0 \
  --dump-dom "file://$PWD/ENTREGAS/<período>/dashboard_turnover.html" > /tmp/dom.html 2> /tmp/err.txt
```

Conferir: `grep -ci "uncaught" /tmp/err.txt` deve dar 0, e o texto do DOM não pode conter `undefined` nem `NaN`. Para ver visualmente, use `--screenshot` com `--window-size=1360,2700` (ou 1100,7600 para o relatório).

## Como responder ao usuário

- Português, direto, no papel de analista de dados sênior. Primeiro o que importa (as mudanças contra o trimestre anterior), depois o detalhe.
- Cada achado vem com o número que o sustenta, o quanto pesa e o que fazer. Diga de forma explícita o que é fraco, o que pode ser coincidência e o que a base não consegue provar. Nunca afirme causa a partir de associação.
- Aponte quando um resultado muda a conclusão que demos antes, em vez de repetir o texto velho.
- Cite os caminhos dos arquivos entregues e diga como abrir.
- Ao alterar qualquer script, confira os valores de referência da próxima seção antes de entregar.

## Valores de referência (primeira entrega, 2025-T4, dados até dez/2025)

Servem para detectar regressão quando os scripts forem alterados: rodar o pipeline sobre os mesmos dados deve dar exatamente isto.

| Indicador | Valor |
|---|---|
| Período | jan/2023 a dez/2025 (36 meses), 1.212 pessoas, 378 desligamentos |
| Headcount atual | 834 |
| Turnover anual / voluntário | 17,4% / 13,8% (300 voluntárias, 78 involuntárias) |
| Por ano | 17,1% (2023), 18,2% (2024), 16,8% (2025) |
| Custo estimado | R$ 5.593.340 (3× o último salário) |
| eNPS (dez/2025) | +7,4; jun/2025 foi +12,1 |
| Abaixo do piso | 72 pessoas ativas (27 delas também detratoras) |
| Área crítica | Atendimento, 32,3% ao ano (170 das 378 saídas) |
| Gestores críticos | Debora Santos, Beatriz Ferreira, Felipe Rodrigues |
| Razão de chances (modelo completo) | gestor crítico 2,38; abaixo do piso 2,10; Atendimento 1,86 (fortes); satisfação carreira 1,65 e detrator 1,48 (moderados) |
| Explicado pelos fatores | 128 das 300 voluntárias (43%) |
| Linhas rejeitadas no histórico | 25 (órfãs, sem cadastro) |

## Testar o pipeline sem mexer nos dados reais

Simular um trimestre anterior cortando os dados em set/2025 numa pasta de teste, e rodar em cima dela:

```
python3 -I src/utilitarios/simular_corte.py DADOS /pasta/teste/DADOS
DIAG_RAIZ=/pasta/teste python3 -I src/rodar_diagnostico.py
```

Depois copie os dados completos para `/pasta/teste/DADOS` e rode de novo: a segunda entrega deve comparar com a primeira. Foi assim que o pipeline foi validado: ano parcial, comparativo entre trimestres e três tipos de falha (coluna renomeada, arquivo ausente e valor novo numa categoria).

## Limitações que valem em toda execução

- Área, modalidade, gestor e salário são os do **cadastro atual**, não o histórico de cada mês. O salário de quem saiu é o último registrado.
- É associação, não causa. O motivo de saída é declarado pelo colaborador, e o eNPS pode refletir uma decisão já tomada.
- A pesquisa de clima cobre uma amostra (cerca de 72% das pessoas), e a mesma pessoa pode aparecer em várias rodadas.
- Cerca de 57% das demissões voluntárias não têm explicação nesta base (motivos pessoais, mudança de cidade, proposta de outra empresa).

## Histórico de decisões

| Data | Decisão |
|---|---|
| 2026-11-19 | Primeira análise completa (dados até dez/2025). Tratamento, turnover, inversão salarial e piso, diagnóstico de fatores, relatório e dashboard. |
| 2026-11-19 | Pipeline generalizado: nenhum ano, data, área ou gestor fixo no código. Período e referências vêm dos dados; gestores críticos e área crítica são detectados por regra. |
| 2026-11-19 | Classificação de fatores passou a ser por regra (limite inferior do IC ≥ 1,4 = forte). Com ela, o eNPS baixo é **moderado** (razão de chances 1,48 depois de controlar o resto; a associação simples é 2,9×). O relatório publicado antes dessa regra o marcava como forte. |
| 2026-11-19 | Horas extras negativas viram vazio (não se sabe se o certo seria o valor absoluto). `satisfacao_carreira` em branco não é imputada. Gestor em branco vira `NI`. Data de desligamento do arquivo de desligamentos prevalece sobre o cadastro. |
| 2026-11-19 | Custo das saídas = 3× o último salário, premissa do usuário. |
