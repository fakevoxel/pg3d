from . import pg3d_utils as utils
from . import pg3d as engine
import numpy as np
import pygame as pg

# TODO: the entire particle system

# basically the way i'm doing the particle system is this:

# particle managers control the spawning/transforming/deleting of the objects in a particle system
# each manager has a hashcode, which is applied as a tag to the objects it controls so everyone knows what belongs to what

# particle managers are NOT objects, and DO NOT CORRESPOND to an object! they are separate and held in a separate list!

# also for now particles aren't looping animations, they're more like explosions and such

class ParticleManager:  
    # separate registry for particle managers
    _registry = []
    

    def __init__(self, name, count, position, useGravity, texture_path, animationFrames, timeBetweenFrames, destroyWhenFinish):
        # we create a string of random numeric characters, of length 24 (random long-enough number that i picked)
        # the hash to apply to spawned objects
        # the particle objects are still kept track of though
        self.hash = utils.random_number_string(24)

        self.name = name

        # each particle manager has some parameters that affect the effect
        self.objectCount = count
        self.useGravity = useGravity

        self.position = position

        self._registry.append(self)

        self.spawnedObjects = []

        self.texture_path = texture_path

        self.vX = 0
        self.vY = 0
        self.vZ = 0

        self.lookAtPlayer = True

        self.animationFrames = animationFrames
        self.timeBetweenFrames = timeBetweenFrames

        self.destroyWhenFinish = destroyWhenFinish

    # play the particle
    def play(self):
        for i in range(self.objectCount):
            # spawn the object and append it to the list
            
            # animation stuff
            if (self.timeBetweenFrames > 0):
                # use the first frame as the texture
                newParticle = engine.spawnPlaneWithTexture("particle object", self.position[0],self.position[1],self.position[2], 5,5,5, ["particle",self.hash,"animated"], self.animationFrames[0])
                if (self.useGravity):
                    newParticle.add_tag("gravity")
                if (self.lookAtPlayer):
                    newParticle.add_tag("lookAtPlayer")

                newParticle.add_data("current_frame_index",0)
                newParticle.add_data("animation_frames",self.animationFrames)
                # in milliseconds
                newParticle.add_data("time_between_frames",self.timeBetweenFrames)
                # the time when we reached the last frame
                newParticle.add_data("last_frame_time",pg.time.get_ticks())

                newParticle.add_data("destroy_when_finish",self.destroyWhenFinish)
            else:
                # no frames, or any other animation data
                newParticle = engine.spawnPlaneWithTexture("particle object", self.position[0],self.position[1],self.position[2], 5,5,5, ["particle",self.hash], self.texture_path)
                if (self.useGravity):
                    newParticle.add_tag("gravity")
                if (self.lookAtPlayer):
                    newParticle.add_tag("lookAtPlayer")

            newParticle.setAsTransparent()
                
            self.spawnedObjects.append(newParticle)
            # particles will always look at the camera
            newParticle.set_local_up(engine.cameraWorldTransform.position - self.position)
            newParticle.set_velocity(self.vX,self.vY,self.vZ)
