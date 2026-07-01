<!-- LLM instruction template for phase-1-init Step 5.
     plan_id is injected by manage-plan-documents script after creation, not by the LLM.
     The script template lives in manage-plan-documents/templates/request.md. -->
# Request: {derived_title}

source: {description|lesson|issue}
source_id: {source_id_or_none}
created: {ISO_timestamp}

## Original Input

{verbatim_original_input}

## Context

{extracted_context_or_none}
