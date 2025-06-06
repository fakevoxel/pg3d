![alt text](https://github.com/fakevoxel/pg3d/blob/master/images/logo_new_big.png?)

This is my implementation of a 3D rendering engine in python, using PyGame and Numba (Numba is necessary in order to speed up the rendering functions).

### All information is as of version 0.1.1! Older/newer versions of this project may not agree with the README file.

# REQUIREMENTS:
For PG3D to run properly, you need the following:
(all versions here are the ones that have been tested, not necessarily the only ones that work)

- an up-to-date c++ installation (download from microsoft here: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)
(despite this being written in python, you need c++ because numba/numpy use c++)
- pygame 2.6.1 or newer (tested with 2.6.1)
(type "pip install pygame" in a terminal to install)
- numba 0.61.2 or newer (tested with 0.61.2)
(type "pip install numba" in a terminal to install)
- python 3.13 or newer (tested with 3.13.2)
- llvmlite 0.44.0 or newer (tested with 0.44.0)
(should be installed along with numba, double check the terminal output to make sure or type "pip list" to see all installed pip packages)

If you find other versions that work, or ones that don't, post an issue here on the github with the "compatibility" tag!

# How To Install:
1. download the **v0.1.zip** file from the releases page
2. copy the **pg3d.py** script, and the **assets** folder (these are assets that the engine needs to work), into your project
   (the **pg3d.py** script should be in the exact same directory as your game files so it can be imported properly)
   (the **example_platformer.py** script is not necessary, it's just an example script)
4. if you want, copy the **3d models** folder into your project too, this folder contains some example models that you can use (these aren't needed)
5. import **pg3d** in the script you want to reference the engine in
6. that's it! you can now call any functions you want from pg3d (see **How To Use** for what functions to use and how to use them)

# How To Use (the basics):
(this only explains the functions that are NECESSARY for the engine to run, there are many more that aren't mentioned)
1. call **pg3d.init()**, passing in the RENDER width (in pixels), RENDER height (in pixels), the SCREEN width (pixels), the SCREEN height (pixels) and the VERTICAL FOV of the camera (in degrees)
   (render width/height is how detailed the game should be and screen width/height is the resolution it will be scaled to)
   (make render w/h as large as you can without frame drops, and screen w/h the resolution of your actual display)
3. for every frame you want to render:
-  call **pg3d.getFrame()** to get the frame data, this will be an array of colors (r [0..255], g [0..255], b [0..255]) with dimensions [screenWidth x screenHeight]
-  make any changes you want to the array, then call **pg3d.drawScreen()**, passing the frame data as the only argument
3. after rendering a frame:
- call **pg3d.update()** to update any physics objects in the scene
4. when you want to quit your program:
- call **pg3d.quit()**, do NOT just call **pygame.quit()**
 
# Credits:
- triangular interpolation algorithm (barycentric coordinates) --> https://codeplea.com/triangular-interpolation
- original idea/rendering code --> https://www.youtube.com/watch?v=U2bPZLU3ntw&t=10s
- triangle clipping algorithm -- > https://gabrielgambetta.com/computer-graphics-from-scratch/11-clipping.html

# Features:
- textured .obj file rendering
- camera system
- built-in player controller (pg3d.updateCamera_firstPerson())
- basic object management (creation, destruction, transformation)
- box colliders
- trigger colliders
- (somewhat janky) physics engine

# Gallery:

![alt text](https://github.com/fakevoxel/pg3d/blob/master/images/sc_1.png?)
![alt text](https://github.com/fakevoxel/pg3d/blob/master/images/sc_2.png?)
