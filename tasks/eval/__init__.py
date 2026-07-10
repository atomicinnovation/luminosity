from invoke import Collection

from . import skills, view

ns = Collection()
ns.add_collection(Collection.from_module(skills))
ns.add_task(view.view)
