-- Enforce one canonical source-local identity link per provider identity.
-- These unique indexes make the materializer idempotent under concurrent runs.
CREATE UNIQUE INDEX provider_team_identity_links_source_identity_uk
    ON veltrix_ai_analyst.provider_team_identity_links(provider, source_id, provider_team_id);

CREATE UNIQUE INDEX provider_competition_identity_links_source_identity_uk
    ON veltrix_ai_analyst.provider_competition_identity_links(
        provider, source_id, provider_competition_id
    );
