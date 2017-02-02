"""
Basic model of a room with a radiator.

All specific enthalpies within room are lumped as one value.
All sources of heat loss are lumped as one value.
Assumed that room is only heated by the radiator.

heat_in => heat_stored => heat out.
Gives basic equation
stored_heat = start_heat + (in_heat + out_heat) [Q_room = Q_start + Q_rad + Q_loss]

"""
import numpy as np
import matplotlib.pyplot as plt


# Simulation setup. SET THESE VALUES.
N_ITERATIONS = 4 * 60 * 60  # on for 20 minutes
START_TEMP = 20.0  # [C]
OUTSIDE_TEMP = 0.0  # [C]
RADIATOR_TEMP = np.array([60.0 if (x < 20 * 60) else 0.0 for x in range(N_ITERATIONS)])  # [C]
ROOM_SIZE = (3.0, 5.0, 2.3)  # w, l, h. Assumes room is cuboid. [m]

# The R(SI) value of the room (resistance to heat transfer).
# Equivalent of 1/U-value. Using R value as easier to combine.
# From U-value of 0.8, given by DHD as typical for poorly insulated house.
# R_WALLS = 0.1  # [K m^2/W]
R_WALLS = 1.25  # [K m^2/W]
# R_WALLS = 10.0  # [K m^2/W]

# Physical constants.
DENSITY_AIR = 1.205  # Density of air at 20 C, 1 Atm. [Kg/m^3]
Cp_AIR = 1005.0  # The constant pressure specific heat capacity of air at 20 C, 1 Atm [J Kg/K]


# Surface area enclosing room. [m^2]
SURFACE_AREA = (ROOM_SIZE[0] * ROOM_SIZE[1] +
                ROOM_SIZE[0] * ROOM_SIZE[2] +
                ROOM_SIZE[1] * ROOM_SIZE[2]) * 2.0
VOLUME = ROOM_SIZE[0] * ROOM_SIZE[1] * ROOM_SIZE[2]  # Volume of room. [m^3]

C_AIR = DENSITY_AIR * VOLUME * Cp_AIR  # Heat capacity of air in the room. [J/K]
# C_AIR = DENSITY_AIR * VOLUME * Cp_AIR + 40000 # Naively adding thermal capacitance to represent extra objects fails.
WALL_CONDUCTANCE = SURFACE_AREA * (1.0 / R_WALLS)  # Thermal conductance of room walls. Equivalent to U-value [W/K]


print("Surface Area: {0:.2f} m^2\nVolume: {1:.2f} m^3".format(SURFACE_AREA, VOLUME))
print("Thermal Conductance: {0:.0f} W/K\nHeat Capacity: {1:.0f} kJ/K".format(WALL_CONDUCTANCE, C_AIR / 1000.0))


def heat_in_radiator(room_temp, radiator_temp):
    """ Heat transfer into the room via the radiator.

    Assume radiator temperature independent of heat transfer.

    :param room_temp: [C]
    :param radiator_temp: [C]
    :return: [J]
    """
    conductance = 25  # thermal conductance [W/K]
    return (radiator_temp - room_temp) * conductance  # assuming 1 kW heat input with room at 20 C [1000 / (60 - 20)]


def heat_loss_walls(room_temp, outside_temp):
    """ Get the heat loss through the walls, floor and ceiling this iteration.

    Assume outside is the same temp for all walls.

    :param room_temp: [C]
    :param outside_temp: [C]
    :return: [J]
    """
    return (outside_temp - room_temp) * WALL_CONDUCTANCE


def calc_temp(room_temp, *args):
    """ Calculate the new room temperature

    Assume entire room heats up instantly and evenly.

    :param room_temp: Current room temperature. [C]
    :param args: Heat flow into room (note! +ve is heat source, -ve is heat sink). [J]
    :return: New room temperature. [C]
    """
    return room_temp + (1.0 / C_AIR) * sum(args)


def foo(room_temp, foo_temp):
    conductance = 100
    capacitance = 1000000.0
    return foo_temp + (((room_temp - foo_temp) * conductance) / capacitance)

bar = np.array([START_TEMP for _ in range(N_ITERATIONS)])
room_temps = np.array([START_TEMP for _ in range(N_ITERATIONS)])
heat_in = np.zeros(N_ITERATIONS)
heat_out = np.zeros(N_ITERATIONS)

for i in range(N_ITERATIONS):
    rad_temp = room_temps[i-1] if RADIATOR_TEMP[i] == 0.0 else RADIATOR_TEMP[i]
    heat_in[i] = heat_in_radiator(room_temps[i-1], rad_temp)
    heat_out[i] = heat_loss_walls(room_temps[i-1], OUTSIDE_TEMP)
    bar[i] = foo(room_temps[i-1], bar[i-1])
    # print(bar)
    room_temps[i] = calc_temp(room_temps[i-1],
                              heat_in[i-1],
                              heat_out[i-1],
                              (bar[i-2]-bar[i-1]) * 1000000.0)

# Print final temp and total energy use.
print("Final Temp: {0:.2f} C\nEnergy Use: {1:.2f} kJ\nEnergy Loss: {2:.2f} kJ".format(room_temps[-1],
                                                                                      sum(heat_in) / 1000.0,
                                                                                      sum(heat_out) / 1000.0))

# Print per iteration values.
for i in range(len(room_temps)):
    if i % 60 == 0:
        print("{}\t| T:{:.2f}\tQ:{:.2f}\tQin:{:.2f}\tQout:{:.2f} ".format(i // 60,
                                                                          room_temps[i],
                                                                          bar[i] * 1000.0,
                                                                          heat_in[i],
                                                                          heat_out[i]))
x = np.array([x / 60.0 for x in range(N_ITERATIONS)])
heat_in /= 1000.0
heat_out /= 1000.0
net_heat = heat_in + heat_out
# heat_stored = room_temps * C_AIR / 1000.0
plt.subplot(2, 1, 1)
plt.plot(x, room_temps, label="air temp C")
plt.plot(x, bar, label="heat stored kJ")
plt.legend()
plt.subplot(2, 1, 2)
plt.plot(x, heat_in, label="heat input kJ")
plt.plot(x, heat_out, label="heat loss kJ")
plt.plot(x, net_heat, label="net heat flow kJ")
plt.legend()
plt.show()
