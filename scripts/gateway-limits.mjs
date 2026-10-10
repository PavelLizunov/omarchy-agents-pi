// Run on the existing DSH host. Credentials remain in its existing key store.
import { pathToFileURL } from 'node:url';

const config = JSON.parse(process.argv[2]);
const started = Date.now();
let requests = 0;
const nativeFetch = globalThis.fetch;
const gateway = new URL(config.gatewayUrl);
if (gateway.username || gateway.password || !['http:', 'https:'].includes(gateway.protocol)) throw new Error('Invalid gateway URL');
globalThis.fetch = async (url, options = {}) => {
  const target = new URL(url);
  if (target.origin !== gateway.origin || !['/v0/management/auth-files', '/v0/management/auth-files/download', '/v0/management/api-call'].includes(target.pathname)) throw new Error('Unexpected management route');
  if (target.pathname === '/v0/management/api-call') {
    const payload = JSON.parse(options.body);
    const quotaUrls = new Set([
      'https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary',
      'https://daily-cloudcode-pa.sandbox.googleapis.com/v1internal:retrieveUserQuotaSummary',
      'https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary',
      'https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist',
      'https://chatgpt.com/backend-api/wham/usage',
      'https://cli-chat-proxy.grok.com/v1/billing?format=credits',
      'https://cli-chat-proxy.grok.com/v1/billing',
    ]);
    if (options.method !== 'POST' || !quotaUrls.has(payload.url) || !['GET', 'POST'].includes(payload.method)) throw new Error('Unexpected quota route');
  } else if (options.method && options.method !== 'GET') throw new Error('Unexpected management method');
  if (++requests > 128 || Date.now() - started > 45000) throw new Error('Collection budget exceeded');
  const response = await nativeFetch(target, {...options, redirect: 'error', signal: AbortSignal.timeout(Math.min(15000, Math.max(1, 45000 - (Date.now() - started))))});
  let size = 0;
  const chunks = [];
  for await (const chunk of response.body) {
    size += chunk.length;
    if (size > 2 * 1024 * 1024) throw new Error('Response too large');
    chunks.push(chunk);
  }
  const body = Buffer.concat(chunks).toString('utf8');
  return {ok: response.ok, status: response.status, json: async () => JSON.parse(body)};
};
const { LimitsCollector } = await import(pathToFileURL(config.collectorPath));
const data = await new LimitsCollector({secretFile: config.secretFile, gatewayUrl: config.gatewayUrl}).getLimits();
if (!Array.isArray(data.perAccount) || data.perAccount.length > 64 || (data.antigravityPool.groups || []).length > 32) throw new Error('Too many quota records');
const string = (v) => typeof v === 'string' ? v.slice(0, 160) : '';
const number = (v) => typeof v === 'number' && Number.isFinite(v) ? v : null;
const accounts = data.perAccount.slice(0, 64).map((a, index) => ({
  provider: string(a.provider), authIndex: string(a.authIndex),
  account: `${string(a.provider)} ${index + 1}`, plan: string(a.plan), status: string(a.status),
  windows: (a.windows || []).slice(0, 16).map(w => ({key: string(w.key), label: string(w.label),
    remainingPercent: number(w.remainingPercent), resetsAt: string(w.resetsAt)})),
}));
const groups = (data.antigravityPool.groups || []).slice(0, 32).map(g => ({
  plan: string(g.plan), label: string(g.label), model: string(g.model), key: string(g.key),
  total: number(g.totalCompatibleAccounts), available: number(g.remainingAccountEquivalents), resetsAt: string(g.resetsAt),
}));
const payload = JSON.stringify({accounts, groups, updatedAt: string(data.updatedAt), requests});
if (Buffer.byteLength(payload) > 65536) throw new Error('Output too large');
process.stdout.write(payload + '\n');
