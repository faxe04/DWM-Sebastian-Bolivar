const fs = require('node:fs');
const { GraphQLError } = require('graphql');

function secret(name) {
  let value = process.env[name];
  if (process.env[name + '_FILE']) {
    value = fs.readFileSync(process.env[name + '_FILE'], 'utf8').trim();
  }
  if (!value) throw new Error('Configuración de integración incompleta');
  return value;
}

async function fetchData(url, secretName, user) {
  try {
    const response = await fetch(url, {
      headers: {
        'X-Gateway-Secret': secret(secretName),
        'X-Authenticated-User': user.id,
        'X-Authenticated-Roles': user.roles.join(','),
        'X-Request-ID': user.requestId
      },
      signal: AbortSignal.timeout(3000)
    });
    if ([401, 403, 404].includes(response.status)) {
      throw new GraphQLError('Recurso no disponible para esta identidad', { extensions: { code: 'FORBIDDEN' } });
    }
    if (!response.ok) throw new Error('Falló la dependencia');
    return await response.json();
  } catch (error) {
    if (error instanceof GraphQLError) throw error;
    throw new GraphQLError('Servicio temporalmente no disponible', { extensions: { code: 'DEPENDENCY_UNAVAILABLE' } });
  }
}

function getData(url, secretName, context) {
  // Evita repetir la misma llamada cuando una consulta usa aliases.
  // Guardar la promesa también evita duplicarla mientras está en curso.
  if (!context.cache.has(url)) {
    context.cache.set(url, fetchData(url, secretName, context.user));
  }
  return context.cache.get(url);
}

module.exports = { secret, getData };
