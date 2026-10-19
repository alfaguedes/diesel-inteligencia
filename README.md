# Diesel Inteligência — versão de produção inicial

Este pacote prepara a publicação gratuita em GitHub Pages e a atualização diária via GitHub Actions. **Não está publicado ainda**: é necessário criar o repositório na conta do proprietário e habilitar Pages/Actions.

## O que faz
- Site sem preços inventados: começa vazio até a primeira importação oficial.
- Uma tarefa diária visita a página de dados abertos da ANP, encontra o CSV mensal mais recente cujo nome contém `diesel-gnv`, baixa e processa registros de Diesel S10 e S500.
- O arquivo `data/prices.json` recebe os registros e metadados de fonte, URL, hash SHA-256, mês de referência e horário de verificação.
- `data/archive/YYYY-MM.json` mantém um arquivo por mês, permitindo montar o histórico.
- `data/status.json` registra a última execução bem-sucedida.
- O workflow pode ser executado manualmente para testar a primeira importação.
- A área de notícias oferece links diretos a fontes; ainda não agrega manchetes automaticamente.
- O módulo de cotações comerciais/granel não está conectado a uma fonte B2B nesta etapa.

## Fontes oficiais
- ANP — série histórica e CSVs: https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis
- Informações sobre metodologia do levantamento: https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis
- Painel dinâmico ANP (revendedores, distribuidores, produtores/importadores): https://www.gov.br/anp/pt-br/centrais-de-conteudo/paineis-dinamicos-da-anp/painel-dinamico-de-precos-de-combustiveis-e-derivados-do-petroleo

## Publicar gratuitamente (passo a passo)
1. Crie ou entre na sua conta em https://github.com/.
2. Clique em **New repository** e dê o nome `diesel-inteligencia`.
3. Selecione **Public** (GitHub Pages no plano gratuito exige repositório público).
4. Extraia este ZIP no computador.
5. Dentro da pasta extraída, envie todos os arquivos para o repositório (na página do repositório, **Add file → Upload files**), incluindo a pasta `.github` e o workflow. Se a interface web não mostrar arquivos ocultos, use GitHub Desktop ou Git local para enviar a pasta completa.
6. Faça commit na branch `main`.
7. No repositório, abra **Settings → Pages**; em **Build and deployment**, escolha **Deploy from a branch** não é necessário aqui — escolha **GitHub Actions** se essa opção estiver disponível, pois o arquivo `.github/workflows/deploy.yml` publica o site.
8. Abra **Actions** e confirme que o workflow **Atualizar dados da ANP e publicar o site** concluiu com sucesso.
9. Execute manualmente o workflow **Atualizar dados da ANP e publicar o site**: Actions → escolha o workflow → Run workflow.
10. Aguarde terminar e recarregue o site publicado. O endereço será parecido com `https://SEU-USUARIO.github.io/diesel-inteligencia/`; só será válido após o GitHub confirmar a publicação.
11. Na aba **Actions**, confira as execuções diárias. Se a ANP alterar o formato dos CSVs, o script falhará com erro visível em vez de substituir dados com uma tabela vazia.

## Limitações e decisões de precisão
- A ANP divulga o levantamento de revenda em periodicidade semanal; executar o verificador diariamente não cria novos dados diários.
- O script descobre o CSV mensal mais recente na página oficial e valida se há registros S10/S500. O esquema dos arquivos oficiais pode mudar; verifique os logs da primeira execução.
- Os preços refletem o levantamento oficial de revenda, não são cotações em tempo real nem necessariamente preços de venda a granel para cooperativas/produtores.
- O histórico mensal é criado a partir da primeira execução deste sistema; para montar histórico de muitos anos, será necessário importar os arquivos históricos anteriores (pode ser uma etapa posterior).
- A notícia é uma lista de fontes, não um feed automático. Para agregação de manchetes, adicionar RSS/API e respeitar os termos das fontes.
- Repositórios públicos são visíveis a qualquer pessoa. Não coloque senhas, tokens, cotações confidenciais nem dados comerciais privados no repositório.
- GitHub Actions agendado pode atrasar; não é um sistema de monitoramento com SLA.
- A publicação não foi feita automaticamente porque exige autenticação na sua conta GitHub e autorização sua.

## Arquitetura
- Frontend estático: HTML/CSS/JavaScript.
- Dados: JSON público versionado no repositório.
- ETL: Python standard library (sem dependências externas).
- Agendamento e publicação: GitHub Actions + GitHub Pages.
- Evolução futura: banco PostgreSQL e API para cotações privadas, login, alertas e notícias automatizadas.

## Testar o ETL localmente
Requer Python 3.10+ e internet:
```bash
python scripts/update_anp.py
```
A execução deve baixar o arquivo oficial atual, criar `data/prices.json`, `data/status.json` e `data/archive/YYYY-MM.json`. Não foi possível testar o download neste ambiente de criação, então a primeira execução no GitHub deve ser tratada como teste de integração e validada pelos logs.
