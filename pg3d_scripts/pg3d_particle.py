from . import pg3d_utils as utils
from . import pg3d as engine
import numpy as np
import pygame as pg
import random
from . import pg3d_math as m

# TODO: the entire particle system

# basically the way i'm doing the particle system is this:

# particle managers control the spawning/transforming/deleting of the objects in a particle system
# each manager has a hashcode, which is applied as a tag to the objects it controls so everyone knows what belongs to what

# particle managers are NOT objects, and DO NOT CORRESPOND to an object! they are separate and held in a separate list!

# also for now particles aren't looping animations, they're more like explosions and such

class ParticleManager:  
    # separate registry for particle managers
    _registry = []
    
    # ALL PARTICLES ARE PLANES, ALWAYS
    # (might change this later)

    # time_between_frames is in milliseconds! (it reduces math)
    # life_time is too! (same reason)
    # also, this might be the most arguments I've ever put in a function/constructor
    def __init__(self, name, min_object_count, max_object_count, min_scale, max_scale, position, use_gravity, texture_path, animation_frames, time_between_frames, destroy_when_finish, loop_animation, velocity_direction, min_velocity_magnitude, max_velocity_magnitude, direction_offset_angle, drag_multiplier, scale_change, min_life_time, max_life_time):
        # there WAS a hashcode, but im not doing that because I can just keep track of the objects in a list
        # there was a chance that the hashes could have repeated anyways

        self.name = name

        # each particle manager has some parameters that affect the effect
        self.min_object_count = min_object_count
        self.max_object_count = max_object_count
        self.useGravity = use_gravity

        self.min_scale = min_scale
        self.max_scale = max_scale

        self.position = position

        self._registry.append(self)

        self.spawnedObjects = []

        self.texture_path = texture_path

        self.velocity_direction = m.normalize_3d(velocity_direction)
        self.min_velocity_magnitude = min_velocity_magnitude
        self.max_velocity_magnitude = max_velocity_magnitude

        self.lookAtPlayer = True

        self.animationFrames = animation_frames
        self.timeBetweenFrames = time_between_frames

        # if destroy_when_finish is true, the particle will destroy itself as soon as the animation finishes playing
        # if not, then it depends:
        # if loop_animation is true, it will just restart
        # if loop_animation is false, it will just stay at the last frame

        # so setting both to false will mean the particle just stays
        self.destroyWhenFinish = destroy_when_finish 
        self.loop_animation = loop_animation

        # when this runs out, regardless of whether the particle is animated or not,
        # it will destroy itself
        # a value of -1 is treated as infinite life,
        # in which case it'll either stick around or wait until the animation is finished playing
        self.max_life_time = max_life_time
        self.min_life_time = min_life_time # we have a max/min because it'll be a random range, like velocity magnitude

        self.direction_offset_angle = direction_offset_angle # currently doesn't do anything :(
        # TODO: figure out how to rotate a vector given ONLY that vector

        # what fraction of the velocity to subtract every update
        # 0 does nothing
        self.drag_multiplier = drag_multiplier

        # what to add to the scale every update
        # 0 does nothing
        self.scale_change = scale_change

    # play the particle system
    # aka spawn all the particles

    # there's not a TON of logic here, most of that is actually in pg3d.update() (engine.update())
    def play(self):
        objectCount = random.random(self.min_object_count, self.max_object_count)
        for i in range(objectCount):
            # spawn the object and append it to the list
            
            objScale = random.random(self.min_scale, self.max_scale)

            # animation stuff
            if (self.timeBetweenFrames > 0):
                # use the first frame as the texture
                newParticle = engine.spawnPlaneWithTexture("particle object", self.position[0],self.position[1],self.position[2], objScale,objScale,objScale, ["particle","animated"], self.animationFrames[0])
                if (self.useGravity):
                    newParticle.add_tag("gravity")

                # for now all particles look at the player
                # why wouldn't they, right?
                if (self.lookAtPlayer):
                    newParticle.add_tag("lookAtPlayer")

                newParticle.add_data("current_frame_index",0)
                newParticle.add_data("animation_frames",self.animationFrames)
                # in milliseconds
                newParticle.add_data("time_between_frames",self.timeBetweenFrames)
                # the time when we reached the last frame
                newParticle.add_data("last_frame_time",pg.time.get_ticks())

                newParticle.add_data("destroy_when_finish",self.destroyWhenFinish)
                newParticle.add_data("loop_animation",self.loop_animation)
            else:
                # no frames, or any other animation data
                newParticle = engine.spawnPlaneWithTexture("particle object", self.position[0],self.position[1],self.position[2], 5,5,5, ["particle"], self.texture_path)
                if (self.useGravity):
                    newParticle.add_tag("gravity")

                # for now all particles look at the player
                # why wouldn't they, right?
                if (self.lookAtPlayer):
                    newParticle.add_tag("lookAtPlayer")

            newParticle.setAsTransparent()

            lifeTime = random.random(self.min_life_time, self.max_life_time)
            newParticle.add_data("life_time",lifeTime)
            newParticle.add_data("time_when_spawned",pg.time.get_ticks())

            if (self.scale_change != 0):
                # stuff about the particle that'll change over time
                newParticle.add_data("scale_change",self.scale_change)
                # the tag is so that the update() function can more easily check
                newParticle.add_tag("scaleChange")
            if (self.drag_multiplier != 0):
                newParticle.add_data("drag_multiplier",self.drag_multiplier)
                # the tag is so that the update() function can more easily check
                newParticle.add_tag("hasDrag")
                
            self.spawnedObjects.append(newParticle)
            # particles will always look at the camera
            newParticle.set_local_up(engine.cameraWorldTransform.position - self.position)

            # applying velocity to the particle
            velocityMagnitude = random.random(self.min_velocity_magnitude, self.max_velocity_magnitude)
            newParticle.set_velocity(self.velocity_direction[0]*velocityMagnitude,self.velocity_direction[1]*velocityMagnitude,self.velocity_direction[2]*velocityMagnitude)
