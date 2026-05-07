"""Shopify reference patterns — Storefront API, Admin API, Hydrogen, Liquid themes,
Shopify Apps, Polaris, App Bridge, Webhooks, OAuth, Functions, Customer Account API.

Indexed by natural-language request.
"""
from __future__ import annotations


SHOPIFY_SEED: list[dict] = [

# ───────── Orientation ─────────
{
    "request": "Shopify ecosystem overview — what to use when",
    "language": "text", "framework": "shopify",
    "code": """STOREFRONT API     — public read of products/collections/cart, server or client
                     Use for: custom storefront, headless, mobile apps
ADMIN API          — privileged read/write, requires app auth
                     Use for: backend integrations, sync jobs, admin apps
HYDROGEN           — Shopify's React framework on Remix, deploys to Oxygen edge
                     Use for: full custom storefront in React
LIQUID THEMES      — Online Store 2.0 themes (Dawn etc.), sections + blocks
                     Use for: storefronts that should stay in Shopify Admin
SHOPIFY APPS       — embedded admin apps (App Bridge + Polaris), via shopify-app-remix
                     Use for: extending merchant admin, public apps in App Store
SHOPIFY FUNCTIONS  — Rust/JS WASM logic for discounts, payment, delivery, cart
                     Use for: custom commerce logic at checkout/cart
CUSTOMER ACCOUNT   — new login system replacing classic accounts
APP BRIDGE         — JS bridge from your iframe to Shopify admin shell
POLARIS            — official React component library matching admin UI
OXYGEN             — Shopify's edge runtime (free for Hydrogen apps)""",
},

# ───────── Hydrogen project ─────────
{
    "request": "create a new Shopify Hydrogen project",
    "language": "bash", "framework": "hydrogen",
    "code": """npm create @shopify/hydrogen@latest
cd my-store
npm install
# .env — fill from your store
#   PUBLIC_STORE_DOMAIN=myshop.myshopify.com
#   PUBLIC_STOREFRONT_API_TOKEN=...
#   PUBLIC_STOREFRONT_ID=...
#   SESSION_SECRET=$(openssl rand -hex 32)
npm run dev      # http://localhost:3000

# Deploy to Oxygen (free, Shopify-managed):
npx shopify hydrogen link
npx shopify hydrogen deploy""",
},
{
    "request": "Hydrogen storefront client setup in server.ts",
    "language": "ts", "framework": "hydrogen",
    "code": """// server.ts
import { createStorefrontClient, storefrontRedirect } from "@shopify/hydrogen";
import { createRequestHandler, getStorefrontHeaders } from "@shopify/remix-oxygen";

export default {
  async fetch(request: Request, env: Env, executionContext: ExecutionContext) {
    const { storefront } = createStorefrontClient({
      cache: await caches.open("hydrogen"),
      waitUntil: (p) => executionContext.waitUntil(p),
      buyerIp: getStorefrontHeaders(request).get("x-forwarded-for") ?? "",
      i18n: { language: "EN", country: "US" },
      publicStorefrontToken: env.PUBLIC_STOREFRONT_API_TOKEN,
      privateStorefrontToken: env.PRIVATE_STOREFRONT_API_TOKEN,
      storeDomain: env.PUBLIC_STORE_DOMAIN,
      storefrontHeaders: getStorefrontHeaders(request),
    });

    const handleRequest = createRequestHandler({
      build: await import("./build/server"),
      mode: process.env.NODE_ENV,
      getLoadContext: () => ({ storefront, env, waitUntil: executionContext.waitUntil }),
    });
    const response = await handleRequest(request);
    if (response.status === 404) return storefrontRedirect({ request, response, storefront });
    return response;
  },
};""",
},

# ───────── Storefront API queries ─────────
{
    "request": "Shopify Storefront API: list products query (Hydrogen loader)",
    "language": "tsx", "framework": "hydrogen",
    "code": """import { json, type LoaderFunctionArgs } from "@shopify/remix-oxygen";
import { useLoaderData, Link } from "@remix-run/react";

const PRODUCTS_QUERY = `#graphql
  query Products($first: Int!) {
    products(first: $first) {
      nodes {
        id handle title
        featuredImage { url altText width height }
        priceRange { minVariantPrice { amount currencyCode } }
      }
    }
  }
`;

export async function loader({ context }: LoaderFunctionArgs) {
  const { products } = await context.storefront.query(PRODUCTS_QUERY, { variables: { first: 20 } });
  return json({ products });
}

export default function Index() {
  const { products } = useLoaderData<typeof loader>();
  return (
    <ul className="grid grid-cols-3 gap-4">
      {products.nodes.map((p: any) => (
        <li key={p.id}>
          <Link to={`/products/${p.handle}`}>
            <img src={p.featuredImage?.url} alt={p.featuredImage?.altText ?? ""} />
            <h3>{p.title}</h3>
            <p>{p.priceRange.minVariantPrice.amount} {p.priceRange.minVariantPrice.currencyCode}</p>
          </Link>
        </li>
      ))}
    </ul>
  );
}""",
},
{
    "request": "Shopify Storefront API: full product detail by handle",
    "language": "tsx", "framework": "hydrogen",
    "code": """const PRODUCT_QUERY = `#graphql
  query Product($handle: String!, $selectedOptions: [SelectedOptionInput!]!) {
    product(handle: $handle) {
      id title handle descriptionHtml vendor
      options { name optionValues { name } }
      selectedOrFirstAvailableVariant(selectedOptions: $selectedOptions) {
        id title availableForSale quantityAvailable
        price { amount currencyCode }
        compareAtPrice { amount currencyCode }
        image { url altText width height }
        product { handle title }
        selectedOptions { name value }
      }
      variants(first: 50) { nodes { id title availableForSale selectedOptions { name value } price { amount currencyCode } } }
      seo { title description }
      images(first: 10) { nodes { url altText width height } }
    }
  }
`;

export async function loader({ params, request, context }: LoaderFunctionArgs) {
  const url = new URL(request.url);
  const selectedOptions = Array.from(url.searchParams.entries())
    .filter(([k]) => !k.startsWith("_"))
    .map(([name, value]) => ({ name, value }));
  const { product } = await context.storefront.query(PRODUCT_QUERY, {
    variables: { handle: params.handle!, selectedOptions },
  });
  if (!product) throw new Response(null, { status: 404 });
  return json({ product });
}""",
},
{
    "request": "Shopify Storefront API: collection with products",
    "language": "graphql", "framework": "hydrogen",
    "code": """query Collection($handle: String!, $first: Int!, $cursor: String) {
  collection(handle: $handle) {
    id title description seo { title description }
    image { url altText }
    products(first: $first, after: $cursor) {
      nodes {
        id handle title
        featuredImage { url altText }
        priceRange { minVariantPrice { amount currencyCode } }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}""",
},

# ───────── Cart API ─────────
{
    "request": "Hydrogen cart: add to cart action",
    "language": "tsx", "framework": "hydrogen",
    "code": """import { CartForm } from "@shopify/hydrogen";
import { type ActionFunctionArgs, json } from "@shopify/remix-oxygen";

export async function action({ request, context }: ActionFunctionArgs) {
  const { cart } = context;
  const formData = await request.formData();
  const { action: cartAction, inputs } = CartForm.getFormInput(formData);

  let result;
  switch (cartAction) {
    case CartForm.ACTIONS.LinesAdd:        result = await cart.addLines(inputs.lines); break;
    case CartForm.ACTIONS.LinesUpdate:     result = await cart.updateLines(inputs.lines); break;
    case CartForm.ACTIONS.LinesRemove:     result = await cart.removeLines(inputs.lineIds); break;
    case CartForm.ACTIONS.DiscountCodesUpdate: result = await cart.updateDiscountCodes(inputs.discountCodes); break;
    case CartForm.ACTIONS.BuyerIdentityUpdate: result = await cart.updateBuyerIdentity(inputs.buyerIdentity); break;
    default: throw new Error(`${cartAction} cart action not defined`);
  }

  const headers = cart.setCartId(result.cart.id);
  return json({ cart: result.cart, errors: result.userErrors }, { status: 200, headers });
}

// Component:
//   <CartForm route="/cart" action={CartForm.ACTIONS.LinesAdd}
//             inputs={{ lines: [{ merchandiseId: variantId, quantity: 1 }] }}>
//     <button>Add to cart</button>
//   </CartForm>""",
},
{
    "request": "Hydrogen cart: read current cart in loader",
    "language": "tsx", "framework": "hydrogen",
    "code": """export async function loader({ context }: LoaderFunctionArgs) {
  const cart = await context.cart.get();
  return json({ cart });
}

// cart fields:
//   cart.id
//   cart.totalQuantity
//   cart.cost.totalAmount.{ amount, currencyCode }
//   cart.cost.subtotalAmount
//   cart.cost.totalTaxAmount
//   cart.lines.nodes[].{ id, quantity, merchandise.{ id, title, product, image, price } }
//   cart.discountCodes
//   cart.checkoutUrl   // redirect here for checkout""",
},
{
    "request": "Hydrogen redirect to Shopify checkout",
    "language": "tsx", "framework": "hydrogen",
    "code": """// Just send the user to cart.checkoutUrl — Shopify hosts the actual checkout.
function CheckoutButton({ checkoutUrl }: { checkoutUrl: string }) {
  return <a href={checkoutUrl} className="btn">Checkout</a>;
}
// Or programmatically:
//   return redirect(cart.checkoutUrl, { status: 303 });""",
},

# ───────── Money / image ─────────
{
    "request": "Hydrogen Money component formatting",
    "language": "tsx", "framework": "hydrogen",
    "code": """import { Money, Image } from "@shopify/hydrogen";

<Money data={product.priceRange.minVariantPrice} />
<Money data={variant.compareAtPrice} as="s" />   // strikethrough

<Image data={product.featuredImage} sizes="(min-width: 768px) 33vw, 100vw"
       aspectRatio="1/1" loading="lazy" />
// Hydrogen auto-generates srcSet from Shopify CDN with width/height/format options.""",
},

# ───────── Customer Account API ─────────
{
    "request": "Hydrogen Customer Account API setup",
    "language": "ts", "framework": "hydrogen",
    "code": """// server.ts — add to context
import { createCustomerAccountClient } from "@shopify/hydrogen";

const customerAccount = createCustomerAccountClient({
  waitUntil: (p) => executionContext.waitUntil(p),
  request, session, customerAccountId: env.PUBLIC_CUSTOMER_ACCOUNT_API_CLIENT_ID,
  customerAccountUrl: env.PUBLIC_CUSTOMER_ACCOUNT_API_URL,
});

// In loaders/actions: context.customerAccount

// app/routes/account.login.ts
import { type LoaderFunctionArgs } from "@shopify/remix-oxygen";
export async function loader({ context }: LoaderFunctionArgs) {
  return context.customerAccount.login();   // 302 to Shopify-hosted login
}

// app/routes/account.authorize.ts — OAuth callback
export async function loader({ context }: LoaderFunctionArgs) {
  return context.customerAccount.authorize();
}

// app/routes/account.logout.ts
export async function loader({ context }: LoaderFunctionArgs) {
  return context.customerAccount.logout();
}""",
},
{
    "request": "Customer Account API: read customer profile + orders",
    "language": "graphql", "framework": "hydrogen",
    "code": """query CustomerOrders($first: Int!) {
  customer {
    firstName lastName emailAddress { emailAddress }
    orders(first: $first, sortKey: PROCESSED_AT, reverse: true) {
      nodes {
        id name processedAt financialStatus fulfillmentStatus
        totalPrice { amount currencyCode }
        lineItems(first: 50) {
          nodes { title quantity image { url altText } variantTitle }
        }
      }
    }
  }
}

// In loader:
//   const { data } = await context.customerAccount.query(CUSTOMER_ORDERS, { variables: { first: 20 } });""",
},

# ───────── Shopify App (admin embedded) ─────────
{
    "request": "Shopify Admin App with shopify-app-remix scaffold",
    "language": "bash", "framework": "shopify-app",
    "code": """npm init @shopify/app@latest -- --template=remix
cd my-app
npm run dev          # opens partner dashboard, installs to dev store

# Key files:
#   shopify.app.toml           — app metadata, scopes, webhooks
#   shopify.web.toml           — your web component
#   app/shopify.server.ts      — auth helpers
#   app/routes/app.tsx         — embedded admin shell
#   app/routes/auth.$.tsx      — OAuth callbacks (auto)
#   app/routes/webhooks.tsx    — webhook receiver (auto)""",
},
{
    "request": "Shopify App admin route with authenticated Admin GraphQL",
    "language": "tsx", "framework": "shopify-app",
    "code": """import { json } from "@remix-run/node";
import { authenticate } from "../shopify.server";
import { Page, Layout, Card, BlockStack, Text } from "@shopify/polaris";
import { useLoaderData } from "@remix-run/react";

export async function loader({ request }: LoaderFunctionArgs) {
  const { admin, session } = await authenticate.admin(request);
  const response = await admin.graphql(`#graphql
    query { products(first: 10) { nodes { id title handle status } } }
  `);
  const { data } = await response.json();
  return json({ shop: session.shop, products: data.products.nodes });
}

export default function App() {
  const { shop, products } = useLoaderData<typeof loader>();
  return (
    <Page title={`Products in ${shop}`}>
      <Layout>
        <Layout.Section>
          <Card>
            <BlockStack gap="200">
              {products.map((p: any) => <Text as="p" key={p.id}>{p.title} ({p.status})</Text>)}
            </BlockStack>
          </Card>
        </Layout.Section>
      </Layout>
    </Page>
  );
}""",
},
{
    "request": "Shopify App: create product mutation from admin app",
    "language": "ts", "framework": "shopify-app",
    "code": """const CREATE_PRODUCT = `#graphql
  mutation productCreate($input: ProductInput!) {
    productCreate(input: $input) {
      product { id title handle }
      userErrors { field message }
    }
  }
`;

export async function action({ request }: ActionFunctionArgs) {
  const { admin } = await authenticate.admin(request);
  const form = await request.formData();
  const res = await admin.graphql(CREATE_PRODUCT, {
    variables: {
      input: {
        title: String(form.get("title")),
        productType: "Shirt",
        vendor: "My Brand",
        status: "ACTIVE",
        variants: [{ price: "29.99", inventoryQuantities: [{ availableQuantity: 10, locationId: "gid://shopify/Location/1" }] }],
      },
    },
  });
  const { data } = await res.json();
  if (data.productCreate.userErrors.length) {
    return json({ errors: data.productCreate.userErrors }, { status: 400 });
  }
  return json({ product: data.productCreate.product });
}""",
},

# ───────── Polaris ─────────
{
    "request": "Shopify Polaris layout with form components",
    "language": "tsx", "framework": "polaris",
    "code": """import { Page, Layout, Card, FormLayout, TextField, Button, Banner } from "@shopify/polaris";
import { useState } from "react";

export default function Settings() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  return (
    <Page title="Settings" backAction={{ content: "Back", url: "/app" }}>
      <Layout>
        <Layout.Section>
          <Banner title="Heads up" tone="info">Changes take a minute to propagate.</Banner>
          <Card>
            <FormLayout>
              <TextField label="Name" value={name} onChange={setName} autoComplete="off" />
              <TextField label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" />
              <Button variant="primary" submit>Save</Button>
            </FormLayout>
          </Card>
        </Layout.Section>
      </Layout>
    </Page>
  );
}""",
},
{
    "request": "Shopify Polaris IndexTable for resource lists",
    "language": "tsx", "framework": "polaris",
    "code": """import { IndexTable, useIndexResourceState, Card, Text, Badge } from "@shopify/polaris";

export function Orders({ orders }: { orders: any[] }) {
  const { selectedResources, allResourcesSelected, handleSelectionChange } =
    useIndexResourceState(orders);

  const rows = orders.map((o, i) => (
    <IndexTable.Row id={o.id} key={o.id} position={i} selected={selectedResources.includes(o.id)}>
      <IndexTable.Cell><Text fontWeight="bold" as="span">{o.name}</Text></IndexTable.Cell>
      <IndexTable.Cell>{o.customer?.email}</IndexTable.Cell>
      <IndexTable.Cell><Badge tone={o.financialStatus === "paid" ? "success" : "attention"}>{o.financialStatus}</Badge></IndexTable.Cell>
      <IndexTable.Cell>${o.total}</IndexTable.Cell>
    </IndexTable.Row>
  ));

  return (
    <Card padding="0">
      <IndexTable
        resourceName={{ singular: "order", plural: "orders" }}
        itemCount={orders.length}
        selectedItemsCount={allResourcesSelected ? "All" : selectedResources.length}
        onSelectionChange={handleSelectionChange}
        headings={[{ title: "Order" }, { title: "Customer" }, { title: "Status" }, { title: "Total" }]}
      >{rows}</IndexTable>
    </Card>
  );
}""",
},

# ───────── App Bridge ─────────
{
    "request": "Shopify App Bridge: open modal from admin app",
    "language": "tsx", "framework": "app-bridge",
    "code": """// App Bridge v4 (declarative web components, no React wrapper needed)
import { Modal, TitleBar } from "@shopify/app-bridge-react";

function ConfirmDelete({ open, onClose, onConfirm }: any) {
  return (
    <Modal open={open} onHide={onClose} variant="small">
      <TitleBar title="Delete product?" />
      <p style={{ padding: 16 }}>This cannot be undone.</p>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, padding: 16 }}>
        <button onClick={onClose}>Cancel</button>
        <button onClick={onConfirm} className="destructive">Delete</button>
      </div>
    </Modal>
  );
}""",
},
{
    "request": "Shopify App Bridge: toast notification",
    "language": "tsx", "framework": "app-bridge",
    "code": """// app/utils/toast.ts (client)
export function showToast(message: string, isError = false) {
  shopify.toast.show(message, { isError, duration: 3000 });
}
// `shopify` is the global injected by App Bridge in embedded apps.""",
},

# ───────── Webhooks ─────────
{
    "request": "Shopify webhook: orders/create receiver in Remix app",
    "language": "ts", "framework": "shopify-app",
    "code": """// app/routes/webhooks.tsx — registered in shopify.app.toml as orders/create
import { authenticate } from "../shopify.server";

export const action = async ({ request }: ActionFunctionArgs) => {
  const { topic, shop, payload } = await authenticate.webhook(request);
  switch (topic) {
    case "ORDERS_CREATE":
      await db.order.create({
        data: {
          shop, shopifyId: payload.id.toString(),
          email: payload.email,
          totalPrice: payload.total_price,
          createdAt: new Date(payload.created_at),
          rawJson: payload,
        },
      });
      break;
    case "APP_UNINSTALLED":
      await db.session.deleteMany({ where: { shop } });
      break;
    case "CUSTOMERS_REDACT":
    case "CUSTOMERS_DATA_REQUEST":
    case "SHOP_REDACT":
      // GDPR — handle within 30 days
      await handleGdpr(topic, shop, payload);
      break;
  }
  return new Response();    // 200, empty body
};""",
},
{
    "request": "Shopify webhook signature verification (raw HMAC, no SDK)",
    "language": "ts", "framework": "shopify",
    "code": """import crypto from "node:crypto";

export function verifyShopifyWebhook(rawBody: string, hmacHeader: string, secret: string): boolean {
  const expected = crypto
    .createHmac("sha256", secret)
    .update(rawBody, "utf8")
    .digest("base64");
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(hmacHeader));
}

// In a generic handler:
//   const raw = await request.text();
//   const hmac = request.headers.get("x-shopify-hmac-sha256")!;
//   if (!verifyShopifyWebhook(raw, hmac, process.env.SHOPIFY_API_SECRET!)) {
//     return new Response("invalid signature", { status: 401 });
//   }""",
},

# ───────── Admin REST + GraphQL ─────────
{
    "request": "Shopify Admin GraphQL: bulk operation for full product export",
    "language": "graphql", "framework": "shopify-admin",
    "code": """# 1. Start bulk operation — runs in background, results streamed to a JSONL file URL
mutation {
  bulkOperationRunQuery(query: \"\"\"
    {
      products {
        edges {
          node {
            id title handle vendor status createdAt
            variants { edges { node { id sku price inventoryQuantity } } }
          }
        }
      }
    }
  \"\"\") {
    bulkOperation { id status }
    userErrors { field message }
  }
}

# 2. Poll status:
query { currentBulkOperation { id status errorCode objectCount url } }

# 3. When status=COMPLETED, fetch `url` (signed JSONL stream).""",
},
{
    "request": "Shopify Admin REST API: list orders with axios",
    "language": "ts", "framework": "shopify-admin",
    "code": """import axios from "axios";
const api = axios.create({
  baseURL: `https://${SHOP}.myshopify.com/admin/api/2024-10`,
  headers: { "X-Shopify-Access-Token": ACCESS_TOKEN, "Content-Type": "application/json" },
});

const res = await api.get("/orders.json", {
  params: { status: "any", limit: 50, financial_status: "paid", created_at_min: "2024-01-01" },
});
console.log(res.data.orders.length);

// Pagination — use `Link` header:
//   const next = parseLinkHeader(res.headers.link).next?.url;""",
},

# ───────── Liquid theme ─────────
{
    "request": "Shopify Liquid: section with schema and blocks",
    "language": "liquid", "framework": "liquid",
    "code": """{% comment %} sections/featured-products.liquid {% endcomment %}
<section class="featured-products" style="background:{{ section.settings.bg }}">
  <h2>{{ section.settings.heading }}</h2>
  <div class="grid">
    {%- for block in section.blocks -%}
      {%- assign p = all_products[block.settings.product] -%}
      <a href="{{ p.url }}" class="card" {{ block.shopify_attributes }}>
        <img src="{{ p.featured_image | image_url: width: 600 }}" alt="{{ p.title | escape }}" loading="lazy">
        <h3>{{ p.title }}</h3>
        <p>{{ p.price | money }}</p>
      </a>
    {%- endfor -%}
  </div>
</section>

{% schema %}
{
  "name": "Featured products",
  "settings": [
    { "type": "text",  "id": "heading", "label": "Heading", "default": "Featured" },
    { "type": "color", "id": "bg",      "label": "Background", "default": "#ffffff" }
  ],
  "blocks": [
    { "type": "product", "name": "Product",
      "settings": [{ "type": "product", "id": "product", "label": "Product" }]
    }
  ],
  "max_blocks": 8,
  "presets": [{ "name": "Featured products" }]
}
{% endschema %}""",
},
{
    "request": "Shopify Liquid: product page with variant picker",
    "language": "liquid", "framework": "liquid",
    "code": """{%- assign current = product.selected_or_first_available_variant -%}
<form method="post" action="/cart/add" data-product-form>
  <input type="hidden" name="id" value="{{ current.id }}">
  {%- for option in product.options_with_values -%}
    <label>{{ option.name }}</label>
    <select name="options[{{ option.name | escape }}]">
      {%- for value in option.values -%}
        <option value="{{ value | escape }}" {% if option.selected_value == value %}selected{% endif %}>{{ value }}</option>
      {%- endfor -%}
    </select>
  {%- endfor -%}
  <span class="price">{{ current.price | money }}</span>
  <button type="submit" {% unless current.available %}disabled{% endunless %}>
    {% if current.available %}Add to cart{% else %}Sold out{% endif %}
  </button>
</form>""",
},
{
    "request": "Shopify Liquid: cart drawer fragment via Section Rendering API",
    "language": "liquid", "framework": "liquid",
    "code": """{% comment %} sections/cart-drawer.liquid {% endcomment %}
<aside class="cart-drawer" data-cart>
  <header><h2>Your cart</h2><button data-close>×</button></header>
  {%- if cart.item_count == 0 -%}
    <p>Empty</p>
  {%- else -%}
    <ul>
      {%- for line in cart.items -%}
      <li>
        <img src="{{ line.image | image_url: width: 100 }}" alt="">
        <div>
          <p>{{ line.product.title }} — {{ line.variant.title }}</p>
          <p>{{ line.final_line_price | money }}</p>
          <input type="number" min="0" data-line="{{ line.key }}" value="{{ line.quantity }}">
        </div>
      </li>
      {%- endfor -%}
    </ul>
    <p>Subtotal: {{ cart.total_price | money }}</p>
    <a href="/checkout" class="btn">Checkout</a>
  {%- endif -%}
</aside>

{% schema %}{ "name": "Cart drawer" }{% endschema %}

{# Update from JS:
   fetch('/cart/change.js', { method:'POST', body: new URLSearchParams({ id: lineKey, quantity: '0' })})
     .then(()=>fetch('/?sections=cart-drawer')).then(r=>r.json()).then(s=>render(s['cart-drawer']));
#}""",
},
{
    "request": "Shopify Liquid: metafields access patterns",
    "language": "liquid", "framework": "liquid",
    "code": """{%- comment -%} read metafields on product / variant / customer / shop {%- endcomment -%}

{%- assign size_chart = product.metafields.custom.size_chart -%}
{%- if size_chart -%}<div class="rich-text">{{ size_chart | metafield_tag }}</div>{%- endif -%}

{%- assign care = product.metafields.custom.care_instructions.value -%}
{%- if care -%}<p>{{ care }}</p>{%- endif -%}

{%- comment -%} list reference metafield {%- endcomment -%}
{%- for related in product.metafields.custom.related_products.value -%}
  <a href="{{ related.url }}">{{ related.title }}</a>
{%- endfor -%}

{%- comment -%} shop-wide metafield {%- endcomment -%}
<p>Phone: {{ shop.metafields.contact.phone }}</p>""",
},

# ───────── Functions ─────────
{
    "request": "Shopify Functions overview and types",
    "language": "text", "framework": "shopify-functions",
    "code": """Shopify Functions = your custom logic in Wasm at checkout.
Types:
  - product_discounts          (e.g. "buy 3 get 1 free")
  - order_discounts            (e.g. "free shipping over $X")
  - shipping_discounts
  - payment_customization      (hide payment methods conditionally)
  - delivery_customization     (hide / rename / reorder shipping methods)
  - cart_transform             (split, merge, expand line items)
  - cart_checkout_validation   (block checkout if rules fail)
  - fulfillment_constraints

Stack: Rust or JS, compiled to Wasm. Defined as `extensions/<name>` in app dir.

Scaffold:
  shopify app generate extension --type=product_discounts --template=rust --name=my-discount
  cd extensions/my-discount && cargo build --target=wasm32-wasip1 --release
  shopify app deploy""",
},
{
    "request": "Shopify Function (JS) — product discount template",
    "language": "ts", "framework": "shopify-functions",
    "code": """// extensions/discount/src/run.ts
import type { RunInput, FunctionRunResult } from "../generated/api";

export function run(input: RunInput): FunctionRunResult {
  const TARGET_TAG = "sale";
  const DISCOUNT_PCT = 15;

  const targets = input.cart.lines
    .filter(line => line.merchandise.__typename === "ProductVariant"
                 && (line.merchandise as any).product.hasAnyTag)
    .map(line => ({ productVariant: { id: (line.merchandise as any).id } }));

  if (targets.length === 0) return { discounts: [], discountApplicationStrategy: "FIRST" as any };

  return {
    discounts: [{
      message: `${DISCOUNT_PCT}% off sale items`,
      targets,
      value: { percentage: { value: DISCOUNT_PCT.toString() } },
    }],
    discountApplicationStrategy: "FIRST" as any,
  };
}""",
},

# ───────── OAuth (custom apps) ─────────
{
    "request": "Shopify OAuth flow for a custom backend (no SDK)",
    "language": "text", "framework": "shopify",
    "code": """For custom/private apps, use shopify-app-remix. For pure backend OAuth:

1. Redirect merchant to:
   https://{shop}.myshopify.com/admin/oauth/authorize
     ?client_id={API_KEY}
     &scope=read_products,write_orders
     &redirect_uri={CALLBACK_URL}
     &state={NONCE}
     &grant_options[]=  (omit for offline, =per-user for online)

2. Shopify redirects back to CALLBACK with ?code=&hmac=&shop=&state=
   - Verify state matches.
   - Verify hmac (sha256 over query minus hmac, with API_SECRET).
   - Confirm shop matches /^[a-zA-Z0-9-]+\\.myshopify\\.com$/

3. Exchange code for token (POST):
   https://{shop}/admin/oauth/access_token
   { client_id, client_secret, code }
   → { access_token, scope }

4. Store {shop, access_token, scope}. Use access_token as
   "X-Shopify-Access-Token" header for all Admin API calls.

5. Subscribe to APP_UNINSTALLED webhook so you can clear credentials.""",
},

# ───────── App Proxy ─────────
{
    "request": "Shopify App Proxy: serve dynamic content under /apps/X",
    "language": "ts", "framework": "shopify-app",
    "code": """// app/routes/apps.proxy.$.tsx — App Proxy verifies signature for you with shopify-app-remix
import { authenticate } from "../shopify.server";

export async function loader({ request }: LoaderFunctionArgs) {
  const { liquid, session } = await authenticate.public.appProxy(request);
  // Return HTML (rendered through theme via liquid()), JSON, or any response
  return liquid(`
    <h2>Hello from app proxy on {{ shop.name }}</h2>
    <p>Logged in as {{ customer.first_name | default: "guest" }}</p>
  `);
}""",
},

# ───────── Subscription billing ─────────
{
    "request": "Shopify recurring application charge (billing API)",
    "language": "ts", "framework": "shopify-app",
    "code": """// shopify.server.ts already configures billing plans. Charge from a route:
import { authenticate, MONTHLY_PLAN } from "../shopify.server";

export async function loader({ request }: LoaderFunctionArgs) {
  const { billing } = await authenticate.admin(request);
  await billing.require({
    plans: [MONTHLY_PLAN],
    isTest: process.env.NODE_ENV !== "production",
    onFailure: async () => billing.request({ plan: MONTHLY_PLAN, isTest: true }),
  });
  return null;   // user has active subscription
}

// shopify.server.ts:
//   export const MONTHLY_PLAN = "Monthly";
//   const shopify = shopifyApp({
//     billing: { [MONTHLY_PLAN]: { amount: 19, currencyCode: "USD", interval: BillingInterval.Every30Days } },
//     ...
//   });""",
},

# ───────── Admin shell deep links ─────────
{
    "request": "Shopify Admin App deep link to a product",
    "language": "tsx", "framework": "app-bridge",
    "code": """// In an embedded admin app, link to native admin pages:
import { useNavigate } from "@shopify/app-bridge-react";

function OpenProduct({ id }: { id: string }) {
  const nav = useNavigate();
  return <button onClick={() => nav(`/products/${id}`)}>Open in admin</button>;
}

// Or directly with a URL:
//   shopify://admin/products/123
//   /products/123  (App Bridge intercepts and opens in shell)""",
},

# ───────── Theme App Extensions ─────────
{
    "request": "Shopify Theme App Extension: app block for sections",
    "language": "liquid", "framework": "shopify-app",
    "code": """{% comment %} extensions/my-extension/blocks/badge.liquid {% endcomment %}
<div class="trust-badge" {{ block.shopify_attributes }}>
  <img src="{{ 'badge.svg' | asset_url }}" alt="">
  <span>{{ block.settings.text }}</span>
</div>

{% schema %}
{
  "name": "Trust badge",
  "target": "section",
  "settings": [
    { "type": "text", "id": "text", "label": "Text", "default": "30-day returns" }
  ]
}
{% endschema %}

{# Merchants then add this block from the theme editor without editing code. #}""",
},

# ───────── Markets / i18n ─────────
{
    "request": "Hydrogen Markets: country/language selector",
    "language": "tsx", "framework": "hydrogen",
    "code": """// Storefront API takes @inContext directives; Hydrogen exposes i18n on context
const PRODUCT_QUERY = `#graphql
  query Product($handle: String!, $country: CountryCode!, $language: LanguageCode!)
  @inContext(country: $country, language: $language) {
    product(handle: $handle) {
      title descriptionHtml
      priceRange { minVariantPrice { amount currencyCode } }
    }
  }
`;

export async function loader({ params, context }: LoaderFunctionArgs) {
  const { storefront } = context;
  const { product } = await storefront.query(PRODUCT_QUERY, {
    variables: {
      handle: params.handle!,
      country: storefront.i18n.country,    // e.g. "US"
      language: storefront.i18n.language,  // e.g. "EN"
    },
  });
  return json({ product });
}""",
},

# ───────── B2B / Customer accounts ─────────
{
    "request": "Hydrogen check if customer is logged in",
    "language": "tsx", "framework": "hydrogen",
    "code": """// In any loader:
const isLoggedIn = await context.customerAccount.isLoggedIn();
if (!isLoggedIn) return redirect("/account/login");

// Or in a layout to gate child routes:
export async function loader({ context }: LoaderFunctionArgs) {
  await context.customerAccount.handleAuthStatus();
  const isLoggedIn = await context.customerAccount.isLoggedIn();
  return json({ isLoggedIn });
}""",
},

# ───────── Image optimization ─────────
{
    "request": "Shopify CDN image URL transforms",
    "language": "text", "framework": "shopify",
    "code": """Append params to any Shopify CDN image URL:
  ...image.jpg?width=800&height=600&crop=center&format=webp&quality=75

Common transforms:
  width / height       (px or %)
  crop=center|top|bottom|left|right
  format=webp|jpg|pjpg|png
  quality=1-100
  pad_color=rrggbb     (when padding to fill aspect ratio)

In Liquid:
  {{ product.featured_image | image_url: width: 800, format: 'webp' }}

In Hydrogen:
  <Image data={image} sizes="(min-width:768px) 50vw, 100vw" aspectRatio="4/5" />""",
},

# ───────── Multi-pass / shop login ─────────
{
    "request": "Shopify Multipass SSO login token",
    "language": "ts", "framework": "shopify",
    "code": """import crypto from "node:crypto";

export function buildMultipassToken(secret: string, customer: { email: string; first_name?: string; last_name?: string; tag_string?: string }) {
  const blockSize = 16;
  const encryptionKey = crypto.createHash("sha256").update(secret).digest().subarray(0, 16);
  const signatureKey  = crypto.createHash("sha256").update(secret).digest().subarray(16, 32);

  const payload = JSON.stringify({ ...customer, created_at: new Date().toISOString() });
  const iv = crypto.randomBytes(blockSize);
  const cipher = crypto.createCipheriv("aes-128-cbc", encryptionKey, iv);
  const encrypted = Buffer.concat([iv, cipher.update(payload, "utf8"), cipher.final()]);
  const signature = crypto.createHmac("sha256", signatureKey).update(encrypted).digest();
  const token = Buffer.concat([encrypted, signature]).toString("base64url");
  return `https://${SHOP}.myshopify.com/account/login/multipass/${token}`;
}""",
},

# ───────── Storefront prefs ─────────
{
    "request": "Hydrogen prefetch product page on hover",
    "language": "tsx", "framework": "hydrogen",
    "code": """import { Link } from "@remix-run/react";

<Link to={`/products/${p.handle}`} prefetch="intent">
  <Image data={p.featuredImage} aspectRatio="1/1" sizes="33vw" />
  <h3>{p.title}</h3>
</Link>""",
},

# ───────── Analytics ─────────
{
    "request": "Hydrogen Shopify Analytics setup",
    "language": "tsx", "framework": "hydrogen",
    "code": """// app/root.tsx
import { Analytics, getShopAnalytics } from "@shopify/hydrogen";

export async function loader({ context }: LoaderFunctionArgs) {
  const shop = await getShopAnalytics({ storefront: context.storefront, publicStorefrontId: context.env.PUBLIC_STOREFRONT_ID });
  return json({ shop, consent: { checkoutDomain: context.env.PUBLIC_CHECKOUT_DOMAIN, storefrontAccessToken: context.env.PUBLIC_STOREFRONT_API_TOKEN } });
}

export default function App() {
  const { shop, consent } = useLoaderData<typeof loader>();
  return (
    <Analytics.Provider shop={shop} consent={consent}>
      {/* ... your app ... */}
    </Analytics.Provider>
  );
}

// Page-level:
//   <Analytics.ProductView data={{ products: [{ id, title, price, vendor, productType }] }} />
//   <Analytics.CartView />
//   <Analytics.SearchView data={{ searchTerm: q, searchResults: results }} />""",
},

# ───────── Local dev helpers ─────────
{
    "request": "Shopify CLI common commands",
    "language": "bash", "framework": "shopify",
    "code": """# Apps
shopify app dev                # tunnel + ngrok-like, opens partners
shopify app deploy             # build + push to Partners
shopify app generate extension # add an extension (function/checkout/theme)
shopify app config link
shopify app config push

# Themes
shopify theme dev              # local dev with hot reload
shopify theme push --live      # push to live theme (use with care)
shopify theme pull             # download theme files
shopify theme check            # lint Liquid

# Hydrogen
shopify hydrogen link
shopify hydrogen deploy
shopify hydrogen env pull""",
},

# ───────── Versioning ─────────
{
    "request": "Shopify API version reference",
    "language": "text", "framework": "shopify",
    "code": """API versions are quarterly: YYYY-01, YYYY-04, YYYY-07, YYYY-10.
- Each is supported for 12 months.
- Pin in the URL: /admin/api/2024-10/...
- Storefront API: include `Shopify-Storefront-Version: 2024-10` header (or use Hydrogen client which handles it).
- Deprecation warnings appear in `X-Shopify-API-Deprecated-Reason` response header.

Always test against the version one ahead of yours quarterly to catch deprecations early.""",
},

# ───────── Common gotchas ─────────
{
    "request": "Shopify GIDs (global IDs) and how to handle them",
    "language": "text", "framework": "shopify",
    "code": """All GraphQL IDs are GIDs:
  gid://shopify/Product/12345
  gid://shopify/ProductVariant/67890
  gid://shopify/Order/111
  gid://shopify/Customer/222

Helpers:
  // extract numeric ID
  const num = id.split("/").pop();
  // build GID
  const gid = `gid://shopify/Product/${num}`;

REST API uses bare numeric IDs; GraphQL uses GIDs. Don't mix them — convert at the boundary.""",
},

# ───────── Inventory ─────────
{
    "request": "Shopify Admin: adjust inventory level",
    "language": "graphql", "framework": "shopify-admin",
    "code": """mutation inventoryAdjust($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    inventoryAdjustmentGroup { reason changes { name delta } }
    userErrors { field message }
  }
}

# variables:
{
  "input": {
    "name": "available",
    "reason": "correction",
    "changes": [
      { "delta": 10,
        "inventoryItemId": "gid://shopify/InventoryItem/12345",
        "locationId":      "gid://shopify/Location/678" }
    ]
  }
}""",
},

# ───────── Discount creation ─────────
{
    "request": "Shopify Admin: create automatic discount via discountAutomaticBasicCreate",
    "language": "graphql", "framework": "shopify-admin",
    "code": """mutation create10off {
  discountAutomaticBasicCreate(automaticBasicDiscount: {
    title: "10% off summer collection"
    startsAt: "2024-06-01T00:00:00Z"
    endsAt:   "2024-08-31T23:59:59Z"
    minimumRequirement: { subtotal: { greaterThanOrEqualToSubtotal: "50.00" } }
    customerGets: {
      value: { percentage: 0.10 }
      items: { collections: { add: ["gid://shopify/Collection/1"] } }
    }
  }) {
    automaticDiscountNode { id }
    userErrors { field message }
  }
}""",
},

]
