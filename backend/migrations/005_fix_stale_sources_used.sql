-- Fix stale document_name references in draft_responses.sources_used
-- caused by migration 004 renaming kb_chunks without updating stored JSON

UPDATE draft_responses
SET sources_used = (
    SELECT jsonb_agg(
        CASE
            WHEN elem->>'document_name' = 'Troubleshooting'
            THEN jsonb_set(elem, '{document_name}', '"Troubleshooting Guide"')
            ELSE elem
        END
    )
    FROM jsonb_array_elements(sources_used) AS elem
)
WHERE sources_used::text LIKE '%"Troubleshooting"%'
  AND sources_used::text NOT LIKE '%"Troubleshooting Guide"%';
