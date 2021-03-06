import pyblish.api
import pyblish_magenta.api
import pyblish_maya

from pyblish_magenta.action import SelectInvalidAction, RepairAction

from maya import cmds


class ValidateMeshNonZeroVertices(pyblish.api.Validator):
    """Validate meshes have no internal points offsets (#34)

    Vertices can have internal vertex offset that mess with subsequent
    deformers and are difficult to track down. The offset values can be seen
    in the channelBox when selecting the vertices, all values there should be
    zero.
    """

    order = pyblish_magenta.api.ValidateMeshOrder
    families = ['model']
    hosts = ['maya']
    category = 'geometry'
    version = (0, 1, 0)
    label = 'Mesh Non Zero Vertices'
    actions = [SelectInvalidAction, RepairAction]

    _tolerance = 1e-8

    @staticmethod
    def _iter_internal_pts(mesh):
        """Yield the internal offset values for each point of the mesh"""
        num_pts = cmds.getAttr('{0}.pnts'.format(mesh), size=True)
        for i in range(num_pts):
            attr = '{0}.pnts[{1}]'.format(mesh, i)
            yield cmds.getAttr(attr)[0]

    @classmethod
    def is_invalid(cls, mesh):
        pts = cls._iter_internal_pts(mesh)
        for pt in pts:
            if any(abs(v) > cls._tolerance for v in pt):
                return True
        return False

    @classmethod
    def get_invalid(cls, instance):

        meshes = cmds.ls(instance, type='mesh', long=True)
        return [mesh for mesh in meshes if cls.is_invalid(mesh)]

    def process(self, instance):
        """Process all meshes"""
        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Meshes found with non-zero vertices: "
                               "{0}".format(invalid))

    @classmethod
    def repair(cls, instance):
        """Repair the meshes by 'baking' offsets into the input mesh"""

        invalid = cls.get_invalid(instance)

        # TODO: Find a better way to reset values whilst preserving offsets
        with pyblish_maya.maintained_selection():
            for mesh in invalid:
                cmds.polyMoveVertex(mesh, constructionHistory=False)
