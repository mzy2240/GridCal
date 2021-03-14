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
import os

import numpy as np

from GridCal.Engine import *


def test_opf_ts():
    fname = os.path.join('data', 'grids', 'IEEE39_1W.gridcal')
    print('Reading...')
    main_circuit = FileOpen(fname).open()

    print('Running OPF-TS...', '')
    opf_options = OptimalPowerFlowOptions(verbose=False,
                                          solver=SolverType.DC_OPF)

    opf_ts = OptimalPowerFlowTimeSeries(grid=main_circuit,
                                        options=opf_options,
                                        start_=0, end_=96)
    opf_ts.run()


if __name__ == '__main__':
    test_opf_ts()