#!/usr/bin/env python3.4
import click
from nectar import server, cli


def startserver():
    server.start_server()


@click.group()
def pomares():
    """Pomares file distribution"""
    pass


@pomares.command()
@click.option('--address',
              default='0.0.0.0',
              help='Address to listen on (default is 0.0.0.0)')
@click.option('--port',
              default='8080',
              help='Port to listen to (default is 8080)')
@click.option('--keyfile',
              default='local.key',
              help='Keypair file to use (default is local.key)')
def run(address, port, keyfile):
    """Run server"""
    cli.run(address, port, keyfile)


@pomares.command()
@click.option('--seeded',
              default='False',
              help='List exported trees', nargs=1)
@click.option('--planted',
              default='True',
              help='List imported trees (default)', nargs=1)
def ls(seeded, planted):
    """List pomares or trees"""
    cli.ls(seeded, planted)


@pomares.command()
@click.argument('dirname', default='/', nargs=1)
def keypairs(dirname):
    """List keypair files

    \b
    DIRNAME - Directory to list
    """
    cli.keypairs(dirname)


@pomares.command()
@click.argument('alias', nargs=1)
@click.argument('tree', nargs=1)
def plant(alias, tree):
    """Plant remote tree

    \b
    ALIAS - peer alias
    TREE - tree name
    """
    cli.plant(alias, tree)


@pomares.command()
@click.argument('directory', nargs=1)
@click.argument('tree', nargs=1)
def seed(directory, tree):
    """Seed local tree

    \b
    DIRECTORY - Directory path
    TREE - Tree name
    """
    cli.seed(directory, tree)


@pomares.command()
@click.argument('keyfile', default=None, required=False)
def genkey(keyfile):
    """Generate keypair files

    \b
    KEYFILE - keypair filename
    """
    cli.genkey(keyfile)


@pomares.command()
@click.argument('alias')
@click.argument('pubkey')
@click.argument('address')
def pubkey(alias, pubkey, address):
    """Add public key

    \b
    ALIAS - Alias
    PUBKEY - Public key
    ADDRESS - Set address to key (add new peer)
    """
    cli.pubkey(alias, pubkey, address)


@pomares.command()
@click.argument('command', nargs=1)
def raw(command):
    """Send raw commands to admin sock

    \b
    COMMAND - Raw command"""
    cli.raw(command)


@pomares.command()
def about():
    cli.about()


if __name__ == '__main__':
    pomares()

"""

    try:
        # TODO get rid of this when using click
        # instead of argparse
        if sys.argv[1] == 'import':
            func = cli.import_tree
        else:
            func = getattr(cli, sys.argv[1])
        func(args)
    except IndexError:
        parser.print_help()
        """
