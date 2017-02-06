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
import json
import datetime as dt


DHD_HLP = 2.56  # SAP Heat loss parameter. Total heat loss / total floor area. [W/(m^2 K)]
# DHD_HLP = 5  # SAP Heat loss parameter. Total heat loss / total floor area. [W/(m^2 K)]

# Simulation setup. SET THESE VALUES.
N_ITERATIONS = 24 * 60 * 60  # on for a day
START_TEMP = 20.0  # [C]
OUTSIDE_TEMP = 0.0  # [C]
RADIATOR_TEMP = np.array([60.0 if (x < 20 * 60) else 0.0 for x in range(N_ITERATIONS)])  # [C]
ROOM_SIZE = (3.0, 5.0, 2.3)  # w, l, h. Assumes room is cuboid. [m]

# Physical constants.
DENSITY_AIR = 1.205  # Density of air at 20 C, 1 Atm. [Kg/m^3]
Cp_AIR = 1005.0  # The constant pressure specific heat capacity of air at 20 C, 1 Atm [J Kg/K]


VOLUME = ROOM_SIZE[0] * ROOM_SIZE[1] * ROOM_SIZE[2]  # Volume of room. [m^3]
C_AIR = DENSITY_AIR * VOLUME * Cp_AIR  # Heat capacity of air in the room. [J/K]
WALL_CONDUCTANCE = ROOM_SIZE[0] * ROOM_SIZE[1] * DHD_HLP  # Thermal conductance based on DHD's SAP
print("Thermal Conductance: {0:.0f} W/K\nHeat Capacity: {1:.0f} kJ/K".format(WALL_CONDUCTANCE, C_AIR / 1000.0))


def get_valve_data(file):
    with open(file, 'r') as f:
        raw_valve_data = f.readlines()
    decoded_valve_data = [json.loads(x) for x in raw_valve_data]
    # valve_ids = list(set((x[2]['@'] for x in decoded_valve_data)))
    # print(valve_ids[0])
    # filtered_valve_data = [x for x in decoded_valve_data if x[2]['@'] == valve_ids[0]]
    filtered_valve_data = [x for x in decoded_valve_data if x[2]['@'] == "96F0CED3B4E690E8"]
    raw_temps = [(x[0], x[2]['T|C16']/16.0) for x in filtered_valve_data if 'T|C16' in x[2]]
    raw_valve_pc = [(x[0], x[2]['H|%']) for x in filtered_valve_data if 'H|%' in x[2]]
    temperatures = []
    valve_open_pc = []
    # Convert date time into seconds.
    for line in raw_temps:
        stripped_date = line[0].replace('T', ' ').replace('Z', '')
        decoded_time = dt.datetime.strptime(stripped_date, "%Y-%m-%d %H:%M:%S")
        temperatures.append((decoded_time, line[1]))
    for line in raw_valve_pc:
        stripped_date = line[0].replace('T', ' ').replace('Z', '')
        decoded_time = dt.datetime.strptime(stripped_date, "%Y-%m-%d %H:%M:%S")
        valve_open_pc.append((decoded_time, line[1]))
    start_time = temperatures[0][0] if temperatures[0][0] < valve_open_pc[0][0] else valve_open_pc[0][0]
    temperatures = [((x[0] - start_time).total_seconds(), x[1]) for x in temperatures]
    valve_open_pc = [((x[0] - start_time).total_seconds(), x[1]) for x in valve_open_pc]
    temp = [None] * N_ITERATIONS
    open_pc = [None] * N_ITERATIONS
    for x in temperatures:
        i = int(x[0])
        if i > N_ITERATIONS:
            break
        temp[i] = x[1]
    for x in valve_open_pc:
        i = int(x[0])
        if i > N_ITERATIONS:
            break
        open_pc[i] = x[1]
    for i in range(N_ITERATIONS):
        if temp[i] is None:
            temp[i] = temp[i-1]
        if open_pc[i] is None:
            open_pc[i] = open_pc[i-1]
    return np.array(temp), np.array(open_pc)

valve_room_temps, valve_open_pc = get_valve_data("201701.json")


def calc_heat_in_radiator(room_temp, radiator_temp):
    """ Heat transfer into the room via the radiator.

    Assume radiator temperature independent of heat transfer.

    :param room_temp: [C]
    :param radiator_temp: [C]
    :return: [J]
    """
    conductance = 25  # thermal conductance [W/K]
    temp = 2 * radiator_temp - 80.0

    return (temp - room_temp) * conductance  # assuming 1 kW heat input with room at 20 C [1000 / (60 - 20)]


def calc_heat_loss_walls(room_temp, outside_temp):
    """ Get the heat loss through the walls, floor and ceiling this iteration.

    Assume outside is the same temp for all walls.

    :param room_temp: [C]
    :param outside_temp: [C]
    :return: [J]
    """
    return (outside_temp - room_temp) * WALL_CONDUCTANCE


def calc_heat_storage(room_temp, storage_temp):
    """ Calculate the amount of heat stored/released by things in the room, other than the air mass.

    Assume everything can be lumped together into a single capacitance/resistance.

    :param room_temp: [C]
    :param storage_temp: [C]
    :return: [J]  # todo fix this currently returns temp.
    """
    conductance = 1.0
    capacitance = 100000000.0
    return storage_temp + (((room_temp - storage_temp) * conductance) / capacitance)  # todo fix this


def calc_temp(room_temp, *args):
    """ Calculate the new room temperature

    Assume entire room heats up instantly and evenly.

    :param room_temp: Current room temperature. [C]
    :param args: Heat flow into room (note! +ve is heat source, -ve is heat sink). [J]
    :return: New room temperature. [C]
    """
    return room_temp + (1.0 / C_AIR) * sum(args)


room_temps = np.array([START_TEMP for _ in range(N_ITERATIONS)])
heat_in = np.zeros(N_ITERATIONS)
heat_out = np.zeros(N_ITERATIONS)
heat_stored = np.array([START_TEMP for _ in range(N_ITERATIONS)])  # todo fix this


for i in range(N_ITERATIONS):
    # rad_temp = room_temps[i-1] if RADIATOR_TEMP[i] == 0.0 else RADIATOR_TEMP[i]
    heat_in[i] = calc_heat_in_radiator(room_temps[i - 1], valve_open_pc[i - 1])
    heat_out[i] = calc_heat_loss_walls(room_temps[i - 1], OUTSIDE_TEMP)
    heat_stored[i] = calc_heat_storage(room_temps[i - 1], heat_stored[i - 1])
    # print(bar)
    room_temps[i] = calc_temp(room_temps[i-1],
                              heat_in[i-1],
                              heat_out[i-1],
                              (heat_stored[i - 2] - heat_stored[i - 1]) * 1000000.0)  # todo fix this

# Print final temp and total energy use.
print("Final Temp: {0:.2f} C\nEnergy Use: {1:.2f} kJ\nEnergy Loss: {2:.2f} kJ".format(room_temps[-1],
                                                                                      sum(heat_in) / 1000.0,
                                                                                      sum(heat_out) / 1000.0))

# # Print per iteration values.
# for i in range(len(room_temps)):
#     if i % 60 == 0:
#         print("{}\t| T:{:.2f}\tQ:{:.2f}\tQin:{:.2f}\tQout:{:.2f} ".format(i // 60,
#                                                                           room_temps[i],
#                                                                           bar[i] * 1000.0,
#                                                                           heat_in[i],
#                                                                           heat_out[i]))
x = np.array(range(N_ITERATIONS))
heat_in /= 1000.0
heat_out /= 1000.0
net_heat = heat_in + heat_out
# heat_stored = room_temps * C_AIR / 1000.0
# plot_valve_temps = valve_room_temps[valve_room_temps[:, 0] < N_ITERATIONS]
# plot_valve_pc = valve_open_pc[valve_open_pc[:, 0] < N_ITERATIONS]
plt.subplot(3, 1, 1)
plt.plot(x, room_temps, label="sim temp C")
plt.plot(x, valve_room_temps, label="valve temp C")
plt.legend()
plt.subplot(3, 1, 2)
plt.plot(x, heat_in, label="heat input kJ")
plt.plot(x, heat_out, label="heat loss kJ")
plt.plot(x, net_heat, label="net heat flow kJ")
plt.legend()
plt.subplot(3, 1, 3)
plt.plot(x, valve_open_pc, label="valve opening %")
plt.legend()
plt.show()
