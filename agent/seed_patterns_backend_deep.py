"""Massive deep backend pattern collection — production Node.js / Express / MongoDB /
WebSockets / queues / security / scaling / microservices.

These complement seed_patterns_nodejs.py with deeper, real-world patterns."""
from __future__ import annotations


BACKEND_DEEP_SEED: list[dict] = [

# ════════ Express — advanced ════════

{
    "request": "Express versioned API with /v1 /v2 mounted routers",
    "language": "javascript", "framework": "express",
    "code": """import v1 from './api/v1/index.js';
import v2 from './api/v2/index.js';

app.use('/api/v1', v1);
app.use('/api/v2', v2);

// version negotiation via header (alternative to URL):
app.use('/api', (req, res, next) => {
  const v = req.headers['accept-version'] || 'v1';
  if (v === 'v2') return v2(req, res, next);
  return v1(req, res, next);
});

// deprecation warnings on v1:
v1.use((_req, res, next) => {
  res.set('Deprecation', 'true');
  res.set('Sunset', 'Sat, 31 Dec 2026 23:59:59 GMT');
  next();
});""",
},
{
    "request": "Express multi-tenancy via subdomain or header",
    "language": "javascript", "framework": "express",
    "code": """import { Tenant } from './models/tenant.js';

app.use(async (req, res, next) => {
  const slug = req.headers['x-tenant'] || req.subdomains[0];
  if (!slug) return res.status(400).json({ error: 'no tenant' });
  const tenant = await Tenant.findOne({ slug, active: true }).lean();
  if (!tenant) return res.status(404).json({ error: 'unknown tenant' });
  req.tenant = tenant;
  next();
});

// scope every Mongo query:
mongoose.plugin((schema) => {
  schema.pre(/^find/, function () {
    if (!this.getQuery().tenant && this.options?.req) {
      this.where({ tenant: this.options.req.tenant._id });
    }
  });
});""",
},
{
    "request": "Express idempotency keys for safe POST retries",
    "language": "javascript", "framework": "express",
    "code": """import { redis } from './redis.js';

export function idempotency() {
  return async (req, res, next) => {
    if (!['POST', 'PUT', 'PATCH'].includes(req.method)) return next();
    const key = req.headers['idempotency-key'];
    if (!key) return next();

    const cacheKey = `idem:${req.user?.id || req.ip}:${key}`;
    const cached = await redis.get(cacheKey);
    if (cached) {
      const { status, body } = JSON.parse(cached);
      return res.status(status).set('X-Idempotent-Replay', 'true').json(body);
    }

    const json = res.json.bind(res);
    res.json = (body) => {
      redis.setex(cacheKey, 86400, JSON.stringify({ status: res.statusCode, body }));
      return json(body);
    };
    next();
  };
}

app.post('/api/payments', idempotency(), createPayment);""",
},
{
    "request": "Express request tracing with continuation-local-storage (AsyncLocalStorage)",
    "language": "javascript", "framework": "express",
    "code": """import { AsyncLocalStorage } from 'async_hooks';
import { randomUUID } from 'crypto';

export const ctx = new AsyncLocalStorage();

export function tracing(req, res, next) {
  const id = req.headers['x-request-id'] || randomUUID();
  res.set('X-Request-Id', id);
  ctx.run({ requestId: id, userId: req.user?.id, startedAt: Date.now() }, next);
}

export function getCtx() {
  return ctx.getStore() || {};
}

// in any helper, deep in the call stack:
import { getCtx } from './tracing.js';
function logger(msg) {
  const { requestId, userId } = getCtx();
  console.log(`[${requestId}] [user:${userId}] ${msg}`);
}""",
},
{
    "request": "Express streaming JSON response for large dataset",
    "language": "javascript", "framework": "express",
    "code": """app.get('/api/orders.ndjson', async (req, res) => {
  res.set('Content-Type', 'application/x-ndjson');
  const cursor = Order.find().lean().cursor();
  for await (const doc of cursor) {
    if (!res.write(JSON.stringify(doc) + '\\n')) {
      await new Promise(r => res.once('drain', r));
    }
  }
  res.end();
});

// or full JSON streaming with stream-json:
import { Readable } from 'stream';
import JSONStream from 'JSONStream';

app.get('/api/orders.json', (req, res) => {
  res.set('Content-Type', 'application/json');
  Order.find().lean().cursor()
    .pipe(JSONStream.stringify('[', ',', ']'))
    .pipe(res);
});""",
},
{
    "request": "Express background task scheduler — fire-and-forget after response",
    "language": "javascript", "framework": "express",
    "code": """import { setImmediate } from 'timers/promises';

app.post('/api/orders', async (req, res) => {
  const order = await Order.create({ ...req.body, user: req.user.id });
  res.status(201).json(order);

  // run AFTER response is sent — does not block client
  setImmediate(async () => {
    try {
      await sendOrderConfirmationEmail(order);
      await analytics.track('order_placed', order);
      await emailQueue.add('admin-notify', { orderId: order._id });
    } catch (e) {
      logger.error({ orderId: order._id, e }, 'post-order tasks failed');
    }
  });
});""",
},
{
    "request": "Express response cache middleware (Redis)",
    "language": "javascript", "framework": "express",
    "code": """import { redis } from './redis.js';

export function cacheResponse({ ttl = 60, key = (req) => req.originalUrl } = {}) {
  return async (req, res, next) => {
    if (req.method !== 'GET') return next();
    const k = `cache:${typeof key === 'function' ? key(req) : key}`;
    const hit = await redis.get(k);
    if (hit) {
      res.set('X-Cache', 'HIT');
      return res.type('json').send(hit);
    }
    res.set('X-Cache', 'MISS');
    const json = res.json.bind(res);
    res.json = (body) => {
      if (res.statusCode === 200) redis.setex(k, ttl, JSON.stringify(body));
      return json(body);
    };
    next();
  };
}

app.get('/api/products', cacheResponse({ ttl: 300 }), listProducts);

// invalidate on mutation:
async function invalidate(pattern) {
  const keys = await redis.keys(`cache:${pattern}`);
  if (keys.length) await redis.del(keys);
}""",
},
{
    "request": "Express ETag and conditional GET",
    "language": "javascript", "framework": "express",
    "code": """import { createHash } from 'crypto';

app.get('/api/products/:id', async (req, res) => {
  const product = await Product.findById(req.params.id).lean();
  if (!product) return res.status(404).end();

  const etag = `\\"${createHash('md5').update(JSON.stringify(product)).digest('hex')}\\"`;
  res.set('ETag', etag);
  res.set('Cache-Control', 'private, max-age=60');

  if (req.headers['if-none-match'] === etag) return res.status(304).end();
  res.json(product);
});""",
},
{
    "request": "Express centralized async error wrapping for all routes",
    "language": "javascript", "framework": "express",
    "code": """// patches the express Router to auto-wrap async handlers
import { Router } from 'express';

function asyncify(fn) {
  return (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
}

['get', 'post', 'put', 'patch', 'delete', 'all'].forEach((method) => {
  const original = Router.prototype[method];
  Router.prototype[method] = function (path, ...handlers) {
    return original.call(this, path, ...handlers.map((h) => h.constructor.name === 'AsyncFunction' ? asyncify(h) : h));
  };
});

// now this just works:
router.get('/:id', async (req, res) => {
  const x = await Order.findById(req.params.id);
  if (!x) throw new AppError('not found', 404);
  res.json(x);
});""",
},
{
    "request": "Express graceful reload (SIGHUP) for config changes",
    "language": "javascript", "framework": "express",
    "code": """let config = await loadConfig();

process.on('SIGHUP', async () => {
  console.log('SIGHUP — reloading config');
  try {
    config = await loadConfig();
    bus.emit('config:reloaded', config);
  } catch (e) {
    console.error('reload failed', e);
  }
});

app.use((req, _res, next) => { req.config = config; next(); });

// can also reload via admin endpoint:
app.post('/admin/reload', adminAuth, async (_req, res) => {
  config = await loadConfig();
  res.json({ reloaded: true });
});""",
},
{
    "request": "Express keep-alive timeout tuning behind a load balancer",
    "language": "javascript", "framework": "express",
    "code": """const server = app.listen(PORT);

// AWS ALB has 60s idle timeout — Node default is 5s which causes 502s under load
server.keepAliveTimeout = 65_000;
server.headersTimeout = 70_000;

// trust proxy for X-Forwarded-* headers
app.set('trust proxy', 1);""",
},
{
    "request": "Express robust file upload with virus scan + cleanup",
    "language": "javascript", "framework": "express",
    "code": """import multer from 'multer';
import { unlink } from 'fs/promises';
import NodeClam from 'clamscan';

const clam = await new NodeClam().init({ clamdscan: { socket: '/var/run/clamav/clamd.ctl' } });
const upload = multer({ dest: 'uploads/tmp/', limits: { fileSize: 25 * 1024 * 1024 } });

router.post('/upload', upload.single('file'), async (req, res, next) => {
  try {
    const { isInfected, viruses } = await clam.isInfected(req.file.path);
    if (isInfected) {
      await unlink(req.file.path);
      return res.status(400).json({ error: 'malware detected', viruses });
    }
    const final = await persistFile(req.file);
    await unlink(req.file.path);
    res.json(final);
  } catch (e) {
    if (req.file) await unlink(req.file.path).catch(() => {});
    next(e);
  }
});""",
},

# ════════ MongoDB / Mongoose — advanced ════════

{
    "request": "Mongoose transaction across multiple collections",
    "language": "javascript", "framework": "mongoose",
    "code": """async function placeOrder({ userId, items }) {
  const session = await mongoose.startSession();
  session.startTransaction();
  try {
    const total = items.reduce((s, i) => s + i.price * i.qty, 0);
    const [order] = await Order.create([{ user: userId, items, total, status: 'pending' }], { session });

    for (const it of items) {
      const result = await Product.updateOne(
        { _id: it.productId, stock: { $gte: it.qty } },
        { $inc: { stock: -it.qty } },
        { session }
      );
      if (result.modifiedCount === 0) throw new Error(`out of stock: ${it.productId}`);
    }

    await User.updateOne({ _id: userId }, { $inc: { orderCount: 1 } }, { session });
    await session.commitTransaction();
    return order;
  } catch (e) {
    await session.abortTransaction();
    throw e;
  } finally {
    session.endSession();
  }
}""",
},
{
    "request": "Mongoose change stream — react to DB changes in real time",
    "language": "javascript", "framework": "mongoose",
    "code": """// requires replica set
const stream = Order.watch([
  { $match: { 'fullDocument.status': 'paid', operationType: 'update' } },
], { fullDocument: 'updateLookup' });

stream.on('change', async (change) => {
  const order = change.fullDocument;
  await fulfillmentQueue.add('process', { orderId: order._id });
  io.to(`user:${order.user}`).emit('order:updated', order);
});

stream.on('error', async (err) => {
  console.error('change stream error', err);
  setTimeout(() => location.reload(), 5000);  // resume strategy
});""",
},
{
    "request": "Mongoose aggregation — $lookup join, $facet for parallel pipelines",
    "language": "javascript", "framework": "mongoose",
    "code": """const dashboard = await Order.aggregate([
  { $match: { createdAt: { $gte: new Date(Date.now() - 30 * 86400e3) } } },
  { $facet: {
      // pipeline 1: revenue by day
      byDay: [
        { $group: {
          _id: { $dateToString: { format: '%Y-%m-%d', date: '$createdAt' } },
          revenue: { $sum: '$total' },
          orders: { $sum: 1 },
        }},
        { $sort: { _id: 1 } },
      ],
      // pipeline 2: top customers
      topCustomers: [
        { $group: { _id: '$user', total: { $sum: '$total' }, orders: { $sum: 1 } } },
        { $sort: { total: -1 } },
        { $limit: 10 },
        { $lookup: { from: 'users', localField: '_id', foreignField: '_id', as: 'user' } },
        { $unwind: '$user' },
        { $project: { _id: 0, name: '$user.name', email: '$user.email', total: 1, orders: 1 } },
      ],
      // pipeline 3: status breakdown
      byStatus: [
        { $group: { _id: '$status', count: { $sum: 1 } } },
      ],
  }},
]);""",
},
{
    "request": "Mongoose geospatial queries — find nearby restaurants",
    "language": "javascript", "framework": "mongoose",
    "code": """const restaurantSchema = new mongoose.Schema({
  name: String,
  location: {
    type: { type: String, enum: ['Point'], required: true },
    coordinates: { type: [Number], required: true },  // [lng, lat]
  },
});
restaurantSchema.index({ location: '2dsphere' });

// find within 5km of user's coordinates:
const nearby = await Restaurant.find({
  location: {
    $near: {
      $geometry: { type: 'Point', coordinates: [userLng, userLat] },
      $maxDistance: 5000,  // meters
    },
  },
}).limit(20);

// or with distance returned:
const withDistance = await Restaurant.aggregate([
  { $geoNear: {
      near: { type: 'Point', coordinates: [userLng, userLat] },
      distanceField: 'distance',
      maxDistance: 5000,
      spherical: true,
  }},
  { $limit: 20 },
]);""",
},
{
    "request": "MongoDB text search index + relevance scoring",
    "language": "javascript", "framework": "mongoose",
    "code": """productSchema.index({ name: 'text', description: 'text', tags: 'text' }, {
  weights: { name: 10, tags: 5, description: 1 },
  default_language: 'english',
});

const results = await Product.find(
  { $text: { $search: query } },
  { score: { $meta: 'textScore' } }
)
  .sort({ score: { $meta: 'textScore' } })
  .limit(20);""",
},
{
    "request": "Mongoose discriminator — single collection inheritance",
    "language": "javascript", "framework": "mongoose",
    "code": """const userSchema = new mongoose.Schema({ email: String, name: String }, { discriminatorKey: 'kind' });
const User = mongoose.model('User', userSchema);

const Customer = User.discriminator('Customer', new mongoose.Schema({
  defaultAddress: String,
  loyaltyPoints: { type: Number, default: 0 },
}));

const Vendor = User.discriminator('Vendor', new mongoose.Schema({
  storeName: String,
  taxId: String,
  payoutAccount: String,
}));

await Customer.create({ email: 'a@b.com', name: 'Alice', defaultAddress: '1 Main St' });
await Vendor.create({ email: 'shop@x.com', name: 'Store', storeName: 'Acme' });

await User.find();   // returns ALL kinds
await Customer.find();   // only customers""",
},
{
    "request": "Mongoose optimistic locking with __v version key",
    "language": "javascript", "framework": "mongoose",
    "code": """// __v is automatic; enable conflict detection:
const orderSchema = new mongoose.Schema({ status: String }, { optimisticConcurrency: true });

const order = await Order.findById(id);
order.status = 'paid';
try {
  await order.save();
} catch (e) {
  if (e.name === 'VersionError') {
    // someone else updated this doc — re-fetch and retry
    return retryWithFreshDoc();
  }
  throw e;
}

// or via atomic update with version check:
const result = await Order.updateOne(
  { _id: id, __v: expectedVersion },
  { $set: { status: 'paid' }, $inc: { __v: 1 } }
);
if (result.modifiedCount === 0) throw new Error('concurrent modification');""",
},
{
    "request": "Mongoose bulk operations for high throughput",
    "language": "javascript", "framework": "mongoose",
    "code": """const ops = updates.map((u) => ({
  updateOne: {
    filter: { _id: u.id },
    update: { $set: { status: u.status, processedAt: new Date() } },
    upsert: false,
  },
}));

const result = await Order.bulkWrite(ops, { ordered: false });
console.log(`matched: ${result.matchedCount}, modified: ${result.modifiedCount}`);

// inserts: stream via insertMany with limit + lean
const BATCH = 1000;
for (let i = 0; i < items.length; i += BATCH) {
  await Item.insertMany(items.slice(i, i + BATCH), { ordered: false, lean: true });
}""",
},
{
    "request": "Mongoose populate with select + nested",
    "language": "javascript", "framework": "mongoose",
    "code": """const order = await Order.findById(id)
  .populate({
    path: 'user',
    select: 'name email',
  })
  .populate({
    path: 'items.product',
    select: 'name price images',
    populate: { path: 'category', select: 'name slug' },  // nested populate
  })
  .lean();  // huge perf gain when you don't need Mongoose docs""",
},
{
    "request": "Mongoose TTL index — auto-delete expired documents",
    "language": "javascript", "framework": "mongoose",
    "code": """const sessionSchema = new mongoose.Schema({
  token: String,
  userId: mongoose.Types.ObjectId,
  expiresAt: { type: Date, required: true },
});
sessionSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });
// Mongo will delete docs as soon as expiresAt < now (with ~60s background sweep)

// or fixed TTL after creation:
sessionSchema.add({ createdAt: { type: Date, default: Date.now } });
sessionSchema.index({ createdAt: 1 }, { expireAfterSeconds: 86400 });""",
},
{
    "request": "Mongoose partial + compound + unique indexes",
    "language": "javascript", "framework": "mongoose",
    "code": """// compound (sort by user + recency)
orderSchema.index({ user: 1, createdAt: -1 });

// partial — only index docs matching the filter (huge space savings)
orderSchema.index(
  { coupon: 1 },
  { partialFilterExpression: { coupon: { $exists: true } } }
);

// case-insensitive unique email
userSchema.index(
  { email: 1 },
  { unique: true, collation: { locale: 'en', strength: 2 } }
);

// sparse — skip docs missing the field
userSchema.index({ phoneNumber: 1 }, { sparse: true });""",
},
{
    "request": "Mongoose plugin — auditable model (createdBy, updatedBy)",
    "language": "javascript", "framework": "mongoose",
    "code": """import { ctx } from './tracing.js';

export function auditable(schema) {
  schema.add({
    createdBy: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
    updatedBy: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  });
  schema.pre('save', function () {
    const userId = ctx.getStore()?.userId;
    if (this.isNew) this.createdBy = userId;
    this.updatedBy = userId;
  });
  schema.pre(['updateOne', 'findOneAndUpdate'], function () {
    const userId = ctx.getStore()?.userId;
    this.set({ updatedBy: userId });
  });
}

orderSchema.plugin(auditable);""",
},
{
    "request": "Mongo connection retry with exponential backoff",
    "language": "javascript", "framework": "mongoose",
    "code": """async function connect() {
  let attempt = 0;
  while (true) {
    try {
      await mongoose.connect(process.env.MONGO_URI, {
        serverSelectionTimeoutMS: 5000,
        maxPoolSize: 50,
        minPoolSize: 5,
      });
      console.log('mongo connected');
      return;
    } catch (e) {
      attempt++;
      const delay = Math.min(30_000, 1000 * 2 ** attempt);
      console.error(`mongo connect failed (attempt ${attempt}), retrying in ${delay}ms`);
      await new Promise(r => setTimeout(r, delay));
    }
  }
}

mongoose.connection.on('disconnected', () => console.warn('mongo disconnected'));
mongoose.connection.on('reconnected', () => console.log('mongo reconnected'));""",
},
{
    "request": "Mongo distinct + countDocuments + estimatedDocumentCount",
    "language": "javascript", "framework": "mongoose",
    "code": """// distinct — like SELECT DISTINCT
const cities = await Order.distinct('shippingAddress.city', { status: 'paid' });

// countDocuments — accurate but slower (uses query)
const paidCount = await Order.countDocuments({ status: 'paid' });

// estimatedDocumentCount — fast, uses metadata, ignores filter
const totalEstimate = await Order.estimatedDocumentCount();""",
},
{
    "request": "Mongo $merge to materialize aggregation results",
    "language": "javascript", "framework": "mongoose",
    "code": """// Build a daily revenue report and persist it:
await Order.aggregate([
  { $match: { status: 'paid', createdAt: { $gte: yesterday } } },
  { $group: {
      _id: { $dateToString: { format: '%Y-%m-%d', date: '$createdAt' } },
      revenue: { $sum: '$total' },
      orderCount: { $sum: 1 },
  }},
  { $merge: {
      into: 'dailyReports',
      on: '_id',
      whenMatched: 'merge',
      whenNotMatched: 'insert',
  }},
]);

// run nightly via cron — stale reports are updated, new days inserted""",
},

# ════════ WebSockets — advanced ════════

{
    "request": "Socket.IO namespaces, rooms, dynamic connect logic",
    "language": "javascript", "framework": "socket.io",
    "code": """// chat namespace
const chat = io.of('/chat');
chat.use(authMiddleware);
chat.on('connection', (socket) => {
  socket.on('join', async (roomId) => {
    const allowed = await canJoin(socket.user, roomId);
    if (!allowed) return socket.emit('error', 'forbidden');
    socket.join(roomId);
    chat.to(roomId).emit('user:joined', { user: socket.user.email });
  });
});

// admin namespace
const admin = io.of('/admin');
admin.use(adminOnly);
admin.on('connection', (socket) => {
  socket.on('broadcast', (msg) => io.emit('announce', msg));
});

// dynamic namespace per tenant:
const tenantNs = io.of(/^\\/t\\/[^/]+$/);
tenantNs.on('connection', (socket) => {
  const tenantSlug = socket.nsp.name.split('/')[2];
  socket.tenant = tenantSlug;
});""",
},
{
    "request": "Socket.IO acknowledgements + timeouts (request/response over WS)",
    "language": "javascript", "framework": "socket.io",
    "code": """// server: acknowledge a callback when emitted
socket.on('order:create', async (data, cb) => {
  try {
    const order = await Order.create({ ...data, user: socket.user.id });
    cb({ ok: true, order });
  } catch (e) {
    cb({ ok: false, error: e.message });
  }
});

// client: get a typed response with timeout
const result = await socket.timeout(5000).emitWithAck('order:create', { productId, qty });
if (!result.ok) toast.error(result.error);""",
},
{
    "request": "Socket.IO presence + typing indicators in a room",
    "language": "javascript", "framework": "socket.io",
    "code": """const presence = new Map();  // roomId -> Set<userId>

io.on('connection', (socket) => {
  socket.on('room:join', (roomId) => {
    socket.join(roomId);
    if (!presence.has(roomId)) presence.set(roomId, new Set());
    presence.get(roomId).add(socket.user.id);
    io.to(roomId).emit('presence', Array.from(presence.get(roomId)));
  });

  socket.on('typing:start', (roomId) =>
    socket.to(roomId).emit('typing', { user: socket.user.email, typing: true }));
  socket.on('typing:stop', (roomId) =>
    socket.to(roomId).emit('typing', { user: socket.user.email, typing: false }));

  socket.on('disconnect', () => {
    for (const room of socket.rooms) {
      const set = presence.get(room);
      if (set) {
        set.delete(socket.user.id);
        io.to(room).emit('presence', Array.from(set));
      }
    }
  });
});""",
},
{
    "request": "Socket.IO read receipts — track delivered/seen per message",
    "language": "javascript", "framework": "socket.io",
    "code": """socket.on('message:send', async ({ roomId, text, clientId }) => {
  const msg = await Message.create({ room: roomId, sender: socket.user.id, text });
  socket.emit('message:ack', { clientId, serverId: msg._id });
  socket.to(roomId).emit('message:new', msg);
});

socket.on('message:seen', async ({ messageId }) => {
  await Message.updateOne(
    { _id: messageId, seenBy: { $ne: socket.user.id } },
    { $push: { seenBy: socket.user.id } }
  );
  const msg = await Message.findById(messageId).populate('sender', 'email').lean();
  io.to(msg.sender._id.toString()).emit('message:seen', {
    messageId, by: socket.user.id, at: Date.now(),
  });
});""",
},
{
    "request": "Socket.IO scale across servers with Redis adapter",
    "language": "javascript", "framework": "socket.io",
    "code": """import { createAdapter } from '@socket.io/redis-adapter';
import { createClient } from 'redis';

const pub = createClient({ url: process.env.REDIS_URL });
const sub = pub.duplicate();
await Promise.all([pub.connect(), sub.connect()]);
io.adapter(createAdapter(pub, sub));

// now io.to('room1').emit() works across all server instances
// emit from outside socket.io (e.g. an HTTP handler):
import { Emitter } from '@socket.io/redis-emitter';
const emitter = new Emitter(pub);
emitter.to(`user:${userId}`).emit('notification', { kind: 'order_paid' });""",
},
{
    "request": "Socket.IO rate limiting per-event with sliding window",
    "language": "javascript", "framework": "socket.io",
    "code": """const buckets = new Map();
function rateCheck(key, limit, windowMs) {
  const now = Date.now();
  const arr = buckets.get(key) || [];
  const fresh = arr.filter(t => now - t < windowMs);
  fresh.push(now);
  buckets.set(key, fresh);
  return fresh.length <= limit;
}

io.on('connection', (socket) => {
  socket.use(([event, ...args], next) => {
    if (event === 'message:send') {
      if (!rateCheck(`${socket.user.id}:msg`, 30, 60_000)) {
        return next(new Error('rate limit'));
      }
    }
    next();
  });
});""",
},
{
    "request": "Socket.IO live-cursor collaboration",
    "language": "javascript", "framework": "socket.io",
    "code": """// throttle cursor updates server-side
io.on('connection', (socket) => {
  socket.on('cursor:move', ({ roomId, x, y }) => {
    socket.to(roomId).volatile.emit('cursor:remote', {
      user: socket.user.id, x, y, color: socket.user.color, t: Date.now(),
    });
  });
});

// client (React + Tailwind):
ws.on('cursor:remote', ({ user, x, y, color }) => {
  let dot = document.querySelector(`#cursor-${user}`);
  if (!dot) {
    dot = document.createElement('div');
    dot.id = `cursor-${user}`;
    dot.className = 'fixed pointer-events-none w-3 h-3 rounded-full transition-transform';
    dot.style.background = color;
    document.body.appendChild(dot);
  }
  dot.style.transform = `translate(${x}px, ${y}px)`;
});""",
},
{
    "request": "Socket.IO compress + binary transfer + msgpack",
    "language": "javascript", "framework": "socket.io",
    "code": """import { Server } from 'socket.io';
import msgpackParser from 'socket.io-msgpack-parser';

const io = new Server(server, {
  parser: msgpackParser,
  perMessageDeflate: { threshold: 1024 },
  maxHttpBufferSize: 5e7,
});

// binary blob (e.g. live audio)
socket.on('audio:chunk', (buffer) => {
  // buffer is a Uint8Array directly
  socket.to(roomId).volatile.emit('audio:remote', buffer);
});""",
},

# ════════ Auth — advanced ════════

{
    "request": "JWT access + refresh tokens with rotation",
    "language": "javascript", "framework": "jsonwebtoken",
    "code": """import jwt from 'jsonwebtoken';
import { randomUUID } from 'crypto';
import { redis } from './redis.js';

const ACCESS_TTL = '15m';
const REFRESH_TTL_DAYS = 30;

function signAccess(user) {
  return jwt.sign({ sub: user.id }, process.env.JWT_ACCESS_SECRET, { expiresIn: ACCESS_TTL });
}
async function newRefresh(user) {
  const jti = randomUUID();
  const token = jwt.sign({ sub: user.id, jti }, process.env.JWT_REFRESH_SECRET, { expiresIn: `${REFRESH_TTL_DAYS}d` });
  await redis.set(`rt:${jti}`, user.id, 'EX', REFRESH_TTL_DAYS * 86400);
  return token;
}

router.post('/auth/login', async (req, res) => {
  const user = await authenticate(req.body);
  res.json({ accessToken: signAccess(user), refreshToken: await newRefresh(user) });
});

router.post('/auth/refresh', async (req, res) => {
  const { refreshToken } = req.body;
  let payload;
  try { payload = jwt.verify(refreshToken, process.env.JWT_REFRESH_SECRET); }
  catch { return res.status(401).json({ error: 'invalid token' }); }

  const owner = await redis.get(`rt:${payload.jti}`);
  if (!owner) return res.status(401).json({ error: 'token revoked' });

  await redis.del(`rt:${payload.jti}`);  // rotate: invalidate old
  const user = await User.findById(payload.sub);
  res.json({ accessToken: signAccess(user), refreshToken: await newRefresh(user) });
});

router.post('/auth/logout', async (req, res) => {
  const { refreshToken } = req.body;
  try {
    const { jti } = jwt.verify(refreshToken, process.env.JWT_REFRESH_SECRET);
    await redis.del(`rt:${jti}`);
  } catch {}
  res.status(204).end();
});""",
},
{
    "request": "magic link / passwordless authentication",
    "language": "javascript", "framework": "express",
    "code": """import crypto from 'crypto';

router.post('/auth/magic-link', async (req, res) => {
  const { email } = req.body;
  const user = await User.findOneAndUpdate(
    { email }, { email }, { upsert: true, new: true }
  );
  const token = crypto.randomBytes(32).toString('hex');
  await redis.set(`magic:${token}`, user._id.toString(), 'EX', 600);  // 10 min
  await sendEmail(email, 'Your sign-in link',
    `<a href="https://app.com/auth/verify?token=${token}">Click to sign in</a>`);
  res.json({ ok: true });
});

router.get('/auth/verify', async (req, res) => {
  const userId = await redis.get(`magic:${req.query.token}`);
  if (!userId) return res.status(401).send('Invalid or expired link');
  await redis.del(`magic:${req.query.token}`);
  const user = await User.findById(userId);
  const accessToken = signAccess(user);
  res.cookie('token', accessToken, { httpOnly: true, secure: true, sameSite: 'lax', maxAge: 86400000 });
  res.redirect('/dashboard');
});""",
},
{
    "request": "OAuth2 client credentials flow for service-to-service",
    "language": "javascript", "framework": "express",
    "code": """// app A requesting a token from auth server:
async function getServiceToken() {
  const r = await fetch('https://auth.example.com/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: process.env.OAUTH_CLIENT_ID,
      client_secret: process.env.OAUTH_CLIENT_SECRET,
      scope: 'orders:read orders:write',
    }),
  });
  const { access_token, expires_in } = await r.json();
  return { token: access_token, expiresAt: Date.now() + expires_in * 1000 };
}

// cache + auto-refresh:
let token;
async function authedFetch(url, opts = {}) {
  if (!token || token.expiresAt < Date.now() + 30_000) token = await getServiceToken();
  return fetch(url, { ...opts, headers: { ...opts.headers, Authorization: `Bearer ${token.token}` } });
}""",
},
{
    "request": "RBAC middleware — role-based route protection",
    "language": "javascript", "framework": "express",
    "code": """const PERMISSIONS = {
  admin:    ['*'],
  manager:  ['orders:*', 'users:read', 'reports:read'],
  staff:    ['orders:read', 'orders:update', 'users:read'],
  customer: ['orders:read:own'],
};

function can(role, action) {
  const perms = PERMISSIONS[role] || [];
  return perms.some((p) => p === '*' || p === action || (p.endsWith('*') && action.startsWith(p.slice(0, -1))));
}

export const requirePerm = (action) => (req, res, next) => {
  if (!can(req.user?.role, action))
    return res.status(403).json({ error: 'forbidden' });
  next();
};

router.delete('/orders/:id', requirePerm('orders:delete'), ctrl.remove);
router.get('/reports', requirePerm('reports:read'), ctrl.report);""",
},

# ════════ Performance / Scaling ════════

{
    "request": "Express compression + Brotli for production",
    "language": "javascript", "framework": "express",
    "code": """import compression from 'compression';
import zlib from 'zlib';

app.use(compression({
  level: 6,
  threshold: 1024,
  filter: (req, res) => {
    if (req.headers['x-no-compress']) return false;
    return compression.filter(req, res);
  },
  brotli: { params: { [zlib.constants.BROTLI_PARAM_QUALITY]: 4 } },
}));""",
},
{
    "request": "Connection pool sizing + monitoring",
    "language": "javascript", "framework": "node-core",
    "code": """// HTTP outbound — reuse sockets
import { Agent } from 'undici';
export const httpClient = new Agent({
  keepAliveTimeout: 10_000,
  keepAliveMaxTimeout: 600_000,
  connections: 100,
});

// MongoDB pool (in connection string):
// ?maxPoolSize=50&minPoolSize=5&maxIdleTimeMS=30000

// Postgres:
import { Pool } from 'pg';
export const pgPool = new Pool({
  max: 20,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 2000,
});
setInterval(() => {
  console.log('pg pool', { total: pgPool.totalCount, idle: pgPool.idleCount, waiting: pgPool.waitingCount });
}, 60_000);""",
},
{
    "request": "Two-level cache (in-memory LRU + Redis)",
    "language": "javascript", "framework": "node-core",
    "code": """import { LRUCache } from 'lru-cache';
import { redis } from './redis.js';

const local = new LRUCache({ max: 1000, ttl: 30_000 });

export async function cachedGet(key, fetcher, { localTtl = 30, redisTtl = 300 } = {}) {
  const hot = local.get(key);
  if (hot !== undefined) return hot;

  const cold = await redis.get(key);
  if (cold) {
    const value = JSON.parse(cold);
    local.set(key, value, { ttl: localTtl * 1000 });
    return value;
  }

  const value = await fetcher();
  await redis.set(key, JSON.stringify(value), 'EX', redisTtl);
  local.set(key, value, { ttl: localTtl * 1000 });
  return value;
}

const product = await cachedGet(`product:${id}`, () => Product.findById(id).lean());""",
},
{
    "request": "request coalescing — dedupe in-flight requests",
    "language": "javascript", "framework": "node-core",
    "code": """const inflight = new Map();

export async function coalesce(key, fetcher) {
  if (inflight.has(key)) return inflight.get(key);
  const p = fetcher().finally(() => inflight.delete(key));
  inflight.set(key, p);
  return p;
}

// 100 concurrent requests for the same resource → 1 db hit
const product = await coalesce(`prod:${id}`, () => Product.findById(id).lean());""",
},

# ════════ Microservices ════════

{
    "request": "outbox pattern — reliable event publishing",
    "language": "javascript", "framework": "mongoose",
    "code": """// in same transaction as your business write, append to outbox
async function placeOrder(payload) {
  const session = await mongoose.startSession();
  session.startTransaction();
  try {
    const [order] = await Order.create([payload], { session });
    await Outbox.create([{
      aggregate: 'Order',
      aggregateId: order._id,
      type: 'OrderPlaced',
      payload: { orderId: order._id, total: order.total },
    }], { session });
    await session.commitTransaction();
    return order;
  } catch (e) {
    await session.abortTransaction(); throw e;
  } finally { session.endSession(); }
}

// background relay reads outbox and publishes:
setInterval(async () => {
  const events = await Outbox.find({ publishedAt: null }).limit(50).sort('createdAt');
  for (const e of events) {
    await rabbitChannel.publish('events', e.type, Buffer.from(JSON.stringify(e.payload)), { persistent: true });
    e.publishedAt = new Date();
    await e.save();
  }
}, 1000);""",
},
{
    "request": "saga pattern — distributed multi-service transaction",
    "language": "javascript", "framework": "node-core",
    "code": """class Saga {
  constructor() { this.steps = []; }
  step(name, action, compensation) { this.steps.push({ name, action, compensation }); return this; }
  async run(ctx) {
    const completed = [];
    try {
      for (const s of this.steps) {
        await s.action(ctx);
        completed.push(s);
      }
    } catch (e) {
      for (const s of completed.reverse()) {
        try { await s.compensation(ctx); }
        catch (compErr) { console.error('compensation failed', s.name, compErr); }
      }
      throw e;
    }
  }
}

const orderSaga = new Saga()
  .step('reserve-stock',
    (ctx) => stockSvc.reserve(ctx.items),
    (ctx) => stockSvc.release(ctx.items))
  .step('charge-payment',
    (ctx) => paymentSvc.charge(ctx.userId, ctx.total),
    (ctx) => paymentSvc.refund(ctx.userId, ctx.total))
  .step('create-order',
    (ctx) => Order.create(ctx),
    () => {});

await orderSaga.run({ userId, items, total });""",
},
{
    "request": "service discovery + health check via Consul",
    "language": "javascript", "framework": "consul",
    "code": """import Consul from 'consul';
const consul = new Consul({ host: process.env.CONSUL_HOST });

await consul.agent.service.register({
  id: `${SERVICE_NAME}-${process.pid}`,
  name: SERVICE_NAME,
  port: PORT,
  tags: ['v1'],
  check: {
    http: `http://${HOST}:${PORT}/api/health`,
    interval: '10s',
    deregistercriticalserviceafter: '1m',
  },
});

process.on('SIGTERM', async () => {
  await consul.agent.service.deregister(`${SERVICE_NAME}-${process.pid}`);
});

// resolve another service:
const services = await consul.health.service({ service: 'payment', passing: true });
const node = services[Math.floor(Math.random() * services.length)];
const url = `http://${node.Service.Address}:${node.Service.Port}`;""",
},
{
    "request": "RabbitMQ topic exchange for event-driven services",
    "language": "javascript", "framework": "amqplib",
    "code": """// publisher
await ch.assertExchange('events', 'topic', { durable: true });
ch.publish('events', 'order.placed', Buffer.from(JSON.stringify(order)), { persistent: true });
ch.publish('events', 'payment.failed', Buffer.from(JSON.stringify(p)), { persistent: true });

// consumer for ALL order events:
await ch.assertExchange('events', 'topic', { durable: true });
const { queue } = await ch.assertQueue('analytics-orders', { durable: true });
await ch.bindQueue(queue, 'events', 'order.*');
await ch.bindQueue(queue, 'events', 'payment.*');
ch.prefetch(20);
ch.consume(queue, async (msg) => {
  try {
    await analytics.handle(msg.fields.routingKey, JSON.parse(msg.content));
    ch.ack(msg);
  } catch (e) {
    ch.nack(msg, false, false);  // dead-letter
  }
});""",
},
{
    "request": "dead-letter queue with retry counter",
    "language": "javascript", "framework": "amqplib",
    "code": """const MAX_RETRIES = 5;

await ch.assertExchange('dlx', 'direct', { durable: true });
await ch.assertQueue('jobs.dead', { durable: true });
await ch.bindQueue('jobs.dead', 'dlx', 'jobs');

await ch.assertQueue('jobs', {
  durable: true,
  arguments: { 'x-dead-letter-exchange': 'dlx', 'x-dead-letter-routing-key': 'jobs' },
});

ch.consume('jobs', async (msg) => {
  const retries = (msg.properties.headers?.['x-retries'] || 0) + 1;
  try {
    await processJob(JSON.parse(msg.content));
    ch.ack(msg);
  } catch (e) {
    if (retries >= MAX_RETRIES) {
      ch.nack(msg, false, false);  // → DLQ
    } else {
      ch.publish('', 'jobs', msg.content, {
        persistent: true,
        headers: { 'x-retries': retries },
        expiration: String(1000 * Math.pow(2, retries)),
      });
      ch.ack(msg);
    }
  }
});""",
},

# ════════ Real-world features ════════

{
    "request": "Stripe subscription billing — checkout + webhook + portal",
    "language": "javascript", "framework": "stripe",
    "code": """import Stripe from 'stripe';
const stripe = new Stripe(process.env.STRIPE_SECRET);

// 1. start checkout
router.post('/billing/checkout', async (req, res) => {
  const session = await stripe.checkout.sessions.create({
    mode: 'subscription',
    line_items: [{ price: process.env.PRICE_ID, quantity: 1 }],
    customer_email: req.user.email,
    success_url: `${BASE}/billing/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${BASE}/billing/cancel`,
    client_reference_id: req.user.id,
  });
  res.json({ url: session.url });
});

// 2. webhook updates user
router.post('/webhooks/stripe', express.raw({ type: 'application/json' }), async (req, res) => {
  const event = stripe.webhooks.constructEvent(req.body, req.headers['stripe-signature'], process.env.STRIPE_WH);
  switch (event.type) {
    case 'checkout.session.completed': {
      const s = event.data.object;
      await User.updateOne({ _id: s.client_reference_id },
        { stripeCustomerId: s.customer, plan: 'pro', status: 'active' });
      break;
    }
    case 'customer.subscription.deleted':
      await User.updateOne({ stripeCustomerId: event.data.object.customer }, { plan: 'free' });
      break;
    case 'invoice.payment_failed':
      await User.updateOne({ stripeCustomerId: event.data.object.customer }, { status: 'past_due' });
      break;
  }
  res.json({ received: true });
});

// 3. self-serve portal
router.post('/billing/portal', async (req, res) => {
  const session = await stripe.billingPortal.sessions.create({
    customer: req.user.stripeCustomerId,
    return_url: `${BASE}/account`,
  });
  res.json({ url: session.url });
});""",
},
{
    "request": "Elasticsearch product search with filters + facets",
    "language": "javascript", "framework": "elasticsearch",
    "code": """import { Client } from '@elastic/elasticsearch';
const es = new Client({ node: process.env.ES_URL });

await es.indices.create({
  index: 'products',
  mappings: {
    properties: {
      name: { type: 'text', analyzer: 'english' },
      description: { type: 'text', analyzer: 'english' },
      price: { type: 'float' },
      category: { type: 'keyword' },
      tags: { type: 'keyword' },
      inStock: { type: 'boolean' },
    },
  },
});

// search with multi-match + filters + facets
const result = await es.search({
  index: 'products',
  body: {
    query: {
      bool: {
        must: [{ multi_match: { query: q, fields: ['name^3', 'description'] } }],
        filter: [
          ...(category ? [{ term: { category } }] : []),
          ...(priceMax ? [{ range: { price: { lte: priceMax } } }] : []),
          { term: { inStock: true } },
        ],
      },
    },
    aggs: {
      categories: { terms: { field: 'category' } },
      priceRanges: { range: { field: 'price', ranges: [{ to: 50 }, { from: 50, to: 200 }, { from: 200 }] } },
    },
    highlight: { fields: { name: {}, description: {} } },
  },
});""",
},
{
    "request": "PDF generation with Puppeteer for invoices",
    "language": "javascript", "framework": "puppeteer",
    "code": """import puppeteer from 'puppeteer';
import ejs from 'ejs';
import { readFile } from 'fs/promises';

let browser;
async function getBrowser() {
  if (!browser) browser = await puppeteer.launch({ args: ['--no-sandbox'], headless: 'new' });
  return browser;
}

export async function generateInvoicePdf(order) {
  const tpl = await readFile('templates/invoice.ejs', 'utf8');
  const html = ejs.render(tpl, { order, total: order.total.toFixed(2) });
  const page = await (await getBrowser()).newPage();
  await page.setContent(html, { waitUntil: 'networkidle0' });
  const pdf = await page.pdf({ format: 'A4', printBackground: true, margin: { top: '20mm', bottom: '20mm', left: '15mm', right: '15mm' } });
  await page.close();
  return pdf;
}

router.get('/orders/:id/invoice.pdf', async (req, res) => {
  const order = await Order.findById(req.params.id);
  const pdf = await generateInvoicePdf(order);
  res.set('Content-Type', 'application/pdf');
  res.set('Content-Disposition', `attachment; filename=invoice-${order._id}.pdf`);
  res.send(pdf);
});""",
},
{
    "request": "audit log middleware — record who did what",
    "language": "javascript", "framework": "express",
    "code": """const auditSchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  action: String,
  resource: String,
  resourceId: mongoose.Schema.Types.Mixed,
  before: mongoose.Schema.Types.Mixed,
  after: mongoose.Schema.Types.Mixed,
  ip: String,
  userAgent: String,
  status: Number,
}, { timestamps: true, capped: { size: 1024 * 1024 * 1024, max: 5_000_000 } });

const Audit = mongoose.model('Audit', auditSchema);

export function audit(action, resource) {
  return async (req, res, next) => {
    const json = res.json.bind(res);
    res.json = (body) => {
      Audit.create({
        user: req.user?.id,
        action, resource,
        resourceId: req.params?.id || body?._id,
        ip: req.ip, userAgent: req.headers['user-agent'],
        status: res.statusCode,
      }).catch(() => {});
      return json(body);
    };
    next();
  };
}

router.delete('/orders/:id', audit('delete', 'order'), ctrl.remove);""",
},
{
    "request": "soft-delete with cascade + history",
    "language": "javascript", "framework": "mongoose",
    "code": """orderSchema.add({ deletedAt: { type: Date, default: null, index: true } });

orderSchema.pre(/^find/, function () {
  if (!this.getOptions().withDeleted) this.where({ deletedAt: null });
});

orderSchema.methods.softDelete = async function (userId) {
  this.deletedAt = new Date();
  await this.save();
  await OrderItem.updateMany({ order: this._id }, { deletedAt: new Date() });
  await Audit.create({ user: userId, action: 'soft_delete', resource: 'order', resourceId: this._id });
};

orderSchema.methods.restore = async function () {
  this.deletedAt = null;
  await this.save();
  await OrderItem.updateMany({ order: this._id }, { deletedAt: null });
};

// admin can see deleted:
const all = await Order.find({}, null, { withDeleted: true });""",
},
{
    "request": "activity feed — fan-out on write vs fan-out on read",
    "language": "javascript", "framework": "mongoose",
    "code": """// Strategy: fan-out on write for normal users (push to feeds)
//           fan-out on read for celebrities (avoid huge writes)

async function publishActivity(actor, verb, object) {
  const activity = await Activity.create({ actor, verb, object, ts: new Date() });
  if (actor.followers > 100_000) return;  // celebrity → feed reads activities directly
  const followers = await Follow.find({ following: actor._id }).select('follower').lean();
  await Feed.insertMany(followers.map(f => ({
    user: f.follower, activity: activity._id, ts: activity.ts,
  })), { ordered: false });
}

async function getFeed(userId, beforeTs) {
  const me = await User.findById(userId);
  // fan-out write items
  const own = await Feed.find({ user: userId, ts: { $lt: beforeTs } })
    .populate('activity').sort('-ts').limit(20).lean();
  // pull from celebrities I follow
  const celebs = await Follow.find({ follower: userId }).populate('following').lean();
  const celebActivity = await Activity.find({
    actor: { $in: celebs.filter(c => c.following.followers > 100_000).map(c => c.following._id) },
    ts: { $lt: beforeTs },
  }).sort('-ts').limit(20).lean();
  return [...own.map(f => f.activity), ...celebActivity].sort((a, b) => b.ts - a.ts).slice(0, 20);
}""",
},
{
    "request": "rate-limited notification dispatcher — multi-channel",
    "language": "javascript", "framework": "node-core",
    "code": """const CHANNELS = { email, sms, push, inApp };

export async function notify(userId, kind, data) {
  const user = await User.findById(userId).lean();
  const prefs = user.notificationPrefs?.[kind] || ['inApp'];

  await Promise.allSettled(prefs.map(async (channel) => {
    if (channel === 'email' && !await rateOk(`notif:email:${userId}`, 50, 86400)) return;
    if (channel === 'sms' && !await rateOk(`notif:sms:${userId}`, 5, 86400)) return;
    await CHANNELS[channel](user, kind, data);
  }));

  await InAppNotification.create({ user: userId, kind, data });
  io.to(`user:${userId}`).emit('notification', { kind, data });
}

async function rateOk(key, limit, windowSec) {
  const n = await redis.incr(key);
  if (n === 1) await redis.expire(key, windowSec);
  return n <= limit;
}""",
},

# ════════ Testing — advanced ════════

{
    "request": "load test with autocannon",
    "language": "javascript", "framework": "autocannon",
    "code": """import autocannon from 'autocannon';

const result = await autocannon({
  url: 'http://localhost:3000/api/orders',
  connections: 100,
  duration: 30,
  pipelining: 1,
  headers: { Authorization: `Bearer ${TOKEN}` },
  requests: [
    { method: 'GET', path: '/api/orders' },
    { method: 'POST', path: '/api/orders', body: JSON.stringify({ productId: 'p1', quantity: 1 }) },
  ],
});
console.log(autocannon.printResult(result));

// CI gate:
if (result.latency.p99 > 500) {
  console.error('p99 latency regression!');
  process.exit(1);
}""",
},
{
    "request": "contract test with Pact (consumer-driven)",
    "language": "javascript", "framework": "pact",
    "code": """import { PactV3, MatchersV3 } from '@pact-foundation/pact';
const { like, eachLike, regex } = MatchersV3;

const provider = new PactV3({ consumer: 'web', provider: 'order-api' });

it('GET /orders/:id', () => {
  provider
    .given('order 123 exists')
    .uponReceiving('request for order 123')
    .withRequest({ method: 'GET', path: '/orders/123' })
    .willRespondWith({
      status: 200,
      body: like({
        id: '123', total: 99.99, status: regex('pending|paid|shipped', 'paid'),
        items: eachLike({ productId: 'p1', quantity: 1 }, { min: 1 }),
      }),
    });

  return provider.executeTest(async (mock) => {
    const r = await fetch(`${mock.url}/orders/123`);
    expect(r.status).toBe(200);
  });
});""",
},

# ════════ Observability ════════

{
    "request": "Prometheus metrics endpoint with prom-client",
    "language": "javascript", "framework": "prom-client",
    "code": """import client from 'prom-client';

client.collectDefaultMetrics({ prefix: 'app_' });

const httpDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'duration of HTTP requests',
  labelNames: ['method', 'route', 'status'],
  buckets: [0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5],
});

app.use((req, res, next) => {
  const end = httpDuration.startTimer();
  res.on('finish', () => {
    const route = req.route?.path || req.path;
    end({ method: req.method, route, status: res.statusCode });
  });
  next();
});

app.get('/metrics', async (_req, res) => {
  res.set('Content-Type', client.register.contentType);
  res.end(await client.register.metrics());
});

// custom business metric
const ordersPlaced = new client.Counter({ name: 'orders_placed_total', help: 'orders' });
ordersPlaced.inc();""",
},
{
    "request": "structured access log with request body redaction",
    "language": "javascript", "framework": "pino-http",
    "code": """import pinoHttp from 'pino-http';

app.use(pinoHttp({
  logger,
  redact: {
    paths: [
      'req.headers.authorization', 'req.headers.cookie',
      'req.body.password', 'req.body.creditCard', 'req.body.cvv',
      'res.headers["set-cookie"]',
    ],
    censor: '[REDACTED]',
  },
  serializers: {
    req: (req) => ({ method: req.method, url: req.url, id: req.id }),
    res: (res) => ({ status: res.statusCode }),
  },
  customLogLevel: (_req, res, err) => {
    if (err || res.statusCode >= 500) return 'error';
    if (res.statusCode >= 400) return 'warn';
    return 'info';
  },
}));""",
},
{
    "request": "Sentry error tracking",
    "language": "javascript", "framework": "sentry",
    "code": """import * as Sentry from '@sentry/node';
import { ProfilingIntegration } from '@sentry/profiling-node';

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
  release: process.env.GIT_SHA,
  tracesSampleRate: 0.1,
  profilesSampleRate: 0.1,
  integrations: [new ProfilingIntegration()],
  beforeSend(event) {
    if (event.request?.headers?.authorization) delete event.request.headers.authorization;
    return event;
  },
});

app.use(Sentry.Handlers.requestHandler());
app.use(Sentry.Handlers.tracingHandler());
// ... your routes ...
app.use(Sentry.Handlers.errorHandler());""",
},

# ════════ DevOps / Deploy ════════

{
    "request": "Kubernetes HPA + readiness/liveness for an API",
    "language": "yaml", "framework": "kubernetes",
    "code": """apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: api }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: api }
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource: { name: cpu,    target: { type: Utilization, averageUtilization: 65 } }
    - type: Resource
      resource: { name: memory, target: { type: Utilization, averageUtilization: 80 } }
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
    scaleUp:
      stabilizationWindowSeconds: 30
      policies: [{ type: Percent, value: 100, periodSeconds: 30 }]
---
# Deployment fragment with health probes:
# spec.template.spec.containers[0]:
#   readinessProbe:
#     httpGet: { path: /api/health, port: 3000 }
#     initialDelaySeconds: 5
#     periodSeconds: 5
#     failureThreshold: 3
#   livenessProbe:
#     httpGet: { path: /api/health, port: 3000 }
#     initialDelaySeconds: 30
#     periodSeconds: 15
#     failureThreshold: 3
#   startupProbe:
#     httpGet: { path: /api/health, port: 3000 }
#     failureThreshold: 30
#     periodSeconds: 10""",
},
{
    "request": "GitHub Actions deploy to k8s with image build + tag",
    "language": "yaml", "framework": "github-actions",
    "code": """name: Deploy
on: { push: { branches: [main] } }
permissions: { contents: read, packages: write, id-token: write }

jobs:
  build-deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha,prefix=
            type=raw,value=latest

      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - uses: azure/setup-kubectl@v4
      - run: |
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > kubeconfig
          KUBECONFIG=kubeconfig kubectl set image deployment/api \\
            api=ghcr.io/${{ github.repository }}:${{ github.sha }}
          KUBECONFIG=kubeconfig kubectl rollout status deployment/api --timeout=5m""",
},
{
    "request": "blue-green deployment with kubectl",
    "language": "bash", "framework": "kubernetes",
    "code": """#!/usr/bin/env bash
# deploy GREEN, smoke test, switch traffic
set -e
NEW_IMAGE=$1
GREEN=api-green
BLUE=api-blue
SVC=api

kubectl set image deployment/$GREEN api=$NEW_IMAGE
kubectl rollout status deployment/$GREEN --timeout=5m

# smoke test against green
GREEN_IP=$(kubectl get pod -l app=$GREEN -o jsonpath='{.items[0].status.podIP}')
kubectl run --rm smoke-test --image=curlimages/curl --restart=Never -- \\
  curl -sf http://$GREEN_IP:3000/api/health || { echo "smoke failed"; exit 1; }

# flip selector
kubectl patch service $SVC -p "{\\"spec\\":{\\"selector\\":{\\"app\\":\\"$GREEN\\"}}}"

# scale down blue after grace period
sleep 60
kubectl scale deployment/$BLUE --replicas=0

echo "✓ traffic shifted to $GREEN with $NEW_IMAGE"
""",
},

# ════════ Misc patterns ════════

{
    "request": "type-safe environment with @t3-oss/env",
    "language": "typescript", "framework": "t3-env",
    "code": """import { createEnv } from '@t3-oss/env-core';
import { z } from 'zod';

export const env = createEnv({
  server: {
    NODE_ENV: z.enum(['development', 'production', 'test']),
    DATABASE_URL: z.string().url(),
    JWT_SECRET: z.string().min(16),
    REDIS_URL: z.string().url().optional(),
    LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  },
  runtimeEnv: process.env,
  emptyStringAsUndefined: true,
});

// usage anywhere — fully typed:
import { env } from './env';
const log = pino({ level: env.LOG_LEVEL });""",
},
{
    "request": "graceful Mongoose disconnect + Redis quit on shutdown",
    "language": "javascript", "framework": "node-core",
    "code": """const shutdown = async (signal) => {
  console.log(`${signal} — graceful shutdown started`);
  server.close();  // stop accepting new connections
  setTimeout(() => { console.error('forced exit'); process.exit(1); }, 30_000).unref();

  await Promise.allSettled([
    mongoose.connection.close(),
    redis.quit(),
    rabbitChannel?.close(),
    rabbitConn?.close(),
    pgPool.end(),
  ]);

  await flushPendingTelemetry();
  console.log('✓ clean exit');
  process.exit(0);
};

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT',  () => shutdown('SIGINT'));""",
},
{
    "request": "feature flag with Unleash open-source",
    "language": "javascript", "framework": "unleash",
    "code": """import { startUnleash } from 'unleash-client';

const unleash = await startUnleash({
  url: process.env.UNLEASH_URL,
  appName: 'api',
  customHeaders: { Authorization: process.env.UNLEASH_TOKEN },
});

app.use((req, _res, next) => {
  req.unleashCtx = {
    userId: req.user?.id,
    properties: { tier: req.user?.plan, country: req.headers['cf-ipcountry'] },
  };
  next();
});

router.get('/checkout', (req, res) => {
  if (unleash.isEnabled('new_checkout', req.unleashCtx)) {
    return newCheckoutController(req, res);
  }
  return legacyCheckoutController(req, res);
});""",
},
{
    "request": "cron-driven data sync with idempotent upsert",
    "language": "javascript", "framework": "node-core",
    "code": """import cron from 'node-cron';

cron.schedule('*/15 * * * *', async () => {
  const lastSync = (await Meta.findOne({ key: 'productsLastSync' }))?.value || new Date(0);
  const updated = await fetchUpdatedSince(lastSync);

  const ops = updated.map(p => ({
    updateOne: {
      filter: { externalId: p.id },
      update: { $set: { name: p.name, price: p.price, updatedAt: new Date() } },
      upsert: true,
    },
  }));
  if (ops.length) await Product.bulkWrite(ops, { ordered: false });

  await Meta.updateOne({ key: 'productsLastSync' }, { value: new Date() }, { upsert: true });
  console.log(`synced ${ops.length} products`);
});""",
},
{
    "request": "Express app structure for production (folder layout)",
    "language": "text", "framework": "express",
    "code": """src/
├── app.js                 # express setup, middleware wiring
├── server.js              # http listen, graceful shutdown
├── config/
│   ├── env.js            # env validation
│   ├── db.js             # mongoose connect
│   └── redis.js
├── middleware/
│   ├── auth.js
│   ├── error.js
│   ├── validate.js
│   ├── rateLimit.js
│   ├── audit.js
│   └── tracing.js
├── routes/
│   ├── index.js
│   ├── auth.js
│   ├── orders.js
│   └── users.js
├── controllers/          # request handlers (thin)
│   └── order.controller.js
├── services/             # business logic (testable, no req/res)
│   └── order.service.js
├── repositories/         # data access (Mongoose calls)
│   └── order.repo.js
├── models/               # schemas
│   ├── User.js
│   └── Order.js
├── jobs/                 # bullmq workers
│   └── email.worker.js
├── events/               # event bus + handlers
├── utils/
│   ├── AppError.js
│   ├── asyncHandler.js
│   └── logger.js
└── tests/""",
},
{
    "request": "command bus / handler pattern",
    "language": "typescript", "framework": "node-core",
    "code": """interface Command<R = unknown> { readonly _result?: R; }

type Handler<C extends Command> = (cmd: C) => Promise<C extends Command<infer R> ? R : never>;

class CommandBus {
  private handlers = new Map<string, Handler<any>>();
  register<C extends Command>(name: string, handler: Handler<C>) { this.handlers.set(name, handler); }
  async dispatch<C extends Command>(name: string, cmd: C) {
    const h = this.handlers.get(name);
    if (!h) throw new Error(`no handler for ${name}`);
    return h(cmd);
  }
}

export const bus = new CommandBus();

class PlaceOrderCmd implements Command<{ id: string }> { constructor(public userId: string, public items: any[]) {} }

bus.register<PlaceOrderCmd>('PlaceOrder', async (cmd) => {
  const order = await Order.create({ user: cmd.userId, items: cmd.items });
  return { id: order._id.toString() };
});

const { id } = await bus.dispatch('PlaceOrder', new PlaceOrderCmd(userId, items));""",
},
]
