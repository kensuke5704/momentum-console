import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const OUTPUT = resolve("public/data/atlas-layout.json");
const UNIVERSE = resolve("public/data/universe-current.json");
const FORMAT_VERSION = 5;
const USER_AGENT = "MomentumConsole/2.0 (https://github.com/kensuke5704/momentum-console)";
const STOP = new Set(`a an and are as at be been being but by can company corporation could did do does for from had has have if in into is it its may more most not of on or our over such than that the their them then there these they this those through to under up was we were what when where which while who will with within would you your`.split(" "));
const GENRES = {
  chipsai: { label: "SEMICONDUCTORS · AI INFRASTRUCTURE" },
  software: { label: "SOFTWARE · CLOUD · INTERNET" },
  security: { label: "CYBERSECURITY" },
  power: { label: "POWER · ENERGY INFRASTRUCTURE" },
  health: { label: "HEALTHCARE · BIOTECH" },
  finance: { label: "FINANCE · PAYMENTS" },
  consumer: { label: "CONSUMER · MEDIA" },
  industrial: { label: "INDUSTRIAL · MOBILITY" },
  crypto: { label: "DIGITAL ASSETS" },
  other: { label: "OTHER" },
};

const sleep = (ms) => new Promise((resolvePromise) => setTimeout(resolvePromise, ms));
async function requestJson(url, attempts = 3, options = {}) {
  let lastError;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await fetch(url, { headers: { "User-Agent": USER_AGENT, Accept: "application/json", ...(options.headers ?? {}) }, signal: AbortSignal.timeout(options.timeout ?? 20000) });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      return await response.json();
    } catch (error) {
      lastError = error;
      if (attempt + 1 < attempts) await sleep(450 * (attempt + 1));
    }
  }
  throw lastError;
}

function companyScore(result) {
  const description = String(result?.description ?? "").toLowerCase();
  const positive = ["company", "corporation", "manufacturer", "bank", "retailer", "technology", "pharmaceutical", "business", "conglomerate", "platform", "exchange"];
  return positive.reduce((score, word) => score + (description.includes(word) ? 1 : 0), 0);
}
function nameTokens(name) { return new Set(String(name ?? "").toLowerCase().match(/[a-z0-9]{2,}/g) ?? []); }
const LEGAL_NAME_WORDS = new Set(["the", "inc", "incorporated", "corp", "corporation", "company", "co", "class", "holdings", "holding", "group", "plc", "llc", "new"]);
function titleMatches(title, expectedName) {
  if (!title || !expectedName || /\bv\.?\s|timeline|lawsuit|channel|executive compensation|disambiguation|\(\d{4}s?\)/i.test(title)) return false;
  const expected = [...nameTokens(expectedName)].filter((token) => !LEGAL_NAME_WORDS.has(token));
  const actual = nameTokens(title);
  const overlap = expected.filter((token) => actual.has(token)).length;
  return overlap >= Math.min(2, Math.max(1, expected.length));
}
function identityScore(result, expectedName) {
  const expected = nameTokens(expectedName), actual = nameTokens(result?.label ?? result?.title);
  let overlap = 0;
  for (const token of expected) if (actual.has(token)) overlap += token.length > 4 ? 3 : 1;
  return companyScore(result) * 2 + overlap * 5;
}

function cleanCompanyName(name) {
  return String(name ?? "").replace(/\b(Class [A-Z]|Common Stock|Ordinary Shares?|American Depositary Shares?|Depositary Shares?)\b.*$/i, "").replace(/\s+/g, " ").trim();
}

async function fetchNasdaqDirectory() {
  const payload = await requestJson("https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true", 3, {
    timeout: 60000,
    headers: { "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36", Origin: "https://www.nasdaq.com", Referer: "https://www.nasdaq.com/" },
  });
  return new Map((payload.data?.rows ?? []).map((row) => [String(row.symbol).replace("/", "."), {
    name: cleanCompanyName(row.name),
    sourceName: row.name,
    sector: row.sector || "",
    industry: row.industry || "",
  }]));
}

async function fetchProfile(symbol, listing = {}) {
  const searchName = listing.name || symbol;
  const searchUrl = new URL("https://www.wikidata.org/w/api.php");
  searchUrl.search = new URLSearchParams({ action: "wbsearchentities", search: searchName, language: "en", limit: "8", format: "json", origin: "*" });
  const search = await requestJson(searchUrl);
  const candidate = [...(search.search ?? [])].filter((item) => titleMatches(item.label, searchName)).sort((a, b) => identityScore(b, searchName) - identityScore(a, searchName))[0];
  if (!candidate || companyScore(candidate) === 0) return fetchWikipediaByTicker(symbol, listing);

  const entityUrl = new URL("https://www.wikidata.org/w/api.php");
  entityUrl.search = new URLSearchParams({ action: "wbgetentities", ids: candidate.id, props: "labels|descriptions|sitelinks", languages: "en", sitefilter: "enwiki", format: "json", origin: "*" });
  const entityPayload = await requestJson(entityUrl);
  const entity = entityPayload.entities?.[candidate.id] ?? {};
  const name = entity.labels?.en?.value ?? candidate.label ?? listing.name ?? symbol;
  const description = entity.descriptions?.en?.value ?? candidate.description ?? "";
  const pageTitle = entity.sitelinks?.enwiki?.title;
  if (!titleMatches(pageTitle, searchName)) return fetchWikipediaByTicker(symbol, listing);
  let extract = "";
  if (pageTitle) {
    const extractUrl = new URL("https://en.wikipedia.org/w/api.php");
    extractUrl.search = new URLSearchParams({ action: "query", prop: "extracts", titles: pageTitle, exintro: "1", explaintext: "1", redirects: "1", format: "json", origin: "*" });
    const article = await requestJson(extractUrl);
    extract = Object.values(article.query?.pages ?? {})[0]?.extract ?? "";
  }
  return { symbol, name, description, sector: listing.sector ?? "", industry: listing.industry ?? "", sourceName: listing.sourceName ?? null, pageTitle: pageTitle ?? null, text: `${name}. ${listing.sector ?? ""}. ${listing.industry ?? ""}. ${description}. ${extract}`.trim() };
}

async function fetchWikipediaByTicker(symbol, listing = {}) {
  let pages = [];
  for (const query of [listing.name ? `"${listing.name}" company` : null, `"ticker symbol ${symbol}"`, `"${symbol}" stock company`].filter(Boolean)) {
    const searchUrl = new URL("https://en.wikipedia.org/w/api.php");
    searchUrl.search = new URLSearchParams({ action: "query", generator: "search", gsrsearch: query, gsrnamespace: "0", gsrlimit: "6", prop: "extracts|description", exintro: "1", explaintext: "1", format: "json", origin: "*" });
    const payload = await requestJson(searchUrl);
    pages = Object.values(payload.query?.pages ?? {});
    if (pages.length) break;
  }
  const businessWords = ["company", "corporation", "manufacturer", "bank", "retailer", "technology", "pharmaceutical", "software", "services", "conglomerate", "exchange"];
  const page = pages.filter((item) => titleMatches(item.title, listing.name ?? symbol)).sort((left, right) => {
    const score = (item) => {
      const text = `${item.description ?? ""} ${item.extract ?? ""}`.toLowerCase();
      const business = businessWords.reduce((total, word) => total + (text.includes(word) ? 2 : 0), 0);
      const titlePenalty = /^(list of|index of)|index$|sector$/i.test(item.title ?? "") ? 20 : 0;
      const identity = identityScore({ label: item.title, description: item.description }, listing.name ?? symbol);
      return business + identity * 3 - titlePenalty - (item.index ?? 9) * .2;
    };
    return score(right) - score(left);
  })[0];
  if (!page?.extract) return { symbol, name: listing.name ?? symbol, description: "", sector: listing.sector ?? "", industry: listing.industry ?? "", sourceName: listing.sourceName ?? null, pageTitle: null, text: `${listing.name ?? symbol}. ${listing.sector ?? ""}. ${listing.industry ?? ""}`.trim() };
  return { symbol, name: page.title ?? listing.name ?? symbol, description: page.description ?? "", sector: listing.sector ?? "", industry: listing.industry ?? "", sourceName: listing.sourceName ?? null, pageTitle: page.title ?? null, text: `${page.title}. ${listing.sector ?? ""}. ${listing.industry ?? ""}. ${page.description ?? ""}. ${page.extract}`.trim() };
}

async function mapConcurrent(items, limit, mapper) {
  const output = new Array(items.length);
  let cursor = 0;
  async function worker() {
    while (cursor < items.length) {
      const index = cursor++;
      output[index] = await mapper(items[index], index);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return output;
}

function stem(word) {
  return word.replace(/(?:ization|ational|fulness|ousness|iveness|ments|ment|ingly|edly|ing|ies|ers|ed|ly|s)$/u, (suffix) => suffix === "ies" ? "y" : "");
}
function tokens(text) {
  const raw = text.toLowerCase().match(/[a-z][a-z0-9-]{2,}/g) ?? [];
  const unigram = raw.map(stem).filter((word) => !STOP.has(word) && word.length > 2);
  const bigram = unigram.slice(0, -1).map((word, index) => `${word}_${unigram[index + 1]}`);
  return [...unigram, ...bigram];
}
function tfidfVectors(profiles) {
  const documents = profiles.map((profile) => tokens(profile.text));
  const documentFrequency = new Map();
  for (const document of documents) for (const term of new Set(document)) documentFrequency.set(term, (documentFrequency.get(term) ?? 0) + 1);
  return documents.map((document) => {
    const counts = new Map();
    for (const term of document) counts.set(term, (counts.get(term) ?? 0) + 1);
    const vector = new Map();
    let norm = 0;
    for (const [term, count] of counts) {
      const value = (1 + Math.log(count)) * Math.log((profiles.length + 1) / ((documentFrequency.get(term) ?? 0) + 1));
      if (value > 0) { vector.set(term, value); norm += value * value; }
    }
    norm = Math.sqrt(norm) || 1;
    for (const [term, value] of vector) vector.set(term, value / norm);
    return vector;
  });
}
function cosine(left, right) {
  let total = 0;
  const [small, large] = left.size < right.size ? [left, right] : [right, left];
  for (const [term, value] of small) total += value * (large.get(term) ?? 0);
  return Math.max(0, Math.min(1, total));
}
function multiply(matrix, vector) { return matrix.map((row) => row.reduce((sum, value, index) => sum + value * vector[index], 0)); }
function dot(a, b) { return a.reduce((sum, value, index) => sum + value * b[index], 0); }
function normalize(vector) { const length = Math.sqrt(dot(vector, vector)) || 1; return vector.map((value) => value / length); }
function topEigenvectors(matrix, count) {
  const vectors = [];
  const values = [];
  for (let axis = 0; axis < count; axis += 1) {
    let vector = normalize(matrix.map((_, index) => Math.sin((index + 1) * (axis + 1) * 1.731) + Math.cos((index + 1) * .619)));
    for (let iteration = 0; iteration < 180; iteration += 1) {
      let next = multiply(matrix, vector);
      for (const previous of vectors) { const projection = dot(next, previous); next = next.map((value, index) => value - projection * previous[index]); }
      vector = normalize(next);
    }
    vectors.push(vector);
    values.push(Math.max(0, dot(vector, multiply(matrix, vector))));
  }
  return { vectors, values };
}
function classicalMds(similarities) {
  const count = similarities.length;
  const squared = similarities.map((row) => row.map((value) => (1 - value) ** 2));
  const rowMeans = squared.map((row) => row.reduce((sum, value) => sum + value, 0) / count);
  const totalMean = rowMeans.reduce((sum, value) => sum + value, 0) / count;
  const gram = squared.map((row, i) => row.map((value, j) => -.5 * (value - rowMeans[i] - rowMeans[j] + totalMean)));
  const { vectors, values } = topEigenvectors(gram, 3);
  const raw = Array.from({ length: count }, (_, index) => vectors.map((vector, axis) => vector[index] * Math.sqrt(values[axis])));
  const magnitudes = raw.flat().map(Math.abs).sort((a, b) => a - b);
  const scale = Math.max(magnitudes[Math.floor(magnitudes.length * .9)] ?? 0, .001);
  const fit = (value) => Math.max(-1.35, Math.min(1.35, value / scale));
  return raw.map(([x, y, z]) => ({ x: fit(x), y: fit(y), z: fit(z) }));
}
function classify(profile) {
  const sector = String(profile.sector ?? "").toLowerCase();
  const industry = String(profile.industry ?? "").toLowerCase();
  const text = `${profile.name ?? ""} ${profile.description ?? ""} ${sector} ${industry} ${profile.text ?? ""}`.toLowerCase();
  const has = (...phrases) => phrases.some((phrase) => text.includes(phrase));

  if (has("cryptocurrency", "crypto exchange", "bitcoin", "blockchain", "digital asset", "stablecoin", "coinbase")) return "crypto";
  if (has("cybersecurity", "cyber-security", "network security", "computer security", "firewall", "endpoint security", "zero trust")) return "security";
  if (sector.includes("utilities") || sector.includes("energy") || has("electric utilities", "power generation", "power grid", "energy infrastructure", "energy technology", "nuclear power", "oil and gas", "integrated oil")) return "power";
  if (sector.includes("health") || has("pharmaceutical", "biotechnology", "medical device", "health care", "healthcare")) return "health";
  if (sector.includes("finance") || has("payment card", "payment network", "financial services", "major banks", "investment bank", "brokerage", "stock exchange", "insurance company")) return "finance";
  if (has("semiconductor", "chipmaker", "microprocessor", "electronic components", "computer manufacturing", "data center", "data centre", "networking equipment", "communications equipment", "electronic design automation", "power management") || (sector.includes("technology") && has("industrial machinery", "electrical products"))) return "chipsai";
  if (sector.includes("consumer") || has("retailer", "retail stores", "entertainment", "mass media", "beverage", "food delivery", "travel services", "lodging")) return "consumer";
  if (sector.includes("industrials") || has("aerospace", "defense contractor", "automotive", "auto manufacturing", "industrial machinery", "construction equipment", "transportation services", "robotics")) return "industrial";
  if (sector.includes("technology") || sector.includes("telecommunications") || has("software company", "cloud computing", "internet company", "social media", "digital advertising")) return "software";
  if (sector.includes("real estate")) return has("data center", "data centre") ? "chipsai" : "finance";
  return "other";
}

async function main() {
  const universe = JSON.parse(await readFile(UNIVERSE, "utf8"));
  const symbols = universe.current?.symbols?.map((member) => member.symbol) ?? [];
  if (!symbols.length) throw new Error("Universe is empty; run sync:universe first");
  let previous = {};
  try { previous = JSON.parse(await readFile(OUTPUT, "utf8")); } catch {}
  const previousSymbols = Object.keys(previous.positions ?? {}).sort();
  const symbolsMatch = previousSymbols.length === symbols.length && previousSymbols.every((symbol, index) => symbol === [...symbols].sort()[index]);
  if (previous.formatVersion === FORMAT_VERSION && previous.universeGeneratedAt === universe.generatedAt && symbolsMatch) {
    console.log(`Semantic atlas is current for ${symbols.length} symbols`);
    return;
  }
  if (previous.formatVersion < FORMAT_VERSION && previous.universeGeneratedAt === universe.generatedAt && symbolsMatch && previous.profiles) {
    const positions = Object.fromEntries(symbols.map((symbol) => [symbol, { ...previous.positions[symbol], genre: classify(previous.profiles[symbol] ?? {}) }]));
    const output = { ...previous, formatVersion: FORMAT_VERSION, generatedAt: new Date().toISOString(), genres: Object.fromEntries(Object.entries(GENRES).map(([id, genre]) => [id, genre.label])), positions };
    await writeFile(OUTPUT, `${JSON.stringify(output)}\n`);
    console.log(`Reclassified ${symbols.length} existing semantic positions`);
    return;
  }
  const cached = previous.profiles ?? {};
  const directory = await fetchNasdaqDirectory();
  console.log(`Building semantic atlas for ${symbols.length} symbols (${Object.keys(cached).length} cached profiles)`);
  const profiles = await mapConcurrent(symbols, 4, async (symbol) => {
    const listing = directory.get(symbol) ?? {};
    if (cached[symbol]?.text?.length > symbol.length + 20 && cached[symbol]?.sourceName === (listing.sourceName ?? null) && cached[symbol]?.profileVersion === 3 && (!cached[symbol]?.pageTitle || titleMatches(cached[symbol].pageTitle, listing.name))) return cached[symbol];
    try { return { ...(await fetchProfile(symbol, listing)), profileVersion: 3 }; }
    catch (error) { console.warn(error instanceof Error ? error.message : `${symbol}: profile fetch failed`); return { symbol, name: listing.name ?? symbol, description: "", sector: listing.sector ?? "", industry: listing.industry ?? "", sourceName: listing.sourceName ?? null, pageTitle: null, profileVersion: 3, text: `${listing.name ?? symbol}. ${listing.sector ?? ""}. ${listing.industry ?? ""}` }; }
  });
  const vectors = tfidfVectors(profiles);
  const similarities = vectors.map((left) => vectors.map((right) => cosine(left, right)));
  const coordinates = classicalMds(similarities);
  const positions = {};
  const neighbors = {};
  const profileMap = {};
  profiles.forEach((profile, index) => {
    const genre = classify(profile);
    positions[profile.symbol] = { ...coordinates[index], genre };
    const publicProfile = { ...profile };
    delete publicProfile.text;
    profileMap[profile.symbol] = { ...publicProfile, sourceUrl: profile.pageTitle ? `https://en.wikipedia.org/wiki/${encodeURIComponent(profile.pageTitle.replaceAll(" ", "_"))}` : null };
    neighbors[profile.symbol] = profiles.map((candidate, otherIndex) => ({ symbol: candidate.symbol, similarity: similarities[index][otherIndex] })).filter((entry) => entry.symbol !== profile.symbol).sort((a, b) => b.similarity - a.similarity).slice(0, 8).map((entry) => ({ ...entry, similarity: Number(entry.similarity.toFixed(4)) }));
  });
  const output = { formatVersion: FORMAT_VERSION, generatedAt: new Date().toISOString(), universeGeneratedAt: universe.generatedAt, method: "tfidf-company-profile-cooccurrence-classical-mds", sources: ["Nasdaq Stock Screener", "Wikidata", "English Wikipedia introductions"], genres: Object.fromEntries(Object.entries(GENRES).map(([id, genre]) => [id, genre.label])), positions, neighbors, profiles: profileMap };
  await mkdir(dirname(OUTPUT), { recursive: true });
  await writeFile(OUTPUT, `${JSON.stringify(output)}\n`);
  console.log(`Saved ${OUTPUT}`);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
