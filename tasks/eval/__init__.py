from invoke import Collection

from . import skills

ns = Collection()
ns.add_collection(Collection.from_module(skills))
