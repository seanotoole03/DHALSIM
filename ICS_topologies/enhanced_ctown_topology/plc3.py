from basePLC import BasePLC
from utils import PLC3_DATA, STATE, PLC3_PROTOCOL
from utils import T2, T3, T4, V2, V2F, PU4, PU5, PU6, PU7, PU4F, PU5F, PU6F, PU7F, ENIP_LISTEN_PLC_ADDR, CTOWN_IPS, CONTROL
from utils import J300, J256, J289, J415, J14, J422
from utils import ATT_1, ATT_2
from decimal import Decimal
import time
import threading
import sys
import yaml

class PLC3(BasePLC):

    def pre_loop(self):
        print 'DEBUG: plc3 enters pre_loop'

        # We wish we could implement this as arg_parse, but we cannot overwrite the constructor
        self.week_index = sys.argv[2]
        self.attack_flag = False
        self.attack_dict = None

        if len(sys.argv) >= 4:
            self.attack_flag = sys.argv[4]
            self.attack_path = sys.argv[6]
            self.attack_name = sys.argv[8]

        if self.attack_flag:
            self.attack_dict = self.get_attack_dict(self.attack_path, self.attack_name)
            print "PLC3 running attack: " + str(self.attack_dict)

        self.local_time = 0

        # Used to sync the actuators and the physical process
        self.plc_mask = 2


        # Flag used to stop the thread
        self.reader = True
        self.saved_tank_levels = [["iteration", "timestamp", "T2", "T3", "T4"]]

        self.t2 = Decimal(self.get(T2))
        self.v2 = int(self.get(V2))
        self.v2f = Decimal(self.get(V2F))

        self.j300 = Decimal(self.get(J300))
        self.j256 = Decimal(self.get(J256))
        self.j289 = Decimal(self.get(J289))
        self.j415 = Decimal(self.get(J415))
        self.j14 = Decimal(self.get(J14))
        self.j422 = Decimal(self.get(J422))

        self.pu4 = int(self.get(PU4))
        self.pu5 = int(self.get(PU5))
        self.pu6 = int(self.get(PU6))
        self.pu7 = int(self.get(PU7))

        self.pu4f = Decimal(self.get(PU4F))
        self.pu5f = Decimal(self.get(PU5F))
        self.pu6f = Decimal(self.get(PU6F))
        self.pu7f = Decimal(self.get(PU7F))

        self.lock = threading.Lock()
        path = 'plc3_saved_tank_levels_received.csv'
        tags = [T2, V2, V2F, J300, J256, J289, J415, J14, J422, PU4, PU5, PU6, PU7, PU4F, PU5F, PU6F, PU7F]
        values = [self.t2, self.v2, self.v2f, self.j300, self.j256, self.j289, self.j415, self.j14, self.j422, self.pu4, self.pu5,
                  self.pu6, self.pu7, self.pu4f, self.pu5f, self.pu6f, self.pu7f]

        # Used in handling of sigint and sigterm signals, also sets the parameters to save the system state variable
        # values into a persistent file
        BasePLC.set_parameters(self, tags, values, self.reader, self.lock,
                               ENIP_LISTEN_PLC_ADDR)
        self.startup()

    def get_attack_dict(self, path, name):
        with open(path) as config_file:
            attack_file = yaml.load(config_file, Loader=yaml.FullLoader)

        for attack in attack_file['attacks']:
            if name == attack['name']:
                return attack

    def check_control(self, mask):
        control = int(self.get(CONTROL))
        if not (mask & control):
            return True
        return False

    def main_loop(self):
        while True:
            try:

                # Check if we need to launch an attack
                attack_on = int(self.get(ATT_2))
                self.set(ATT_1, attack_on)

                #if self.check_control(self.plc_mask):
                self.local_time += 1
                self.t2 = Decimal( self.get( T2 ) )
                self.t3 = Decimal(self.receive( T3, CTOWN_IPS['plc4'] ))
                self.t4 = Decimal(self.receive( T4, CTOWN_IPS['plc6'] ))

                #self.saved_tank_levels.append([self.local_time, datetime.now(), self.t2, self.t3, self.t4])
                with self.lock:
                    if self.t2 < 0.5:
                        self.v2 = 1

                    if self.t2 > 5.5:
                        self.v2 = 0

                    if self.t3 < 3.0:
                        self.pu4 = 1

                    if self.t3 > 5.3:
                        self.pu4 = 0

                    if self.t3 < 1.0:
                        self.pu5 = 1

                    if self.t3 > 3.5:
                        self.pu5 = 0

                    if self.t4 < 2.0:
                        self.pu6 = 1

                    if self.t4 > 3.5:
                        self.pu6 = 0

                    if self.t4 < 3.0:
                        self.pu7 = 1

                    if self.t4 > 4.5:
                        self.pu7 = 0

                    if self.attack_flag:
                        # Now ATT_2 is set in the physical_process. This in order to make more predictable the
                        # attack start and end time
                        if attack_on == 1:
                            # toDo: Improve this still, hardcoded
                            if self.attack_dict['actuators'][0] == 'v2':
                                if self.attack_dict['command'] == 'Close':
                                    # toDo: Implement this dynamically.
                                    # There's a horrible way of doing it with the current code. This would be much
                                    # easier (and less horrible) if we use the general topology
                                    self.v2 = 0
                                elif self.attack_dict['command'] == 'Open':
                                    self.v2 = 1
                                elif self.attack_dict['command'] == 'Maintain':
                                    continue
                                elif self.attack_dict['command'] == 'Toggle':
                                    if self.v2 == 1:
                                        self.v2 = 0
                                    else:
                                        self.v2 = 1
                                else:
                                    print "Warning. Attack not implemented yet"

                            # toDo: Improve this still, hardcoded
                            if self.attack_dict['actuators'][0] == 'pu4' or self.attack_dict['actuators'][0] == 'pu5':
                                if self.attack_dict['command'] == 'Close':
                                    # toDo: Implement this dynamically.
                                    # There's a horrible way of doing it with the current code. This would be much
                                    # easier (and less horrible) if we use the general topology
                                    self.pu4 = 0
                                    self.pu5 = 0
                                elif self.attack_dict['command'] == 'Open':
                                    self.pu4 = 1
                                    self.pu5 = 1
                                # toDo: Maintain is not properly implemented
                                elif self.attack_dict['command'] == 'Maintain':
                                    continue
                                elif self.attack_dict['command'] == 'Toggle':
                                    if self.pu4 == 1:
                                        self.pu4 = 0
                                    else:
                                        self.pu4 = 1

                                    if self.pu5 == 1:
                                        self.pu5 = 0
                                    else:
                                        self.pu5 = 1
                                else:
                                    print "Warning. Attack not implemented yet"

                    self.set(V2, self.v2)
                    self.set(PU4, self.pu4)
                    self.set(PU5, self.pu5)
                    self.set(PU6, self.pu6)
                    self.set(PU7, self.pu7)

                control = int(self.get(CONTROL))
                control += self.plc_mask
                self.set(CONTROL, control)
                time.sleep(0.05)
                #else:
                #    time.sleep(0.1)

            except Exception:
                continue


if __name__ == "__main__":
    plc3 = PLC3(
        name='plc3',
        state=STATE,
        protocol=PLC3_PROTOCOL,
        memory=PLC3_DATA,
        disk=PLC3_DATA)