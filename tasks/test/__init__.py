from invoke import Collection

from . import cli, integration, unit

ns = Collection()
ns.add_collection(Collection.from_module(unit))
ns.add_collection(Collection.from_module(integration))
ns.add_collection(Collection.from_module(cli))
