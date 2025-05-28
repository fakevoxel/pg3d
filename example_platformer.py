import pg3d as engine
import numpy as np
import pygame as pg
from pg3d import Color

# where the actual game-code is located

def main():
    # start the engine
    engine.init(800,600,70)

    # set the background color to blue
    engine.setBackGroundColor(0,100,200)
    # might disable this later
    engine.disableBackfaceCulling()

    engine.spawnObjectWithTexture('3d models/platform.obj','3d models/platform_texture.png',"platform", 0.0,0.0,0.0, ["box_collider"], Color.orange)
    engine.getObject("platform").add_data("collider_bounds",np.asarray([10.0,1.0,10.0]))
    engine.getObject("platform").set_scale(5.0,1.0,5.0)

    engine.spawnCube(0.0, 5.0, 0.0, ["physics","box_collider"])
    engine.getObject("cube").add_data("collider_bounds",np.asarray([2.0,2.0,2.0]))

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
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE: 
                playerObj.add_position(0.0,0.1,0.0)
                playerObj.add_velocity(0.0,10.0,0.0)

        pressed_keys = pg.key.get_pressed()

        moveSpeed = 0.2
        
        if pressed_keys[ord('w')]:
            playerObj.add_position(0.0,0.0,1.0 * moveSpeed)
        elif pressed_keys[ord('s')]:
            playerObj.add_position(0.0,0.0,-1.0 * moveSpeed)
        if pressed_keys[ord('a')]:
            playerObj.add_position(1.0 * moveSpeed,0.0,0.0)
        elif pressed_keys[ord('d')]:
            playerObj.add_position(-1.0 * moveSpeed,0.0,0.0)

        engine.moveCameraToObject(engine.getObject("cube"), 0, 4, 0)
        engine.updateCamera_firstPerson()

        # (annoyingly) MUST CALL update() AFTER getFrame() and drawScreen()!
        engine.update()

    engine.quit()

main()