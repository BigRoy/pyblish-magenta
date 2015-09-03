import os

import pyblish.api
import pyblish_magenta.plugin
from pyblish_magenta.vendor import capture

from maya import cmds


@pyblish.api.log
class ExtractReview(pyblish_magenta.api.Extractor):
    """Extract camera(s) from an instances as a quicktime

    Arguments:
        startFrame (float): Start frame of output
        endFrame (float): End frame of output
        width (int): Width of output in pixels
        height (int): Height of output in pixels
        format (str): Which format to use for the given filename,
            defaults to "qt"
        compression (str): Which compression to use with the given
            format, defaults to "h264"
        offScreen (bool): Capture off-screen
        maintainAspectRatio (bool): Whether or not to modify height for width
            in order to preserve the current aspect ratio.
        show (str): Space-separated list of which node-types to show,
            e.g. "nurbsCurves polymeshes"

    """

    families = ["review"]
    hosts = ["maya"]
    optional = True
    label = "Quicktime"

    def process(self, instance):
        self.log.info("Extracting capture..")

        current_min_time = cmds.playbackOptions(minTime=True, query=True)
        current_max_time = cmds.playbackOptions(maxTime=True, query=True)

        default_width = cmds.getAttr("defaultResolution.width")
        default_height = cmds.getAttr("defaultResolution.height")

        width = instance.data('width') or default_width
        height = instance.data('height') or default_height
        start_frame = instance.data('startFrame') or current_min_time
        end_frame = instance.data('endFrame') or current_max_time

        format = instance.data('format') or 'qt'
        compression = instance.data('compression') or 'h264'
        off_screen = instance.data('offScreen', False)
        maintain_aspect_ratio = instance.data('maintainAspectRatio', True)

        cam_opts = capture.CameraOptions()

        # Set viewport settings
        view_opts = capture.ViewportOptions()
        view_opts.displayAppearance = "smoothShaded"
        view_opts.polymeshes = True
        view_opts.nurbsSurfaces = True

        cameras = [c for c in instance if cmds.nodeType(c) == "camera"]
        cameras = [cmds.listRelatives(c, parent=True)[0] for c in cameras]

        path = self.temp_dir(instance)

        for camera in cameras:
            # Ensure name of camera is valid
            camera = pyblish.api.format_filename(camera)

            if format == 'image':
                # Append sub-directory for image-sequence
                path = os.path.join(path, camera)
            else:
                path = os.path.join(path, camera + ".mov")

            self.log.info("Outputting to %s" % path)

            output = capture.capture(
                filename=path,
                camera=camera,
                width=width,
                height=height,
                start_frame=start_frame,
                end_frame=end_frame,
                format=format,
                viewer=False,
                compression=compression,
                off_screen=off_screen,
                maintain_aspect_ratio=maintain_aspect_ratio,
                viewport_options=view_opts,
                camera_options=cam_opts)

            self.log.info("Outputted to: %s" % output)
            instance.set_data("reviewOutput", output)
