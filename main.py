import pg3d as engine
import numpy as np
import pygame as pg

# where the actual game-code is located

def main():
    # start the engine
    engine.init(800,600,np.pi / 4)

    # set the background color to blue
    engine.setBackGroundColor(0,0,255)

    # spawn a cube as the ground
    engine.spawnObjectWithTexture('assets/cube.obj','assets/grid_16.png',"ground", 0.0,0.0,0.0, ["box_collider"])
    engine.getObject("ground").set_scale(10,0.1,10)
    engine.getObject("ground").add_data("collider_bounds",np.array([20,0.2,20]))

    engine.spawnObjectWithTexture('assets/cube.obj','assets/grid_16.png',"block", 0.0,20.0,0.0, ["physics","box_collider"])
    # collider has the same size as the object (2m cube)
    engine.getObject("block").add_data("collider_bounds",np.array([2.0,2.0,2.0]))

    engine.moveCameraToObject(engine.getObject("block"), 0, 4, 0)

    engine.enablePhysics()

    running = True
    while running:
        # handle main events (quit, basically)
        for event in pg.event.get():
            if event.type == pg.QUIT: running = False
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE: running = False

        frame = engine.getFrame()
        engine.drawScreen(frame)

        pressed_keys = pg.key.get_pressed()
        playerObject = engine.getObject("block")

        engine.moveCameraToObject(playerObject, 0, 4, 0)

        if pressed_keys[ord('w')]:
            playerObject.add_position(0,0,1)
        if pressed_keys[ord('s')]:
            playerObject.add_position(0,0,-1)
        if pressed_keys[ord('d')]:
            playerObject.add_position(1,0,0)
        if pressed_keys[ord('a')]:
            playerObject.add_position(-1,0,0) 
        
        engine.rotateCamera()

        # (annoyingly) MUST CALL update() AFTER getFrame() and drawScreen()!
        engine.update()

    engine.quit()

main()