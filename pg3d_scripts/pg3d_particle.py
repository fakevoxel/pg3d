from . import pg3d_utils as utils

# TODO: the entire particle system

# basically the way i'm doing the particle system is this:

# particle managers control the spawning/transforming/deleting of the objects in a particle system
# each manager has a hashcode, which is applied as a tag to the objects it controls so everyone knows what belongs to what

# particle managers are NOT objects, and DO NOT CORRESPOND to an object! they are separate and held in a separate list!

class ParticleManager:  
    # separate registry for particle managers
    _registry = []

    hash = ""

    # each particle manager has some parameters that affect the effect
    

    def __init__(self):
        # we create a string of random numeric characters, of length 24 (random long-enough number that i picked)
        hash = utils.random_number_string(24)

        self._registry.append(self)