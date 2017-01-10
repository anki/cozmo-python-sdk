# Cube and Charger images

This folder contains the images for the 3 cubes and the charger. These are provided as a courtesy for people who want to try unusual (and unsupported) experimentation with the SDK, as an alternative to you having to scan the images yourselves.

**WARNING**: Use these images at your own risk, there are many caveats around how the app and the engine expect to see these, and you will cause strange bugs to occur if you use them incorrectly.

1) The size, shape, and location on the object is critical. The size is used to calculate how far away the object is, so if you e.g. print it 2x the size then Cozmo will think it's closer than it really is. The shape is used to calculate rotation, so if you printed these askew they would appear to Cozmo as if the object was rotated.

2) Cozmo only expects to see 1 of each of the objects (1 of each cube type, and 1 charger), if Cozmo sees multiple images of the same type then it will confuse Cozmo and the resultant behavior is unspecified.