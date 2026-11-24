const express = require('express');
const crypto = require('node:crypto');
const { ApolloServer } = require('@apollo/server');
const { expressMiddleware } = require('@as-integrations/express5');
const { GraphQLError } = require('graphql');
const { checkQuery } = require('./limits');
const { secret, getData } = require('./services');


const typeDefs = `
type Product {
  id: ID!
  name: String!
  description: String!
  category: String!
  price: Float!
  available: Boolean!
}
type OrderItem {
  product_id: ID!
  name: String!
  quantity: Int!
  price: Float!
}
type Payment {
  id: ID!
  status: String!
  amount: Float!
  currency: String!
}
type Customer {
  user_id: ID!
  full_name: String!
  email: String!
}
type OrderSummary {
  id: ID!
  status: String!
  total: Float!
  currency: String!
  items: [OrderItem!]!
  customer: Customer
  payment: Payment
  requestKey: String
}
type Query {
  catalog(skip: Int = 0, limit: Int = 20): [Product!]
  orderSummary(id: ID!): OrderSummary
}
`;

const INVENTORY_URL = process.env.INVENTORY_URL || 'http://localhost:9000';
const ORDERS_URL = process.env.ORDERS_URL || 'http://localhost:9100';
const CLIENTS_URL = process.env.CLIENTS_URL || 'http://localhost:9200';
const PAYMENTS_URL = process.env.PAYMENTS_URL || 'http://localhost:9300';


function validId(value) {
  if (!/^[1-9][0-9]{0,15}$/.test(value)) throw new GraphQLError('ID inválido', { extensions: { code: 'BAD_USER_INPUT' } });
  return value;
}

const resolvers = {
  Query: {
    async catalog(obj, { skip, limit }, context) {
      if (skip < 0 || limit < 1 || limit > 50) {
        throw new GraphQLError('Paginación inválida');
      }
      const url = INVENTORY_URL + '/products?skip=' + skip + '&limit=' + limit;
      return await getData(url, 'INVENTORY_GATEWAY_SECRET', context);
    },
    async orderSummary(obj, { id }, context) {
      // Orders comprueba que el pedido sea del usuario antes de devolver sus datos
      const url = ORDERS_URL + '/orders/' + validId(id);
      return await getData(url, 'ORDERS_GATEWAY_SECRET', context);
    }
  },
  // Estos resolvers solo se ejecutan si la consulta pide customer o payment
  OrderSummary: {
    async customer(order, args, context) {
      let url = CLIENTS_URL + '/clients/me';
      if (context.user.roles.includes('admin')) {
        url = CLIENTS_URL + '/admin/clients/' + order.user_id;
      }
      return await getData(url, 'CLIENTS_GATEWAY_SECRET', context);
    },
    async payment(order, args, context) {
      if (!order.payment_id) {
        return null;
      }
      const url = PAYMENTS_URL + '/payments/' + order.payment_id;
      return await getData(url, 'PAYMENTS_GATEWAY_SECRET', context);
    },
    requestKey(order, args, context) {
      if (!context.user.roles.includes('admin')) {
        throw new GraphQLError('Campo exclusivo de administración', { extensions: { code: 'FORBIDDEN' } });
      }
      return order.request_key;
    }
  }
};

async function startServer() {
  const app = express();
  app.disable('x-powered-by');
  // No acepta identidad si falta primero el secreto del API Gateway
  app.use((req, res, next) => {
    try {
      const expected = Buffer.from(secret('INTERNAL_GATEWAY_SECRET'));
      const received = Buffer.from(req.get('X-Gateway-Secret') || '');
      if (expected.length !== received.length || !crypto.timingSafeEqual(expected, received))
        return res.status(403).json({ detail: 'Gateway no autorizado' });
      next();
    } catch {
      res.status(503).json({ detail: 'Falta configuración' });
    }
  });

  app.get('/health', (_, res) => res.json({ status: 'ok', service: 'graphql' }));
  app.use('/graphql', express.json({ limit: '16kb' }), (req, res, next) => {
    if (req.method !== 'POST') return res.sendStatus(405);
    try { checkQuery(req.body); next(); }
    catch (error) { res.status(400).json({ errors: [{ message: error.message }] }); }
  });

  const server = new ApolloServer({
    typeDefs, resolvers, introspection: false, includeStacktraceInErrorResponses: false,
    formatError: error => ({ message: error.extensions?.code === 'INTERNAL_SERVER_ERROR' ? 'Error de agregación' : error.message,
      path: error.path, extensions: { code: error.extensions?.code } })
  });

  await server.start();
  app.use('/graphql', expressMiddleware(server, { context: async ({ req }) => {
    const id = req.get('X-Authenticated-User') || '';
    const roles = (req.get('X-Authenticated-Roles') || '').split(',');
    if (!/^[1-9][0-9]*$/.test(id) || !roles.some(r => ['client','admin'].includes(r)))
      throw new GraphQLError('Identidad requerida', { extensions: { code: 'UNAUTHENTICATED' } });
    // context son datos compartidos por los resolvers de esta solicitud
    return {
      user: { id, roles, requestId: req.get('X-Request-ID') || crypto.randomUUID() },
      cache: new Map()
    };
    
  } }));

  app.use((error, req, res, next) => res.status(error.status === 413 ? 413 : 400).json({ detail: 'Solicitud inválida' }));

  return app.listen(Number(process.env.PORT || 9400), process.env.HOST || '127.0.0.1', () => console.log('GraphQL listo'));
}

if (require.main === module) startServer().catch(() => { console.error('No se pudo iniciar GraphQL'); process.exitCode = 1; });
module.exports = { resolvers, startServer };
