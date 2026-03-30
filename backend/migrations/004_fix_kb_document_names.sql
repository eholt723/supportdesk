-- Fix kb_chunks document names to match demo ticket source names
UPDATE kb_chunks SET document_name = 'Billing FAQ'          WHERE document_name ILIKE 'billing faq';
UPDATE kb_chunks SET document_name = 'Terms of Service'     WHERE document_name ILIKE 'terms of service';
UPDATE kb_chunks SET document_name = 'Feature Overview'     WHERE document_name ILIKE 'feature overview';
UPDATE kb_chunks SET document_name = 'Getting Started'      WHERE document_name ILIKE 'getting started';
UPDATE kb_chunks SET document_name = 'Troubleshooting Guide' WHERE document_name ILIKE 'troubleshooting';
