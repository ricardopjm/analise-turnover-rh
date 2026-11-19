# Dicionário de dados — Vantel Serviços (empresa fictícia)

Empresa de serviços com call center, operação e áreas corporativas. **Jan/2023 a dez/2025**, 834 pessoas ativas hoje e 378 desligamentos no período. Tudo sintético — nomes, salários e avaliações não são reais.

## Arquivos

### `colaboradores.csv` — 1 linha por pessoa (~1.230 linhas)
| coluna | descrição |
|---|---|
| `colaborador_id` | id da pessoa (liga com todos os outros arquivos) |
| `nome` | nome |
| `area` | Atendimento, Operacoes, Comercial, Tecnologia, Logistica, Financeiro, Marketing, RH |
| `cargo`, `nivel` | Estagiario / Assistente / Analista / Especialista / Coordenador / Gerente + Junior / Pleno / Senior / Unico |
| `gestor_id`, `gestor` | quem lidera essa pessoa |
| `data_admissao` | entrada |
| `data_desligamento` | vazio = ainda trabalha aqui |
| `salario` | salário atual |
| `modalidade` | Presencial / Hibrido / Remoto |
| `cidade`, `uf` | localização |
| `data_nascimento` | permite calcular idade |
| `data_ultima_promocao` | última promoção registrada (igual à admissão se nunca foi promovido) |

### `historico_mensal.csv` — 1 linha por pessoa por mês (~26 mil linhas)
`mes`, `colaborador_id`, `horas_extras`, `faltas_dias`
→ É um **painel**: acompanha a mesma pessoa ao longo do tempo. Só existe linha nos meses em que a pessoa estava na empresa.

### `pesquisa_clima.csv` — pesquisas semestrais, jun e dez (~3.200 respostas)
`data_pesquisa`, `colaborador_id`, `enps` (0 a 10), `satisfacao_gestor`, `satisfacao_salario`, `satisfacao_carreira` (1 a 5)
→ ~72% respondem. eNPS: 0-6 detrator, 7-8 neutro, 9-10 promotor.

### `desligamentos.csv` — 1 linha por saída (378)
`colaborador_id`, `data_desligamento`, `tipo` (Voluntario/Involuntario), `motivo`, `aviso_previo`

### `faixas_salariais.csv` — tabela de referência (9 linhas)
`cargo`, `nivel`, `faixa_min`, `faixa_media`, `faixa_max`
→ Permite responder **quem está abaixo do piso da própria faixa**.

O tratamento aplicado a cada arquivo está descrito no [README](../README.md) e registrado a cada execução em `log_limpeza.csv`.
