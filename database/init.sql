-- ============================================
-- INTELLIGENCE TERMINAL - DATABASE INITIALIZATION
-- ============================================

-- Enable Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- ============================================
-- SCHEMA: Core Tables
-- ============================================

-- Symbols/Instruments
CREATE TABLE IF NOT EXISTS symbols (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'forex', 'futures', 'equity', 'index'
    description TEXT,
    contract_multiplier DECIMAL(10, 2),
    tick_size DECIMAL(10, 6),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Data Sources
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'broker', 'provider', 'feed'
    description TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Symbol-DataSource relationship
CREATE TABLE IF NOT EXISTS symbol_data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol_id UUID NOT NULL REFERENCES symbols(id),
    data_source_id UUID NOT NULL REFERENCES data_sources(id),
    external_symbol VARCHAR(50),
    priority INT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol_id, data_source_id)
);

-- ============================================
-- TIMESERIES: Market Data
-- ============================================

-- OHLCV Data (Hypertable)
CREATE TABLE IF NOT EXISTS market_data (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol_id UUID NOT NULL REFERENCES symbols(id),
    timeframe VARCHAR(10) NOT NULL, -- '1m', '5m', '1h', '1d', etc
    open DECIMAL(18, 8) NOT NULL,
    high DECIMAL(18, 8) NOT NULL,
    low DECIMAL(18, 8) NOT NULL,
    close DECIMAL(18, 8) NOT NULL,
    volume DECIMAL(20, 2) NOT NULL,
    data_source_id UUID REFERENCES data_sources(id)
);

SELECT create_hypertable('market_data', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time 
    ON market_data (symbol_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_timeframe 
    ON market_data (timeframe);

-- Tick Data (Hypertable)
CREATE TABLE IF NOT EXISTS tick_data (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol_id UUID NOT NULL REFERENCES symbols(id),
    bid DECIMAL(18, 8) NOT NULL,
    ask DECIMAL(18, 8) NOT NULL,
    mid DECIMAL(18, 8) NOT NULL,
    bid_size DECIMAL(20, 2),
    ask_size DECIMAL(20, 2),
    volume DECIMAL(20, 2),
    data_source_id UUID REFERENCES data_sources(id)
);

SELECT create_hypertable('tick_data', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_tick_data_symbol_time 
    ON tick_data (symbol_id, time DESC);

-- ============================================
-- Analysis & Indicators
-- ============================================

-- Market Regimes
CREATE TABLE IF NOT EXISTS market_regimes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    regime VARCHAR(50) NOT NULL, -- 'risk_on', 'risk_off', 'transitional'
    confidence DECIMAL(5, 2) NOT NULL, -- 0-100
    indicators JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_market_regimes_timestamp 
    ON market_regimes(timestamp DESC);

-- Macro Regimes
CREATE TABLE IF NOT EXISTS macro_regimes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    regime VARCHAR(50) NOT NULL, -- 'hawkish', 'dovish', 'neutral'
    risk_score INT CHECK (risk_score >= 0 AND risk_score <= 100),
    macro_score INT CHECK (macro_score >= 0 AND macro_score <= 100),
    gold_bias VARCHAR(50) NOT NULL, -- 'bullish', 'neutral', 'bearish'
    confidence DECIMAL(5, 2) NOT NULL,
    inputs JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_macro_regimes_timestamp 
    ON macro_regimes(timestamp DESC);

-- Smart Money Events
CREATE TABLE IF NOT EXISTS smart_money_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol_id UUID NOT NULL REFERENCES symbols(id),
    timeframe VARCHAR(10) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'BOS', 'CHOCH', 'FVG', 'ORDER_BLOCK', etc
    price DECIMAL(18, 8) NOT NULL,
    intensity DECIMAL(5, 2), -- 0-100
    probability DECIMAL(5, 2), -- 0-100
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_smc_events_symbol_time 
    ON smart_money_events(symbol_id, timestamp DESC);

-- Volatility Readings
CREATE TABLE IF NOT EXISTS volatility_readings (
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol_id UUID NOT NULL REFERENCES symbols(id),
    atr DECIMAL(18, 8),
    realized_vol DECIMAL(5, 2),
    regime VARCHAR(50), -- 'low', 'medium', 'high'
    compression_score DECIMAL(5, 2),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('volatility_readings', 'timestamp', if_not_exists => TRUE);

-- Correlations
CREATE TABLE IF NOT EXISTS correlations (
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol_1_id UUID NOT NULL REFERENCES symbols(id),
    symbol_2_id UUID NOT NULL REFERENCES symbols(id),
    correlation_value DECIMAL(5, 3),
    period VARCHAR(20), -- '1h', '1d', '1w', '1m'
    significance DECIMAL(5, 2),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

SELECT create_hypertable('correlations', 'timestamp', if_not_exists => TRUE);

-- ============================================
-- AI & Predictions
-- ============================================

-- Predictions
CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol_id UUID NOT NULL REFERENCES symbols(id),
    model_id VARCHAR(100) NOT NULL,
    prediction_value DECIMAL(18, 8),
    confidence DECIMAL(5, 2),
    timeframe VARCHAR(20),
    outcome DECIMAL(18, 8),
    outcome_timestamp TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_symbol_time 
    ON predictions(symbol_id, timestamp DESC);

-- Analysis Reports
CREATE TABLE IF NOT EXISTS analysis_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol_id UUID NOT NULL REFERENCES symbols(id),
    report_type VARCHAR(50), -- 'executive_summary', 'scenario', 'risk'
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Alerts & Notifications
-- ============================================

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol_id UUID NOT NULL REFERENCES symbols(id),
    alert_type VARCHAR(50) NOT NULL,
    condition_description TEXT NOT NULL,
    threshold DECIMAL(18, 8),
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active', 'triggered', 'dismissed'
    triggered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Jobs & Logs
-- ============================================

CREATE TABLE IF NOT EXISTS job_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'pending', 'running', 'success', 'error'
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_job_logs_created_at 
    ON job_logs(created_at DESC);

-- ============================================
-- Insert Default Data
-- ============================================

-- Default Symbols
INSERT INTO symbols (symbol, name, type, description, contract_multiplier, tick_size)
VALUES
    ('XAUUSD', 'Gold/USD', 'forex', 'Gold spot price in USD', 1, 0.01),
    ('GC', 'Gold Futures', 'futures', 'COMEX Gold Futures', 100, 0.1),
    ('DXY', 'US Dollar Index', 'index', 'Dollar Strength Index', 1, 0.01),
    ('US10Y', '10Y Treasury', 'bond', 'US 10-Year Treasury Yield', 1, 0.01),
    ('US02Y', '2Y Treasury', 'bond', 'US 2-Year Treasury Yield', 1, 0.01),
    ('SPX', 'S&P 500', 'index', 'S&P 500 Index', 1, 0.01),
    ('NDX', 'Nasdaq 100', 'index', 'Nasdaq 100 Index', 1, 0.01),
    ('VIX', 'Volatility Index', 'index', 'VIX Volatility Index', 1, 0.01)
ON CONFLICT (symbol) DO NOTHING;

-- Default Data Sources
INSERT INTO data_sources (name, type, description, active)
VALUES
    ('Alpha Vantage', 'provider', 'Free/Premium data provider', true),
    ('Twelve Data', 'provider', 'Professional data provider', true),
    ('Polygon', 'provider', 'High-quality market data', true),
    ('Interactive Brokers', 'broker', 'IB Data Feed', true)
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- Grants (for application user if needed)
-- ============================================

-- Create application user (uncomment if needed)
-- CREATE USER intelligence_app WITH PASSWORD 'change_me_in_production';
-- GRANT CONNECT ON DATABASE intelligence_terminal TO intelligence_app;
-- GRANT USAGE ON SCHEMA public TO intelligence_app;
-- GRANT ALL TABLES IN SCHEMA public TO intelligence_app;

COMMIT;
