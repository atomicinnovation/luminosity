from invoke import Collection

from . import (
    build,
    changelog,
    deny,
    deps,
    git,
    github,
    lint,
    marketplace,
    pup,
    release,
    test,
    types,
    version,
)
from . import format as format_

ns = Collection()

ns_prerelease = Collection("prerelease")
ns_prerelease.add_task(release.prerelease, default=True)
ns_prerelease.add_task(release.prerelease_prepare, name="prepare")
ns_prerelease.add_task(release.prerelease_finalise, name="finalise")
ns.add_collection(ns_prerelease)

ns_release = Collection("release")
ns_release.add_task(release.release, default=True)
ns_release.add_task(release.release_prepare, name="prepare")
ns_release.add_task(release.release_finalise, name="finalise")
ns.add_collection(ns_release)

ns.add_collection(Collection.from_module(build))
ns.add_collection(Collection.from_module(changelog))
ns.add_collection(Collection.from_module(deny))
ns.add_collection(Collection.from_module(deps))
ns.add_collection(Collection.from_module(git))
ns.add_collection(Collection.from_module(github))
ns.add_collection(Collection.from_module(marketplace))
ns.add_collection(Collection.from_module(pup))
ns.add_collection(Collection.from_module(test))
ns.add_collection(Collection.from_module(version))

ns_format = Collection("format")
ns_format.add_collection(Collection.from_module(format_.scripts))
ns_format.add_collection(Collection.from_module(format_.build_system))
ns_format.add_collection(Collection.from_module(format_.cli))
ns_format.add_collection(Collection.from_module(format_.kernel))
ns.add_collection(ns_format)

ns_lint = Collection("lint")
ns_lint.add_collection(Collection.from_module(lint.scripts))
ns_lint.add_collection(Collection.from_module(lint.build_system))
ns_lint.add_collection(Collection.from_module(lint.workflows))
ns_lint.add_collection(Collection.from_module(lint.cli))
ns_lint.add_collection(Collection.from_module(lint.kernel))
ns.add_collection(ns_lint)

ns_types = Collection("types")
ns_types.add_collection(Collection.from_module(types.build_system))
ns.add_collection(ns_types)
