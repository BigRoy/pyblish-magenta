import pyblish.api
import pyblish_magenta.api
from maya import cmds


class ValidateMeshSingleUVSet(pyblish.api.InstancePlugin):
    """Ensure no multiple UV sets exist for each polygon mesh"""

    order = pyblish_magenta.api.ValidateMeshOrder
    families = ['model', 'pointcache']
    hosts = ['maya']
    category = 'uv'
    optional = True
    version = (0, 1, 0)
    label = "Mesh Single UV Set"

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""
        meshes = cmds.ls(instance, type='mesh', long=True)

        invalid = []
        for mesh in meshes:
            uvSets = cmds.polyUVSet(mesh, query=True, allUVSets=True)
            if len(uvSets) != 1:
                invalid.append(mesh)

        if invalid:
            raise ValueError("Nodes found with multiple "
                             "UV sets: {0}".format(invalid))
                
    def repair(self, instance):
        """Keep only current UV set and ensure it's the default 'map1'"""
        meshes = cmds.ls(instance, type='mesh', long=True)

        for mesh in meshes:
            uvSets = cmds.polyUVSet(mesh,
                                    query=True,
                                    allUVSets=True)
            current = cmds.polyUVSet(mesh,
                                     query=True,
                                     currentUVSet=True)[0]
            if len(uvSets) != 1:
                
                # Copy over to map1
                if current != 'map1':
                    cmds.polyUVSet(mesh,
                                   uvSet=current,
                                   newUVSet='map1',
                                   copy=True)
                    cmds.polyUVSet(mesh,
                                   currentUVSet=True,
                                   uvSet='map1')
                    current = 'map1'
                
                # Delete all non-current UV sets
                deleteUVSets = [uvSet for uvSet in uvSets if uvSet != current]
                uvSet = None

                # Maya Bug (tested in 2015/2016):
                # In some cases the API's MFnMesh will report less UV sets
                # than maya.cmds.polyUVSet.
                # This seems to happen when the deletion of UV sets has not
                # triggered a cleanup of the UVSet array
                # attribute on the mesh node. It will still have extra
                # entries in the attribute, though it will not
                # show up in API or UI. Nevertheless it does show up in
                # maya.cmds.polyUVSet.
                # To ensure we clean up the array we'll force delete the
                # extra remaining 'indices' that we don't want.

                # TODO: Implement a better fix
                # The best way to fix would be to get the UVSet
                # indices from api with MFnMesh (to ensure we keep
                # correct ones) and then only force delete the other
                # entries in the array attribute on the node.
                # But for now we're deleting all entries except first
                # one. Note that the first entry could never
                # be removed (the default 'map1' always exists and is
                # supposed to be undeletable.)
                try:
                    for uvSet in deleteUVSets:
                        cmds.polyUVSet(mesh, delete=True, uvSet=uvSet)
                except RuntimeError, e:
                    self.log.warning('uvSet: {0} - '
                                     'Error: {1}'.format(uvSet, e))

                    # Delete from end to avoid shifting indices
                    indices = cmds.getAttr('{0}.uvSet'.format(mesh),
                                           multiIndices=True)
                    indices = reversed(indices)

                    # Skip first
                    it = iter(indices)
                    next(it)

                    # Remove the indices in the attribute
                    for i in it:
                        attr = '{0}.uvSet[{1}]'.format(mesh, i)
                        cmds.removeMultiInstance(attr, b=True)