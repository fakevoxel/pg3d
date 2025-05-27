import pg3d as engine
import numpy as np
import pygame as pg

# where the actual game-code is located

def main():
    # start the engine
    engine.init(800,600,np.pi / 4)
    # set the background color to blue
    engine.setBackGroundColor(0,0,255)

    # spawn a cube as a test
    engine.spawnObject('assets/cube.obj','assets/grid_16.png',"cube", 0.0,0.0,0.0, [])
    engine.getObject("cube").set_scale(10,0.1,10)

    running = True
    while running:
        # handle main events (quit, basically)
        for event in pg.event.get():
            if event.type == pg.QUIT: running = False
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE: running = False

        engine.update()

        engine.moveCamera()
        engine.rotateCamera()

        frame = engine.getFrame()
        engine.drawScreen(frame)

    engine.quit()

main()