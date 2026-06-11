# synergy_data/seo_views.py
"""Lightweight SEO + AI-crawler endpoints: robots.txt, an XML sitemap, and
an llms.txt site map for large language models.

Hand-rolled (no django.contrib.sitemaps / sites framework) because the public
site has a small, fixed set of indexable pages and no per-record detail URLs,
so a dependency-free view keeps things simple and avoids an extra migration.
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

# Paths kept out of every crawler's index (private, admin, raw JSON API).
DISALLOW_PATHS = [
    '/admin/',
    '/accounts/',
    '/data-entry/',
    '/bulk-import/',
    '/api/v1/',
]

# AI / LLM crawlers we explicitly welcome so the database can be cited by
# assistants and answer engines (training + retrieval + on-demand fetch).
AI_CRAWLERS = [
    'GPTBot',            # OpenAI (training)
    'OAI-SearchBot',     # OpenAI (search index)
    'ChatGPT-User',      # OpenAI (on-demand fetch from ChatGPT)
    'Google-Extended',   # Google Gemini / Vertex AI (training token)
    'ClaudeBot',         # Anthropic (training)
    'anthropic-ai',      # Anthropic (legacy)
    'Claude-Web',        # Anthropic (on-demand fetch)
    'PerplexityBot',     # Perplexity (index)
    'Perplexity-User',   # Perplexity (on-demand fetch)
    'CCBot',             # Common Crawl (feeds many LLMs)
    'Applebot-Extended', # Apple Intelligence
    'Amazonbot',         # Amazon
    'Bytespider',        # ByteDance
    'Meta-ExternalAgent',# Meta AI
    'cohere-ai',         # Cohere
]


def _abs(path):
    """Absolute URL on the canonical domain for a root-relative path."""
    return settings.SITE_URL + path


def _agent_block(user_agent):
    """One robots.txt stanza: allow the public site, keep private paths out."""
    lines = ["User-agent: {0}".format(user_agent), "Allow: /"]
    lines += ["Disallow: {0}".format(p) for p in DISALLOW_PATHS]
    return lines


def robots_txt(request):
    """Allow crawling of public pages by both search engines and AI crawlers;
    keep private/admin/API-JSON out of the index; advertise the sitemap."""
    lines = []
    # Default rules for all other crawlers (classic search engines included).
    lines += _agent_block('*')
    lines.append("")
    # Explicitly welcome named AI / LLM crawlers.
    for bot in AI_CRAWLERS:
        lines += _agent_block(bot)
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

## Key pages

- [Home]({s}/): Overview, ESKAPE summary, and live statistics.
- [Browse the database]({s}/database/): Search and filter synergy experiments by compound, antibiotic, pathogen, chemical class, and FIC interpretation (Synergy / Additive / Indifference / Antagonism).
- [Download dataset (CSV)]({s}/database/download/): Full database or any filtered subset as CSV.
- [Analytics]({s}/analytics/): Top compounds and antibiotics, FIC interpretation breakdown, ESKAPE coverage, synergy heatmap.
- [About and methodology]({s}/about/): Scope, data model, curation methodology, FIC standards, limitations, licensing, and citation.

## Programmatic access (REST API, JSON)

- [API documentation]({s}/api/docs/): Endpoint reference and parameters.
- Experiments: {s}/api/v1/experiments/ - paginated, filterable list of synergy experiments (JSON).
- Statistics: {s}/api/v1/statistics/ - aggregate counts and summaries (JSON).

## Interpreting the data

- FIC index thresholds: up to 0.5 = Synergy; up to 1.0 = Additive; up to 4.0 = Indifference; above 4.0 = Antagonism.
- MIC values are reported in the units given per record (default ug/mL), for each agent alone and in combination.

## How to cite

Cite the database URL ({s}/) together with the original publication DOI/PMID
for each experiment referenced. PhytoSynergyDB is an independent, expert-curated
academic resource; it does not accept public data submissions.
""".format(s=s)
    return HttpResponse(body, content_type="text/plain; charset=utf-8")
