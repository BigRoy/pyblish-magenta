import os

import pyblish_maya
import pyblish_magenta.api


class ExtractRig(pyblish_magenta.api.Extractor):
    """Extract as Maya Ascii"""

    label = "Extract Rig (Maya ASCII)"
    hosts = ["maya"]
    families = ["rig"]

    def process(self, instance):
        from maya import cmds

        # Define extract output file path
        dir_path = self.temp_dir(instance)
        filename = "{0}.ma".format(instance.name)
        path = os.path.join(dir_path, filename)

        # Perform extraction
        self.log.info("Performing extraction..")
        with pyblish_maya.maintained_selection():
            cmds.select(instance, noExpand=True)
            cmds.file(path,
                      force=True,
                      typ="mayaAscii",
                      exportSelected=True,
                      preserveReferences=False,
                      channels=True,
                      constraints=True,
                      expressions=True,
                      constructionHistory=True)

        self.log.info("Extracted instance '{0}' to: {1}".format(
            instance.name, path))
