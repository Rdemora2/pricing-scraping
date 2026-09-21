# Produto

## Problema

Pesquisar manualmente anúncios não produz uma visão rastreável do mercado. URLs
mudam, variantes semelhantes são confundidas, condições comerciais distorcem a
comparação e falhas de coleta são frequentemente tratadas como ausência de oferta.

O Signal Price demonstra uma alternativa local e explicável: descobrir ofertas em
fontes conhecidas, guardar evidências, associar somente equivalências defensáveis e
mostrar exatamente quais observações sustentam cada indicador.

## Usuário e decisão inicial

O primeiro usuário é um analista de pricing ou desenvolvedor avaliando a posição
de uma variante e de um aparelho completo no mercado. As decisões suportadas são:
"qual é a faixa anunciada agora e por que cada oferta entrou ou saiu da
comparação?" e "como armazenamento e cor alteram o preço observado deste modelo?".

## Escopo entregue

- catálogo tipado com 17 aparelhos e 221 variantes de mercado: linhas iPhone
  16/17/18 Pro e Air, Galaxy S25/S26 e Motorola Edge 70 Pro, cada família com
  referência oficial explícita;
- coletores reais para Zoom, Buscapé, KaBuM!, Americanas e Samsung
  Shop, configurados pela raiz
  da fonte e orientados por aparelho/capacidade, com descoberta limitada de
  páginas, evidência, vendedor efetivo e atualização manual;
- extratores dedicados também existentes para Fast Shop, 2aFinder e Amazon,
  mantidos candidatos enquanto o fluxo completo não produz evidência permitida;
- integrações diretas iPlace e Magalu mantidas como candidatas enquanto o acesso
  automatizado declarado responder HTTP 403; ofertas desses vendedores ainda
  podem ser comprovadas por marketplaces públicos;
- radar opcional de referências na web, com confiança e revisão antes de coleta;
- portfólio governado de 33 fontes, separando coletores ativos, raízes candidatas,
  referências oficiais, APIs pendentes, operadoras e sinais promocionais;
- duas fontes HTTP com markup diferente, paginação e múltiplos vendedores;
- coleta manual assíncrona e idempotente;
- extração JSON-LD validada e evidência com hash/versão do extrator;
- waterfall de aquisição com API oficial opcional, HTTP/JSON-LD, DOM e Chromium
  headless limitado como último recurso para fontes JavaScript revisadas;
- matching determinístico por GTIN e, quando o GTIN está ausente, atributos;
- comparação de preço atual com mínimo, mediana, máximo e exclusões;
- leitura executiva por aparelho com cobertura, escada de preço entre
  capacidades e índice de cor normalizado por armazenamento;
- painel para iniciar coletas, acompanhar fontes e explorar variantes.
- landing page própria e workspace com visão geral, aparelhos, fontes, radar,
  cadastro de equipamento e cadastro de referência.

Catálogo e cobertura são contratos diferentes. Os seis coletores homologados
podem pesquisar todos os 17 aparelhos sem que novas URLs sejam cadastradas.
Isso não significa que todas as 221 variantes tenham oferta ativa: cada
observação continua exigindo modelo, armazenamento e cor exatos. iPhone 18 Pro,
iPhone 18 Pro Max e Motorola Edge 70 Pro permanecem prontos para busca, mas sem
preço quando não existe uma matriz brasileira pública e estável.

## População comparável

Uma observação entra na comparação somente quando:

1. está associada à variante selecionada;
2. usa BRL;
3. descreve produto novo;
4. está anunciada como disponível;
5. é a observação mais recente daquele anúncio.
6. o preço não depende de cartão, clube, troca ou outra condição comercial.
7. existe no máximo uma observação por varejista, preferindo a fonte direta.
8. a observação está dentro da janela configurável de frescor, 72 horas por
   padrão.

Frete desconhecido permanece desconhecido. Cupom, parcelamento e desconto à vista
são exibidos como condições, não aplicados silenciosamente ao preço-base. Preço
ausente ou inválido causa falha de extração; nunca vira zero.

Quando nenhuma oferta satisfaz a população, a resposta é explicitamente "dados
insuficientes". **Varejistas distintos** mede diversidade comercial; **canais de
evidência** mede quantas fontes sustentam as ofertas. Nenhuma das duas representa
cobertura total da internet.

## Inteligência consolidada do aparelho

O modelo nunca agrega anúncios brutos diretamente. Primeiro, cada variante exata
é filtrada pela população comparável e deduplicada por varejista. Depois:

1. armazenamento usa a mediana dos preços medianos das cores observadas;
2. cada salto adjacente informa o acréscimo absoluto e percentual de preço;
3. cor é comparada à mediana das cores dentro do mesmo armazenamento;
4. cobertura informa quantas variantes canônicas possuem observações válidas;
5. cada salto exige duas cores observadas nas duas capacidades e três
   varejistas entre elas; o índice de cor exige ao menos duas capacidades comparáveis.

Esse contrato evita concluir que uma cor é barata apenas porque apareceu em uma
capacidade menor e não chama a maior capacidade de melhor compra apenas porque o
custo unitário cai. O painel expõe método, amostra e estados `sem dados`,
`limitada`, `em formação` ou `robusta`.

## Meta de amostragem

O piso desejado é 6–8 valores de varejistas confiáveis por aparelho/variante;
mais é melhor. Esse número é meta operacional, não seed ou dado decorativo. Na
execução local de `2026-09-21`, as buscas por fonte do iPhone 17 Pro Max
produziram runs de referência em Zoom, Buscapé, KaBuM!, Americanas e Carrefour
e, após matching e deduplicação, `54` ofertas de `17` varejistas. As 12
combinações canônicas de armazenamento e cor ficaram
observadas; a diversidade por combinação exata, porém, variou de `3` a `11`
varejistas. A UX explicita essa diferença e não mistura capacidades, cores ou
aliases para completar artificialmente a meta.

Essa evidência histórica não mantém uma fonte ativa por si só. Na revalidação
do iPhone 16, o Carrefour recusou as três buscas por capacidade porque seu
`robots.txt` atual proíbe `/busca/`; o adapter voltou a `candidate` sem apagar
as observações já auditáveis.

## Fora do escopo atual

- resolução de CAPTCHA, contorno de bloqueio, paywall ou autenticação de lojas;
- recomendação/alteração automática de preços;
- inferência de vendas, demanda, elasticidade ou preço ótimo;
- custos, margens, integrações comerciais, multi-tenancy ou cloud;
- uso de IA no fluxo principal.

Resultados da busca ampla são referências, não cobertura total da internet. Apple
Brasil sustenta o catálogo e a lista de revendedores, mas não é coletada
automaticamente. Cada nova loja exige avaliação de acesso, parser específico e
decisão explícita de habilitação.
