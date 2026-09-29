# Pixelbot Tablet

## Overview

This package allows running a drawing application on a tablet. Subdrawings are detected and send via a ROS2 topic in a specific format(list of stroke koordinates).

**Keywords:** drawing application, subdrawing detection and capturing, Pygame

### License

[![License: GPL-3.0](https://img.shields.io/badge/license-GPLv3-blue)](https://www.gnu.org/licenses/gpl-3.0.en.html)

The whole package is under GPL-3.0 License, see [LICENSE](https://github.com/RomainMaure/PixelBot/blob/main/LICENSE).

**Author:  
Affiliation:  
Maintainer:**

The [pixelbot_tablet] package has been tested under [ROS2 Jazzy Jalisco] on Ubuntu 22.04.??? This is research code, expect that it changes often and any fitness for a particular purpose is disclaimed.

## Installation

### Building from Source

#### Dependencies

- [Robot  Operating System (ROS2)](https://docs.ros.org/en/jazzy/index.html) (middleware for robotics).
- [Pygame-ce](https://www.pygame.org/docs/) (Python game developping library) for developping the drawing application running on the tablet
    ```
    sudo apt install python3-pygame-ce
    ```

#### Building

1) Copy this package in your ROS2 workspace (e.g. `~/ros2_ws/src`).

2) Build the package with colcon:
    ```
    cd ~/ros2_ws
    colcon build --packages-select pixelbot_tablet
    ```
## Usage

You can run the main node with:
```
ros2 run pixelbot_tablet draw_node
```
