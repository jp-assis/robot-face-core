# Robot Face Player

Small Python application that shows facial expressions in fullscreen using **pygame** and receives expression commands via **ROS 2** on the `/robot_face` topic.

Each expression is a sequence of `.jpg` images that form a simple animation.


## Dependencies

- [ROS 2](https://docs.ros.org/)
- `pygame` (pip)


## Expression folder structure

Expressions are read from a directory that contains one subfolder per expression:

```text
expressions/
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

Expressions are controlled through the `/robot_face` topic, which receives `std_msgs/msg/String` messages containing the expression name, e.g. `"happy"`, `"sad"`, `"blank"`.

### Example: publish command

Publish the `sad` expression **5 times** to `/robot_face`:

```bash
ros2 topic pub --times 5 /robot_face std_msgs/msg/String "data: 'sad'"
```