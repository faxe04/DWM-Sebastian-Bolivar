const test = require('node:test');
const assert = require('node:assert/strict');
const { checkQuery } = require('./limits');
const { getData } = require('./services');
const { resolvers } = require('./server');


test('permite resumen acotado', () => {
  assert.ok(checkQuery({ query: '{ orderSummary(id:"1") { id total items { name quantity } payment { status } } }' }).cost < 500);
});

test('rechaza batches, mutaciones y fragmentos circulares', () => {
  for (const input of [[], { query: 'mutation { x }' }, { query: '{ ...A } fragment A on Query { ...A }' }])
    assert.throws(() => checkQuery(input));
});

test('limita profundidad, aliases y paginación', () => {
  assert.throws(() => checkQuery({ query: '{ a { b { c { d { e { f { g } } } } } } }' }));
  assert.throws(() => checkQuery({ query: '{ ' + Array.from({length:81}, (_,i) => 'a'+i+': catalog { id }').join(' ') + ' }' }));
  assert.throws(() => checkQuery({ query: 'query($n:Int){ catalog(limit:$n){id} }', variables: {n:10000} }));
});

test('cachea llamadas por solicitud y no comparte identidades', async (t) => {
  process.env.ORDERS_GATEWAY_SECRET = 'test';
  let calls = 0;
  const request = async () => { calls++; return { ok: true, json: async () => ({id:1}) }; };
  t.mock.method(global, 'fetch', request);
  const context = {user:{id:'1', roles:['client'], requestId:'test'}, cache:new Map()};
  await Promise.all([getData('http://orders/orders/1','ORDERS_GATEWAY_SECRET',context), getData('http://orders/orders/1','ORDERS_GATEWAY_SECRET',context)]);
  assert.equal(calls, 1);
  await getData('http://orders/orders/1','ORDERS_GATEWAY_SECRET',{user:{id:'2',roles:['client'],requestId:'test'},cache:new Map()});
  assert.equal(calls, 2);
});

test('un fallo parcial no expone claves ni URL', async (t) => {
  process.env.PAYMENTS_GATEWAY_SECRET = 'test';
  t.mock.method(global, 'fetch', async () => { throw new Error('secret URL'); });
  const context = {user:{id:'1',roles:['client'],requestId:'test'},cache:new Map()};
  await assert.rejects(getData('http://payments/payments/1','PAYMENTS_GATEWAY_SECRET',context), error => error.message === 'Servicio temporalmente no disponible');
});

test('campo requestKey exige admin', () => {
  assert.throws(() => resolvers.OrderSummary.requestKey({request_key:'key'}, {}, {user:{roles:['client']}}));
  assert.equal(resolvers.OrderSummary.requestKey({request_key:'key'}, {}, {user:{roles:['admin']}}), 'key');
});
