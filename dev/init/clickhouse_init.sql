-- Minimal schema for local dev. Real prod schema lives in vista; here we just
-- create a pointer table so integration tests can do SELECT 1-style smoke.
CREATE DATABASE IF NOT EXISTS vista;

CREATE TABLE IF NOT EXISTS vista.klines_mini
(
    dt     DateTime,
    symbol String,
    open   Float64,
    high   Float64,
    low    Float64,
    close  Float64,
    vol    Float64,
    amount Float64
)
ENGINE = MergeTree
ORDER BY (symbol, dt);

INSERT INTO vista.klines_mini VALUES
    (now(), 'SFIF9001.CFE', 4000.0, 4010.0, 3990.0, 4005.0, 100, 400000),
    (now() - INTERVAL 1 MINUTE, 'SFIF9001.CFE', 3998.0, 4005.0, 3995.0, 4000.0, 80, 320000);
