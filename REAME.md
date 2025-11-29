# Robot Face Player

Small Python application that shows facial expressions in fullscreen using **pygame** and receives mood commands via **ROS 2** on the `/robot_face` topic.

Each mood is a sequence of `.jpg` images that form a simple animation.


## Dependencies

- [ROS 2](https://docs.ros.org/)
- `pygame` (pip)


## Expression folder structure

Moods are read from a directory that contains one subfolder per expression:

```text
moods/
  blank/
    000.jpg
    001.jpg
    ...
  happy/
    000.jpg
    001.jpg
    ...
```

## Control via ROS 2

Moods are controlled through the `/robot_face` topic, which receives `std_msgs/msg/String` messages containing the mood name, e.g. `"happy"`, `"sad"`, `"blank"`.

### Example: publish command

Publish the `sad` mood **5 times** to `/robot_face`:

```bash
ros2 topic pub --times 5 /robot_face std_msgs/msg/String "data: 'sad'"
```