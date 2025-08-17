import click

# Import all commands directly (no groups)
from .commands.core import add, list, update_notes, update_decision, sort_by_status, share, clear, rescrape
from .commands.data_protection import notes_status, protection_status, protect_fields, unprotect_fields, reset_hashes
from .commands.cache_management import cache_clear, cache_stats
from .commands.setup import setup, help

@click.group()
def cli():
    """Oregon Trail - Rental Listing Summarizer"""
    pass

# Register all commands directly (maintaining flat structure)
cli.add_command(add)
cli.add_command(list)
cli.add_command(update_notes)
cli.add_command(update_decision)
cli.add_command(sort_by_status)
cli.add_command(share)
cli.add_command(clear)
cli.add_command(rescrape)
cli.add_command(notes_status)
cli.add_command(protection_status)
cli.add_command(protect_fields)
cli.add_command(unprotect_fields)
cli.add_command(reset_hashes)
cli.add_command(cache_clear)
cli.add_command(cache_stats)
cli.add_command(setup)
cli.add_command(help)

if __name__ == '__main__':
    cli()
