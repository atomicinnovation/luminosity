from invoke import Collection

from . import cli, evals, integration, kernel, launcher, unit

ns = Collection()
ns.add_collection(Collection.from_module(unit))
ns.add_collection(Collection.from_module(integration))
ns.add_collection(Collection.from_module(cli))
ns.add_collection(Collection.from_module(evals))
ns.add_collection(Collection.from_module(launcher))
ns.add_collection(Collection.from_module(kernel))
