from pg3d_scripts import pg3d as engine
import numpy as np
import pygame as pg
from pg3d_scripts.pg3d import Color

# This is an example of how to use the PG3D engine to make a platformer.
# Feel free to either use this script as a starting point for your own projects or start from scratch!
# (make sure to read README.md for what functions to use when getting started from scratch)

# This script is set up to call the main() function immediately (see the last line), and all code runs inside main().
def main():
    # Always start the engine by calling pg3d.init(). Pass in the render resolution, screen resolution, and VERTICAL fov.
    engine.init(200,150,800,600, 70)

    ping_sound = pg.mixer.Sound('ping.wav')

    engine.setBackgroundMode("skybox")
    # You can change the background color of the game with this function:
    engine.setBackGroundColor(0,100,200)
    # We're making it a fairly neutral blue color.
    
    # PG3D has backface culling enabled by default, we want to change that so that coins and collectibles render from both sides.
    engine.disableBackfaceCulling()
    # It also has the "texture" rendering mode on by default, which we want.

    # Something to note: objects cannot have the same name!

    # spawning a row of platforms
    platformCount = 5
    for i in range(platformCount):
        engine.spawnObjectWithTexture('3d models/platform/platform.obj','3d models/platform/platform_texture.png',"platform" + str(i+1), 0.0 + i * 15,0.0,0.0, [], Color.green)
        engine.getObject("platform" + str(i+1)).add_box_collider(10.0,1.0,10.0)
        engine.getObject("platform" + str(i+1)).set_scale(5.0,1.0,5.0)

    engine.spawnObjectWithTexture('3d models/coin/coin.obj','3d models/coin/coin_texture.png',"coin", 0.0 + 15 * 4,2.0,0.0, [], Color.white)
    engine.getObject("coin").set_scale(2,2,2)
    # add a trigger so that we can detect when the coin is picked up
    engine.getObject("coin").add_box_trigger(2.0,2.0,2.0)
    engine.getObject("coin").setAsTransparent()

    # interact tag so it works with trigger colliders
    engine.spawnCube("cube", 0.0, 50.0, 0.0, ["physics","interact","gravity"])
    engine.getObject("cube").add_box_collider(2.0,2.0,2.0)

    # For the player object, we want it to be invisible so it doesn't block the camera.
    # It's possible to do this by giving it an all-black texture, which the game treats as transparent,
    # but for performance reasons it's better to just call hide() on the object.
    engine.getObject("cube").hide()

    engine.parentCameraWithName("cube",0.0,4.0,0.0)

    engine.enablePhysics()
    engine.enableParticles()

    running = True
    while running:
        frame = engine.getFrame()
        engine.drawScreen(frame)

        playerObj = engine.getObject("cube")

        # handle main events (quit, basically)
        
        # TODO: maybe get the engine to do more of the event handling?
        for event in pg.event.get():
            if event.type == pg.QUIT: running = False
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE: running = False

            if event.type == pg.JOYDEVICEADDED: engine.connectJoystick(event)

        # (annoyingly) MUST CALL update() AFTER getFrame() and drawScreen()!
        # also, I'm pretty sure, call it befwore any camera update functions
        engine.update()

        # make sure there actually IS a coin
        if (engine.getObject("coin") != None):
            engine.getObject("coin").rotate(0.1, np.asarray([0.0,1.0,0.0]))

            if (engine.getObject("coin").is_triggered_cheap()):
                engine.setBackGroundColor(255,255,255)
                # we picked up the coin, so remove it
                engine.destroyObjectWithName("coin")
                pg.mixer.Sound.play(ping_sound)

        # A lot of games use a first person camera controller, so PG3D has that as a built-in feature.
        # All you have to do is parent the camera to an object (the object represents the player) which we did above,
        # and then call updateCamera_firstPerson() to handle movement and all that.
        engine.updateCamera_firstPerson(10, 1, True)

    engine.quit()

main()