"""
Setup and Help CLI Commands

Commands for setup instructions and general help
"""

import click


@click.command()
def setup():
    """Setup instructions for Google Sheets API"""
    click.echo("🔧 Google Sheets API Setup Instructions:")
    click.echo()
    click.echo("1. Go to Google Cloud Console: https://console.cloud.google.com/")
    click.echo("2. Create a new project or select existing one")
    click.echo("3. Enable Google Sheets API and Google Drive API")
    click.echo("4. Create a Service Account:")
    click.echo("   - Go to 'IAM & Admin' > 'Service Accounts'")
    click.echo("   - Click 'Create Service Account'")
    click.echo("   - Give it a name like 'oregon-trail-sheets'")
    click.echo("5. Create and download JSON key:")
    click.echo("   - Click on the service account")
    click.echo("   - Go to 'Keys' tab")
    click.echo("   - Click 'Add Key' > 'Create new key' > 'JSON'")
    click.echo("   - Download the JSON file")
    click.echo("6. Rename the downloaded file to 'credentials.json'")
    click.echo("7. Place 'credentials.json' in the project root directory")
    click.echo()
    click.echo("✅ You're ready to use the app!")


@click.command()
def help():
    """Show detailed help for all available commands"""
    click.echo("🔧 Oregon Trail - Rental Listing Summarizer")
    click.echo("=" * 50)
    click.echo()
    click.echo("📋 CORE COMMANDS:")
    click.echo("  add                    - Add rental listings from URLs")
    click.echo("  list                   - Show all listings in the sheet")
    click.echo("  update-notes           - Update notes for a specific listing")
    click.echo("  share                  - Share the sheet with someone")
    click.echo("  clear                  - Clear all listings from the sheet")
    click.echo("  rescrape               - Rescrape all URLs from the sheet")
    click.echo()
    click.echo("🛡️  DATA PROTECTION COMMANDS:")
    click.echo("  notes-status           - Show which listings have notes")
    click.echo("  protection-status      - Show which fields are protected")
    click.echo("  protect-fields         - Manually protect specific fields")
    click.echo("  unprotect-fields       - Remove protection from specific fields")
    click.echo("  reset-hashes           - Reset field hashes for a listing")
    click.echo()
    click.echo("🗄️  CACHE MANAGEMENT:")
    click.echo("  cache-clear            - Clear expired cache entries")
    click.echo("  cache-stats            - Show cache statistics")
    click.echo()
    click.echo("⚙️  SETUP:")
    click.echo("  setup                  - Google Sheets API setup instructions")
    click.echo()
    click.echo("💡 NOTES PROTECTION:")
    click.echo("  • Notes are automatically protected when you add them")
    click.echo("  • Protected fields are preserved during rescraping")
    click.echo("  • Use --ignore-hashes to force update all fields")
    click.echo("  • Use --reset-hashes to remove protection from a listing")
    click.echo()
    click.echo("📖 For detailed help on any command:")
    click.echo("  python main.py <command> --help")
