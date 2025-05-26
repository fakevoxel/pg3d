import pg3d as engine
import numpy as np
import pygame as pg

def main():
    # start the engine
    engine.init(400,300,np.pi / 4)
    # set the background color to blue
    engine.setBackGroundColor(0,0,255)

    engine.spawnObject('assets/cube.obj','assets/grid_16.png',"ground", 0.0,0.0,0.0, ["collider"])
    #engine.getObject("ground").set_scale(5.0,0.1,5.0)

    #engine.spawnObject('assets/cube.obj','assets/grid_16.png',"test cube", 0.0,4.0,0.0, ["physics","collider"])

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