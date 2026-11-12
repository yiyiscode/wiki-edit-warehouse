-- raw 層:recentchanges API 的原始紀錄(SPEC 第 7 節)。永不刪除;來源只留 30 天,這裡是唯一副本。
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.raw_recentchange (
    wiki         text        NOT NULL,              -- 例:zhwiki
    rcid         bigint      NOT NULL,              -- 來源流水號,每個維基各自編號
    rc_timestamp timestamptz NOT NULL,              -- 取自 payload->>'timestamp',供 staging 以小時切分
    payload      jsonb       NOT NULL,              -- API 回傳的原始紀錄,不做任何修改
    loaded_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (wiki, rcid)
);

CREATE INDEX IF NOT EXISTS raw_recentchange_wiki_ts
    ON raw.raw_recentchange (wiki, rc_timestamp);
