# Database Migration for API Analytics

## Create the api_analytics table

Run this SQL to create the analytics table:

```sql
CREATE TABLE IF NOT EXISTS api_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms REAL NOT NULL,
    user_id INTEGER,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    request_size INTEGER,
    response_size INTEGER,
    error_message VARCHAR(1000),
    extra_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_api_analytics_endpoint ON api_analytics(endpoint);
CREATE INDEX idx_api_analytics_method ON api_analytics(method);
CREATE INDEX idx_api_analytics_status_code ON api_analytics(status_code);
CREATE INDEX idx_api_analytics_user_id ON api_analytics(user_id);
CREATE INDEX idx_api_analytics_created_at ON api_analytics(created_at);
CREATE INDEX idx_endpoint_method ON api_analytics(endpoint, method);
CREATE INDEX idx_created_at_endpoint ON api_analytics(created_at, endpoint);
CREATE INDEX idx_status_created ON api_analytics(status_code, created_at);
```

## Or simply restart the backend

The table will be created automatically when you restart the FastAPI backend since we're using SQLAlchemy's `create_all()`.
