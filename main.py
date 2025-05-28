import pg3d as engine
import numpy as np
import pygame as pg

# where the actual game-code is located

def main():
    # start the engine
    engine.init(800,600,45)

    # set the background color to blue
    engine.setBackGroundColor(0,100,200)

    engine.spawnObjectWithTexture('3d models/forest.obj','3d models/forest_texture.png',"tree", 0.0,0.0,0.0, [])
    engine.disableBackfaceCulling()

    running = True
    while running:
        # handle main events (quit, basically)
        for event in pg.event.get():
            if event.type == pg.QUIT: running = False
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE: running = False

        frame = engine.getFrame()
        engine.drawScreen(frame)

        engine.moveCamera()
        engine.rotateCamera()

        # (annoyingly) MUST CALL update() AFTER getFrame() and drawScreen()!
        engine.update()

    engine.quit()

main()