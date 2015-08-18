import os
import json

import maya.api.OpenMaya as om
import maya.cmds as cmds

import pyblish_magenta.schema


def lsattr(attr, value=None):
    """Return nodes matching `key` and `value`

    Arguments:
        attr (str): Name of Maya attribute
        value (object, optional): Value of attribute. If none
            is provided, return all nodes with this attribute.

    Example:
        >> lsattr("id", "myId")
        ["myNode"]
        >> lsattr("id")
        ["myNode", "myOtherNode"]

    """

    if value is None:
        return cmds.ls("*.%s" % attr)
    return lsattrs({attr: value})


def lsattrs(attrs):
    """Return nodes with the given attribute(s).

    Arguments:
        attrs (dict): Name and value pairs of expected matches

    Example:
        >> lsattr("age")  # Return nodes with attribute `age`
        >> lsattr({"age": 5})  # Return nodes with an `age` of 5
        >> # Return nodes with both `age` and `color` of 5 and blue
        >> lsattr({"age": 5, "color": "blue"})

    Returns a list.

    """

    dep_fn = om.MFnDependencyNode()
    dag_fn = om.MFnDagNode()
    selection_list = om.MSelectionList()

    first_attr = attrs.iterkeys().next()

    try:
        selection_list.add("*.{0}".format(first_attr),
                           searchChildNamespaces=True)
    except RuntimeError, e:
        if str(e).endswith("Object does not exist"):
            return []

    matches = set()
    for i in range(selection_list.length()):
        node = selection_list.getDependNode(i)
        if node.hasFn(om.MFn.kDagNode):
            fn_node = dag_fn.setObject(node)
            full_path_names = [path.fullPathName()
                               for path in fn_node.getAllPaths()]
        else:
            fn_node = dep_fn.setObject(node)
            full_path_names = [fn_node.name()]

        for attr in attrs:
            try:
                plug = fn_node.findPlug(attr, True)
                if plug.asString() != attrs[attr]:
                    break
            except RuntimeError:
                break
        else:
            matches.update(full_path_names)

    return list(matches)


def lookdev_link():
    origins_cache = dict()
    schema = pyblish_magenta.schema.load()

    for reference in cmds.ls(type="reference"):
        if reference in ("sharedReferenceNode",):
            continue

        filename = cmds.referenceQuery(reference, filename=True)

        # Determine version of reference
        # NOTE(marcus): Will need to determine whether
        # we're in a shot, or asset
        data = schema["shot.full"].parse(filename)
        version = data["version"]

        # Reduce filename to the /publish directory
        template = schema["shot.publish"]
        data = template.parse(filename)
        root = template.format(data)

        versiondir = os.path.join(root, version)
        origindir = os.path.join(
            versiondir, "metadata", "origin").replace("/", "\\")
        if not os.path.exists(origindir):
            continue  # no origin

        originfile = os.path.join(origindir, os.listdir(origindir)[0])

        if originfile not in origins_cache:
            with open(originfile) as f:
                origins_cache[originfile] = json.load(f)

        origin = origins_cache[originfile]

        if not origin["references"]:
            continue  # no references, no match

        reference = origin["references"][0]
        template = schema["asset.publish"]
        data = {
            "asset": reference["item"],
            "root": data["root"],
            "task": "lookdev"
        }
        assetdir = template.format(data)

        # NOTE(marcus): Need more robust version comparison
        version = sorted(os.listdir(assetdir))[-1]
        instancedir = os.path.join(
            assetdir, version, "lookdev", reference["item"])

        # NOTE(marcus): Will need more robust versions of these
        shaderfile = next(os.path.join(instancedir, f)
                          for f in os.listdir(instancedir)
                          if f.endswith(".ma"))
        linksfile = next(os.path.join(instancedir, f)
                         for f in os.listdir(instancedir)
                         if f.endswith(".json"))

        # Load shaders
        # NOTE(marcus): We'll need this to be separate, at least functionally
        namespace = "%s_shaders_" % reference["item"]
        if namespace not in cmds.namespaceInfo(
                ":", recurse=True, listOnlyNamespaces=True):
            cmds.file(shaderfile, reference=True, namespace=namespace)

        with open(linksfile) as f:
            payload = json.load(f)

        for sgdata in payload:
            for count, sgnode in enumerate(lsattrs({"uuid": sgdata["uuid"]})):
                assert count < 1, "More than one shading group found"
                for mdata in sgdata["members"]:
                    for mnode in lsattrs({"uuid": mdata["uuid"]}):
                        # There may be more than one mesh with a UUID

                        if mdata["components"]:
                            mnode = mnode + "." + mdata["components"]

                        print("Adding \"%s\" to \"%s\"" % (mnode, sgnode))
                        cmds.sets(mnode, forceElement=sgnode)
