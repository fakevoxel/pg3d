import pg3d as engine
import numpy as np
import pygame as pg
from pg3d import Color

# This is an example of how to use the PG3D engine to make a platformer.
# Feel free to either use this script as a starting point for your own projects or start from scratch!
# (make sure to read README.md for what functions to use when getting started from scratch)

# This script is set up to call the main() function immediately (see the last line), and all code runs inside main().
def main():
    # start the engine
    engine.init(200,150,800,600, 70)

    # You can change the background color of the game with this function:
    engine.setBackGroundColor(0,100,200)
    # We're making it a fairly neutral blue color.
    
    # PG3D has backface culling enabled by default, so we don't need to change that.
    # It also has the "texture" rendering mode on by default, which we want.

    # spawning a row of platforms
    platformCount = 5
    for i in range(platformCount):
        engine.spawnObjectWithTexture('3d models/platform.obj','3d models/platform_texture.png',"platform" + str(i+1), 0.0 + i * 15,0.0,0.0, ["box_collider"], Color.green)
        engine.getObject("platform" + str(i+1)).add_data("collider_bounds",np.asarray([10.0,1.0,10.0]))
        engine.getObject("platform" + str(i+1)).set_scale(5.0,1.0,5.0)

    engine.spawnCube(0.0, 5.0, 0.0, ["physics","box_collider"])
    engine.getObject("cube").add_data("collider_bounds",np.asarray([2.0,2.0,2.0]))

    engine.parentCamera("cube",0.0,4.0,0.0)

    engine.enablePhysics()

    running = True
    while running:
        frame = engine.getFrame()
        engine.drawScreen(frame)

        playerObj = engine.getObject("cube")

        # handle main events (quit, basically)
        for event in pg.event.get():
            if event.type == pg.QUIT: running = False
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE: running = False

            # jumping
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE: 
                playerObj.add_position(0.0,0.1,0.0)
                playerObj.add_velocity(0.0,10.0,0.0)

        # A lot of games use a first person camera controller, so PG3D has that as a built-in feature.
        # All you have to do is parent the camera to an object (the object represents the player) which we did above,
        # and then call updateCamera_firstPerson() to handle movement and all that.
        engine.updateCamera_firstPerson(4)

        # (annoyingly) MUST CALL update() AFTER getFrame() and drawScreen()!
        engine.update()

    engine.quit()

main()