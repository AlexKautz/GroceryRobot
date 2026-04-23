"""
arm_camera_localizer.py
=======================
Stub node for the arm-mounted wrist camera.

PURPOSE
-------
This node subscribes to the UR3e arm's wrist camera feeds and publishes the
estimated 3D location of the orange in world coordinates.

The computer vision logic is intentionally left unimplemented — the ROS 2
plumbing, topic wiring, and tf2 transform setup are all in place. The sections
marked with # TODO are where the CV implementation belongs.

SUBSCRIBED TOPICS
-----------------
  /arm_camera/image_raw         (sensor_msgs/msg/Image)
      A 640x480 RGB color image captured 30 times per second from the camera
      mounted on the robot's wrist_3_link. Each pixel is 3 bytes: R, G, B,
      each in the range 0–255. Because this camera is physically attached to
      the arm, its view changes whenever the arm moves.

  /arm_depth_camera/depth_image (sensor_msgs/msg/Image)
      A 640x480 depth image captured 30 times per second. Each pixel is a
      32-bit float representing the distance from the camera to that point
      in the scene, measured in meters. A pixel value of 1.2 means that
      point in the scene is 1.2 m from the camera lens.

  /arm_depth_camera/camera_info (sensor_msgs/msg/CameraInfo)
      Metadata about the depth camera: focal length, principal point, and
      distortion coefficients. These are the "intrinsics" needed to convert
      a (pixel_x, pixel_y, depth) tuple into a 3D (x, y, z) point in the
      camera's coordinate frame. See image_geometry.PinholeCameraModel.

PUBLISHED TOPICS
----------------
  /arm_camera/orange_location    (geometry_msgs/msg/PointStamped)
      The estimated 3D position of the orange in the WORLD coordinate frame.
      A PointStamped contains:
          header.frame_id — the coordinate frame ("world")
          header.stamp    — the time this estimate was made
          point.x/y/z     — position in meters from the world origin

      Currently publishes a dummy (0, 0, 0) placeholder. Replace with real
      detection output once the CV logic is implemented.

COORDINATE FRAMES AND TF2
--------------------------
This is the most important concept to understand when working on this node.

The arm camera is physically attached to the robot wrist. As the arm moves,
the camera moves with it. A point that appears at image coordinates (320, 240)
with depth 0.5 m is at position (0, 0, 0.5) in the CAMERA frame — but that
camera frame is constantly changing position and orientation relative to the
world as the arm moves.

To publish a useful orange location, the result must be expressed in the WORLD
frame (fixed, with its origin at the robot base). tf2 handles this:

    transform = tf_buffer.lookup_transform(
        'world',        # target frame — where we want the point expressed
        'camera_link',  # source frame — where the point currently lives
        rclpy.time.Time()
    )

tf2 knows where camera_link is relative to world at every moment because
robot_state_publisher continuously reads /joint_states and publishes the
full transform tree to /tf. The _lookup_camera_to_world() helper below
wraps this call.

SUGGESTED CV PIPELINE
----------------------
The following is a general outline of how to go from a camera frame to a
published orange location. This is not prescriptive — adapt it to whichever
detection approach makes sense for the project.

  1. Detect the orange in the RGB image
     Use object detection (e.g. YOLO, or HSV color thresholding for red) to
     locate the orange in the 2D image. The useful output is a pixel coordinate:
     (center_x, center_y) within the 640x480 frame.

  2. Look up the depth at that pixel
     Index into the depth image at (center_y, center_x) — note that image
     arrays are indexed [row, col] which corresponds to [y, x]. The result
     is the distance to the orange in meters.

  3. Convert pixel + depth to a 3D point in camera frame
     Use the camera intrinsics from /arm_depth_camera/camera_info.
     The image_geometry.PinholeCameraModel class is a convenient way to do
     this without manual matrix math.

  4. Transform the point from camera frame to world frame
     Use the _lookup_camera_to_world() helper and tf2_geometry_msgs to apply
     the transform. The result is an (x, y, z) position in world coordinates.

  5. Publish the result
     Replace the dummy publish in _publish_dummy_location() with the real
     world-frame PointStamped.
"""

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PointStamped, Point
from visualization_msgs.msg import Marker
from std_msgs.msg import Header
from tf2_ros import Buffer, TransformListener
from image_geometry import PinholeCameraModel

from ultralytics import YOLO
import cv2
import tf2_geometry_msgs
from cv_bridge import CvBridge


class ArmCameraLocalizer(Node):

    def __init__(self):
        super().__init__('arm_camera_localizer')

        # --- tf2 setup ---
        # The Buffer stores the live transform tree that robot_state_publisher
        # broadcasts onto /tf. The TransformListener populates it in the
        # background — it does not need to be called directly.
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        
        # Initialize YOLO model
        self.model = YOLO("yolov8n.pt")

        self.bridge = CvBridge()

        # --- Subscriptions ---

        # RGB image from the wrist camera — the primary input for detection
        self._rgb_sub = self.create_subscription(
            Image,
            '/arm_camera/image_raw',
            self._rgb_callback,
            10,
        )

        # Depth image — provides per-pixel distance for localization
        self._depth_sub = self.create_subscription(
            Image,
            '/arm_depth_camera/depth_image',
            self._depth_callback,
            10,
        )

        # Camera intrinsics — required to convert pixel coordinates to 3D rays
        self._camera_info_sub = self.create_subscription(
            CameraInfo,
            '/arm_depth_camera/camera_info',
            self._camera_info_callback,
            10,
        )

        # --- Publisher ---

        # The estimated orange location in world coordinates.
        # The manipulation node consumes this topic to plan the pick motion.
        self._orange_location_pub = self.create_publisher(
            PointStamped,
            '/arm_camera/orange_location',
            10,
        )

        # Bounding box for orange
        self._bounding_box_pub = self.create_publisher(
            Image,
            '/arm_camera/annotated_image',
            10
        )

        # Marker 
        self._orange_marker_pub = self.create_publisher(
            Marker,
            '/arm_camera/orange_marker',
            10
        )


        # Store the latest camera info so it is available during depth processing
        self._latest_camera_info = None
        self._latest_centroid = None
        self._depth = None

        self.get_logger().info('arm_camera_localizer started — waiting for camera topics...')

    # ------------------------------------------------------------------ #
    #  RGB IMAGE CALLBACK                                                  #
    # ------------------------------------------------------------------ #

    def _rgb_callback(self, msg: Image):
        """
        Called every time a new color frame arrives (~30 Hz).

        msg.data      — raw pixel bytes (R, G, B, R, G, B, ...)
        msg.width     — image width in pixels (640)
        msg.height    — image height in pixels (480)
        msg.encoding  — pixel format, e.g. 'rgb8'
        msg.header    — contains frame_id ('camera_link') and timestamp
        """

        # --- Diagnostic logging ---
        # Convert raw bytes to a numpy array shaped (height, width, 3).
        # The three channels are R, G, B in that order.
        pixels = np.frombuffer(msg.data, dtype=np.uint8).reshape(
            msg.height, msg.width, 3
        ).copy()
        mean_r = float(np.mean(pixels[:, :, 0]))
        mean_g = float(np.mean(pixels[:, :, 1]))
        mean_b = float(np.mean(pixels[:, :, 2]))
        self.get_logger().info(
            f'[arm RGB] {msg.width}x{msg.height} | '
            f'mean R={mean_r:.1f}  G={mean_g:.1f}  B={mean_b:.1f}',
            throttle_duration_sec=2.0,
        )

        #   Detection
        #   This is where the CV implementation begins. The `pixels` array
        #   above is a standard numpy image ready for processing.
        #
        #   The goal is to produce (center_x, center_y) in pixel coordinates.
        #   If nothing is detected, consider returning early rather than
        #   publishing a misleading location.
        #
        #   One starting point for a red object is HSV color thresholding:
        #     import cv2
        #     hsv = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV)
        #     mask = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255))
        #     contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        #     # find the largest contour and compute its centroid
        
        

        # assumes there is one orange in frame
        results = self.model.predict(pixels)
        center_x, center_y = None, None
        for result in results:
            boxes = result.boxes
            for box in boxes:
                if self.model.names[int(box.cls)] == 'orange':
                    x1, y1, x2, y2 = box.xyxy[0]      # bounding box corners [x1, y1, x2, y2]
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    cv2.rectangle(pixels, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        
        # store centroid if orange in frame
        if center_x is not None and center_y is not None:
            self._latest_centroid = np.array([center_y, center_x])
            
        # convert pixels to cv2 image
        cv_img = self.bridge.cv2_to_imgmsg(pixels, 'rgb8')
        self._bounding_box_pub.publish(cv_img)
        # calls self._projection with timestamp
        self._projection(msg.header.stamp)

    # ------------------------------------------------------------------ #
    #  DEPTH IMAGE CALLBACK                                                #
    # ------------------------------------------------------------------ #

    def _depth_callback(self, msg: Image):
        """
        Called every time a new depth frame arrives (~30 Hz).

        msg.data      — raw float32 bytes, one 4-byte float per pixel
        msg.width     — image width in pixels (640)
        msg.height    — image height in pixels (480)
        msg.encoding  — '32FC1' (single-channel 32-bit float)
        msg.header    — contains frame_id ('camera_link') and timestamp
        """

        # --- Diagnostic logging ---
        depth_pixels = np.frombuffer(msg.data, dtype=np.float32).reshape(
            msg.height, msg.width
        )
        # NaN and inf represent pixels with no valid depth reading
        valid = depth_pixels[np.isfinite(depth_pixels)]
        if valid.size > 0:
            self.get_logger().info(
                f'[arm depth] {msg.width}x{msg.height} | '
                f'depth min={valid.min():.2f}m  max={valid.max():.2f}m  '
                f'mean={valid.mean():.2f}m  stamp={msg.header.stamp.sec}',
                throttle_duration_sec=2.0,
            )

        #  s Depth lookup
        #   Once a detection pixel (center_x, center_y) is available from
        #   the RGB callback, retrieve its depth here:
        #     depth_value = depth_pixels[center_y, center_x]
        #   Note the [y, x] indexing — rows come first in numpy arrays.
        #   Verify the value is finite before using it downstream.
        if self._latest_centroid is not None:
            depth_value = depth_pixels[self._latest_centroid]
            if np.isfinite(depth_value):
                self._depth = depth_value

    # ------------------------------------------------------------------ #
    #  CAMERA INFO CALLBACK                                                #
    # ------------------------------------------------------------------ #

    def _camera_info_callback(self, msg: CameraInfo):
        """
        Called when camera intrinsics are published (typically once at startup).

        Stores the message so it is available when converting a detected pixel
        and its depth into a 3D point in camera space.

        The key field is msg.k — a 3x3 intrinsic matrix flattened to 9 values
        containing the focal lengths (fx, fy) and principal point (cx, cy).
        """
        self._latest_camera_info = msg

    def _projection(self, timestamp):

        """
        Pixel-to-3D projection
        With a (center_x, center_y) and a depth_value, the intrinsics
        here allow computing a 3D point in the camera coordinate frame.
        """

        #   Pixel-to-3D projection
        #   With a (center_x, center_y) and a depth_value, the intrinsics
        #   here allow computing a 3D point in the camera coordinate frame.
        #   image_geometry.PinholeCameraModel is a convenient abstraction:
        #
        #     from image_geometry import PinholeCameraModel
        #     model = PinholeCameraModel()
        #     model.fromCameraInfo(self._latest_camera_info)
        #     ray = model.projectPixelTo3dRay((center_x, center_y))
        #     point_in_camera_frame = [r * depth_value for r in ray]
        #
        #   point_in_camera_frame is (x, y, z) in meters, expressed in the
        #   camera_link frame. It still needs to be transformed to world frame.

        if self._latest_centroid is not None and self._depth is not None and self._latest_camera_info is not None:
        
            model = PinholeCameraModel()
            model.fromCameraInfo(self._latest_camera_info)
            center_x, center_y = self._latest_centroid[1], self._latest_centroid[0]
            ray = model.projectPixelTo3dRay((center_x, center_y))
            point_in_camera_frame = [r * self._depth for r in ray]
            

            transform = self._lookup_camera_to_world()

            if transform is not None:
                point_stamped = PointStamped()
                point_stamped.header.frame_id = 'camera_link'
                point_stamped.header.stamp = timestamp
                point_stamped.point = Point(x=point_in_camera_frame[0], y=point_in_camera_frame[1], z=point_in_camera_frame[2])
                world_point = tf2_geometry_msgs.do_transform_point(point_stamped, transform)
                self._publish_world_frame(world_point)

    # ------------------------------------------------------------------ #
    #  TF2 TRANSFORM HELPER                                                #
    # ------------------------------------------------------------------ #

    def _lookup_camera_to_world(self):
        """
        Returns the current transform from camera_link to world, or None
        if it is not yet available (e.g. during early startup).

        Once a 3D point in camera_link frame is known, this transform can
        be applied to express it in the world frame:

            import tf2_geometry_msgs
            transform = self._lookup_camera_to_world()
            if transform is None:
                return  # not ready — skip this frame

            point_stamped = PointStamped()
            point_stamped.header.frame_id = 'camera_link'
            point_stamped.point = Point(x=..., y=..., z=...)
            world_point = tf2_geometry_msgs.do_transform_point(point_stamped, transform)
            # world_point.point is now (x, y, z) in world frame
        """
        try:
            return self._tf_buffer.lookup_transform(
                'world',
                'camera_link',
                rclpy.time.Time(),
            )
        except Exception:
            # Transform not available yet — the arm may still be initializing
            return None

    # ------------------------------------------------------------------ #
    #  PLACEHOLDER PUBLISHER                                               #
    # ------------------------------------------------------------------ #

    def _publish_world_frame(self, world_point):
        """
        Publishes the real world-frame PointStamped once the detection and transform 
        pipeline above is complete.
        """

        self._orange_location_pub.publish(world_point)

        marker = Marker()
        marker.header.frame_id = 'world'
        marker.ns = 'orange_detection'
        marker.id = 0
        marker.action = Marker.ADD
        marker.type = Marker.SPHERE
        marker.scale.x = 0.1
        marker.scale.y = 0.1
        marker.scale.z = 0.1
        marker.color.a = 1.0 # Alpha
        marker.color.r = 1.0 # Color
        marker.color.g = 0.0
        marker.color.b = 0.0
        #marker.location=Duration(sec=0)

        self._orange_marker_pub(marker)


def main(args=None):
    rclpy.init(args=args)
    node = ArmCameraLocalizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
