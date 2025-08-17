"""
Cache Management CLI Commands

Commands for managing the cache system, including statistics and cleanup
"""

import click


@click.command()
@click.option('--max-age-hours', default=168, help='Maximum age of cache entries in hours (default: 168 = 7 days)')
def cache_clear(max_age_hours: int):
    """Clear expired cache entries"""
    try:
        from ...cache import WebPageCache
        cache = WebPageCache()
        cache.clear(max_age_hours=max_age_hours)
        click.echo(f"✅ Cleared cache entries older than {max_age_hours} hours")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")


@click.command()
def cache_stats():
    """Show cache statistics"""
    try:
        from ...cache import WebPageCache
        cache = WebPageCache()
        stats = cache.get_stats()
        
        if stats:
            click.echo("📊 Cache Statistics:")
            click.echo(f"   Web pages cached: {stats.get('total_pages', 0)}")
            click.echo(f"   Recent pages (24h): {stats.get('recent_pages', 0)}")
            click.echo(f"   Field hashes stored: {stats.get('total_hashes', 0)}")
            click.echo(f"   URLs with hashes: {stats.get('urls_with_hashes', 0)}")
        else:
            click.echo("📊 No cache statistics available")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
