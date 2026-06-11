# synergy_data/seo_views.py
"""Lightweight SEO + AI-crawler endpoints: robots.txt, an XML sitemap, and
an llms.txt site map for large language models.

Crawler policy (set by robots.txt below):
  * Search engines and AI *answer/citation* bots may read and cite the public
    pages (this drives visibility and sends users back to the site).
  * AI *training* crawlers are disallowed (the curated data is not for model
    training).
  * The bulk-data endpoints (full CSV export and the JSON API) are off-limits
    to all crawlers so the dataset cannot be vacuumed and shown without
    attribution.

Hand-rolled (no django.contrib.sitemaps / sites framework) because the public
site has a small, fixed set of indexable pages and no per-record detail URLs.
"""
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse

# (url name, priority, change frequency) for each public, indexable page.
SITEMAP_PAGES = [
    ('home', '1.0', 'weekly'),
    ('database_search', '0.9', 'daily'),
    ('analytics', '0.8', 'weekly'),
    ('about', '0.7', 'monthly'),
    ('download_data', '0.7', 'weekly'),
    ('api_docs', '0.6', 'monthly'),
]

# Paths kept out of every crawler's index: private/admin pages plus the
# bulk-data endpoints (JSON API and the CSV export query) so the full dataset
# is not scraped wholesale.
DISALLOW_PATHS = [
    '/admin/',
    '/accounts/',
    '/data-entry/',
    '/bulk-import/',
    '/api/v1/',
    '/*export=',
]

# Content-Signal rights declaration: permit search indexing and use in AI
# answers (citation/grounding), but reserve rights against model training.
CONTENT_SIGNAL = 'search=yes,ai-input=yes,ai-train=no'

# AI assistants that read a page on demand and cite it with a link back -
# good for visibility, so they get the same access as search engines.
AI_CITE_CRAWLERS = [
    'OAI-SearchBot',    # OpenAI / ChatGPT search index
    'ChatGPT-User',     # OpenAI on-demand fetch from ChatGPT
    'PerplexityBot',    # Perplexity index (cites with links)
    'Perplexity-User',  # Perplexity on-demand fetch
    'Claude-Web',       # Anthropic on-demand fetch
]

# AI crawlers used for model training / bulk ingestion - fully disallowed.
AI_TRAIN_CRAWLERS = [
    'GPTBot',            # OpenAI (training)
    'ClaudeBot',         # Anthropic (training)
    'anthropic-ai',      # Anthropic (legacy training)
    'Google-Extended',   # Google Gemini / Vertex AI (training token)
    'CCBot',             # Common Crawl (feeds many training sets)
    'Amazonbot',         # Amazon
    'Applebot-Extended', # Apple Intelligence (training)
    'Bytespider',        # ByteDance
    'meta-externalagent',# Meta AI
    'cohere-ai',         # Cohere
]


def _abs(path):
    """Absolute URL on the canonical domain for a root-relative path."""
    return settings.SITE_URL + path


def _allow_group(user_agents):
    """A robots.txt group that allows the public site but keeps private and
    bulk-data paths out, with the content-signal rights declaration."""
    lines = ["User-agent: {0}".format(ua) for ua in user_agents]
    lines.append("Content-Signal: " + CONTENT_SIGNAL)
    lines.append("Allow: /")
    lines += ["Disallow: {0}".format(p) for p in DISALLOW_PATHS]
    return lines


def robots_txt(request):
    """Welcome search engines and AI citation bots to read/cite public pages;
    disallow AI training crawlers; keep bulk-data endpoints off-limits."""
    lines = []
    # Default group for all other crawlers (classic search engines included).
    lines += _allow_group(['*'])
    lines.append("")
    # AI answer/citation bots: same access as search engines (drive traffic).
    lines += _allow_group(AI_CITE_CRAWLERS)
    lines.append("")
    # AI training / bulk-ingestion crawlers: fully disallowed.
    lines += ["User-agent: {0}".format(ua) for ua in AI_TRAIN_CRAWLERS]
    lines.append("Disallow: /")
    lines.append("")
    lines.append("Sitemap: " + _abs(reverse('sitemap_xml')))
    lines.append("")
    return HttpResponse("\n".join(lines), content_type="text/plain")


def sitemap_xml(request):
    """Render an XML sitemap of the public pages on the canonical domain."""
    urls = []
    for name, priority, freq in SITEMAP_PAGES:
        loc = _abs(reverse(name))
        urls.append(
            "  <url>\n"
            "    <loc>{loc}</loc>\n"
            "    <changefreq>{freq}</changefreq>\n"
            "    <priority>{priority}</priority>\n"
            "  </url>".format(loc=loc, freq=freq, priority=priority)
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    return HttpResponse(xml, content_type="application/xml")


def llms_txt(request):
    """Serve /llms.txt (see llmstxt.org): a concise, link-rich markdown map of
    the site so large language models can understand and cite the database."""
    s = settings.SITE_URL
    body = """# PhytoSynergyDB

> PhytoSynergyDB is a free, expert-curated database of phytochemical-antibiotic
> synergy experiments against ESKAPE pathogens (Enterococcus faecium,
> Staphylococcus aureus, Klebsiella pneumoniae, Acinetobacter baumannii,
> Pseudomonas aeruginosa, Enterobacter spp.). Every record is manually
> extracted from a peer-reviewed publication (DOI/PMID) and captures the FIC
> index, MIC values (each agent alone and in combination), assay method,
> observed mechanism of action, and source. It supports antimicrobial
> resistance (AMR) research. Data is free to reuse under CC-BY-4.0.

## Usage policy

You may read these pages and cite PhytoSynergyDB in answers, always with a
link back to the relevant page. Please do not use the content for AI model
training, and do not redistribute the full dataset; link users to the site
instead.

## Key pages

- [Home]({s}/): Overview, ESKAPE summary, and live statistics.
- [Browse the database]({s}/database/): Search and filter synergy experiments by compound, antibiotic, pathogen, chemical class, and FIC interpretation (Synergy / Additive / Indifference / Antagonism).
- [Analytics]({s}/analytics/): Top compounds and antibiotics, FIC interpretation breakdown, ESKAPE coverage, synergy heatmap.
- [About and methodology]({s}/about/): Scope, data model, curation methodology, FIC standards, limitations, licensing, and citation.
- [API documentation]({s}/api/docs/): How to access data programmatically.

## Interpreting the data

- FIC index thresholds: up to 0.5 = Synergy; up to 1.0 = Additive; up to 4.0 = Indifference; above 4.0 = Antagonism.
- MIC values are reported in the units given per record (default ug/mL), for each agent alone and in combination.

## How to cite

Cite the database URL ({s}/) together with the original publication DOI/PMID
for each experiment referenced. PhytoSynergyDB is an independent, expert-curated
academic resource; it does not accept public data submissions.
""".format(s=s)
    return HttpResponse(body, content_type="text/plain; charset=utf-8")
