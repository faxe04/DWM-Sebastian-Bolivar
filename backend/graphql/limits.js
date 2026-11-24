const { parse } = require('graphql');

// Inspección corta antes de ejecutar: también cuenta aliases y fragmentos.
function checkQuery(body) {
  if (!body || Array.isArray(body) || typeof body.query !== 'string' || body.query.length > 8192)
    throw new Error('Envía una consulta de hasta 8192 caracteres; sin batches');
  const document = parse(body.query, { maxTokens: 1000 });
  const operations = document.definitions.filter(d => d.kind === 'OperationDefinition');
  if (operations.length !== 1 || operations[0].operation !== 'query')
    throw new Error('Solo una Query por solicitud; las escrituras usan REST');
  const fragments = new Map(document.definitions.filter(d => d.kind === 'FragmentDefinition').map(d => [d.name.value, d]));
  let cost = 0;
  let fields = 0;
  function visit(selectionSet, depth, multiplier, trail = []) {
    if (!selectionSet) return;
    for (const node of selectionSet.selections) {
      if (node.kind === 'FragmentSpread') {
        const name = node.name.value;
        if (trail.includes(name) || !fragments.has(name)) throw new Error('Fragmento inválido');
        visit(fragments.get(name).selectionSet, depth, multiplier, [...trail, name]);
      } else if (node.kind === 'InlineFragment') {
        visit(node.selectionSet, depth, multiplier, trail);
      } else {
        fields++;
        cost += multiplier;
        if (depth > 6 || cost > 500 || fields > 80) throw new Error('Consulta excede profundidad 6, costo 500 o 80 campos');
        let nextMultiplier = multiplier;
        if (node.name.value === 'catalog') {
          const limit = node.arguments.find(a => a.name.value === 'limit');
          let value = 20;
          if (limit) value = limit.value.kind === 'Variable' ? body.variables?.[limit.value.name.value] : Number(limit.value.value);
          // Las variables con default se estiman conservadoramente en 50.
          if (value === undefined) value = 50;
          if (!Number.isInteger(value) || value < 1 || value > 50) throw new Error('limit debe estar entre 1 y 50');
          nextMultiplier *= value;
        }
        if (node.name.value === 'items') nextMultiplier *= 50;
        visit(node.selectionSet, depth + 1, nextMultiplier, trail);
      }
    }
  }
  visit(operations[0].selectionSet, 1, 1);
  return { cost, fields };
}
module.exports = { checkQuery };
