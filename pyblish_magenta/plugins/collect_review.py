import pyblish.api

import maya.cmds as cmds


@pyblish.api.log
class CollectCameras(pyblish.api.Collector):
    order = pyblish.api.Collector.order + 0.2
    hosts = ["maya"]
    label = "Collect Cameras"

    def process(self, context):
        for camera_shape in cmds.ls("*_CAPShape",
                                    objectsOnly=True,
                                    type="camera",
                                    long=True,
                                    recursive=True):  # Include namespace

            camera = cmds.listRelatives(camera_shape, parent=True)[0]

            # Use short name
            name = cmds.ls(camera, long=False)[0].rsplit("_CAP", 1)[0].title()

            instance = context.create_instance(name=name, family="review")
            instance.add(camera)

            self.log.info("Found: {0}".format(camera))

            attrs = cmds.listAttr(camera, userDefined=True) or list()
            for attr in attrs:
                if attr == "parent":
                    # Instance has a parent instance
                    parent_instance = cmds.listConnections(
                        camera + ".parent",
                        destination=False,
                        source=True)
                    instance.set_data("parent", parent_instance)

                try:
                    value = cmds.getAttr(camera + "." + attr)
                except:
                    continue

                instance.set_data(attr, value=value)
