// Pulls your public works from ORCID, enriches each with Crossref (authors, venue, abstract),
// and writes publications.json next to index.html. Node 18+ (uses built-in fetch). No dependencies.
import { writeFile } from "node:fs/promises";

const ORCID = process.env.ORCID_ID || "0009-0005-1609-1036";
const MY_FAMILY = (process.env.MY_FAMILY_NAME || "Abdelsalam").toLowerCase();
const OUT = process.env.OUT_FILE || "publications.json";
const MAX_AUTHORS = 5;

async function getJSON(url, headers = {}) {
  const r = await fetch(url, { headers: { Accept: "application/json", ...headers } });
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

function initials(given = "") {
  return given.split(/[\s.-]+/).filter(Boolean).map(s => s[0].toUpperCase()).join("");
}

function formatAuthors(list = []) {
  const names = list.map(a => a.name || `${initials(a.given)} ${a.family || ""}`.trim()).filter(Boolean);
  if (!names.length) return "";
  return names.length > MAX_AUTHORS ? names.slice(0, MAX_AUTHORS).join(", ") + ", et al." : names.join(", ");
}

// Crossref abstracts are JATS XML. Convert to the simple <p><strong>Heading.</strong> text</p> style the page uses.
function jatsToHtml(x = "") {
  return x
    .replace(/<jats:title>\s*(.*?)\s*<\/jats:title>/gis, (_, t) => `<strong>${t.replace(/[.:]?\s*$/, "")}.</strong> `)
    .replace(/<jats:p>/gi, "<p>").replace(/<\/jats:p>/gi, "</p>")
    .replace(/<jats:(sec|abstract)[^>]*>|<\/jats:(sec|abstract)>/gi, "")
    .replace(/<\/?jats:[^>]+>/gi, "")
    .replace(/<p>\s*(<strong>[^<]*<\/strong>)\s*<\/p>\s*<p>/gi, "<p>$1 ")
    .trim();
}

function kindOf(orcidType, doi, title) {
  const t = (orcidType || "").toLowerCase();
  if (t.includes("conference")) return "abs";
  if (/^10\.1212\/wnl\./i.test(doi || "")) return "abs";              // Neurology (AAN) abstracts
  if (/^(P\d|HL-\d|\d{2,}\s)/.test(title || "")) return "abs";   // e.g. "P344 ...", "HL-1124: ...", "543 ..."
  return "art";
}

const orcid = await getJSON(`https://pub.orcid.org/v3.0/${ORCID}/works`);
const out = [];

for (const g of orcid.group || []) {
  const w = g["work-summary"]?.[0];
  if (!w) continue;
  const ids = g["external-ids"]?.["external-id"] || [];
  const doi = (ids.find(i => i["external-id-type"] === "doi")?.["external-id-value"] || "")
    .replace(/^https?:\/\/(dx\.)?doi\.org\//i, "").trim();
  const title = w.title?.title?.value || "";
  const item = {
    t: title,
    y: parseInt(w["publication-date"]?.year?.value, 10) || null,
    v: w["journal-title"]?.value || "",
    doi,
    url: doi ? "" : (w.url?.value || `https://orcid.org/${ORCID}`),
    a: "",
    kind: kindOf(w.type, doi, title),
  };

  if (doi) {
    try {
      const { message: m } = await getJSON(`https://api.crossref.org/works/${encodeURIComponent(doi)}?mailto=none@example.com`);
      item.t = m.title?.[0] || item.t;
      item.v = m["container-title"]?.[0] || item.v;
      item.y = m.issued?.["date-parts"]?.[0]?.[0] || item.y;
      item.a = formatAuthors(m.author);
      item.first = (m.author?.[0]?.family || "").toLowerCase() === MY_FAMILY;
      if (m.abstract) item.abs = jatsToHtml(m.abstract);
    } catch (e) {
      console.warn("Crossref miss for", doi, "-", e.message); // keep the ORCID-only data
    }
  }
  if (item.t) out.push(item);
}

out.sort((a, b) => (b.y || 0) - (a.y || 0));
await writeFile(OUT, JSON.stringify({ orcid: ORCID, updated: new Date().toISOString().slice(0, 10), works: out }, null, 2) + "\n");
console.log(`Wrote ${out.length} works to ${OUT}`);
