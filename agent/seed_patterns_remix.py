"""Remix (and React Router 7) reference patterns — basics through advanced.

Indexed by natural-language request. Each entry is an adaptable template the
agent retrieves before generating new code, so the user gets known-good
Remix idioms instead of model-invented variants.
"""
from __future__ import annotations


REMIX_SEED: list[dict] = [

# ───────── Project setup ─────────
{
    "request": "create a new Remix project from scratch",
    "language": "bash", "framework": "remix",
    "code": """npx create-remix@latest my-app
cd my-app
npm install
npm run dev   # http://localhost:3000""",
},
{
    "request": "Remix project structure overview",
    "language": "text", "framework": "remix",
    "code": """app/
  root.tsx           # HTML shell, top-level layout, ErrorBoundary
  entry.client.tsx   # hydrate
  entry.server.tsx   # SSR render
  routes/
    _index.tsx       # /
    about.tsx        # /about
    posts.$id.tsx    # /posts/:id
    posts.tsx        # parent layout for /posts/*
    _auth.login.tsx  # /login (pathless layout: _auth.tsx wraps)
  utils/
    db.server.ts     # .server.* = server-only, never bundled to client
    session.server.ts
public/              # static assets
remix.config.js
tsconfig.json""",
},
{
    "request": "Remix root.tsx with Links/Meta/Scripts and ErrorBoundary",
    "language": "tsx", "framework": "remix",
    "code": """import { Links, Meta, Outlet, Scripts, ScrollRestoration, isRouteErrorResponse, useRouteError } from "@remix-run/react";
import type { LinksFunction, MetaFunction } from "@remix-run/node";
import styles from "./tailwind.css?url";

export const links: LinksFunction = () => [{ rel: "stylesheet", href: styles }];
export const meta: MetaFunction = () => [{ title: "My App" }];

export default function App() {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width,initial-scale=1" />
        <Meta /><Links />
      </head>
      <body>
        <Outlet />
        <ScrollRestoration /><Scripts />
      </body>
    </html>
  );
}

export function ErrorBoundary() {
  const error = useRouteError();
  if (isRouteErrorResponse(error)) {
    return <div><h1>{error.status} {error.statusText}</h1><p>{error.data}</p></div>;
  }
  return <div><h1>App Error</h1><pre>{error instanceof Error ? error.message : "Unknown"}</pre></div>;
}""",
},

# ───────── Routing ─────────
{
    "request": "Remix file-based routing conventions",
    "language": "text", "framework": "remix",
    "code": """File             | URL              | Notes
-----------------|------------------|----------------------------------
_index.tsx       | /                | index of parent
about.tsx        | /about           | leaf route
posts.tsx        | /posts/*         | layout (renders <Outlet/>)
posts._index.tsx | /posts           | index of /posts
posts.$id.tsx    | /posts/:id       | dynamic param
posts.$.tsx      | /posts/*         | splat
_auth.tsx        | (pathless)       | wraps without adding URL segment
($lang)._index   | /:lang? optional | optional segment
admin._layout    | /admin           | nested layout

Use dots for hierarchy. Underscore prefix = pathless wrapper. Dollar = param.""",
},
{
    "request": "Remix dynamic route with loader using params",
    "language": "tsx", "framework": "remix",
    "code": """// app/routes/posts.$slug.tsx
import { json, type LoaderFunctionArgs } from "@remix-run/node";
import { useLoaderData } from "@remix-run/react";
import { db } from "~/utils/db.server";

export async function loader({ params }: LoaderFunctionArgs) {
  const post = await db.post.findUnique({ where: { slug: params.slug! } });
  if (!post) throw new Response("Not found", { status: 404 });
  return json({ post });
}

export default function Post() {
  const { post } = useLoaderData<typeof loader>();
  return <article><h1>{post.title}</h1><div dangerouslySetInnerHTML={{__html: post.html}} /></article>;
}""",
},
{
    "request": "Remix nested layout with Outlet",
    "language": "tsx", "framework": "remix",
    "code": """// app/routes/dashboard.tsx — parent layout for /dashboard/*
import { Outlet, NavLink } from "@remix-run/react";

export default function DashboardLayout() {
  return (
    <div className="grid grid-cols-[200px_1fr]">
      <aside>
        <NavLink to=".">Overview</NavLink>
        <NavLink to="orders">Orders</NavLink>
        <NavLink to="settings">Settings</NavLink>
      </aside>
      <main><Outlet /></main>
    </div>
  );
}""",
},
{
    "request": "Remix pathless layout route",
    "language": "tsx", "framework": "remix",
    "code": """// app/routes/_auth.tsx — wraps login/register WITHOUT adding URL segment
// /login and /register both render inside this layout
import { Outlet } from "@remix-run/react";
export default function AuthLayout() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-6 bg-white rounded shadow"><Outlet /></div>
    </div>
  );
}
// app/routes/_auth.login.tsx — /login uses _auth.tsx as layout
// app/routes/_auth.register.tsx — /register uses _auth.tsx as layout""",
},

# ───────── Loaders ─────────
{
    "request": "Remix loader with searchParams pagination",
    "language": "tsx", "framework": "remix",
    "code": """import { json, type LoaderFunctionArgs } from "@remix-run/node";
import { useLoaderData, Link, useSearchParams } from "@remix-run/react";
import { db } from "~/utils/db.server";

export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url);
  const page = Number(url.searchParams.get("page") ?? "1");
  const q = url.searchParams.get("q") ?? "";
  const PAGE_SIZE = 20;
  const where = q ? { title: { contains: q, mode: "insensitive" as const } } : {};
  const [items, total] = await Promise.all([
    db.post.findMany({ where, skip: (page - 1) * PAGE_SIZE, take: PAGE_SIZE, orderBy: { createdAt: "desc" } }),
    db.post.count({ where }),
  ]);
  return json({ items, total, page, pageCount: Math.ceil(total / PAGE_SIZE) });
}

export default function Posts() {
  const { items, page, pageCount } = useLoaderData<typeof loader>();
  const [params] = useSearchParams();
  const next = new URLSearchParams(params); next.set("page", String(page + 1));
  return (<>
    <ul>{items.map(p => <li key={p.id}>{p.title}</li>)}</ul>
    {page < pageCount && <Link to={`?${next}`}>Next</Link>}
  </>);
}""",
},
{
    "request": "Remix loader response headers and caching",
    "language": "tsx", "framework": "remix",
    "code": """import { json, type LoaderFunctionArgs, type HeadersFunction } from "@remix-run/node";

export async function loader({ request }: LoaderFunctionArgs) {
  const data = await fetchPublicFeed();
  return json(data, {
    headers: {
      "Cache-Control": "public, max-age=60, s-maxage=300, stale-while-revalidate=86400",
    },
  });
}

// Promote loader headers to the route response
export const headers: HeadersFunction = ({ loaderHeaders }) => ({
  "Cache-Control": loaderHeaders.get("Cache-Control") ?? "no-store",
});""",
},
{
    "request": "Remix throw redirect from loader",
    "language": "tsx", "framework": "remix",
    "code": """import { redirect, type LoaderFunctionArgs } from "@remix-run/node";
import { requireUserId } from "~/utils/session.server";

export async function loader({ request }: LoaderFunctionArgs) {
  const userId = await requireUserId(request);  // throws redirect("/login") if missing
  // ... continue
  return null;
}""",
},
{
    "request": "Remix parallel loaders with Promise.all",
    "language": "tsx", "framework": "remix",
    "code": """export async function loader({ params }: LoaderFunctionArgs) {
  const [user, orders, stats] = await Promise.all([
    db.user.findUniqueOrThrow({ where: { id: params.userId! } }),
    db.order.findMany({ where: { userId: params.userId }, take: 10, orderBy: { createdAt: "desc" } }),
    getStats(params.userId!),
  ]);
  return json({ user, orders, stats });
}""",
},

# ───────── Actions / Mutations ─────────
{
    "request": "Remix action handling form POST",
    "language": "tsx", "framework": "remix",
    "code": """import { json, redirect, type ActionFunctionArgs } from "@remix-run/node";
import { Form, useActionData, useNavigation } from "@remix-run/react";

export async function action({ request }: ActionFunctionArgs) {
  const form = await request.formData();
  const title = String(form.get("title") ?? "").trim();
  const body = String(form.get("body") ?? "").trim();

  const errors: Record<string, string> = {};
  if (title.length < 3) errors.title = "Title must be 3+ chars";
  if (body.length < 10) errors.body = "Body must be 10+ chars";
  if (Object.keys(errors).length) return json({ errors }, { status: 400 });

  const post = await db.post.create({ data: { title, body } });
  return redirect(`/posts/${post.id}`);
}

export default function NewPost() {
  const data = useActionData<typeof action>();
  const nav = useNavigation();
  const busy = nav.state === "submitting";
  return (
    <Form method="post" className="space-y-3">
      <input name="title" placeholder="Title" />
      {data?.errors?.title && <p className="text-red-500">{data.errors.title}</p>}
      <textarea name="body" placeholder="Body" />
      {data?.errors?.body && <p className="text-red-500">{data.errors.body}</p>}
      <button disabled={busy}>{busy ? "Saving…" : "Publish"}</button>
    </Form>
  );
}""",
},
{
    "request": "Remix action with intent-based multi-button form",
    "language": "tsx", "framework": "remix",
    "code": """// One Form, multiple actions distinguished by name="intent"
export async function action({ request, params }: ActionFunctionArgs) {
  const form = await request.formData();
  const intent = form.get("intent");
  switch (intent) {
    case "delete":
      await db.post.delete({ where: { id: params.id! } });
      return redirect("/posts");
    case "publish":
      await db.post.update({ where: { id: params.id! }, data: { published: true } });
      return json({ ok: true });
    default:
      throw new Response("bad intent", { status: 400 });
  }
}

export default function Edit() {
  return (
    <Form method="post">
      <button name="intent" value="publish">Publish</button>
      <button name="intent" value="delete">Delete</button>
    </Form>
  );
}""",
},
{
    "request": "Remix Zod validation in action",
    "language": "tsx", "framework": "remix",
    "code": """import { z } from "zod";
const Schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  name: z.string().min(2).max(60),
});

export async function action({ request }: ActionFunctionArgs) {
  const form = Object.fromEntries(await request.formData());
  const parsed = Schema.safeParse(form);
  if (!parsed.success) {
    return json({ errors: parsed.error.flatten().fieldErrors }, { status: 400 });
  }
  const user = await db.user.create({ data: parsed.data });
  return redirect(`/users/${user.id}`);
}""",
},

# ───────── useFetcher / Optimistic UI ─────────
{
    "request": "Remix useFetcher for inline mutations without navigation",
    "language": "tsx", "framework": "remix",
    "code": """import { useFetcher } from "@remix-run/react";

function LikeButton({ postId, liked, count }: { postId: string; liked: boolean; count: number }) {
  const fetcher = useFetcher();
  // optimistic — assume the toggle succeeds
  const optimisticLiked = fetcher.formData ? fetcher.formData.get("liked") === "true" : liked;
  const optimisticCount = count + (optimisticLiked === liked ? 0 : optimisticLiked ? 1 : -1);
  return (
    <fetcher.Form method="post" action={`/posts/${postId}/like`}>
      <input type="hidden" name="liked" value={optimisticLiked ? "false" : "true"} />
      <button>{optimisticLiked ? "♥" : "♡"} {optimisticCount}</button>
    </fetcher.Form>
  );
}""",
},
{
    "request": "Remix optimistic create-and-clear list",
    "language": "tsx", "framework": "remix",
    "code": """import { Form, useFetchers, useLoaderData } from "@remix-run/react";

export default function Todos() {
  const { todos } = useLoaderData<typeof loader>();
  const fetchers = useFetchers();
  const pendingItems = fetchers
    .filter(f => f.formAction === "/todos" && f.formMethod === "POST" && f.formData)
    .map(f => ({ id: `pending-${f.key}`, text: String(f.formData!.get("text")), pending: true }));
  const all = [...todos, ...pendingItems];
  return (<>
    <Form method="post" replace><input name="text" /><button>Add</button></Form>
    <ul>{all.map(t => <li key={t.id} style={{opacity: t.pending ? 0.5 : 1}}>{t.text}</li>)}</ul>
  </>);
}""",
},

# ───────── Sessions / Auth ─────────
{
    "request": "Remix cookie session storage",
    "language": "ts", "framework": "remix",
    "code": """// app/utils/session.server.ts
import { createCookieSessionStorage, redirect } from "@remix-run/node";

const storage = createCookieSessionStorage({
  cookie: {
    name: "__session",
    secure: process.env.NODE_ENV === "production",
    secrets: [process.env.SESSION_SECRET!],
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,   // 30 days
    httpOnly: true,
  },
});

export async function getSession(request: Request) {
  return storage.getSession(request.headers.get("Cookie"));
}

export async function requireUserId(request: Request, redirectTo = new URL(request.url).pathname) {
  const session = await getSession(request);
  const userId = session.get("userId");
  if (!userId) {
    const params = new URLSearchParams([["redirectTo", redirectTo]]);
    throw redirect(`/login?${params}`);
  }
  return userId as string;
}

export async function createUserSession(userId: string, redirectTo: string) {
  const session = await storage.getSession();
  session.set("userId", userId);
  return redirect(redirectTo, {
    headers: { "Set-Cookie": await storage.commitSession(session) },
  });
}

export async function logout(request: Request) {
  const session = await getSession(request);
  return redirect("/", { headers: { "Set-Cookie": await storage.destroySession(session) } });
}""",
},
{
    "request": "Remix login route with bcrypt password check",
    "language": "tsx", "framework": "remix",
    "code": """// app/routes/_auth.login.tsx
import { json, redirect, type ActionFunctionArgs } from "@remix-run/node";
import { Form, useActionData, useSearchParams } from "@remix-run/react";
import bcrypt from "bcryptjs";
import { db } from "~/utils/db.server";
import { createUserSession } from "~/utils/session.server";

export async function action({ request }: ActionFunctionArgs) {
  const form = await request.formData();
  const email = String(form.get("email"));
  const password = String(form.get("password"));
  const redirectTo = String(form.get("redirectTo") || "/");

  const user = await db.user.findUnique({ where: { email } });
  if (!user || !(await bcrypt.compare(password, user.passwordHash))) {
    return json({ error: "Invalid credentials" }, { status: 401 });
  }
  return createUserSession(user.id, redirectTo);
}

export default function Login() {
  const data = useActionData<typeof action>();
  const [params] = useSearchParams();
  return (
    <Form method="post">
      <input type="hidden" name="redirectTo" value={params.get("redirectTo") ?? "/"} />
      <input name="email" type="email" required />
      <input name="password" type="password" required />
      {data?.error && <p className="text-red-500">{data.error}</p>}
      <button>Sign in</button>
    </Form>
  );
}""",
},
{
    "request": "Remix logout action route",
    "language": "tsx", "framework": "remix",
    "code": """// app/routes/logout.tsx
import { type ActionFunctionArgs, redirect } from "@remix-run/node";
import { logout } from "~/utils/session.server";

export const action = ({ request }: ActionFunctionArgs) => logout(request);
export const loader = () => redirect("/");

// Trigger from anywhere with:
// <Form action="/logout" method="post"><button>Sign out</button></Form>""",
},
{
    "request": "Remix flash message via session",
    "language": "ts", "framework": "remix",
    "code": """// session.server.ts — extend with flash helpers
export async function setFlash(request: Request, message: string, type: "ok"|"error" = "ok") {
  const session = await getSession(request);
  session.flash("flash", { message, type });
  return storage.commitSession(session);
}

// In an action:
//   const cookie = await setFlash(request, "Saved", "ok");
//   return redirect("/x", { headers: { "Set-Cookie": cookie } });

// In root.tsx loader:
//   const session = await getSession(request);
//   const flash = session.get("flash");
//   return json({ flash }, { headers: { "Set-Cookie": await storage.commitSession(session) } });""",
},

# ───────── Streaming / defer ─────────
{
    "request": "Remix defer with Await for slow data",
    "language": "tsx", "framework": "remix",
    "code": """import { defer, type LoaderFunctionArgs } from "@remix-run/node";
import { Await, useLoaderData } from "@remix-run/react";
import { Suspense } from "react";

export async function loader({ params }: LoaderFunctionArgs) {
  const productPromise = db.product.findUniqueOrThrow({ where: { id: params.id! } });
  const reviewsPromise = fetchReviews(params.id!); // slow — defer
  // await fast data, defer slow data
  return defer({ product: await productPromise, reviews: reviewsPromise });
}

export default function Product() {
  const { product, reviews } = useLoaderData<typeof loader>();
  return (
    <>
      <h1>{product.title}</h1>
      <Suspense fallback={<p>Loading reviews…</p>}>
        <Await resolve={reviews} errorElement={<p>Failed to load reviews</p>}>
          {(r) => <ul>{r.map(x => <li key={x.id}>{x.text}</li>)}</ul>}
        </Await>
      </Suspense>
    </>
  );
}""",
},

# ───────── Resource routes ─────────
{
    "request": "Remix resource route returning JSON API",
    "language": "ts", "framework": "remix",
    "code": """// app/routes/api.posts.ts — no default export = resource route
import { json, type LoaderFunctionArgs } from "@remix-run/node";
import { db } from "~/utils/db.server";

export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url);
  const limit = Math.min(50, Number(url.searchParams.get("limit") ?? 20));
  const items = await db.post.findMany({ take: limit, orderBy: { createdAt: "desc" } });
  return json({ items }, { headers: { "Cache-Control": "public, max-age=30" } });
}""",
},
{
    "request": "Remix resource route serving an image",
    "language": "ts", "framework": "remix",
    "code": """// app/routes/avatar.$userId[.png].ts
import type { LoaderFunctionArgs } from "@remix-run/node";
import { renderAvatar } from "~/utils/avatar.server";

export async function loader({ params }: LoaderFunctionArgs) {
  const png = await renderAvatar(params.userId!);
  return new Response(png, {
    headers: {
      "Content-Type": "image/png",
      "Cache-Control": "public, max-age=86400, immutable",
    },
  });
}""",
},
{
    "request": "Remix resource route generating sitemap.xml",
    "language": "ts", "framework": "remix",
    "code": """// app/routes/[sitemap.xml].ts
import { db } from "~/utils/db.server";
export async function loader() {
  const posts = await db.post.findMany({ select: { slug: true, updatedAt: true } });
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${posts.map(p => `<url><loc>https://example.com/posts/${p.slug}</loc><lastmod>${p.updatedAt.toISOString()}</lastmod></url>`).join("\\n")}
</urlset>`;
  return new Response(xml, { headers: { "Content-Type": "application/xml" } });
}""",
},

# ───────── File uploads ─────────
{
    "request": "Remix file upload to disk",
    "language": "tsx", "framework": "remix",
    "code": """import {
  json, unstable_composeUploadHandlers, unstable_createFileUploadHandler,
  unstable_createMemoryUploadHandler, unstable_parseMultipartFormData,
} from "@remix-run/node";

export async function action({ request }: ActionFunctionArgs) {
  const handler = unstable_composeUploadHandlers(
    unstable_createFileUploadHandler({
      directory: "./public/uploads",
      maxPartSize: 10_000_000,    // 10 MB
      file: ({ filename }) => `${Date.now()}-${filename}`,
    }),
    unstable_createMemoryUploadHandler(),
  );
  const form = await unstable_parseMultipartFormData(request, handler);
  const file = form.get("file") as any;
  return json({ url: `/uploads/${file.name}` });
}

// <Form encType="multipart/form-data" method="post">
//   <input type="file" name="file" />
//   <button>Upload</button>
// </Form>""",
},

# ───────── Meta / SEO ─────────
{
    "request": "Remix meta function with parent data",
    "language": "tsx", "framework": "remix",
    "code": """import type { MetaFunction } from "@remix-run/node";

export const meta: MetaFunction<typeof loader> = ({ data, matches }) => {
  if (!data) return [{ title: "Not found" }];
  const root = matches.find(m => m.id === "root")?.data as any;
  return [
    { title: `${data.post.title} — ${root?.siteName ?? "Blog"}` },
    { name: "description", content: data.post.excerpt },
    { property: "og:title", content: data.post.title },
    { property: "og:image", content: data.post.coverUrl },
    { tagName: "link", rel: "canonical", href: `https://example.com/posts/${data.post.slug}` },
  ];
};""",
},

# ───────── Forms quality of life ─────────
{
    "request": "Remix form with conform-to/zod for typed errors",
    "language": "tsx", "framework": "remix",
    "code": """import { useForm, getInputProps } from "@conform-to/react";
import { parseWithZod } from "@conform-to/zod";
import { z } from "zod";

const Schema = z.object({ name: z.string().min(2), email: z.string().email() });

export async function action({ request }: ActionFunctionArgs) {
  const submission = parseWithZod(await request.formData(), { schema: Schema });
  if (submission.status !== "success") return json(submission.reply(), { status: 400 });
  // submission.value is fully typed
  await db.contact.create({ data: submission.value });
  return redirect("/thanks");
}

export default function Contact() {
  const lastResult = useActionData<typeof action>();
  const [form, fields] = useForm({ lastResult, onValidate: ({ formData }) => parseWithZod(formData, { schema: Schema }) });
  return (
    <Form method="post" id={form.id} onSubmit={form.onSubmit}>
      <input {...getInputProps(fields.name, { type: "text" })} /><span>{fields.name.errors}</span>
      <input {...getInputProps(fields.email, { type: "email" })} /><span>{fields.email.errors}</span>
      <button>Send</button>
    </Form>
  );
}""",
},

# ───────── Database ─────────
{
    "request": "Remix Prisma client singleton (db.server.ts)",
    "language": "ts", "framework": "remix",
    "code": """// app/utils/db.server.ts
import { PrismaClient } from "@prisma/client";

let db: PrismaClient;
declare global { var __db__: PrismaClient | undefined; }

if (process.env.NODE_ENV === "production") {
  db = new PrismaClient();
} else {
  if (!global.__db__) global.__db__ = new PrismaClient({ log: ["query", "error"] });
  db = global.__db__;
}
export { db };""",
},

# ───────── Errors ─────────
{
    "request": "Remix per-route ErrorBoundary",
    "language": "tsx", "framework": "remix",
    "code": """import { isRouteErrorResponse, useRouteError } from "@remix-run/react";

export function ErrorBoundary() {
  const error = useRouteError();
  if (isRouteErrorResponse(error)) {
    if (error.status === 404) return <h1>Post not found</h1>;
    if (error.status === 401) return <h1>Please sign in</h1>;
    return <h1>{error.status} {error.statusText}</h1>;
  }
  return <h1>Unexpected error</h1>;
}""",
},

# ───────── Env / config ─────────
{
    "request": "Remix typed environment variables",
    "language": "ts", "framework": "remix",
    "code": """// app/utils/env.server.ts
import { z } from "zod";
const Env = z.object({
  DATABASE_URL: z.string().url(),
  SESSION_SECRET: z.string().min(32),
  STRIPE_SECRET: z.string().startsWith("sk_"),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
});
export const env = Env.parse(process.env);   // throws on boot if invalid""",
},

# ───────── Middleware-ish (entry.server) ─────────
{
    "request": "Remix add security headers in entry.server.tsx",
    "language": "tsx", "framework": "remix",
    "code": """// app/entry.server.tsx — wrap the response after rendering
export default async function handleRequest(
  request: Request, statusCode: number, headers: Headers, ctx: any, loadCtx: any,
) {
  const response = await renderToReadable(...);   // your existing render
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "geolocation=(), camera=(), microphone=()");
  response.headers.set(
    "Content-Security-Policy",
    "default-src 'self'; img-src 'self' data: https:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
  );
  return response;
}""",
},

# ───────── Testing ─────────
{
    "request": "Remix loader unit test with vitest",
    "language": "ts", "framework": "remix",
    "code": """import { loader } from "~/routes/posts.$slug";
import { describe, it, expect, vi } from "vitest";

vi.mock("~/utils/db.server", () => ({
  db: { post: { findUnique: vi.fn().mockResolvedValue({ id: "1", slug: "hello", title: "Hello" }) } },
}));

describe("posts.$slug loader", () => {
  it("returns the post", async () => {
    const res = await loader({ params: { slug: "hello" }, request: new Request("http://t/"), context: {} } as any);
    const data = await res.json();
    expect(data.post.title).toBe("Hello");
  });
});""",
},

# ───────── Caching layers ─────────
{
    "request": "Remix per-request cache with cachified",
    "language": "ts", "framework": "remix",
    "code": """import { cachified, lruCacheAdapter } from "@epic-web/cachified";
import { LRUCache } from "lru-cache";
const lru = lruCacheAdapter(new LRUCache<string, any>({ max: 1000 }));

export async function getProduct(id: string) {
  return cachified({
    key: `product:${id}`, cache: lru, ttl: 1000 * 60 * 5,        // 5 min
    staleWhileRevalidate: 1000 * 60 * 60,                          // 1 hour
    getFreshValue: () => db.product.findUniqueOrThrow({ where: { id } }),
  });
}""",
},

# ───────── Shopify-on-Hydrogen note ─────────
{
    "request": "Remix is the foundation of Shopify Hydrogen",
    "language": "text", "framework": "remix",
    "code": """Shopify Hydrogen 2+ is built directly on Remix:
- Routes, loaders, actions, useFetcher → all standard Remix.
- Hydrogen adds Storefront API client (storefront.query / storefront.mutate),
  cart helpers, customer account API, image/money formatters, analytics.
- Deploys on Oxygen (Shopify's edge runtime).
- All Remix patterns above apply directly. See SHOPIFY_SEED for Hydrogen-specific patterns.""",
},

# ───────── Cookie auth alt ─────────
{
    "request": "Remix JWT-in-cookie auth",
    "language": "ts", "framework": "remix",
    "code": """import { createCookie, redirect } from "@remix-run/node";
import jwt from "jsonwebtoken";

const tokenCookie = createCookie("token", {
  httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production",
  path: "/", maxAge: 60 * 60 * 24 * 7,
});

export async function setToken(payload: object) {
  const token = jwt.sign(payload, process.env.JWT_SECRET!, { expiresIn: "7d" });
  return tokenCookie.serialize(token);
}

export async function getUserFromRequest(request: Request) {
  const token = await tokenCookie.parse(request.headers.get("Cookie"));
  if (!token) return null;
  try { return jwt.verify(token, process.env.JWT_SECRET!) as { sub: string; email: string }; }
  catch { return null; }
}""",
},

# ───────── Server only utility marker ─────────
{
    "request": "Remix .server.ts files explained",
    "language": "text", "framework": "remix",
    "code": """File suffix `.server.ts` (or `.server.tsx`) marks a module as server-only:
- Never bundled into the client.
- Safe place for: db queries, secrets, fs access, server SDKs (Stripe, AWS, etc).
- Loaders/actions can import them freely; components must NOT.
- Counterpart: `.client.tsx` for client-only modules (e.g. window-dependent libs).

Example: app/utils/stripe.server.ts
  import Stripe from "stripe";
  export const stripe = new Stripe(process.env.STRIPE_SECRET!, { apiVersion: "2024-06-20" });""",
},

# ───────── Search/filters URL pattern ─────────
{
    "request": "Remix searchParams driven filter UI",
    "language": "tsx", "framework": "remix",
    "code": """// URL is the source of truth for filters → bookmarkable + shareable
import { Form, useLoaderData, useSearchParams, useSubmit } from "@remix-run/react";

export default function Products() {
  const { items } = useLoaderData<typeof loader>();
  const [params] = useSearchParams();
  const submit = useSubmit();
  return (
    <Form method="get" onChange={(e) => submit(e.currentTarget)}>
      <input name="q" defaultValue={params.get("q") ?? ""} placeholder="search" />
      <select name="sort" defaultValue={params.get("sort") ?? "new"}>
        <option value="new">Newest</option>
        <option value="price">Price</option>
      </select>
      <ul>{items.map(p => <li key={p.id}>{p.title}</li>)}</ul>
    </Form>
  );
}""",
},

# ───────── Webhooks ─────────
{
    "request": "Remix webhook receiver with signature verify",
    "language": "ts", "framework": "remix",
    "code": """// app/routes/webhooks.stripe.ts
import { type ActionFunctionArgs, json } from "@remix-run/node";
import { stripe } from "~/utils/stripe.server";

export async function action({ request }: ActionFunctionArgs) {
  const sig = request.headers.get("stripe-signature")!;
  const raw = await request.text();
  let event;
  try {
    event = stripe.webhooks.constructEvent(raw, sig, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch (e) {
    return new Response(`Bad sig: ${(e as Error).message}`, { status: 400 });
  }

  switch (event.type) {
    case "checkout.session.completed": await fulfillOrder(event.data.object); break;
    case "invoice.payment_failed":     await markPaymentFailed(event.data.object); break;
  }
  return json({ received: true });
}""",
},

# ───────── Background jobs ─────────
{
    "request": "Remix background job queue with bullmq",
    "language": "ts", "framework": "remix",
    "code": """// queue.server.ts
import { Queue, Worker } from "bullmq";
import IORedis from "ioredis";
const connection = new IORedis(process.env.REDIS_URL!, { maxRetriesPerRequest: null });

export const emailQueue = new Queue("email", { connection });

if (process.env.RUN_WORKERS === "true") {
  new Worker("email", async (job) => {
    const { to, subject, body } = job.data;
    await sendMail({ to, subject, body });
  }, { connection });
}

// In an action:
//   await emailQueue.add("welcome", { to: user.email, subject: "Welcome", body: "..." });""",
},

# ───────── Realtime via SSE ─────────
{
    "request": "Remix Server-Sent Events stream from a resource route",
    "language": "ts", "framework": "remix",
    "code": """// app/routes/events.ts
import { type LoaderFunctionArgs } from "@remix-run/node";
import { eventStream } from "remix-utils/sse/server";

export async function loader({ request }: LoaderFunctionArgs) {
  return eventStream(request.signal, function setup(send) {
    const sub = bus.on("notification", (n) => send({ event: "notification", data: JSON.stringify(n) }));
    return () => sub.unsubscribe();
  });
}

// Client:
//   import { useEventSource } from "remix-utils/sse/react";
//   const last = useEventSource("/events", { event: "notification" });""",
},

# ───────── Pricing / Stripe ─────────
{
    "request": "Remix Stripe Checkout session creation",
    "language": "ts", "framework": "remix",
    "code": """// app/routes/checkout.tsx
import { redirect, type ActionFunctionArgs } from "@remix-run/node";
import { stripe } from "~/utils/stripe.server";
import { requireUserId } from "~/utils/session.server";

export async function action({ request }: ActionFunctionArgs) {
  const userId = await requireUserId(request);
  const form = await request.formData();
  const priceId = String(form.get("priceId"));
  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    line_items: [{ price: priceId, quantity: 1 }],
    customer_email: (await db.user.findUniqueOrThrow({ where: { id: userId } })).email,
    success_url: `${process.env.BASE_URL}/billing?success=1`,
    cancel_url:  `${process.env.BASE_URL}/billing?cancel=1`,
    metadata: { userId },
  });
  return redirect(session.url!, { status: 303 });
}""",
},

# ───────── Internationalization ─────────
{
    "request": "Remix i18n with remix-i18next basic setup",
    "language": "ts", "framework": "remix",
    "code": """// app/utils/i18n.server.ts
import { RemixI18Next } from "remix-i18next/server";
import Backend from "i18next-fs-backend";
import { resolve } from "node:path";

export const i18next = new RemixI18Next({
  detection: { supportedLanguages: ["en","es","ja"], fallbackLanguage: "en" },
  i18next: {
    backend: { loadPath: resolve("./public/locales/{{lng}}/{{ns}}.json") },
  },
  plugins: [Backend],
});

// In root.tsx loader:
//   const locale = await i18next.getLocale(request);
//   return json({ locale });""",
},

# ───────── Static / public ─────────
{
    "request": "Remix robots.txt resource route",
    "language": "ts", "framework": "remix",
    "code": """// app/routes/[robots.txt].ts
export const loader = () => new Response(
  `User-agent: *\\nAllow: /\\nSitemap: https://example.com/sitemap.xml\\n`,
  { headers: { "Content-Type": "text/plain" } },
);""",
},

# ───────── Remix v2 future flags ─────────
{
    "request": "Remix v2/React Router 7 future flags reference",
    "language": "js", "framework": "remix",
    "code": """// remix.config.js
/** @type {import('@remix-run/dev').AppConfig} */
module.exports = {
  future: {
    v3_fetcherPersist: true,        // persist fetchers across navigations
    v3_relativeSplatPath: true,     // fixes relative paths under splat routes
    v3_throwAbortReason: true,      // useNavigate aborts throw real reasons
    v3_singleFetch: true,           // single round-trip for nested loaders
    v3_lazyRouteDiscovery: true,    // smaller manifests
  },
  serverModuleFormat: "esm",
};""",
},

# ───────── Performance ─────────
{
    "request": "Remix prefetch links on hover",
    "language": "tsx", "framework": "remix",
    "code": """import { Link } from "@remix-run/react";

// "intent" = prefetch route module + loader data on mouseover/focus
<Link to="/posts" prefetch="intent">Posts</Link>

// "render" = prefetch immediately (use sparingly)
<Link to="/critical" prefetch="render">Critical</Link>

// "viewport" = prefetch when link enters viewport
<Link to="/feed" prefetch="viewport">Feed</Link>""",
},

# ───────── Debug ─────────
{
    "request": "Remix log all loader/action timings",
    "language": "ts", "framework": "remix",
    "code": """// In each .server util or as wrapper:
export function withTiming<T>(name: string, fn: () => Promise<T>): Promise<T> {
  const t0 = performance.now();
  return fn().finally(() => {
    const ms = (performance.now() - t0).toFixed(1);
    console.log(`[${name}] ${ms}ms`);
  });
}
// Usage:
//   const post = await withTiming("loader:posts.$slug", () => db.post.findUnique(...));""",
},

# ───────── Deployment ─────────
{
    "request": "Remix deploy to Vercel/Netlify/Fly.io quick reference",
    "language": "text", "framework": "remix",
    "code": """Vercel:    `npx create-remix@latest --template remix-run/remix/templates/vercel`
Netlify:   adapter `@netlify/remix-adapter`; `netlify deploy --prod`
Fly.io:    `fly launch --copy-config` from official Remix Fly template
Cloudflare:adapter `@remix-run/cloudflare`; deploy via Wrangler
Node:      `npm run build && npm run start` (default Remix Node server)
Oxygen:    Shopify Hydrogen apps deploy here automatically.""",
},

]
