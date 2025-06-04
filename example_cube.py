from pg3d_scripts import pg3d as engine
import numpy as np
import pygame as pg
from pg3d_scripts.pg3d import Color
from pg3d_scripts.pg3d import Vector3
from pg3d_scripts.pg3d import Rotation
from pg3d_scripts.pg3d_model import Model

# This is an example of how to use the PG3D engine to make a platformer.
# Feel free to either use this script as a starting point for your own projects or start from scratch!
# (make sure to read README.md for what functions to use when getting started from scratch)

# This script is set up to call the main() function immediately (see the last line), and all code runs inside main().
def main():
    # Always start the engine by calling pg3d.init(). Pass in the render resolution, screen resolution, and VERTICAL fov.
    engine.init(200,150,800,600, 70)

    engine.setBackgroundMode("solid color")
    # You can change the background color of the game with this function:
    engine.setBackGroundColor(0,100,200)
    # We're making it a fairly neutral blue color.

    engine.setRenderingMode("texture")
    
    # PG3D has backface culling enabled by default, we want to change that so that coins and collectibles render from both sides.
    engine.disableBackfaceCulling()
    # It also has the "texture" rendering mode on by default, which we want.

    # Something to note: objects cannot have the same name!

    # interact tag so it works with trigger colliders
    engine.spawnCube("cube", 0.0, 0.0, 0.0, [])

    engine.spawnCube("cube 2", 0.0, 2.0, 0.0, []).set_scale(2,2,2)

    engine.getObject("cube 2").setParent(engine.getObject("cube"))

    running = True
    while running:
        frame = engine.getFrame()
        engine.drawScreen(frame)

        # handle main events (quit, basically)
        for event in pg.event.get():
            if event.type == pg.QUIT: running = False
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE: running = False

        # (annoyingly) MUST CALL update() AFTER getFrame() and drawScreen()!
        # also, I'm pretty sure, call it befwore any camera update functions
        engine.update()

        # A lot of games use a first person camera controller, so PG3D has that as a built-in feature.
        # All you have to do is parent the camera to an object (the object represents the player) which we did above,
        # and then call updateCamera_firstPerson() to handle movement and all that.
        engine.updateCamera_freecam(10)

    engine.quit()

main()