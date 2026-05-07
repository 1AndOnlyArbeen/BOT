"""Curated reference patterns for common stacks.

These get ingested into the code_library vector store on first run.
After that, asking 'how do I X with Y?' returns these as starting points.

Each entry: {request, code, language, framework, notes}.
Ground truth, kept short — meant as adaptable templates."""
from __future__ import annotations


SEED: list[dict] = [

# ───────── Node.js / Express ─────────
{
    "request": "create a basic Express REST API server",
    "language": "javascript", "framework": "express",
    "code": """const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

app.get('/api/health', (_req, res) => res.json({ ok: true }));

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(err.status || 500).json({ error: err.message });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`API on :${PORT}`));""",
},
{
    "request": "Express CRUD route for a resource",
    "language": "javascript", "framework": "express",
    "code": """const router = require('express').Router();
const ctrl = require('../controllers/order.controller');

router.get('/', ctrl.list);
router.get('/:id', ctrl.getById);
router.post('/', ctrl.create);
router.patch('/:id', ctrl.update);
router.delete('/:id', ctrl.remove);

module.exports = router;""",
},
{
    "request": "Express JWT authentication middleware",
    "language": "javascript", "framework": "express",
    "code": """const jwt = require('jsonwebtoken');

function authRequired(req, res, next) {
  const header = req.headers.authorization || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;
  if (!token) return res.status(401).json({ error: 'no token' });
  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET);
    next();
  } catch {
    res.status(401).json({ error: 'invalid token' });
  }
}

function signToken(payload) {
  return jwt.sign(payload, process.env.JWT_SECRET, { expiresIn: '7d' });
}

module.exports = { authRequired, signToken };""",
},
{
    "request": "Express file upload with multer",
    "language": "javascript", "framework": "express",
    "code": """const multer = require('multer');
const path = require('path');

const upload = multer({
  storage: multer.diskStorage({
    destination: (_req, _file, cb) => cb(null, 'uploads/'),
    filename: (_req, file, cb) =>
      cb(null, `${Date.now()}-${file.originalname}`),
  }),
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const ok = ['.png', '.jpg', '.jpeg', '.pdf'].includes(
      path.extname(file.originalname).toLowerCase()
    );
    cb(ok ? null : new Error('bad type'), ok);
  },
});

router.post('/upload', upload.single('file'), (req, res) => {
  res.json({ filename: req.file.filename, size: req.file.size });
});""",
},
{
    "request": "Express request validation with Joi",
    "language": "javascript", "framework": "express",
    "code": """const Joi = require('joi');

const orderSchema = Joi.object({
  productId: Joi.string().required(),
  quantity: Joi.number().integer().min(1).required(),
  shippingAddress: Joi.string().min(5).required(),
});

const validate = (schema) => (req, res, next) => {
  const { error, value } = schema.validate(req.body, { abortEarly: false });
  if (error) return res.status(400).json({ errors: error.details.map(d => d.message) });
  req.body = value;
  next();
};

router.post('/', validate(orderSchema), createOrder);""",
},

# ───────── MongoDB / Mongoose ─────────
{
    "request": "Mongoose schema and model for orders",
    "language": "javascript", "framework": "mongoose",
    "code": """const mongoose = require('mongoose');

const orderSchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  items: [{
    product: { type: mongoose.Schema.Types.ObjectId, ref: 'Product', required: true },
    quantity: { type: Number, required: true, min: 1 },
    price: { type: Number, required: true },
  }],
  total: { type: Number, required: true },
  status: { type: String, enum: ['pending', 'paid', 'shipped', 'delivered', 'cancelled'], default: 'pending' },
  shippingAddress: String,
}, { timestamps: true });

orderSchema.index({ user: 1, createdAt: -1 });

module.exports = mongoose.model('Order', orderSchema);""",
},
{
    "request": "MongoDB CRUD controller for orders",
    "language": "javascript", "framework": "mongoose",
    "code": """const Order = require('../models/order.model');

exports.list = async (req, res) => {
  const orders = await Order.find({ user: req.user.id })
    .populate('items.product', 'name price')
    .sort('-createdAt')
    .limit(50);
  res.json(orders);
};

exports.getById = async (req, res) => {
  const order = await Order.findById(req.params.id).populate('items.product');
  if (!order) return res.status(404).json({ error: 'not found' });
  res.json(order);
};

exports.create = async (req, res) => {
  const order = await Order.create({ ...req.body, user: req.user.id });
  res.status(201).json(order);
};

exports.update = async (req, res) => {
  const order = await Order.findByIdAndUpdate(req.params.id, req.body, { new: true });
  res.json(order);
};

exports.remove = async (req, res) => {
  await Order.findByIdAndDelete(req.params.id);
  res.status(204).end();
};""",
},
{
    "request": "MongoDB aggregation pipeline for sales report",
    "language": "javascript", "framework": "mongoose",
    "code": """const monthlyRevenue = await Order.aggregate([
  { $match: { status: 'paid', createdAt: { $gte: new Date(Date.now() - 30 * 86400e3) } } },
  { $unwind: '$items' },
  { $group: {
      _id: { y: { $year: '$createdAt' }, m: { $month: '$createdAt' } },
      revenue: { $sum: { $multiply: ['$items.price', '$items.quantity'] } },
      orders: { $addToSet: '$_id' },
  }},
  { $project: { revenue: 1, orderCount: { $size: '$orders' } } },
  { $sort: { '_id.y': -1, '_id.m': -1 } },
]);""",
},

# ───────── Postgres ─────────
{
    "request": "Postgres connection pool with node-postgres",
    "language": "javascript", "framework": "postgres",
    "code": """const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 2000,
});

module.exports = {
  query: (text, params) => pool.query(text, params),
  getClient: () => pool.connect(),
};""",
},
{
    "request": "Postgres transaction across multiple tables",
    "language": "javascript", "framework": "postgres",
    "code": """async function placeOrder({ userId, items }) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const { rows: [order] } = await client.query(
      'INSERT INTO orders (user_id, total, status) VALUES ($1,$2,$3) RETURNING *',
      [userId, items.reduce((s, i) => s + i.price * i.qty, 0), 'pending'],
    );
    for (const it of items) {
      await client.query(
        'INSERT INTO order_items (order_id, product_id, quantity, price) VALUES ($1,$2,$3,$4)',
        [order.id, it.productId, it.qty, it.price],
      );
      await client.query(
        'UPDATE products SET stock = stock - $1 WHERE id = $2 AND stock >= $1',
        [it.qty, it.productId],
      );
    }
    await client.query('COMMIT');
    return order;
  } catch (e) {
    await client.query('ROLLBACK');
    throw e;
  } finally {
    client.release();
  }
}""",
},
{
    "request": "Postgres schema for orders with foreign keys",
    "language": "sql", "framework": "postgres",
    "code": """CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE orders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  total NUMERIC(12,2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','paid','shipped','delivered','cancelled')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_orders_user_created ON orders(user_id, created_at DESC);

CREATE TABLE order_items (
  id BIGSERIAL PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL,
  quantity INT NOT NULL CHECK (quantity > 0),
  price NUMERIC(12,2) NOT NULL
);""",
},

# ───────── SQLite ─────────
{
    "request": "SQLite quickstart with Python",
    "language": "python", "framework": "sqlite3",
    "code": """import sqlite3
from contextlib import contextmanager

@contextmanager
def conn(path='app.db'):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys = ON')
    try:
        yield c
        c.commit()
    finally:
        c.close()

with conn() as c:
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL
        );
    ''')

with conn() as c:
    c.execute('INSERT INTO users(email) VALUES (?)', ('a@b.com',))
    rows = c.execute('SELECT * FROM users').fetchall()
    for r in rows:
        print(dict(r))""",
},

# ───────── Vector DB (Chroma local) ─────────
{
    "request": "local vector DB with ChromaDB and sentence embeddings",
    "language": "python", "framework": "chromadb",
    "code": """import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path='./chroma_db')
embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name='all-MiniLM-L6-v2'
)
col = client.get_or_create_collection('docs', embedding_function=embedder)

col.add(
    ids=['doc1', 'doc2'],
    documents=['Ultron is a local AI assistant.', 'Vector search powers RAG.'],
    metadatas=[{'source': 'readme'}, {'source': 'tutorial'}],
)

results = col.query(query_texts=['what is Ultron?'], n_results=3)
for doc, meta, dist in zip(
    results['documents'][0], results['metadatas'][0], results['distances'][0]
):
    print(f'[{dist:.3f}] {meta["source"]}: {doc}')""",
},

# ───────── React ─────────
{
    "request": "React functional component with hooks and fetch",
    "language": "tsx", "framework": "react",
    "code": """import { useEffect, useState } from 'react';

interface Order { id: number; total: number; status: string; }

export function OrderList() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/orders')
      .then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
      .then((data) => { if (!cancelled) setOrders(data); })
      .catch((e) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div>Loading…</div>;
  if (error) return <div className="text-red-500">{error}</div>;

  return (
    <ul className="space-y-2">
      {orders.map((o) => (
        <li key={o.id} className="border p-3 rounded">
          #{o.id} · ${o.total} · <span className="text-xs">{o.status}</span>
        </li>
      ))}
    </ul>
  );
}""",
},
{
    "request": "React form with validation and submit",
    "language": "tsx", "framework": "react",
    "code": """import { useState } from 'react';

export function OrderForm({ onSubmit }: { onSubmit: (data: any) => Promise<void> }) {
  const [form, setForm] = useState({ productId: '', quantity: 1, address: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.productId) e.productId = 'required';
    if (form.quantity < 1) e.quantity = 'must be ≥ 1';
    if (form.address.length < 5) e.address = 'too short';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handle = async (ev: React.FormEvent) => {
    ev.preventDefault();
    if (!validate()) return;
    setBusy(true);
    try { await onSubmit(form); } finally { setBusy(false); }
  };

  return (
    <form onSubmit={handle} className="space-y-3">
      <input
        value={form.productId}
        onChange={(e) => setForm({ ...form, productId: e.target.value })}
        placeholder="product id"
        className="w-full border rounded p-2"
      />
      {errors.productId && <p className="text-red-500 text-sm">{errors.productId}</p>}

      <input
        type="number" min={1}
        value={form.quantity}
        onChange={(e) => setForm({ ...form, quantity: +e.target.value })}
        className="w-full border rounded p-2"
      />
      <textarea
        value={form.address}
        onChange={(e) => setForm({ ...form, address: e.target.value })}
        placeholder="shipping address"
        className="w-full border rounded p-2"
      />
      <button disabled={busy} className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50">
        {busy ? 'Submitting…' : 'Place order'}
      </button>
    </form>
  );
}""",
},
{
    "request": "React Context for global auth state",
    "language": "tsx", "framework": "react",
    "code": """import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface User { id: string; email: string; }
interface AuthCtx {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const t = localStorage.getItem('token');
    if (t) fetch('/api/me', { headers: { Authorization: `Bearer ${t}` } })
      .then(r => r.ok ? r.json() : null).then(setUser);
  }, []);

  const login = async (email: string, password: string) => {
    const r = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const { token, user } = await r.json();
    localStorage.setItem('token', token);
    setUser(user);
  };

  const logout = () => { localStorage.removeItem('token'); setUser(null); };

  return <Ctx.Provider value={{ user, login, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth outside AuthProvider');
  return v;
};""",
},
{
    "request": "React custom hook for debounced input",
    "language": "ts", "framework": "react",
    "code": """import { useEffect, useState } from 'react';

export function useDebounced<T>(value: T, delay = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return v;
}

// usage:
// const debounced = useDebounced(searchInput, 250);
// useEffect(() => { fetch(`/api/search?q=${debounced}`); }, [debounced]);""",
},

# ───────── Tailwind / HTML / CSS ─────────
{
    "request": "responsive Tailwind landing page hero",
    "language": "html", "framework": "tailwindcss",
    "code": """<section class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
  <nav class="flex items-center justify-between p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold">Brand</h1>
    <div class="hidden md:flex gap-6">
      <a href="#" class="hover:text-emerald-400">Features</a>
      <a href="#" class="hover:text-emerald-400">Pricing</a>
    </div>
    <button class="bg-emerald-500 hover:bg-emerald-600 px-4 py-2 rounded-md">Sign up</button>
  </nav>

  <div class="max-w-6xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-12 items-center">
    <div>
      <h2 class="text-5xl font-bold mb-4">Build faster.<br/>Ship today.</h2>
      <p class="text-slate-300 text-lg mb-8">A simple, beautiful product that gets out of your way.</p>
      <div class="flex gap-3">
        <button class="bg-emerald-500 hover:bg-emerald-600 px-6 py-3 rounded-md font-medium">Get started</button>
        <button class="border border-slate-600 hover:border-slate-400 px-6 py-3 rounded-md">Demo</button>
      </div>
    </div>
    <img src="/hero.png" alt="" class="rounded-lg shadow-2xl"/>
  </div>
</section>""",
},
{
    "request": "Tailwind dark mode toggle and styles",
    "language": "tsx", "framework": "tailwindcss",
    "code": """// 1. tailwind.config.js: darkMode: 'class'
// 2. wrap your app:

import { useEffect, useState } from 'react';

export function ThemeToggle() {
  const [dark, setDark] = useState(() =>
    localStorage.getItem('theme') === 'dark' ||
    (!localStorage.getItem('theme') && matchMedia('(prefers-color-scheme: dark)').matches)
  );
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);
  return (
    <button onClick={() => setDark(!dark)} className="p-2 rounded bg-slate-200 dark:bg-slate-700">
      {dark ? '☀️' : '🌙'}
    </button>
  );
}

// usage in components:
// <div className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">""",
},
{
    "request": "CSS Grid responsive 3-column to single-column layout",
    "language": "html", "framework": "css",
    "code": """<style>
  .grid {
    display: grid;
    gap: 1.5rem;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }
  .card {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.5rem;
    transition: transform .2s, box-shadow .2s;
  }
  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,.08);
  }
</style>
<div class="grid">
  <div class="card">…</div>
  <div class="card">…</div>
  <div class="card">…</div>
</div>""",
},

# ───────── Python / Django ─────────
{
    "request": "Django model with custom manager",
    "language": "python", "framework": "django",
    "code": """from django.db import models
from django.contrib.auth.models import User

class OrderManager(models.Manager):
    def pending(self):
        return self.filter(status='pending')
    def for_user(self, user):
        return self.filter(user=user).order_by('-created_at')

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = OrderManager()

    class Meta:
        indexes = [models.Index(fields=['user', '-created_at'])]
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.id} ({self.status})'""",
},
{
    "request": "Django REST Framework viewset for orders",
    "language": "python", "framework": "django-rest-framework",
    "code": """from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Order
from .serializers import OrderSerializer

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.for_user(self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status not in ('pending', 'paid'):
            return Response({'error': 'cannot cancel'}, status=400)
        order.status = 'cancelled'
        order.save()
        return Response({'status': 'cancelled'})""",
},
{
    "request": "Django URL routing with router and namespace",
    "language": "python", "framework": "django",
    "code": """from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'products', views.ProductViewSet, basename='product')

app_name = 'shop'
urlpatterns = [
    path('api/', include(router.urls)),
    path('api/auth/', include('rest_framework.urls')),
    path('checkout/', views.checkout_view, name='checkout'),
]""",
},

# ───────── FastAPI ─────────
{
    "request": "FastAPI minimal app with Pydantic + dependencies",
    "language": "python", "framework": "fastapi",
    "code": """from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Annotated

app = FastAPI()

class OrderCreate(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)
    address: str = Field(min_length=5)

class OrderOut(BaseModel):
    id: int
    total: float
    status: str

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = decode_token(token)
    if not user:
        raise HTTPException(401, 'invalid token')
    return user

@app.post('/orders', response_model=OrderOut, status_code=201)
async def create_order(
    payload: OrderCreate,
    user = Depends(get_current_user),
):
    order = await db.orders.insert(**payload.dict(), user_id=user.id)
    return order

@app.get('/orders/{order_id}', response_model=OrderOut)
async def get_order(order_id: int, user = Depends(get_current_user)):
    order = await db.orders.get(order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404)
    return order""",
},
{
    "request": "FastAPI async SQLAlchemy with PostgreSQL",
    "language": "python", "framework": "fastapi",
    "code": """from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine('postgresql+asyncpg://user:pw@localhost/db', echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): ...

class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    total: Mapped[float]
    status: Mapped[str] = mapped_column(default='pending')

async def get_db():
    async with SessionLocal() as s:
        yield s

@app.get('/orders/{order_id}')
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    o = await db.get(Order, order_id)
    if not o:
        raise HTTPException(404)
    return o""",
},

# ───────── Authentication ─────────
{
    "request": "bcrypt password hashing in Python",
    "language": "python", "framework": "bcrypt",
    "code": """import bcrypt

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())""",
},
{
    "request": "JWT login flow in Express",
    "language": "javascript", "framework": "express",
    "code": """const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');

router.post('/auth/register', async (req, res) => {
  const { email, password } = req.body;
  const hash = await bcrypt.hash(password, 12);
  const user = await User.create({ email, password: hash });
  const token = jwt.sign({ sub: user._id }, process.env.JWT_SECRET, { expiresIn: '7d' });
  res.status(201).json({ token, user: { id: user._id, email } });
});

router.post('/auth/login', async (req, res) => {
  const { email, password } = req.body;
  const user = await User.findOne({ email });
  if (!user || !(await bcrypt.compare(password, user.password)))
    return res.status(401).json({ error: 'bad credentials' });
  const token = jwt.sign({ sub: user._id }, process.env.JWT_SECRET, { expiresIn: '7d' });
  res.json({ token, user: { id: user._id, email } });
});""",
},

# ───────── Docker ─────────
{
    "request": "Dockerfile for Node.js Express app (multi-stage)",
    "language": "dockerfile", "framework": "docker",
    "code": """FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=deps /app/node_modules ./node_modules
COPY . .
USER node
EXPOSE 3000
CMD ["node", "src/server.js"]""",
},
{
    "request": "Dockerfile for Python FastAPI app",
    "language": "dockerfile", "framework": "docker",
    "code": """FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \\
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]""",
},
{
    "request": "docker-compose for backend + Postgres + Redis",
    "language": "yaml", "framework": "docker-compose",
    "code": """version: "3.9"
services:
  api:
    build: ./backend
    ports: ["3000:3000"]
    environment:
      DATABASE_URL: postgres://app:secret@db:5432/appdb
      REDIS_URL: redis://redis:6379
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_started }
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
    volumes: ["pg_data:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "app"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes: ["redis_data:/data"]

volumes:
  pg_data:
  redis_data:""",
},

# ───────── Kubernetes ─────────
{
    "request": "Kubernetes deployment + service + ingress for an API",
    "language": "yaml", "framework": "kubernetes",
    "code": """apiVersion: apps/v1
kind: Deployment
metadata: { name: api }
spec:
  replicas: 3
  selector: { matchLabels: { app: api } }
  template:
    metadata: { labels: { app: api } }
    spec:
      containers:
        - name: api
          image: registry.example.com/api:1.0.0
          ports: [{ containerPort: 3000 }]
          envFrom: [{ secretRef: { name: api-secrets } }]
          resources:
            requests: { cpu: "100m", memory: "128Mi" }
            limits:   { cpu: "500m", memory: "512Mi" }
          readinessProbe:
            httpGet: { path: /api/health, port: 3000 }
            initialDelaySeconds: 5
          livenessProbe:
            httpGet: { path: /api/health, port: 3000 }
            initialDelaySeconds: 15
---
apiVersion: v1
kind: Service
metadata: { name: api }
spec:
  selector: { app: api }
  ports: [{ port: 80, targetPort: 3000 }]
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt
spec:
  tls: [{ hosts: [api.example.com], secretName: api-tls }]
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend: { service: { name: api, port: { number: 80 } } }""",
},
{
    "request": "Kubernetes ConfigMap + Secret + envFrom usage",
    "language": "yaml", "framework": "kubernetes",
    "code": """apiVersion: v1
kind: ConfigMap
metadata: { name: api-config }
data:
  LOG_LEVEL: "info"
  PORT: "3000"
---
apiVersion: v1
kind: Secret
metadata: { name: api-secrets }
type: Opaque
stringData:
  JWT_SECRET: "change-me"
  DATABASE_URL: "postgres://app:secret@postgres:5432/appdb"
---
# Inside the Pod spec:
# envFrom:
#   - configMapRef: { name: api-config }
#   - secretRef:    { name: api-secrets }""",
},

# ───────── Python advanced ─────────
{
    "request": "Python decorator with arguments and functools.wraps",
    "language": "python", "framework": "stdlib",
    "code": """from functools import wraps
import time

def retry(times=3, backoff=1.0, exc=(Exception,)):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            for i in range(times):
                try:
                    return fn(*a, **kw)
                except exc as e:
                    if i == times - 1:
                        raise
                    time.sleep(backoff * (2 ** i))
        return wrapper
    return deco

@retry(times=4, backoff=0.5)
def fetch(url):
    import requests
    return requests.get(url, timeout=5).json()""",
},
{
    "request": "Python async aiohttp concurrent requests",
    "language": "python", "framework": "aiohttp",
    "code": """import asyncio, aiohttp

async def fetch(session, url):
    async with session.get(url) as r:
        return await r.json()

async def main(urls):
    async with aiohttp.ClientSession() as s:
        return await asyncio.gather(*(fetch(s, u) for u in urls))

if __name__ == '__main__':
    urls = ['https://api.github.com/repos/python/cpython',
            'https://api.github.com/repos/django/django']
    results = asyncio.run(main(urls))
    for r in results:
        print(r['name'], r['stargazers_count'])""",
},
{
    "request": "Python dataclass with validation and defaults",
    "language": "python", "framework": "stdlib",
    "code": """from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class Order:
    id: int
    user_id: int
    items: list[dict] = field(default_factory=list)
    total: float = 0.0
    status: str = 'pending'
    created_at: datetime = field(default_factory=datetime.utcnow)
    notes: Optional[str] = None

    def __post_init__(self):
        valid = {'pending', 'paid', 'shipped', 'delivered', 'cancelled'}
        if self.status not in valid:
            raise ValueError(f'status must be one of {valid}')
        if self.total < 0:
            raise ValueError('total cannot be negative')""",
},

# ───────── Testing ─────────
{
    "request": "Jest test for an Express endpoint with supertest",
    "language": "javascript", "framework": "jest",
    "code": """const request = require('supertest');
const app = require('../src/app');

describe('POST /api/orders', () => {
  it('creates an order with valid data', async () => {
    const r = await request(app)
      .post('/api/orders')
      .set('Authorization', `Bearer ${TEST_TOKEN}`)
      .send({ productId: 'p1', quantity: 2, address: '12 Main St' });
    expect(r.status).toBe(201);
    expect(r.body).toHaveProperty('_id');
    expect(r.body.total).toBeGreaterThan(0);
  });

  it('rejects invalid quantity', async () => {
    const r = await request(app)
      .post('/api/orders')
      .set('Authorization', `Bearer ${TEST_TOKEN}`)
      .send({ productId: 'p1', quantity: 0, address: '12 Main St' });
    expect(r.status).toBe(400);
  });
});""",
},
{
    "request": "pytest with fixtures and parametrize for Django",
    "language": "python", "framework": "pytest",
    "code": """import pytest
from django.contrib.auth.models import User
from .models import Order

@pytest.fixture
def user(db):
    return User.objects.create_user(username='alice', password='pw')

@pytest.fixture
def order(user):
    return Order.objects.create(user=user, total=100, status='pending')

@pytest.mark.parametrize('status,expected_code', [
    ('paid', 200),
    ('shipped', 200),
    ('cancelled', 400),
])
def test_cancel_order(client, user, order, status, expected_code):
    order.status = status
    order.save()
    client.force_login(user)
    r = client.post(f'/api/orders/{order.id}/cancel/')
    assert r.status_code == expected_code""",
},

# ───────── WebSockets ─────────
{
    "request": "Express + Socket.IO realtime chat server",
    "language": "javascript", "framework": "socket.io",
    "code": """const http = require('http');
const { Server } = require('socket.io');
const app = require('./app');

const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*' } });

io.use((socket, next) => {
  const token = socket.handshake.auth?.token;
  try { socket.user = jwt.verify(token, process.env.JWT_SECRET); next(); }
  catch { next(new Error('unauthorized')); }
});

io.on('connection', (socket) => {
  socket.on('join', (roomId) => socket.join(roomId));
  socket.on('message', ({ roomId, text }) => {
    io.to(roomId).emit('message', { user: socket.user.email, text, ts: Date.now() });
  });
  socket.on('disconnect', () => {});
});

server.listen(3000);""",
},

# ───────── Caching / Redis ─────────
{
    "request": "Redis caching wrapper around a slow function",
    "language": "python", "framework": "redis",
    "code": """import json, hashlib, redis
from functools import wraps

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

def cached(ttl=300, prefix='c'):
    def deco(fn):
        @wraps(fn)
        def wrap(*args, **kwargs):
            key = f'{prefix}:{fn.__name__}:' + hashlib.md5(
                json.dumps([args, kwargs], default=str).encode()
            ).hexdigest()
            hit = r.get(key)
            if hit:
                return json.loads(hit)
            result = fn(*args, **kwargs)
            r.setex(key, ttl, json.dumps(result, default=str))
            return result
        return wrap
    return deco

@cached(ttl=60)
def get_top_products(limit=10):
    # heavy DB query
    return Product.objects.order_by('-sales')[:limit]""",
},

# ───────── Web scraping ─────────
{
    "request": "Python web scraper with BeautifulSoup + requests",
    "language": "python", "framework": "beautifulsoup4",
    "code": """import requests
from bs4 import BeautifulSoup

def scrape_articles(url):
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    out = []
    for art in soup.select('article'):
        title = art.select_one('h2, h3')
        link = art.select_one('a[href]')
        if title and link:
            out.append({
                'title': title.get_text(strip=True),
                'url': requests.compat.urljoin(url, link['href']),
            })
    return out""",
},

# ───────── CI/CD ─────────
{
    "request": "GitHub Actions CI workflow for Node.js + tests",
    "language": "yaml", "framework": "github-actions",
    "code": """name: CI
on: { push: { branches: [main] }, pull_request: {} }

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [18, 20]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --coverage
      - uses: codecov/codecov-action@v4
        with: { token: ${{ secrets.CODECOV_TOKEN }} }""",
},

# ───────── React Query ─────────
{
    "request": "React Query (TanStack) for fetching & mutations",
    "language": "tsx", "framework": "tanstack-query",
    "code": """import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const fetchOrders = () => fetch('/api/orders').then(r => r.json());
const createOrder = (data: any) => fetch('/api/orders', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
}).then(r => r.json());

export function Orders() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['orders'], queryFn: fetchOrders });
  const m = useMutation({
    mutationFn: createOrder,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  });
  if (isLoading) return <p>Loading…</p>;
  return (
    <>
      <ul>{data.map((o: any) => <li key={o.id}>{o.id}</li>)}</ul>
      <button onClick={() => m.mutate({ productId: 1, qty: 1 })}>+ order</button>
    </>
  );
}""",
},
]
