import datetime
import os
from pathlib import Path
from shutil import copy

import wntr
import yaml


class BatchReadMeGenerator:
    """
    Class which deals with generating a readme for each batch.
    :param intermediate_yaml_path: contains the path to intermediate yaml
    :type intermediate_yaml_path: str
    """
    def __init__(self, intermediate_yaml_path):
        with intermediate_yaml_path.open() as yaml_file:
            self.intermediate_yaml = yaml.load(yaml_file, Loader=yaml.FullLoader)

        os.makedirs(str(Path(self.intermediate_yaml['config_path']).parent
                        / self.intermediate_yaml['output_path']), exist_ok=True)
        self.readme_path = str(Path(self.intermediate_yaml['config_path']).parent
                          / self.intermediate_yaml['output_path'] / 'readme_batch.md')

    def write_batch(self, start_time, end_time, wn, master_time):
        """
        Creates a small readme for each batch.
        :param start_time: is the start time of batch
        :param end_time: is the end time of batch
        :param wn: is WNTR instance
        :param master_time: is current iteration
        """
        with open(self.readme_path, 'w') as readme:
            readme.write("# Auto-generated README of {file} for batch {no}"
                         .format(file=os.path.basename(str(self.intermediate_yaml['inp_file']))[:-4],
                                 no=self.intermediate_yaml['batch_index'] + 1))
            readme.write("\n\nThis is batch {x} out of {y}."
                         .format(x=self.intermediate_yaml['batch_index'] + 1,
                                 y=self.intermediate_yaml['batch_simulations']))
            if 'initial_tank_values' in self.intermediate_yaml:
                readme.write("\n\n## Initial tank data")
                readme.write("\n\n{data}".format(data=str(self.intermediate_yaml['initial_tank_values'])))
            if 'network_loss_values' in self.intermediate_yaml:
                readme.write("\n\n## Network loss values")
                readme.write("\n\n{data}".format(data=str(self.intermediate_yaml['network_loss_values'])))
            if 'network_delay_values' in self.intermediate_yaml:
                readme.write("\n\n## Network delay values")
                readme.write("\n\n{data}".format(data=str(self.intermediate_yaml['network_delay_values'])))
            if 'demand_patterns_path' in self.intermediate_yaml:
                readme.write("\n\n## Demand patterns")
                readme.write("\n\n{data}".format(data=str(self.intermediate_yaml['demand_patterns_path'])))
            readme.write("\n\n## Information about this batch")
            readme.write("\n\nRan for {x} out of {y} iterations with hydraulic timestep {step}."
                         .format(x=str(master_time),
                                 y=str(self.intermediate_yaml['iterations']),
                                 step=str(wn.options.time.hydraulic_timestep)))
            readme.write("\n\nStarted at {start} and finished at {end}."
                         .format(start=str(start_time.strftime("%Y-%m-%d %H:%M:%S")),
                                 end=str(end_time.strftime("%Y-%m-%d %H:%M:%S"))))
            readme.write("\n\nThe duration of this batch was {time}."
                         .format(time=str(end_time - start_time)))
            readme.write("\n\nFor more information with regard to this experiment, consult "
                         "```readme_experiment.md``` in the root of the output folder.")

class InputFilesCopier:
    """
    Copies all input files.
    """
    def __init__(self, config_file):
        self.config_file = config_file

        with self.config_file.open(mode='r') as conf:
            self.config = yaml.load(conf, Loader=yaml.FullLoader)

        self.configuration_folder = self.config_file.parent / self.config['output_path'] / 'configuration'

    def copy_input_files(self):
        """Copies all input files, mandatory and optional ones included."""
        os.makedirs(str(self.configuration_folder), exist_ok=True)

        # Copy mandatory files.
        with open(str(self.configuration_folder / 'config.yaml'), 'w') as config_file:
            yaml.dump(self.config, config_file)

        copy(self.config_file.parent / self.config['inp_file'],
             self.configuration_folder / 'map.inp')

        # Copy optional csv files.
        if 'initial_tank_data' in self.config:
            copy(self.config_file.parent / self.config['initial_tank_data'],
                 self.configuration_folder / 'initial_tank_data.csv')

        if 'demand_patterns' in self.config:
            if 'batch_simulations' in self.config:
                os.makedirs(self.configuration_folder / 'demand_patterns', exist_ok=True)
                for batch in range(self.config['batch_simulations']):
                    copy(self.config_file.parent / self.config['demand_patterns'] / (str(batch) + ".csv"),
                         self.configuration_folder / 'demand_patterns' / (str(batch) + ".csv"))
            else:
                copy(self.config_file.parent / self.config['demand_patterns'],
                     self.configuration_folder / 'demand_patterns.csv')

        if 'network_loss_data' in self.config:
            copy(self.config_file.parent / self.config['network_loss_data'],
                 self.configuration_folder / 'network_loss_data.csv')

        if 'network_delay_data' in self.config:
            copy(self.config_file.parent / self.config['network_delay_data'],
                 self.configuration_folder / 'network_delay_data.csv')
