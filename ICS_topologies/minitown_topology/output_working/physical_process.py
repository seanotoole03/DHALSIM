import wntr
import wntr.network.controls as controls
import sqlite3
import csv
import time
import sys
from datetime import datetime


"""
This class uses the WNTR simulation to simulate the minitown topology.
The simulation is run in concurrence with the minitown MiniCPS topology. This class reads the DB to access the
P1 and P2 status, updates the WNTR controls of those actuators, runs a new simulation step, and outputs the new
water tank level into the DB. Finally, the results of the simulation are stored in .csv format
"""
class Simulation:

    def __init__(self):
        # connection to the database
        self.conn = sqlite3.connect('minitown_db.sqlite')
        self.cursor = self.conn.cursor()

        # Master time used to synchronize the PLCs
        rows = self.cursor.execute("SELECT value FROM minitown WHERE name = 'TIME'").fetchall()
        self.conn.commit()
        self.master_time = int(rows[0][0])  # PUMP1 STATUS FROM DATABASE

        # Create the network in WNTR
        self.inp_file = sys.argv[2]+'_map.inp'
        self.wn = wntr.network.WaterNetworkModel(self.inp_file)

    def main(self):
        # Set option for step-by-step simulation
        self.wn.options.time.duration = 900

        # This lists will be used to build the .csv file
        results_list = []

        node_list = list(self.wn.node_name_list)
        junction_list = []
        for node in node_list:
            if self.wn.get_node(node).node_type == 'Junction':
                junction_list.append(str(node))

        list_header = ["iteration", "timestamps", "TANK_LEVEL", "RESERVOIR_LEVEL"]
        list_header.extend(junction_list)
        another_list = ["FLOW_PUMP1", "FLOW_PUMP2", "STATUS_PUMP1", "STATUS_PUMP2", "Attack#01", "Attack#02"]
        list_header.extend(another_list)

        results_list.append(list_header)

        # We get these objects to make more readable the code
        tank = self.wn.get_node("TANK")  # WNTR TANK OBJECT
        pump1 = self.wn.get_link("PUMP1")  # WNTR PUMP OBJECT
        pump2 = self.wn.get_link("PUMP2")  # WNTR PUMP OBJECT
        reservoir = self.wn.get_node("R1")

        # Since we now use the same inp file, we need to delete the default controls
        for control in self.wn.control_name_list:
            self.wn.remove_control(control)

        # We define a dummy condition that should always be true
        condition = controls.ValueCondition(tank, 'level', '>=', -1)

        # Set the initial conditions of the actuators to the one pre defined into the DB
        rows = self.cursor.execute("SELECT value FROM minitown WHERE name = 'P1_STS'").fetchall()
        self.conn.commit()
        pump1_status = int(rows[0][0])  # PUMP1 STATUS FROM DATABASE
        act1 = controls.ControlAction(pump1, 'status', pump1_status)
        print("pump1 status %d" %pump1_status)

        pump1_control = controls.Control(condition, act1, name='pump1control')
        pump1.status = pump1_status

        # Set the initial conditions of the actuators to the one pre defined into the DB
        rows = self.cursor.execute("SELECT value FROM minitown WHERE name = 'P2_STS'").fetchall()
        self.conn.commit()
        pump2_status = int(rows[0][0])  # PUMP1 STATUS FROM DATABASE
        act2 = controls.ControlAction(pump2, 'status', pump2_status)
        print("pump2 status %d" %pump2_status)

        pump2_control = controls.Control(condition, act2, name='pump2control')
        pump2.status = pump2_status

        # WNTR works by reading these control objects and updating the state of the actuators
        self.wn.add_control('WnPump1Control', pump1_control)
        self.wn.add_control('WnPump2Control', pump2_control)

        if sys.argv[1] == 'pdd':
            print('Running simulation using PDD')
            sim = wntr.sim.WNTRSimulator(self.wn, mode='PDD')
        elif sys.argv[1] == 'dd':
            print('Running simulation using DD')
            sim = wntr.sim.WNTRSimulator(self.wn)
        else:
            print('Invalid simulation mode, exiting...')
            sys.exit(1)

        days_simulated = 7
        iteration_limit = days_simulated*(24*3600) / self.wn.options.time.duration

        # To write the time -1 (or 0) of the results
        results = None
        attack1 = 0
        attack2 = 0

        values_list = []
        values_list.extend([self.master_time, datetime.now(), tank.level, reservoir.head])

        for junction in junction_list:
            values_list.extend([self.wn.get_node(junction).base_demand])

        values_list.extend([pump1.flow, pump2.flow])

        if type(pump1.status) is int:
            values_list.extend([pump1.status])
        else:
            values_list.extend([pump1.status.value])

        if type(pump2.status) is int:
            values_list.extend([pump2.status])
        else:
            values_list.extend([pump2.status.value])

        values_list.extend([attack1, attack2])
        results_list.append(values_list)

        print(str(self.wn.control_name_list))
        print(str(self.wn.get_control('WnPump1Control')))
        print(str(self.wn.get_control('WnPump2Control')))

        # START STEP BY STEP SIMULATION
        while self.master_time <= iteration_limit:

            rows = self.cursor.execute("SELECT value FROM minitown WHERE name = 'CONTROL'").fetchall()
            self.conn.commit()
            control = int(rows[0][0])  # PUMP1 STATUS FROM DATABASE

            if control == 1:

                rows_1 = self.cursor.execute("SELECT value FROM minitown WHERE name = 'P1_STS'").fetchall()
                self.conn.commit()

                rows_2 = self.cursor.execute("SELECT value FROM minitown WHERE name = 'P2_STS'").fetchall()
                self.conn.commit()

                pump1_status = rows_1[0][0]  # PUMP1 STATUS FROM DATABASE
                act1 = controls.ControlAction(pump1, 'status', int(pump1_status))
                pump1_control = controls.Control(condition, act1, name='pump1control')

                pump2_status = rows_2[0][0]  # PUMP1 STATUS FROM DATABASE
                act2 = controls.ControlAction(pump2, 'status', int(pump2_status))
                pump2_control = controls.Control(condition, act2, name='pump2control')

                self.wn.remove_control("WnPump1Control")
                self.wn.remove_control("WnPump2Control")

                self.wn.add_control('WnPump1Control', pump1_control)
                self.wn.add_control('WnPump2Control', pump2_control)

                values_list = []
                if results:
                    values_list.extend([self.master_time, results.timestamp, tank.level, reservoir.head])
                    for junction in junction_list:
                        values_list.extend([self.wn.get_node(junction).head - self.wn.get_node(junction).elevation])

                    values_list.extend([pump1.flow, pump2.flow, pump1_status, pump2_status, attack1, attack2])
                    results_list.append(values_list)

                results = sim.run_sim(convergence_error=True)
                self.master_time += 1

                self.cursor.execute("UPDATE minitown SET value = %f WHERE name = 'T_LVL'" % tank.level)  # UPDATE TANK LEVEL IN THE DATABASE
                self.conn.commit()

                # take the value of attacks labels from the database
                rows = self.cursor.execute("SELECT value FROM minitown WHERE name = 'ATT_1'").fetchall()
                self.conn.commit()
                attack1 = rows[0][0]

                rows = self.cursor.execute("SELECT value FROM minitown WHERE name = 'ATT_2'").fetchall()
                self.conn.commit()
                attack2 = rows[0][0]

                self.cursor.execute("UPDATE minitown SET value = 0 WHERE name = 'CONTROL'")
                self.conn.commit()

                if results:
                    time.sleep(0.5)

        self.write_results(results_list)

    def write_results(self, results):
        with open('output/'+sys.argv[3], 'w', newline='\n') as f:
            writer = csv.writer(f)
            writer.writerows(results)


if __name__=="__main__":
    simulation = Simulation()
    simulation.main()
    exit(0)