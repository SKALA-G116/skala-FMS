"""Explicit domain ownership: no request writes outside the shared transaction."""
from backend.app.domains.identity import api as identity
from backend.app.domains.ingestion import api as ingestion
from backend.app.domains.pricing import api as pricing
from backend.app.domains.catalog import api as catalog
from backend.app.domains.analysis import api as analysis
from backend.app.domains.jobs import api as jobs
from backend.app.domains.review import api as review
from backend.app.domains.reporting import api as reporting

DOMAINS = (identity, ingestion, pricing, catalog, analysis, jobs, review, reporting,)

HANDLERS = {
    'auth': identity.handle,
    'document-selections': ingestion.handle,
    'document-actions': ingestion.handle,
    'price-workbooks': pricing.handle,
    'price-sheets': pricing.handle,
    'dashboard': reporting.handle,
    'sources': ingestion.handle,
    'collection-runs': ingestion.handle,
    'documents': ingestion.handle,
    'document-revisions': ingestion.handle,
    'analysis-profiles': analysis.handle,
    'analysis-runs': analysis.handle,
    'jobs': jobs.handle,
    'proposals': review.handle,
    'applications': review.handle,
    'suppliers': catalog.handle,
    'foods': catalog.handle,
    'products': catalog.handle,
    'supplier-items': catalog.handle,
    'prices': pricing.handle,
    'evidence': ingestion.handle,
    'audit-events': review.handle,
    'assets': ingestion.handle,
}

def handler_for(root):
    return HANDLERS[root]
