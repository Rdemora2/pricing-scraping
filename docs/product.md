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
de uma variante em um conjunto pequeno de fontes. A primeira decisão suportada é:
"qual é a faixa anunciada agora e por que cada oferta entrou ou saiu da
comparação?".

## Escopo entregue no laboratório

- produto canônico com três variantes sintéticas;
- duas fontes HTTP com markup diferente, paginação e múltiplos vendedores;
- coleta manual assíncrona e idempotente;
- extração JSON-LD validada e evidência com hash/versão do extrator;
- matching determinístico por GTIN e, quando o GTIN está ausente, atributos;
- comparação de preço atual com mínimo, mediana, máximo e exclusões;
- painel para iniciar coletas, acompanhar fontes e explorar variantes.

## População comparável

Uma observação entra na comparação somente quando:

1. está associada à variante selecionada;
2. usa BRL;
3. descreve produto novo;
4. está anunciada como disponível;
5. é a observação mais recente daquele anúncio.

Frete desconhecido permanece desconhecido. Cupom, parcelamento e desconto à vista
são exibidos como condições, não aplicados silenciosamente ao preço-base. Preço
ausente ou inválido causa falha de extração; nunca vira zero.

Quando nenhuma oferta satisfaz a população, a resposta é explicitamente "dados
insuficientes". A quantidade de fontes representa as fontes das ofertas incluídas,
não cobertura da internet.

## Fora do escopo atual

- descoberta irrestrita de novos domínios;
- navegador automatizado, CAPTCHA, paywall ou autenticação de lojas;
- recomendação/alteração automática de preços;
- inferência de vendas, demanda, elasticidade ou preço ótimo;
- custos, margens, integrações comerciais, multi-tenancy ou cloud;
- uso de IA no fluxo principal.

## Próximas decisões de produto

Antes da primeira fonte real, definir categoria, mercado, termos de acesso,
frequência, limites locais e critérios formais para habilitar/desabilitar uma fonte.
