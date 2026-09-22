const express = require('express');
const mysql = require('mysql2/promise');
const cors = require('cors');
require('dotenv').config();

const {ApolloServer, gql} = require('apollo-server-express');

const db = mysql.createPool({
    host: 'localhost',
    port: process.env.DB_PORT,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME
})

const typeDefs = gql`
    type Producto{
        id_producto: ID!
        nombre: String!
        descripcion: String!
        precio: Float!
        categoria: String!
    } 
    input ProductoInput{
        nombre: String!
        descripcion: String!
        precio: Float!
        categoria: String!
    }
    type Alert{
        message: String
    }
    type Query{
        getProductos: [Producto]
        getProductoById(id_producto: ID!): Producto
    }
    type Mutation{
        addProducto(input: ProductoInput!): Producto
        updProducto(id_producto: ID!, input: ProductoInput!): Producto
        delProducto(id_producto: ID!): Alert
    }
`

const resolvers = {
    Query: {
        async getProductos(obj){
            const [productos] = await db.query('SELECT * FROM productos');
            return productos;
        },
        async getProductoById(obj, {id_producto}){
            const [productoBus] = await db.query('SELECT * FROM productos WHERE id_producto = ?', [id_producto]);
            if (productoBus.length === 0){
                return null;
            } else {
                return productoBus[0];
            }
        }
    },
    Mutation: {
        async addProducto(obj, {input}){
            const [result] = await db.query('INSERT INTO productos SET ?', [input]);
            return {id_producto: result.insertId, ...input};
        },
        async updProducto(obj, {id_producto, input}){
            const [result] = await db.query('UPDATE productos SET ? WHERE id_producto = ?', [input, id_producto]);
            if (result.affectedRows === 0){
                return null;
            }
            return {id_producto: id_producto, ...input};
        },
        async delProducto(obj, {id_producto}){
            await db.query('DELETE FROM productos WHERE id_producto = ?', [id_producto]);
            return {message: "Producto Eliminado"};
        }
    }
};

let apolloServer = null;
const corsOptions = {
    origin: "http://localhost:8090",
    credentials: false
};
async function startServer(){
    apolloServer = new ApolloServer({typeDefs, resolvers, corsOptions});
    await apolloServer.start();
    apolloServer.applyMiddleware({app, cors: false});
}
startServer();
const app = express();
app.use(cors());
app.listen(8090, function(){
    console.log("Graphql Iniciado")
})
