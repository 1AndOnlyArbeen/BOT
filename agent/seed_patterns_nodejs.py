"""Comprehensive Node.js pattern collection — ingested into Ultron's code library.

Covers: core APIs, HTTP/Express deep, Fastify/Koa/Nest, all major DBs, auth, security,
realtime, queues, testing, TS, GraphQL, tRPC, performance, deployment, microservices."""
from __future__ import annotations


NODEJS_SEED: list[dict] = [

# ───────────── Core Node.js ─────────────
{
    "request": "read and write files asynchronously with fs/promises",
    "language": "javascript", "framework": "node-core",
    "code": """import { readFile, writeFile, mkdir, readdir, stat } from 'fs/promises';
import { join } from 'path';

await mkdir('output', { recursive: true });

const text = await readFile('input.txt', 'utf8');
const transformed = text.toUpperCase();
await writeFile(join('output', 'result.txt'), transformed);

const entries = await readdir('output');
for (const name of entries) {
  const info = await stat(join('output', name));
  console.log(name, info.size);
}""",
},
{
    "request": "stream a large file and transform it line-by-line",
    "language": "javascript", "framework": "node-core",
    "code": """import { createReadStream, createWriteStream } from 'fs';
import { pipeline } from 'stream/promises';
import { Transform } from 'stream';
import readline from 'readline';

const upper = new Transform({
  transform(chunk, _enc, cb) { cb(null, chunk.toString().toUpperCase()); },
});

await pipeline(
  createReadStream('big.log'),
  upper,
  createWriteStream('big.upper.log'),
);

// Or line-by-line:
const rl = readline.createInterface({ input: createReadStream('big.log'), crlfDelay: Infinity });
for await (const line of rl) {
  if (line.includes('ERROR')) console.log(line);
}""",
},
{
    "request": "spawn child process and capture output",
    "language": "javascript", "framework": "node-core",
    "code": """import { spawn, exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);
const { stdout, stderr } = await execAsync('git log -5 --oneline');
console.log(stdout);

// Streaming variant for long-running:
const ls = spawn('find', ['/var/log', '-name', '*.log']);
ls.stdout.on('data', (d) => process.stdout.write(d));
ls.stderr.on('data', (d) => process.stderr.write(d));
ls.on('close', (code) => console.log(`exit ${code}`));""",
},
{
    "request": "EventEmitter custom event bus",
    "language": "javascript", "framework": "node-core",
    "code": """import { EventEmitter } from 'events';

class OrderBus extends EventEmitter {}
export const bus = new OrderBus();

bus.on('order.placed', async (order) => {
  await sendEmail(order.userEmail, 'Order received', `Total: ${order.total}`);
});
bus.on('order.placed', async (order) => {
  await analytics.track('order_placed', order);
});

// emit anywhere:
bus.emit('order.placed', order);""",
},
{
    "request": "worker_threads for CPU-bound work",
    "language": "javascript", "framework": "node-core",
    "code": """// main.js
import { Worker } from 'worker_threads';

function runWorker(data) {
  return new Promise((resolve, reject) => {
    const w = new Worker(new URL('./hash-worker.js', import.meta.url), { workerData: data });
    w.on('message', resolve);
    w.on('error', reject);
    w.on('exit', (code) => code !== 0 && reject(new Error(`exit ${code}`)));
  });
}

const result = await runWorker('large input');

// hash-worker.js
import { parentPort, workerData } from 'worker_threads';
import { createHash } from 'crypto';
parentPort.postMessage(createHash('sha256').update(workerData).digest('hex'));""",
},
{
    "request": "cluster module for multi-core HTTP server",
    "language": "javascript", "framework": "node-core",
    "code": """import cluster from 'cluster';
import { cpus } from 'os';
import http from 'http';

if (cluster.isPrimary) {
  for (let i = 0; i < cpus().length; i++) cluster.fork();
  cluster.on('exit', (worker) => {
    console.log(`worker ${worker.process.pid} died, respawning`);
    cluster.fork();
  });
} else {
  http.createServer((_req, res) => {
    res.end(`hello from ${process.pid}\\n`);
  }).listen(3000);
}""",
},
{
    "request": "graceful shutdown handler for an HTTP server",
    "language": "javascript", "framework": "node-core",
    "code": """const server = app.listen(3000);

const shutdown = async (signal) => {
  console.log(`${signal} received, draining…`);
  server.close(async () => {
    await mongoose.disconnect();
    await redis.quit();
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10_000).unref();
};

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT',  () => shutdown('SIGINT'));
process.on('unhandledRejection', (err) => { console.error(err); shutdown('unhandledRejection'); });""",
},
{
    "request": "encrypt and decrypt with Node crypto AES-256-GCM",
    "language": "javascript", "framework": "node-core",
    "code": """import { randomBytes, createCipheriv, createDecipheriv, scryptSync } from 'crypto';

const KEY = scryptSync(process.env.SECRET, 'salt', 32);

export function encrypt(plain) {
  const iv = randomBytes(12);
  const c = createCipheriv('aes-256-gcm', KEY, iv);
  const enc = Buffer.concat([c.update(plain, 'utf8'), c.final()]);
  return Buffer.concat([iv, c.getAuthTag(), enc]).toString('base64');
}

export function decrypt(b64) {
  const buf = Buffer.from(b64, 'base64');
  const iv = buf.subarray(0, 12);
  const tag = buf.subarray(12, 28);
  const data = buf.subarray(28);
  const d = createDecipheriv('aes-256-gcm', KEY, iv);
  d.setAuthTag(tag);
  return Buffer.concat([d.update(data), d.final()]).toString('utf8');
}""",
},
{
    "request": "load env vars and validate at startup",
    "language": "javascript", "framework": "dotenv",
    "code": """import 'dotenv/config';
import { z } from 'zod';

const Env = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(16),
  REDIS_URL: z.string().url().optional(),
});

export const env = Env.parse(process.env);
console.log(`✓ env validated for ${env.NODE_ENV}`);""",
},

# ───────────── Express — deep ─────────────
{
    "request": "Express app structure with separate router and controller",
    "language": "javascript", "framework": "express",
    "code": """// src/app.js
import express from 'express';
import helmet from 'helmet';
import compression from 'compression';
import cors from 'cors';
import morgan from 'morgan';
import orders from './routes/orders.js';
import users from './routes/users.js';
import { errorHandler } from './middleware/error.js';

const app = express();
app.use(helmet());
app.use(compression());
app.use(cors({ origin: process.env.WEB_ORIGIN, credentials: true }));
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(morgan('dev'));

app.use('/api/orders', orders);
app.use('/api/users', users);
app.get('/api/health', (_q, r) => r.json({ ok: true }));

app.use(errorHandler);
export default app;""",
},
{
    "request": "Express centralized error handler with custom AppError",
    "language": "javascript", "framework": "express",
    "code": """// src/utils/AppError.js
export class AppError extends Error {
  constructor(message, status = 500, code = 'INTERNAL') {
    super(message);
    this.status = status;
    this.code = code;
    this.isOperational = true;
  }
}

// src/middleware/error.js
export function errorHandler(err, req, res, _next) {
  const status = err.status || 500;
  const log = status >= 500 ? console.error : console.warn;
  log(`[${req.method} ${req.path}] ${err.message}`, err.isOperational ? '' : err.stack);
  res.status(status).json({
    error: { code: err.code || 'INTERNAL', message: err.message },
  });
}

// src/utils/asyncHandler.js
export const asyncHandler = (fn) => (req, res, next) =>
  Promise.resolve(fn(req, res, next)).catch(next);

// usage:
// router.get('/:id', asyncHandler(ctrl.getById));""",
},
{
    "request": "Express rate limiting per route and per user",
    "language": "javascript", "framework": "express-rate-limit",
    "code": """import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';
import { redis } from './redis.js';

export const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  store: new RedisStore({
    sendCommand: (...args) => redis.sendCommand(args),
  }),
});

export const loginLimiter = rateLimit({
  windowMs: 10 * 60 * 1000,
  max: 5,
  keyGenerator: (req) => req.body?.email || req.ip,
  message: { error: 'too many login attempts' },
});

app.use('/api/', apiLimiter);
app.post('/api/auth/login', loginLimiter, ctrl.login);""",
},
{
    "request": "Express pagination + filtering + sorting helper",
    "language": "javascript", "framework": "express",
    "code": """export function listMiddleware({ allowedSort = ['createdAt'], maxLimit = 100 } = {}) {
  return (req, _res, next) => {
    const page = Math.max(1, parseInt(req.query.page) || 1);
    const limit = Math.min(maxLimit, Math.max(1, parseInt(req.query.limit) || 20));
    const sort = allowedSort.includes(req.query.sort) ? req.query.sort : allowedSort[0];
    const order = req.query.order === 'asc' ? 1 : -1;
    req.list = { page, limit, skip: (page - 1) * limit, sort: { [sort]: order } };
    req.filters = Object.fromEntries(
      Object.entries(req.query).filter(([k]) => k.startsWith('filter.')).map(([k, v]) => [k.replace('filter.', ''), v])
    );
    next();
  };
}

router.get('/', listMiddleware(), async (req, res) => {
  const { skip, limit, sort } = req.list;
  const [items, total] = await Promise.all([
    Order.find(req.filters).sort(sort).skip(skip).limit(limit),
    Order.countDocuments(req.filters),
  ]);
  res.json({ items, total, page: req.list.page, pages: Math.ceil(total / limit) });
});""",
},
{
    "request": "Express request validation with Zod (better than Joi)",
    "language": "javascript", "framework": "zod",
    "code": """import { z } from 'zod';

export const validate = (schemas) => (req, res, next) => {
  try {
    if (schemas.body) req.body = schemas.body.parse(req.body);
    if (schemas.query) req.query = schemas.query.parse(req.query);
    if (schemas.params) req.params = schemas.params.parse(req.params);
    next();
  } catch (err) {
    res.status(400).json({ error: 'validation', issues: err.errors });
  }
};

const createOrderSchema = z.object({
  productId: z.string().uuid(),
  quantity: z.number().int().positive(),
  shippingAddress: z.string().min(5).max(200),
  giftWrap: z.boolean().optional(),
});

router.post('/', validate({ body: createOrderSchema }), ctrl.create);""",
},
{
    "request": "Express cookie-based session with express-session + Redis",
    "language": "javascript", "framework": "express-session",
    "code": """import session from 'express-session';
import RedisStore from 'connect-redis';
import { redis } from './redis.js';

app.use(session({
  store: new RedisStore({ client: redis, prefix: 'sess:' }),
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  rolling: true,
  cookie: {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 7 * 24 * 60 * 60 * 1000,
  },
}));

// usage:
router.post('/login', async (req, res) => {
  const user = await authenticate(req.body);
  req.session.userId = user.id;
  res.json({ ok: true });
});""",
},
{
    "request": "Express CSRF protection",
    "language": "javascript", "framework": "csurf",
    "code": """import csrf from 'csurf';

const csrfProtection = csrf({ cookie: { httpOnly: true, sameSite: 'strict' } });

app.get('/api/csrf-token', csrfProtection, (req, res) => {
  res.json({ csrfToken: req.csrfToken() });
});

app.post('/api/orders', csrfProtection, ctrl.create);

// On the frontend, send X-CSRF-Token header on every mutating request.""",
},
{
    "request": "Express SSE (Server-Sent Events) endpoint",
    "language": "javascript", "framework": "express",
    "code": """app.get('/api/events', (req, res) => {
  res.set({
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  });
  res.flushHeaders();

  const send = (event, data) => {
    res.write(`event: ${event}\\n`);
    res.write(`data: ${JSON.stringify(data)}\\n\\n`);
  };

  send('hello', { ts: Date.now() });
  const interval = setInterval(() => send('heartbeat', { ts: Date.now() }), 15_000);

  const onUpdate = (payload) => send('update', payload);
  bus.on('order.updated', onUpdate);

  req.on('close', () => {
    clearInterval(interval);
    bus.off('order.updated', onUpdate);
  });
});""",
},
{
    "request": "Express GraphQL with Apollo Server v4",
    "language": "javascript", "framework": "apollo-server",
    "code": """import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';
import { typeDefs } from './schema.js';
import { resolvers } from './resolvers.js';

const apollo = new ApolloServer({ typeDefs, resolvers });
await apollo.start();

app.use('/graphql', express.json(), expressMiddleware(apollo, {
  context: async ({ req }) => {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const user = token ? await verifyToken(token) : null;
    return { user };
  },
}));

// schema.js
export const typeDefs = `#graphql
  type Order { id: ID!, total: Float!, status: String! }
  type Query { orders: [Order!]! }
  type Mutation { placeOrder(productId: ID!, quantity: Int!): Order! }
`;""",
},

# ───────────── Fastify (alternative to Express) ─────────────
{
    "request": "Fastify server with schema validation built-in",
    "language": "javascript", "framework": "fastify",
    "code": """import Fastify from 'fastify';
const app = Fastify({ logger: true });

await app.register(import('@fastify/cors'));
await app.register(import('@fastify/helmet'));
await app.register(import('@fastify/jwt'), { secret: process.env.JWT_SECRET });

const orderSchema = {
  body: {
    type: 'object',
    required: ['productId', 'quantity'],
    properties: {
      productId: { type: 'string' },
      quantity: { type: 'integer', minimum: 1 },
    },
  },
};

app.post('/orders', { schema: orderSchema, preHandler: app.authenticate }, async (req) => {
  return { id: '123', ...req.body };
});

app.listen({ port: 3000, host: '0.0.0.0' });""",
},

# ───────────── Database integrations ─────────────
{
    "request": "Mongoose advanced query with virtuals, hooks, populate",
    "language": "javascript", "framework": "mongoose",
    "code": """const userSchema = new mongoose.Schema({
  email: { type: String, required: true, unique: true, lowercase: true, trim: true },
  passwordHash: { type: String, required: true, select: false },
  firstName: String, lastName: String,
}, { timestamps: true, toJSON: { virtuals: true } });

userSchema.virtual('fullName').get(function () {
  return `${this.firstName} ${this.lastName}`.trim();
});

userSchema.virtual('orders', {
  ref: 'Order', localField: '_id', foreignField: 'user',
});

userSchema.pre('save', async function (next) {
  if (this.isModified('passwordHash') && !this.passwordHash.startsWith('$2')) {
    this.passwordHash = await bcrypt.hash(this.passwordHash, 12);
  }
  next();
});

userSchema.statics.findByEmail = function (email) {
  return this.findOne({ email: email.toLowerCase() }).select('+passwordHash');
};

const User = mongoose.model('User', userSchema);""",
},
{
    "request": "Sequelize models with relations and migrations",
    "language": "javascript", "framework": "sequelize",
    "code": """import { Sequelize, DataTypes, Model } from 'sequelize';

const sequelize = new Sequelize(process.env.DATABASE_URL, { dialect: 'postgres', logging: false });

class User extends Model {}
User.init({
  id: { type: DataTypes.UUID, defaultValue: DataTypes.UUIDV4, primaryKey: true },
  email: { type: DataTypes.STRING, allowNull: false, unique: true, validate: { isEmail: true } },
  passwordHash: { type: DataTypes.STRING, allowNull: false },
}, { sequelize, modelName: 'user' });

class Order extends Model {}
Order.init({
  id: { type: DataTypes.UUID, defaultValue: DataTypes.UUIDV4, primaryKey: true },
  total: { type: DataTypes.DECIMAL(12, 2), allowNull: false },
  status: { type: DataTypes.ENUM('pending', 'paid', 'shipped'), defaultValue: 'pending' },
}, { sequelize, modelName: 'order' });

User.hasMany(Order, { foreignKey: 'userId' });
Order.belongsTo(User, { foreignKey: 'userId' });

await sequelize.sync();""",
},
{
    "request": "Prisma schema, migrations, and queries",
    "language": "javascript", "framework": "prisma",
    "code": """// schema.prisma
// generator client { provider = "prisma-client-js" }
// datasource db   { provider = "postgresql"; url = env("DATABASE_URL") }
//
// model User {
//   id    String  @id @default(cuid())
//   email String  @unique
//   orders Order[]
// }
// model Order {
//   id     String @id @default(cuid())
//   user   User   @relation(fields: [userId], references: [id])
//   userId String
//   total  Decimal
//   status String @default("pending")
// }

import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

const order = await prisma.order.create({
  data: { total: 99.99, status: 'pending', user: { connect: { id: userId } } },
  include: { user: { select: { email: true } } },
});

const recent = await prisma.order.findMany({
  where: { status: 'paid', total: { gte: 50 } },
  orderBy: { createdAt: 'desc' },
  take: 20,
  include: { user: true },
});""",
},
{
    "request": "TypeORM entity, repository, and connection",
    "language": "typescript", "framework": "typeorm",
    "code": """import 'reflect-metadata';
import { DataSource, Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, ManyToOne } from 'typeorm';

@Entity()
export class User {
  @PrimaryGeneratedColumn('uuid') id!: string;
  @Column({ unique: true }) email!: string;
  @Column() passwordHash!: string;
  @CreateDateColumn() createdAt!: Date;
}

@Entity()
export class Order {
  @PrimaryGeneratedColumn('uuid') id!: string;
  @Column('decimal', { precision: 12, scale: 2 }) total!: number;
  @Column({ default: 'pending' }) status!: string;
  @ManyToOne(() => User, { onDelete: 'CASCADE' }) user!: User;
  @CreateDateColumn() createdAt!: Date;
}

export const AppDataSource = new DataSource({
  type: 'postgres', url: process.env.DATABASE_URL,
  synchronize: false, logging: false,
  entities: [User, Order],
  migrations: ['migrations/*.ts'],
});

await AppDataSource.initialize();
const orderRepo = AppDataSource.getRepository(Order);
const order = orderRepo.create({ total: 99, user });
await orderRepo.save(order);""",
},
{
    "request": "Knex query builder with migrations",
    "language": "javascript", "framework": "knex",
    "code": """import knex from 'knex';
const db = knex({ client: 'pg', connection: process.env.DATABASE_URL });

const orders = await db('orders')
  .where({ status: 'paid' })
  .where('total', '>', 50)
  .join('users', 'users.id', 'orders.user_id')
  .select('orders.*', 'users.email')
  .orderBy('orders.created_at', 'desc')
  .limit(20);

await db('orders').insert({ user_id: userId, total: 99, status: 'pending' });
await db('orders').where({ id: orderId }).update({ status: 'paid' });

// migrations/20240101_init.js
exports.up = (knex) => knex.schema.createTable('orders', (t) => {
  t.uuid('id').primary().defaultTo(knex.raw('gen_random_uuid()'));
  t.uuid('user_id').notNullable();
  t.decimal('total', 12, 2).notNullable();
  t.string('status').defaultTo('pending');
  t.timestamps(true, true);
});
exports.down = (knex) => knex.schema.dropTable('orders');""",
},
{
    "request": "Redis client patterns: get/set, pub/sub, lists, sorted sets",
    "language": "javascript", "framework": "ioredis",
    "code": """import Redis from 'ioredis';
const redis = new Redis(process.env.REDIS_URL);

// cache
await redis.set('user:123', JSON.stringify(user), 'EX', 300);
const cached = JSON.parse(await redis.get('user:123') || 'null');

// counter
await redis.incr('page:home:views');

// list / queue
await redis.lpush('jobs', JSON.stringify({ type: 'email', to: 'a@b.com' }));
const job = await redis.brpop('jobs', 0);

// sorted set leaderboard
await redis.zadd('leaderboard', score, userId);
const top10 = await redis.zrevrange('leaderboard', 0, 9, 'WITHSCORES');

// pub/sub
const sub = new Redis(process.env.REDIS_URL);
sub.subscribe('order.events');
sub.on('message', (channel, msg) => console.log(channel, msg));
await redis.publish('order.events', JSON.stringify({ id: 1 }));""",
},
{
    "request": "MySQL with mysql2/promise pool",
    "language": "javascript", "framework": "mysql2",
    "code": """import mysql from 'mysql2/promise';

export const pool = mysql.createPool({
  uri: process.env.DATABASE_URL,
  waitForConnections: true,
  connectionLimit: 20,
  namedPlaceholders: true,
});

const [rows] = await pool.execute(
  'SELECT * FROM orders WHERE user_id = :userId AND status = :status LIMIT 20',
  { userId, status: 'paid' },
);

// transaction
const conn = await pool.getConnection();
try {
  await conn.beginTransaction();
  await conn.execute('INSERT INTO orders (user_id, total) VALUES (?, ?)', [userId, total]);
  await conn.execute('UPDATE products SET stock = stock - 1 WHERE id = ?', [productId]);
  await conn.commit();
} catch (e) {
  await conn.rollback(); throw e;
} finally {
  conn.release();
}""",
},

# ───────────── Auth deeper ─────────────
{
    "request": "Passport.js with Google OAuth2",
    "language": "javascript", "framework": "passport",
    "code": """import passport from 'passport';
import { Strategy as GoogleStrategy } from 'passport-google-oauth20';

passport.use(new GoogleStrategy({
  clientID: process.env.GOOGLE_CLIENT_ID,
  clientSecret: process.env.GOOGLE_CLIENT_SECRET,
  callbackURL: '/api/auth/google/callback',
}, async (_at, _rt, profile, done) => {
  const user = await User.findOneAndUpdate(
    { 'google.id': profile.id },
    { $set: {
        'google.id': profile.id,
        email: profile.emails[0].value,
        firstName: profile.name.givenName,
        avatar: profile.photos[0].value,
    } },
    { upsert: true, new: true },
  );
  done(null, user);
}));

app.get('/api/auth/google', passport.authenticate('google', { scope: ['profile', 'email'] }));
app.get('/api/auth/google/callback',
  passport.authenticate('google', { failureRedirect: '/login' }),
  (req, res) => res.redirect('/dashboard'));""",
},
{
    "request": "TOTP 2FA with speakeasy and QR generation",
    "language": "javascript", "framework": "speakeasy",
    "code": """import speakeasy from 'speakeasy';
import QRCode from 'qrcode';

export async function setup2FA(user) {
  const secret = speakeasy.generateSecret({ name: `MyApp (${user.email})` });
  await User.updateOne({ _id: user._id }, { twoFactorSecret: secret.base32, twoFactorEnabled: false });
  const qrDataUrl = await QRCode.toDataURL(secret.otpauth_url);
  return { qrDataUrl, secret: secret.base32 };
}

export function verify2FA(user, token) {
  return speakeasy.totp.verify({
    secret: user.twoFactorSecret,
    encoding: 'base32',
    token,
    window: 1,
  });
}""",
},
{
    "request": "argon2 password hashing (more secure than bcrypt)",
    "language": "javascript", "framework": "argon2",
    "code": """import argon2 from 'argon2';

export async function hashPassword(plain) {
  return argon2.hash(plain, {
    type: argon2.argon2id,
    memoryCost: 19_456,
    timeCost: 2,
    parallelism: 1,
  });
}

export async function verifyPassword(hash, plain) {
  try { return await argon2.verify(hash, plain); }
  catch { return false; }
}""",
},
{
    "request": "API key auth middleware with rate-limit per key",
    "language": "javascript", "framework": "express",
    "code": """import { ApiKey } from '../models/apiKey.js';

export async function apiKeyAuth(req, res, next) {
  const key = req.headers['x-api-key'];
  if (!key) return res.status(401).json({ error: 'no api key' });
  const record = await ApiKey.findOne({ key, revokedAt: null });
  if (!record) return res.status(401).json({ error: 'invalid key' });
  if (record.expiresAt && record.expiresAt < new Date())
    return res.status(401).json({ error: 'expired' });
  req.apiKey = record;
  await ApiKey.updateOne({ _id: record._id }, { lastUsedAt: new Date(), $inc: { hits: 1 } });
  next();
}

app.use('/api/v1', apiKeyAuth);""",
},

# ───────────── Real-time / Streaming ─────────────
{
    "request": "Socket.IO rooms with auth + presence tracking",
    "language": "javascript", "framework": "socket.io",
    "code": """import { Server } from 'socket.io';
import { createAdapter } from '@socket.io/redis-adapter';
import { redis } from './redis.js';

const io = new Server(server, { cors: { origin: '*' } });
io.adapter(createAdapter(redis, redis.duplicate()));

io.use(async (socket, next) => {
  try {
    socket.user = jwt.verify(socket.handshake.auth.token, process.env.JWT_SECRET);
    next();
  } catch { next(new Error('unauthorized')); }
});

io.on('connection', (socket) => {
  socket.on('room:join', async (roomId) => {
    socket.join(roomId);
    io.to(roomId).emit('presence', { user: socket.user.email, action: 'joined' });
  });
  socket.on('message', ({ roomId, text }) => {
    io.to(roomId).emit('message', { user: socket.user.email, text, ts: Date.now() });
  });
  socket.on('disconnecting', () => {
    for (const room of socket.rooms) {
      socket.to(room).emit('presence', { user: socket.user.email, action: 'left' });
    }
  });
});""",
},
{
    "request": "raw WebSocket server with ws library",
    "language": "javascript", "framework": "ws",
    "code": """import { WebSocketServer } from 'ws';

const wss = new WebSocketServer({ server });
const clients = new Map();

wss.on('connection', (ws, req) => {
  const id = crypto.randomUUID();
  clients.set(id, ws);
  ws.send(JSON.stringify({ type: 'welcome', id }));

  ws.on('message', (raw) => {
    try {
      const msg = JSON.parse(raw);
      for (const [cid, c] of clients) {
        if (cid !== id && c.readyState === c.OPEN) c.send(JSON.stringify(msg));
      }
    } catch (e) { ws.send(JSON.stringify({ error: 'bad json' })); }
  });

  ws.on('close', () => clients.delete(id));
});

setInterval(() => wss.clients.forEach(c => c.ping()), 30_000);""",
},
{
    "request": "stream a large CSV download from a database query",
    "language": "javascript", "framework": "express",
    "code": """import { stringify } from 'csv-stringify';

router.get('/orders.csv', async (req, res) => {
  res.set({
    'Content-Type': 'text/csv',
    'Content-Disposition': 'attachment; filename=orders.csv',
  });
  const cursor = Order.find({ status: 'paid' }).lean().cursor();
  const stringifier = stringify({ header: true, columns: ['id', 'total', 'status', 'createdAt'] });
  cursor.on('data', (doc) => stringifier.write(doc));
  cursor.on('end', () => stringifier.end());
  cursor.on('error', () => stringifier.end());
  stringifier.pipe(res);
});""",
},

# ───────────── File handling ─────────────
{
    "request": "image upload + resize with sharp",
    "language": "javascript", "framework": "sharp",
    "code": """import multer from 'multer';
import sharp from 'sharp';
import { mkdir } from 'fs/promises';
import path from 'path';

const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 5 * 1024 * 1024 } });

router.post('/avatar', upload.single('avatar'), async (req, res) => {
  await mkdir('uploads/avatars', { recursive: true });
  const filename = `${req.user.id}-${Date.now()}.webp`;
  const filepath = path.join('uploads/avatars', filename);
  await sharp(req.file.buffer)
    .resize(512, 512, { fit: 'cover' })
    .webp({ quality: 85 })
    .toFile(filepath);
  await User.updateOne({ _id: req.user.id }, { avatar: `/uploads/avatars/${filename}` });
  res.json({ url: `/uploads/avatars/${filename}` });
});""",
},
{
    "request": "S3 upload with AWS SDK v3 + presigned URLs",
    "language": "javascript", "framework": "aws-sdk-v3",
    "code": """import { S3Client, PutObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

const s3 = new S3Client({ region: process.env.AWS_REGION });
const BUCKET = process.env.S3_BUCKET;

export async function uploadBuffer(key, buffer, contentType) {
  await s3.send(new PutObjectCommand({ Bucket: BUCKET, Key: key, Body: buffer, ContentType: contentType }));
  return `https://${BUCKET}.s3.amazonaws.com/${key}`;
}

export async function presignedUploadUrl(key, contentType, expiresIn = 300) {
  const cmd = new PutObjectCommand({ Bucket: BUCKET, Key: key, ContentType: contentType });
  return getSignedUrl(s3, cmd, { expiresIn });
}

export async function presignedDownloadUrl(key, expiresIn = 3600) {
  const cmd = new GetObjectCommand({ Bucket: BUCKET, Key: key });
  return getSignedUrl(s3, cmd, { expiresIn });
}""",
},
{
    "request": "parse CSV stream with csv-parse",
    "language": "javascript", "framework": "csv-parse",
    "code": """import { parse } from 'csv-parse';
import { createReadStream } from 'fs';

const parser = createReadStream('users.csv').pipe(
  parse({ columns: true, skip_empty_lines: true, trim: true }),
);

let count = 0;
for await (const row of parser) {
  await User.create({ email: row.email, name: row.name });
  count++;
}
console.log(`imported ${count} users`);""",
},

# ───────────── Background jobs ─────────────
{
    "request": "BullMQ job queue with worker and scheduler",
    "language": "javascript", "framework": "bullmq",
    "code": """// queues/email.js
import { Queue, Worker, QueueEvents } from 'bullmq';
import IORedis from 'ioredis';

const connection = new IORedis(process.env.REDIS_URL, { maxRetriesPerRequest: null });

export const emailQueue = new Queue('email', { connection });
export const emailEvents = new QueueEvents('email', { connection });

new Worker('email', async (job) => {
  const { to, subject, body } = job.data;
  await sendEmail(to, subject, body);
}, { connection, concurrency: 5 });

// enqueue:
await emailQueue.add('welcome', { to: user.email, subject: 'Welcome!', body: '...' }, {
  attempts: 3,
  backoff: { type: 'exponential', delay: 1000 },
  removeOnComplete: 100,
  removeOnFail: 500,
});

// scheduled / repeat:
await emailQueue.add('daily-digest', {}, { repeat: { pattern: '0 9 * * *' } });""",
},
{
    "request": "node-cron for scheduled tasks",
    "language": "javascript", "framework": "node-cron",
    "code": """import cron from 'node-cron';

cron.schedule('0 2 * * *', async () => {
  console.log('running nightly cleanup');
  await Order.deleteMany({ status: 'cancelled', createdAt: { $lt: new Date(Date.now() - 30 * 86400_000) } });
}, { timezone: 'UTC' });

cron.schedule('*/5 * * * *', async () => {
  await pingHealthChecks();
});""",
},
{
    "request": "send email with nodemailer (SMTP + SES)",
    "language": "javascript", "framework": "nodemailer",
    "code": """import nodemailer from 'nodemailer';

export const mailer = nodemailer.createTransport({
  host: process.env.SMTP_HOST,
  port: parseInt(process.env.SMTP_PORT || '587'),
  secure: false,
  auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
});

export async function sendEmail(to, subject, html, text) {
  return mailer.sendMail({
    from: `"My App" <${process.env.MAIL_FROM}>`,
    to, subject, html, text,
  });
}

// HTML template via handlebars/ejs:
import ejs from 'ejs';
import { readFile } from 'fs/promises';
async function renderTemplate(name, data) {
  const tpl = await readFile(`templates/${name}.ejs`, 'utf8');
  return ejs.render(tpl, data);
}""",
},

# ───────────── Logging / Observability ─────────────
{
    "request": "structured logging with pino",
    "language": "javascript", "framework": "pino",
    "code": """import pino from 'pino';
import pinoHttp from 'pino-http';

export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  redact: ['req.headers.authorization', 'password', 'creditCard'],
  ...(process.env.NODE_ENV !== 'production' && {
    transport: { target: 'pino-pretty', options: { translateTime: 'HH:MM:ss', colorize: true } },
  }),
});

app.use(pinoHttp({ logger, customLogLevel: (_req, res, err) => err || res.statusCode >= 500 ? 'error' : 'info' }));

logger.info({ userId: 123 }, 'order placed');
logger.error({ err }, 'failed to process');""",
},
{
    "request": "OpenTelemetry tracing in Node.js",
    "language": "javascript", "framework": "opentelemetry",
    "code": """import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';

const sdk = new NodeSDK({
  serviceName: process.env.SERVICE_NAME || 'api',
  traceExporter: new OTLPTraceExporter({ url: process.env.OTLP_ENDPOINT || 'http://localhost:4318/v1/traces' }),
  instrumentations: [getNodeAutoInstrumentations()],
});
sdk.start();
process.on('SIGTERM', () => sdk.shutdown());""",
},

# ───────────── Testing ─────────────
{
    "request": "Vitest + supertest integration tests",
    "language": "typescript", "framework": "vitest",
    "code": """import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import request from 'supertest';
import app from '../src/app';
import { connect, disconnect, clear } from './db.js';

beforeAll(async () => { await connect(); });
afterAll(async () => { await disconnect(); });
beforeEach(async () => { await clear(); });

describe('orders', () => {
  it('creates an order', async () => {
    const r = await request(app).post('/api/orders').send({ productId: 'p1', quantity: 2 });
    expect(r.status).toBe(201);
    expect(r.body.total).toBeGreaterThan(0);
  });
});""",
},
{
    "request": "MongoDB Memory Server for isolated tests",
    "language": "javascript", "framework": "mongodb-memory-server",
    "code": """import { MongoMemoryServer } from 'mongodb-memory-server';
import mongoose from 'mongoose';

let mongo;
export async function connect() {
  mongo = await MongoMemoryServer.create();
  await mongoose.connect(mongo.getUri());
}
export async function disconnect() {
  await mongoose.disconnect();
  await mongo.stop();
}
export async function clear() {
  for (const c of Object.values(mongoose.connection.collections)) await c.deleteMany({});
}""",
},

# ───────────── TypeScript ─────────────
{
    "request": "TypeScript Express app with typed request/response",
    "language": "typescript", "framework": "express",
    "code": """import express, { Request, Response, NextFunction } from 'express';

interface AuthUser { id: string; email: string; }

declare global {
  namespace Express { interface Request { user?: AuthUser } }
}

interface CreateOrderBody { productId: string; quantity: number; }

const router = express.Router();
router.post('/', async (req: Request<{}, {}, CreateOrderBody>, res: Response, next: NextFunction) => {
  try {
    const order = await orderService.create({ ...req.body, userId: req.user!.id });
    res.status(201).json(order);
  } catch (e) { next(e); }
});

export default router;""",
},
{
    "request": "tRPC server with React client",
    "language": "typescript", "framework": "trpc",
    "code": """// server/router.ts
import { initTRPC, TRPCError } from '@trpc/server';
import { z } from 'zod';

const t = initTRPC.create();
export const appRouter = t.router({
  orders: t.router({
    list: t.procedure.query(async () => Order.find().lean()),
    create: t.procedure
      .input(z.object({ productId: z.string(), quantity: z.number().int().positive() }))
      .mutation(async ({ input, ctx }) => Order.create({ ...input, user: ctx.user.id })),
  }),
});
export type AppRouter = typeof appRouter;

// client.ts
import { createTRPCReact, httpBatchLink } from '@trpc/react-query';
import type { AppRouter } from '../server/router';
export const trpc = createTRPCReact<AppRouter>();
const client = trpc.createClient({ links: [httpBatchLink({ url: '/trpc' })] });

// usage in component:
// const { data } = trpc.orders.list.useQuery();""",
},

# ───────────── Performance / Deploy ─────────────
{
    "request": "PM2 ecosystem config for production",
    "language": "javascript", "framework": "pm2",
    "code": """// ecosystem.config.cjs
module.exports = {
  apps: [{
    name: 'api',
    script: 'dist/server.js',
    instances: 'max',
    exec_mode: 'cluster',
    env: { NODE_ENV: 'production', PORT: 3000 },
    max_memory_restart: '500M',
    error_file: '/var/log/api/err.log',
    out_file: '/var/log/api/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    autorestart: true,
    watch: false,
  }],
};

// start:  pm2 start ecosystem.config.cjs
// reload: pm2 reload api  (zero-downtime)""",
},
{
    "request": "Dockerfile for production Node.js with pnpm + non-root user",
    "language": "dockerfile", "framework": "docker",
    "code": """FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@latest --activate

FROM base AS deps
WORKDIR /app
COPY pnpm-lock.yaml package.json ./
RUN pnpm install --frozen-lockfile --prod

FROM base AS build
WORKDIR /app
COPY pnpm-lock.yaml package.json ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json .
USER node
EXPOSE 3000
CMD ["node", "dist/server.js"]""",
},
{
    "request": "in-memory LRU cache layer in front of a slow function",
    "language": "javascript", "framework": "lru-cache",
    "code": """import { LRUCache } from 'lru-cache';

const cache = new LRUCache({
  max: 1000,
  ttl: 5 * 60_000,
  fetchMethod: async (key) => {
    return await db.products.findOne({ id: key });
  },
});

export const getProduct = (id) => cache.fetch(id);""",
},

# ───────────── Microservices / Messaging ─────────────
{
    "request": "RabbitMQ producer + consumer with amqplib",
    "language": "javascript", "framework": "amqplib",
    "code": """import amqp from 'amqplib';
const conn = await amqp.connect(process.env.AMQP_URL);
const ch = await conn.createChannel();
await ch.assertQueue('orders', { durable: true });

// producer
ch.sendToQueue('orders', Buffer.from(JSON.stringify({ id: 1 })), { persistent: true });

// consumer
ch.prefetch(10);
ch.consume('orders', async (msg) => {
  if (!msg) return;
  try {
    const data = JSON.parse(msg.content.toString());
    await processOrder(data);
    ch.ack(msg);
  } catch (e) {
    ch.nack(msg, false, false);
  }
}, { noAck: false });""",
},
{
    "request": "gRPC server in Node.js",
    "language": "javascript", "framework": "grpc",
    "code": """import grpc from '@grpc/grpc-js';
import protoLoader from '@grpc/proto-loader';

const pkgDef = protoLoader.loadSync('orders.proto', { keepCase: true });
const proto = grpc.loadPackageDefinition(pkgDef).orders;

const server = new grpc.Server();
server.addService(proto.OrderService.service, {
  GetOrder: async (call, cb) => {
    const order = await Order.findById(call.request.id);
    if (!order) return cb({ code: grpc.status.NOT_FOUND, message: 'not found' });
    cb(null, order);
  },
  CreateOrder: async (call, cb) => {
    const order = await Order.create(call.request);
    cb(null, order);
  },
});

server.bindAsync('0.0.0.0:50051', grpc.ServerCredentials.createInsecure(), () => {
  server.start();
});""",
},
{
    "request": "webhook receiver with signature verification (Stripe)",
    "language": "javascript", "framework": "stripe",
    "code": """import Stripe from 'stripe';
const stripe = new Stripe(process.env.STRIPE_SECRET);

router.post('/webhooks/stripe',
  express.raw({ type: 'application/json' }),
  async (req, res) => {
    let event;
    try {
      event = stripe.webhooks.constructEvent(
        req.body, req.headers['stripe-signature'], process.env.STRIPE_WEBHOOK_SECRET
      );
    } catch (err) { return res.status(400).send(`bad sig: ${err.message}`); }

    switch (event.type) {
      case 'checkout.session.completed':
        await handleCheckoutComplete(event.data.object);
        break;
      case 'invoice.payment_failed':
        await handlePaymentFailed(event.data.object);
        break;
    }
    res.json({ received: true });
  });""",
},
{
    "request": "Twilio SMS sending",
    "language": "javascript", "framework": "twilio",
    "code": """import twilio from 'twilio';
const client = twilio(process.env.TWILIO_SID, process.env.TWILIO_AUTH);

export async function sendSMS(to, body) {
  return client.messages.create({
    from: process.env.TWILIO_FROM,
    to, body,
  });
}""",
},

# ───────────── Misc patterns ─────────────
{
    "request": "Express healthcheck with DB + Redis status",
    "language": "javascript", "framework": "express",
    "code": """app.get('/api/health', async (_req, res) => {
  const checks = await Promise.allSettled([
    mongoose.connection.db.admin().ping(),
    redis.ping(),
  ]);
  const ok = checks.every(c => c.status === 'fulfilled');
  res.status(ok ? 200 : 503).json({
    ok,
    services: {
      db: checks[0].status === 'fulfilled' ? 'up' : 'down',
      redis: checks[1].status === 'fulfilled' ? 'up' : 'down',
    },
    uptime: process.uptime(),
    memory: process.memoryUsage().rss,
  });
});""",
},
{
    "request": "soft-delete plugin for Mongoose",
    "language": "javascript", "framework": "mongoose",
    "code": """export function softDelete(schema) {
  schema.add({ deletedAt: { type: Date, default: null, index: true } });
  schema.pre(['find', 'findOne', 'findOneAndUpdate', 'countDocuments'], function () {
    if (this.getQuery().withDeleted) { delete this.getQuery().withDeleted; return; }
    this.where({ deletedAt: null });
  });
  schema.methods.softDelete = function () { this.deletedAt = new Date(); return this.save(); };
  schema.methods.restore = function () { this.deletedAt = null; return this.save(); };
}

orderSchema.plugin(softDelete);""",
},
{
    "request": "i18n translation middleware with i18next",
    "language": "javascript", "framework": "i18next",
    "code": """import i18next from 'i18next';
import middleware from 'i18next-http-middleware';
import Backend from 'i18next-fs-backend';

await i18next.use(Backend).use(middleware.LanguageDetector).init({
  fallbackLng: 'en',
  preload: ['en', 'es', 'fr', 'ne'],
  backend: { loadPath: './locales/{{lng}}/{{ns}}.json' },
});

app.use(middleware.handle(i18next));

router.get('/welcome', (req, res) => {
  res.json({ message: req.t('welcome.greeting', { name: req.user?.name }) });
});""",
},
{
    "request": "OpenAPI/Swagger docs generated from routes",
    "language": "javascript", "framework": "swagger-jsdoc",
    "code": """import swaggerJSDoc from 'swagger-jsdoc';
import swaggerUi from 'swagger-ui-express';

const spec = swaggerJSDoc({
  definition: {
    openapi: '3.0.0',
    info: { title: 'API', version: '1.0.0' },
    components: { securitySchemes: { bearerAuth: { type: 'http', scheme: 'bearer' } } },
    security: [{ bearerAuth: [] }],
  },
  apis: ['./src/routes/*.js'],
});

app.use('/api/docs', swaggerUi.serve, swaggerUi.setup(spec));

/**
 * @openapi
 * /api/orders:
 *   get:
 *     summary: List orders
 *     responses:
 *       200:
 *         description: ok
 */
router.get('/', ctrl.list);""",
},
{
    "request": "request id + correlation id middleware",
    "language": "javascript", "framework": "express",
    "code": """import { randomUUID } from 'crypto';

export function requestId(req, res, next) {
  const id = req.headers['x-request-id'] || randomUUID();
  req.id = id;
  res.set('X-Request-Id', id);
  next();
}

app.use(requestId);
// pino-http will pick up req.id automatically""",
},
{
    "request": "feature flag system with environment-based rollout",
    "language": "javascript", "framework": "stdlib",
    "code": """const FLAGS = {
  newCheckoutFlow: { enabled: process.env.FLAG_NEW_CHECKOUT === '1', rollout: 0.25 },
  betaFeatures: { enabled: true, allowedUsers: ['beta@x.com'] },
};

export function isEnabled(name, user) {
  const f = FLAGS[name];
  if (!f) return false;
  if (!f.enabled) return false;
  if (f.allowedUsers?.includes(user?.email)) return true;
  if (typeof f.rollout === 'number') {
    const hash = [...(user?.id || '')].reduce((h, c) => h + c.charCodeAt(0), 0);
    return (hash % 100) / 100 < f.rollout;
  }
  return true;
}""",
},
{
    "request": "circuit breaker pattern with opossum",
    "language": "javascript", "framework": "opossum",
    "code": """import CircuitBreaker from 'opossum';
import axios from 'axios';

const breaker = new CircuitBreaker(
  (url) => axios.get(url, { timeout: 3000 }).then(r => r.data),
  { timeout: 3000, errorThresholdPercentage: 50, resetTimeout: 30_000 },
);
breaker.fallback(() => ({ source: 'cache', data: null }));
breaker.on('open', () => logger.warn('breaker opened'));
breaker.on('halfOpen', () => logger.info('trying again'));

const data = await breaker.fire('https://api.shaky.com/v1/data');""",
},
{
    "request": "deep equality + clone with structuredClone (Node 18+)",
    "language": "javascript", "framework": "stdlib",
    "code": """const original = { user: { id: 1, prefs: ['a', 'b'] }, ts: new Date() };
const copy = structuredClone(original);
copy.user.prefs.push('c');
console.log(original.user.prefs);  // ['a', 'b']  — untouched

// for shallow:
const shallow = { ...original };

// for deep equality without lodash:
const equal = (a, b) =>
  a === b ||
  (typeof a === 'object' && typeof b === 'object' &&
    JSON.stringify(a) === JSON.stringify(b));""",
},
{
    "request": "polling job that respects backpressure",
    "language": "javascript", "framework": "node-core",
    "code": """async function pollLoop({ fn, intervalMs, signal }) {
  while (!signal.aborted) {
    const start = Date.now();
    try { await fn(); } catch (e) { logger.error({ e }, 'poll failed'); }
    const elapsed = Date.now() - start;
    const wait = Math.max(0, intervalMs - elapsed);
    if (wait) await new Promise(r => setTimeout(r, wait));
  }
}

const ac = new AbortController();
pollLoop({ fn: syncOrders, intervalMs: 30_000, signal: ac.signal });
process.on('SIGTERM', () => ac.abort());""",
},
{
    "request": "memoize a function with TTL",
    "language": "javascript", "framework": "stdlib",
    "code": """export function memoize(fn, { ttl = 60_000, keyFn = (...a) => JSON.stringify(a) } = {}) {
  const cache = new Map();
  return (...args) => {
    const k = keyFn(...args);
    const hit = cache.get(k);
    if (hit && hit.exp > Date.now()) return hit.value;
    const value = fn(...args);
    cache.set(k, { value, exp: Date.now() + ttl });
    return value;
  };
}

const slowFn = (id) => db.users.findOne({ id });
const cached = memoize(slowFn, { ttl: 30_000 });""",
},
{
    "request": "exponential backoff retry helper",
    "language": "javascript", "framework": "stdlib",
    "code": """export async function retry(fn, { tries = 5, base = 100, factor = 2, jitter = true } = {}) {
  let lastErr;
  for (let i = 0; i < tries; i++) {
    try { return await fn(); }
    catch (e) {
      lastErr = e;
      if (i === tries - 1) break;
      const delay = base * Math.pow(factor, i) * (jitter ? (0.5 + Math.random()) : 1);
      await new Promise(r => setTimeout(r, delay));
    }
  }
  throw lastErr;
}

const data = await retry(() => fetch(url).then(r => r.json()));""",
},
]
