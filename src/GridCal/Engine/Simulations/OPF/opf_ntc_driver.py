# This file is part of GridCal.
#
# GridCal is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GridCal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GridCal.  If not, see <http://www.gnu.org/licenses/>.
from enum import Enum
import numpy as np
import time

from GridCal.Engine.basic_structures import Logger
from GridCal.Engine.basic_structures import TimeGrouping, MIPSolvers
from GridCal.Engine.Simulations.OPF.opf_results import OptimalPowerFlowResults
from GridCal.Engine.Core.multi_circuit import MultiCircuit
from GridCal.Engine.Simulations.OPF.ntc_opf import OpfNTC
from GridCal.Engine.Simulations.PowerFlow.power_flow_driver import PowerFlowOptions
from GridCal.Engine.Core.snapshot_opf_data import compile_snapshot_opf_circuit
from GridCal.Engine.Simulations.driver_types import SimulationTypes
from GridCal.Engine.Simulations.driver_template import DriverTemplate

from GridCal.Engine.Simulations.result_types import ResultTypes
from GridCal.Engine.Simulations.results_table import ResultsTable
from GridCal.Engine.Simulations.results_template import ResultsTemplate

########################################################################################################################
# Optimal Power flow classes
########################################################################################################################


class OptimalNetTransferCapacityOptions:

    def __init__(self, area_from_bus_idx, area_to_bus_idx,
                 verbose=False,
                 grouping: TimeGrouping = TimeGrouping.NoGrouping,
                 mip_solver=MIPSolvers.CBC):
        """
        Optimal power flow options
        :param verbose:
        :param grouping:
        :param mip_solver:
        """
        self.verbose = verbose

        self.grouping = grouping

        self.mip_solver = mip_solver

        self.area_from_bus_idx = area_from_bus_idx

        self.area_to_bus_idx = area_to_bus_idx



class OptimalNetTransferCapacityResults(ResultsTemplate):
    """
    OPF results.

    Arguments:

        **Sbus**: bus power injections

        **voltage**: bus voltages

        **load_shedding**: load shedding values

        **Sf**: branch power values

        **overloads**: branch overloading values

        **loading**: branch loading values

        **losses**: branch losses

        **converged**: converged?
    """

    def __init__(self, bus_names, branch_names, load_names, generator_names, battery_names,
                 Sbus=None, voltage=None, load_shedding=None, generator_shedding=None,
                 battery_power=None, controlled_generation_power=None,
                 Sf=None, overloads=None, loading=None, losses=None, converged=None, bus_types=None):

        ResultsTemplate.__init__(self,
                                 name='OPF',
                                 available_results=[ResultTypes.BusVoltageModule,
                                                    ResultTypes.BusVoltageAngle,
                                                    ResultTypes.BranchPower,
                                                    ResultTypes.BranchLoading,
                                                    ResultTypes.BranchOverloads,
                                                    ResultTypes.LoadShedding,
                                                    ResultTypes.ControlledGeneratorShedding,
                                                    ResultTypes.ControlledGeneratorPower,
                                                    ResultTypes.BatteryPower],
                                 data_variables=['bus_names',
                                                 'branch_names',
                                                 'load_names',
                                                 'generator_names',
                                                 'battery_names',
                                                 'Sbus',
                                                 'voltage',
                                                 'load_shedding',
                                                 'generator_shedding',
                                                 'Sf',
                                                 'bus_types',
                                                 'overloads',
                                                 'loading',
                                                 'battery_power',
                                                 'generator_power',
                                                 'converged'])

        self.bus_names = bus_names
        self.branch_names = branch_names
        self.load_names = load_names
        self.generator_names = generator_names
        self.battery_names = battery_names

        self.Sbus = Sbus

        self.voltage = voltage

        self.load_shedding = load_shedding

        self.Sf = Sf

        self.bus_types = bus_types

        self.overloads = overloads

        self.loading = loading

        self.losses = losses

        self.battery_power = battery_power

        self.generator_shedding = generator_shedding

        self.generator_power = controlled_generation_power

        self.converged = converged

        self.plot_bars_limit = 100

    def apply_new_rates(self, nc: "SnapshotData"):
        rates = nc.Rates
        self.loading = self.Sf / (rates + 1e-9)

    def copy(self):
        """
        Return a copy of this
        @return:
        """
        return OptimalPowerFlowResults(bus_names=self.bus_names,
                                       branch_names=self.branch_names,
                                       load_names=self.load_names,
                                       generator_names=self.generator_names,
                                       battery_names=self.battery_names,
                                       Sbus=self.Sbus,
                                       voltage=self.voltage,
                                       load_shedding=self.load_shedding,
                                       Sf=self.Sf,
                                       overloads=self.overloads,
                                       loading=self.loading,
                                       generator_shedding=self.generator_shedding,
                                       battery_power=self.battery_power,
                                       controlled_generation_power=self.generator_power,
                                       converged=self.converged)

    def initialize(self, n, m):
        """
        Initialize the arrays
        @param n: number of buses
        @param m: number of branches
        @return:
        """
        self.Sbus = np.zeros(n, dtype=complex)

        self.voltage = np.zeros(n, dtype=complex)

        self.load_shedding = np.zeros(n, dtype=float)

        self.Sf = np.zeros(m, dtype=complex)

        self.loading = np.zeros(m, dtype=complex)

        self.overloads = np.zeros(m, dtype=complex)

        self.losses = np.zeros(m, dtype=complex)

        self.converged = list()

        self.plot_bars_limit = 100

    def mdl(self, result_type) -> "ResultsTable":
        """
        Plot the results
        :param result_type: type of results (string)
        :return: DataFrame of the results (or None if the result was not understood)
        """

        if result_type == ResultTypes.BusVoltageModule:
            labels = self.bus_names
            y = np.abs(self.voltage)
            y_label = '(p.u.)'
            title = 'Bus voltage module'

        elif result_type == ResultTypes.BusVoltageAngle:
            labels = self.bus_names
            y = np.angle(self.voltage)
            y_label = '(Radians)'
            title = 'Bus voltage angle'

        elif result_type == ResultTypes.BranchPower:
            labels = self.branch_names
            y = self.Sf.real
            y_label = '(MW)'
            title = 'Branch power'

        elif result_type == ResultTypes.BusPower:
            labels = self.bus_names
            y = self.Sbus.real
            y_label = '(MW)'
            title = 'Bus power'

        elif result_type == ResultTypes.BranchLoading:
            labels = self.branch_names
            y = self.loading * 100.0
            y_label = '(%)'
            title = 'Branch loading'

        elif result_type == ResultTypes.BranchOverloads:
            labels = self.branch_names
            y = np.abs(self.overloads)
            y_label = '(MW)'
            title = 'Branch overloads'

        elif result_type == ResultTypes.BranchLosses:
            labels = self.branch_names
            y = self.losses.real
            y_label = '(MW)'
            title = 'Branch losses'

        elif result_type == ResultTypes.LoadShedding:
            labels = self.load_names
            y = self.load_shedding
            y_label = '(MW)'
            title = 'Load shedding'

        elif result_type == ResultTypes.ControlledGeneratorShedding:
            labels = self.generator_names
            y = self.generator_shedding
            y_label = '(MW)'
            title = 'Controlled generator shedding'

        elif result_type == ResultTypes.ControlledGeneratorPower:
            labels = self.generator_names
            y = self.generator_power
            y_label = '(MW)'
            title = 'Controlled generators power'

        elif result_type == ResultTypes.BatteryPower:
            labels = self.battery_names
            y = self.battery_power
            y_label = '(MW)'
            title = 'Battery power'

        else:
            labels = []
            y = np.zeros(0)
            y_label = '(MW)'
            title = 'Battery power'

        mdl = ResultsTable(data=y,
                           index=labels,
                           columns=[result_type.value[0]],
                           title=title,
                           ylabel=y_label,
                           xlabel='',
                           units=y_label)
        return mdl


class OptimalNetTransferCapacity(DriverTemplate):
    name = 'Optimal net power capacity'
    tpe = SimulationTypes.OPF_NTC_run

    def __init__(self, grid: MultiCircuit, options: OptimalNetTransferCapacityOptions, pf_options: PowerFlowOptions):
        """
        PowerFlowDriver class constructor
        @param grid: MultiCircuit Object
        @param options: OPF options
        """
        DriverTemplate.__init__(self, grid=grid)

        # Options to use
        self.options = options

        self.pf_options = pf_options

        self.all_solved = True

    def get_steps(self):
        """
        Get time steps list of strings
        """
        return list()

    def opf(self):
        """
        Run a power flow for every circuit
        @return: OptimalPowerFlowResults object
        """

        numerical_circuit = compile_snapshot_opf_circuit(circuit=self.grid,
                                                         apply_temperature=self.pf_options.apply_temperature_correction,
                                                         branch_tolerance_mode=self.pf_options.branch_impedance_tolerance_mode)

        problem = OpfNTC(numerical_circuit,
                         area_from_bus_idx=self.options.area_from_bus_idx,
                         area_to_bus_idx=self.options.area_to_bus_idx,
                         solver_type=self.options.mip_solver)
        # Solve
        problem.solve()

        # get the branch Sf (it is used more than one time)
        Sbr = problem.get_branch_power()
        # ld = problem.get_load_shedding()
        # ld[ld == None] = 0
        # bt = problem.get_battery_power()
        # bt[bt == None] = 0
        gn = problem.get_generator_power()
        gn[gn == None] = 0

        Sbus = problem.get_power_injections()

        # pack the results
        self.results = OptimalNetTransferCapacityResults(bus_names=numerical_circuit.bus_data.bus_names,
                                                         branch_names=numerical_circuit.branch_data.branch_names,
                                                         load_names=numerical_circuit.load_data.load_names,
                                                         generator_names=numerical_circuit.generator_data.generator_names,
                                                         battery_names=numerical_circuit.battery_data.battery_names,
                                                         Sbus=Sbus,
                                                         voltage=problem.get_voltage(),
                                                         load_shedding=np.zeros((numerical_circuit.nload, 1)),
                                                         generator_shedding=np.zeros_like(gn),
                                                         battery_power=np.zeros((numerical_circuit.nbatt, 1)),
                                                         controlled_generation_power=gn,
                                                         Sf=Sbr,
                                                         overloads=problem.get_overloads(),
                                                         loading=problem.get_loading(),
                                                         converged=bool(problem.converged()),
                                                         bus_types=numerical_circuit.bus_types)

        return self.results

    def run(self):
        """

        :return:
        """
        start = time.time()
        self.opf()
        end = time.time()
        self.elapsed = end - start
        self.progress_text.emit('Done!')
        self.done_signal.emit()
