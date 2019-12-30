import numpy as np

from collections import namedtuple

# Align diffractometer to beam and align robot to spinner
# Get spinner coords in diffractometer frame and calculate in xyz frame (spin_dxyz)
# Get gripper coordinates in xyz frame (grip_xyz)
# Calculate diffractometer 0 (in xyz frame) diff0_xyz = grip_xyz - spin_dxyz
# Specify offset of beam wrt to top of brass pin
# Calculate beam_xyz = grip_xyz + beam_offset
# Write diff0_xyz, beam_diff_offset and spin_dxyz to file

# beam_xyz - diff0_xyz (= beam_diff_offset) should be constant. This provides a check whether diff0 has moved.


# Align diffractometer to beam
# Get spinner coords in diffractometer frame and calculate in xyz frame (spin_dxyz)
# Calculate absolute postion of spinner from diff0_xyz: new_grip_xyz = diff0_xyz + spin_dxyz
# Check beam_diff_offset still consistent: ((spin_dxyz + diff0_xyz) + beam_offset) == beam_diff_offset

CoordsXYZ = namedtuple('CoordsXYZ', ['x', 'y', 'z'])


def diffr_pos_to_xyz(samx, samy, samz, om, diffh, diffv, rotate_sense=1):
    """
    Converts the diffractometer axis positions to xyz equivalents in mm.
    Results are rounded to the nearest micron.

    Parameters
    ----------
    samx : float
    Sample goniometer X axis position in mm
    samy : float
    Sample goniometer Y axis position in mm
    samz : float
    Sample goniometer Z axis position in mm
    om : float
    Sample omega axis position in degrees
    diffh : float
    Diffractometer horizontal axis position in mm
    diffv : float
    Diffractometer vertical axis position in mm
    rotate_sense : int
    Sense of rotation. Should have a value of 1 (clockwise) or -1 (counter-
    clockwise)

    Returns
    -------
    spinner_coords : tuple of ints
    The spinner cartesian coordinates as a tuple (shape (3,1)) in mm
    """
    spin_x = np.round(samx + diffh, 3)
    spin_y = np.round((samy * np.cos(np.radians((rotate_sense * -om)))
                       - samz * np.sin(np.radians((rotate_sense * -om)))
                       ) + diffv, 3)
    spin_z = np.round((samy * np.sin(np.radians((rotate_sense * -om)))
                       + samz * np.cos(np.radians((rotate_sense * -om)))
                       ), 3)

    return CoordsXYZ(spin_x, spin_y, spin_z)

# Martin's original algorithm to calculate spinner position. It's wrong, but
# might be useful.
# spin_x = diffh + samx
# spin_y = diffv * np.cos(np.radians(-om)) + samy
# spin_z = diffv * np.sin(np.radians(-om)) + samz
