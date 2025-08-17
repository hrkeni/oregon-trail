# MCP (Model Context Protocol) Configuration

This project includes MCP configuration to enable AI assistants to directly access and query the `cache.db` SQLite database through the dbhub MCP server.

## What is MCP?

Model Context Protocol (MCP) is a standard that allows AI assistants to securely access external data sources and tools. In this project, MCP enables direct database access for better context and data analysis.

## Database Access via dbhub MCP

The `mcp.json` configuration file sets up a dbhub MCP server that provides access to your rental listing cache database.

### Database Structure

**`cache.db`** - SQLite database containing:

#### 1. `web_pages` Table (Primary Cache - Actively Used)

- **Purpose**: Primary cache for web page content to avoid re-scraping
- **Key Fields**:
  - `url`: Rental listing URL (primary key)
  - `content`: Cached HTML/content from the page
  - `headers`: HTTP response headers (stored as JSON)
  - `status_code`: HTTP status code
  - `cached_at`: When the page was cached

#### 2. `field_hashes` Table (Field Protection - Actively Used)

- **Purpose**: Tracks manual edits to prevent data loss during rescraping
- **Key Fields**:
  - `url`: Rental listing URL
  - `field_name`: Name of the field (16 total fields tracked)
  - `field_hash`: MD5 hash of the field value (8 characters)
  - `last_updated`: When the hash was last updated
- **Protected Fields**: url, address, price, beds, baths, sqft, house_type, description, amenities, available_date, parking, utilities, contact_info, appointment_url, scraped_at, notes, decision

#### 3. `page_cache` Table (Legacy Cache - Not Currently Used)

- **Purpose**: Legacy web page cache with URL hashing (exists but unused)
- **Key Fields**:
  - `url_hash`: Unique hash identifier for each URL
  - `url`: Original rental listing URL
  - `content`: Cached HTML/content from the page
  - `headers`: HTTP response headers
  - `status_code`: HTTP status code
  - `created_at`: When the page was first cached
  - `last_accessed`: Last time the cache was accessed

## Usage Examples

### Query Cache Statistics

```sql
-- Count total cached pages (active cache)
SELECT COUNT(*) as total_pages FROM web_pages;

-- Count pages by status code
SELECT status_code, COUNT(*) as count 
FROM web_pages 
GROUP BY status_code;

-- Find oldest cached pages
SELECT url, cached_at 
FROM web_pages 
ORDER BY cached_at ASC 
LIMIT 10;
```

### Analyze Field Protection (Most Important)

```sql
-- See which fields are protected for each listing
SELECT url, field_name, last_updated 
FROM field_hashes 
ORDER BY last_updated DESC;

-- Count protected fields by type
SELECT field_name, COUNT(*) as protected_count 
FROM field_hashes 
GROUP BY field_name;

-- Find listings with multiple protected fields
SELECT url, COUNT(*) as protected_fields 
FROM field_hashes 
GROUP BY url 
HAVING protected_fields > 1;

-- Check specific field protection (e.g., notes and decisions)
SELECT url, field_name, last_updated 
FROM field_hashes 
WHERE field_name IN ('notes', 'decision') 
ORDER BY last_updated DESC;
```

### Cache Management

```sql
-- Find expired cache entries (older than 7 days)
SELECT url, cached_at, 
       julianday('now') - julianday(cached_at) as days_old
FROM web_pages 
WHERE julianday('now') - julianday(cached_at) > 7;

-- Find most recently cached pages
SELECT url, cached_at 
FROM web_pages 
ORDER BY cached_at DESC 
LIMIT 10;
```

### Field Protection Analysis

```sql
-- See which listings have the most protected fields
SELECT url, COUNT(*) as protected_fields 
FROM field_hashes 
GROUP BY url 
ORDER BY protected_fields DESC;

-- Check field protection patterns over time
SELECT 
    DATE(last_updated) as date,
    field_name,
    COUNT(*) as protection_count
FROM field_hashes 
GROUP BY DATE(last_updated), field_name
ORDER BY date DESC, protection_count DESC;

-- Find listings with recent manual edits
SELECT url, field_name, last_updated 
FROM field_hashes 
WHERE julianday('now') - julianday(last_updated) < 1
ORDER BY last_updated DESC;
```

## Benefits of MCP Integration

1. **Direct Database Access**: AI assistants can query your cache data directly
2. **Field Protection Insights**: Understand which fields are manually protected and when
3. **Cache Performance Analysis**: Analyze cache efficiency and usage patterns
4. **Manual Edit Tracking**: See what you've manually edited and when
5. **Troubleshooting**: Debug cache issues and field protection problems

## Configuration Details

The MCP configuration in `mcp.json`:

```json
{
  "mcpServers": {
    "dbhub": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-dbhub"],
      "env": {
        "MCP_DBHUB_DATABASE_PATH": "./cache.db",
        "MCP_DBHUB_DATABASE_TYPE": "sqlite"
      }
    }
  }
}
```

### Environment Variables

- `MCP_DBHUB_DATABASE_PATH`: Path to your SQLite database
- `MCP_DBHUB_DATABASE_TYPE`: Database type (sqlite)

## Security Considerations

- **Local Database**: The database is stored locally in your project directory
- **No External Access**: MCP access is limited to your local environment
- **Field Protection**: Sensitive field hashes are stored but not exposed as plain text
- **Cache Content**: Web page content is cached but can be cleared using CLI commands

## Troubleshooting

### Common Issues

1. **MCP Server Not Starting**
   - Ensure Node.js and npm are installed
   - Check that the database path is correct
   - Verify the database file exists and is readable

2. **Database Locked**
   - Close any other applications accessing the database
   - Ensure no CLI commands are currently running
   - Check file permissions

3. **Schema Changes**
   - If you modify the database schema, update the MCP configuration
   - Restart the MCP server after schema changes

### Commands to Check Database Health

```bash
# Check database integrity
sqlite3 cache.db "PRAGMA integrity_check;"

# View database size
ls -lh cache.db

# Check table row counts
sqlite3 cache.db "SELECT 'web_pages' as table_name, COUNT(*) as count FROM web_pages UNION ALL SELECT 'field_hashes', COUNT(*) FROM field_hashes UNION ALL SELECT 'page_cache', COUNT(*) FROM page_cache;"

# Check field protection status
sqlite3 cache.db "SELECT field_name, COUNT(*) as count FROM field_hashes GROUP BY field_name ORDER BY count DESC;"
```

## Integration with CLI Commands

The MCP database access complements your existing CLI commands:

- **`cache-stats`**: Shows high-level cache statistics
- **`cache-clear`**: Manages cache cleanup
- **`protection-status`**: Shows field protection status
- **`notes-status`**: Shows which listings have notes
- **`reset-hashes`**: Resets field protection for a listing
- **MCP Queries**: Provide detailed database analysis and insights

## Field Protection System

The database implements a sophisticated field protection system:

1. **Hash Generation**: Each field value gets an MD5 hash (8 characters)
2. **Change Detection**: During rescraping, new hashes are compared to stored hashes
3. **Manual Edit Preservation**: Fields with different hashes are preserved (manual edits)
4. **Automatic Protection**: Notes and decisions are automatically protected when set
5. **Hash Management**: Hashes can be reset to allow field updates

### Protected Field Types

- **Core Data**: url, address, price, beds, baths, sqft, house_type
- **Descriptive**: description, amenities, available_date, parking, utilities
- **Contact**: contact_info, appointment_url
- **Metadata**: scraped_at
- **User Input**: notes, decision

## Future Enhancements

Potential MCP server additions:

- **Real-time monitoring**: Live cache hit/miss statistics
- **Performance metrics**: Query execution time analysis
- **Data export**: Export cache data in various formats
- **Backup management**: Automated database backup and restore
- **Field protection analytics**: Advanced insights into manual edit patterns

---

For more information about MCP, visit: <https://modelcontextprotocol.io/>
For dbhub MCP server details: <https://github.com/modelcontextprotocol/server-dbhub>
