-- Pre-loaded demo tickets with classifications and drafts
-- These are inserted only if the tickets table is empty

DO $$
BEGIN
    IF (SELECT COUNT(*) FROM tickets) = 0 THEN

        INSERT INTO tickets (id, source_email, subject, body, type, urgency, status, created_at) VALUES
        (
            1,
            'sarah.chen@example.com',
            'Still being charged after cancellation attempt',
            'I''ve been trying to cancel my subscription for two days and I keep getting charged. I followed the steps in the help center but the cancel button just spins and nothing happens. This is extremely frustrating. Please help urgently.',
            'billing',
            'high',
            'pending',
            NOW() - INTERVAL '2 hours'
        ),
        (
            2,
            'marcus.obi@example.com',
            'Export button broken after latest update',
            'The export button stopped working after your last update. When I click Export to CSV on any project view, I get a blank download with no data. I need this for a client presentation tomorrow morning. Please fix ASAP.',
            'technical',
            'high',
            'pending',
            NOW() - INTERVAL '90 minutes'
        ),
        (
            3,
            'priya.nair@example.com',
            'API access on Pro plan?',
            'Does the Pro plan include API access? I can''t find it anywhere in the docs or the pricing page. I''m evaluating Vela for my team and this is a key requirement before we upgrade.',
            'feature_request',
            'low',
            'pending',
            NOW() - INTERVAL '45 minutes'
        ),
        (
            4,
            'tom.warren@example.com',
            'Three support requests ignored - escalating',
            'I''ve contacted support three times over the past week and no one has responded. Ticket #4821, #4856, and #4901. This is completely unacceptable. I am a paying Pro customer and I expect a response within 24 hours per your own SLA. If I don''t hear back today I will be disputing the charge.',
            'escalation',
            'high',
            'pending',
            NOW() - INTERVAL '20 minutes'
        );

        -- Reset sequence to avoid conflicts with real inserts
        PERFORM setval('tickets_id_seq', 100);

        -- Pre-generate pipeline_runs for demo tickets
        INSERT INTO pipeline_runs (ticket_id, stage, status, duration_ms, created_at) VALUES
        (1, 'classify', 'completed', 312, NOW() - INTERVAL '2 hours' + INTERVAL '1 second'),
        (1, 'search',   'completed', 488, NOW() - INTERVAL '2 hours' + INTERVAL '2 seconds'),
        (1, 'draft',    'completed', 1840, NOW() - INTERVAL '2 hours' + INTERVAL '4 seconds'),
        (2, 'classify', 'completed', 298, NOW() - INTERVAL '90 minutes' + INTERVAL '1 second'),
        (2, 'search',   'completed', 421, NOW() - INTERVAL '90 minutes' + INTERVAL '2 seconds'),
        (2, 'draft',    'completed', 2100, NOW() - INTERVAL '90 minutes' + INTERVAL '4 seconds'),
        (3, 'classify', 'completed', 280, NOW() - INTERVAL '45 minutes' + INTERVAL '1 second'),
        (3, 'search',   'completed', 395, NOW() - INTERVAL '45 minutes' + INTERVAL '2 seconds'),
        (3, 'draft',    'completed', 1650, NOW() - INTERVAL '45 minutes' + INTERVAL '4 seconds'),
        (4, 'classify', 'completed', 305, NOW() - INTERVAL '20 minutes' + INTERVAL '1 second'),
        (4, 'search',   'completed', 440, NOW() - INTERVAL '20 minutes' + INTERVAL '2 seconds'),
        (4, 'draft',    'completed', 1920, NOW() - INTERVAL '20 minutes' + INTERVAL '4 seconds');

        -- Pre-generated draft responses (will be populated by seed script with real RAG)
        INSERT INTO draft_responses (ticket_id, draft_text, sources_used, confidence_score, created_at) VALUES
        (
            1,
            E'Hi Sarah,\n\nThank you for reaching out, and I sincerely apologize for the frustration. Being charged after attempting to cancel is not the experience we want for any Vela customer.\n\nHere''s what I''ll do right now:\n\n1. I''ve flagged your account for an immediate billing review. If any charges were applied after your cancellation attempt, you will receive a full refund within 3-5 business days.\n2. Our team will manually process your cancellation today so you don''t need to use the self-service flow.\n3. You''ll receive a confirmation email once both steps are complete.\n\nRegarding the spinning cancel button — this is a known issue affecting a small number of accounts after our recent authentication update. Our engineering team has a fix deploying within 24 hours.\n\nYou should not have had to reach out twice about this. I''m sorry we let you down.\n\nBest,\nVela Support',
            '[{"document_name": "Billing FAQ", "chunk_text": "To cancel your subscription, navigate to Settings > Billing > Cancel Plan. Cancellations take effect at the end of the current billing period. If you experience issues with the cancellation flow, contact support and we will process it manually.", "score": 0.91}, {"document_name": "Billing FAQ", "chunk_text": "Refunds are issued for charges made after a verified cancellation attempt. Processing time is 3-5 business days depending on your payment provider.", "score": 0.87}, {"document_name": "Terms of Service", "chunk_text": "Vela will refund any charges that occur due to a platform error preventing cancellation, provided the customer contacts support within 30 days.", "score": 0.78}]',
            0.91,
            NOW() - INTERVAL '2 hours' + INTERVAL '4 seconds'
        ),
        (
            2,
            E'Hi Marcus,\n\nThanks for reporting this — I can confirm this is a bug introduced in our v2.14 release that went out Tuesday night. The CSV export is generating empty files for projects with more than 50 tasks due to a pagination error in the export service.\n\nGiven your client presentation tomorrow, here are your options right now:\n\n1. **Immediate workaround**: Use the "Print View" (Cmd/Ctrl + P from any project) and export as PDF. This captures the full task list and is not affected by the bug.\n2. **Direct data export**: I can manually generate and email you a CSV of your project data within the next 2 hours. Reply with your project name and I''ll get that to you.\n\nA patch for the export bug is being deployed tonight and will be live by 8 AM tomorrow.\n\nApologies for the disruption at a critical time.\n\nBest,\nVela Support',
            '[{"document_name": "Troubleshooting Guide", "chunk_text": "Export issues: If CSV export produces an empty or incomplete file, try using the Print View as a workaround. This is available from any project view via Cmd+P (Mac) or Ctrl+P (Windows).", "score": 0.93}, {"document_name": "Troubleshooting Guide", "chunk_text": "Common errors after updates: Some features may be temporarily unavailable following a platform release. Check the Vela status page at status.vela.app for known issues and estimated resolution times.", "score": 0.82}, {"document_name": "Getting Started", "chunk_text": "Exporting project data: Navigate to your project, click the three-dot menu in the top right, and select Export. Choose CSV for spreadsheet-compatible format or PDF for a formatted report.", "score": 0.74}]',
            0.93,
            NOW() - INTERVAL '90 minutes' + INTERVAL '4 seconds'
        ),
        (
            3,
            E'Hi Priya,\n\nGreat question — yes, API access is included on the Pro plan.\n\nHere''s a quick breakdown by plan:\n\n- **Starter**: No API access\n- **Pro**: Full REST API access, up to 10,000 requests/month, all endpoints included\n- **Business**: Full REST API access, unlimited requests, webhook support, OAuth apps\n\nThe API documentation is at docs.vela.app/api. Once you upgrade to Pro, your API key will be available under Settings > Developer > API Keys.\n\nIf you''d like to test the API before committing to an upgrade, I can set you up with a 14-day Pro trial — just let me know.\n\nHappy to answer any other questions as you evaluate Vela for your team.\n\nBest,\nVela Support',
            '[{"document_name": "Feature Overview", "chunk_text": "Pro plan includes: unlimited projects, custom fields, time tracking, CSV/PDF export, REST API access (10,000 requests/month), priority support, and SSO.", "score": 0.95}, {"document_name": "Feature Overview", "chunk_text": "API access is available on Pro and Business plans. The Vela REST API supports all core resources including projects, tasks, members, and comments. Full documentation at docs.vela.app/api.", "score": 0.94}, {"document_name": "Getting Started", "chunk_text": "To access your API key, go to Settings > Developer > API Keys. API keys are scoped per workspace and can be rotated at any time.", "score": 0.81}]',
            0.95,
            NOW() - INTERVAL '45 minutes' + INTERVAL '4 seconds'
        ),
        (
            4,
            E'Hi Tom,\n\nI owe you a direct apology. Three unanswered support requests is a failure on our part, and your frustration is completely warranted.\n\nI''ve pulled up tickets #4821, #4856, and #4901. All three are now assigned to me personally and I will respond to each one within the hour with a status update.\n\nAs a Pro customer you are entitled to a 24-hour response SLA, and we did not meet that. As acknowledgment, I''ve applied a one-month credit to your account — you''ll see it reflected on your next billing statement.\n\nI''m not going to ask you to wait any longer. If you have 10 minutes today, reply to this email and I''ll schedule a call to resolve all three issues in one go.\n\nAgain, I''m sorry. This isn''t how Vela treats its customers.\n\nBest,\nVela Support',
            '[{"document_name": "Terms of Service", "chunk_text": "Vela Pro customers are entitled to a 24-hour first response SLA on all support requests submitted through the official support portal. Business customers receive a 4-hour SLA.", "score": 0.89}, {"document_name": "Billing FAQ", "chunk_text": "Account credits may be applied at the discretion of the support team to acknowledge service failures or extended outages. Credits appear on the next billing statement.", "score": 0.83}, {"document_name": "Getting Started", "chunk_text": "Vela support can be reached via the in-app help widget, email at support@vela.app, or by submitting a ticket at help.vela.app.", "score": 0.71}]',
            0.89,
            NOW() - INTERVAL '20 minutes' + INTERVAL '4 seconds'
        );

    END IF;
END $$;
