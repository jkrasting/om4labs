#!/usr/bin/env python3

import argparse
import glob
import io
import os
import matplotlib as mpl
import matplotlib.pyplot as plt
from om4labs import m6plot
import xarray as xr

from om4labs.diags import generic_section_transport
from om4labs.om4common import image_handler
from om4labs.om4common import discover_ts_dir
from om4labs.om4parser import default_diag_parser

# passages with their frepp component mappings and observed ranges from
# Griffies et al., 2016: OMIP contribution to CMIP6:
#    experimental and diagnostic protocol for the physical component
#    of the Ocean Model Intercomparison Project.
#    Geosci. Model. Dev., 9, 3231-3296. doi:10.5194/gmd-9-3231-2016'

reference = (
    "Griffies et al., 2016, "
    + "Geosci. Model. Dev., 9, 3231-3296. "
    + "doi:10.5194/gmd-9-3231-2016"
)

defined_passages = [
    ("ocean_Agulhas_section", "Agulhas", (129.8, 143.6)),
    ("ocean_Bering_Strait", "Bering Strait", (0.7, 1.1)),
    ("ocean_Barents_opening", "Barents Opening", (1.99, 2.01)),
    ("ocean_Davis_Strait", "Davis Strait", (-2.1, -1.1)),
    ("ocean_Denmark_Strait", "Denmark Strait", (-4.8, -2.0)),
    ("ocean_Drake_Passage", "Drake Passage", (129.8, 143.6)),
    ("ocean_English_Channel", "English Channel", (0.01, 0.1)),
    ("ocean_Faroe_Scotland", "Faroe-Scotland", (0.8, 1.0)),
    ("ocean_Florida_Bahamas", "Florida-Bahamas", (28.9, 34.3)),
    ("ocean_Fram_Strait", "Fram Strait", (-4.7, 0.7)),
    ("ocean_Gibraltar_Strait", "Gibraltar Strait", (0.109, 0.111)),
    (["ocean_Iceland_Faroe_U", "ocean_Iceland_Faroe_V"], "Iceland-Faroe", (4.35, 4.85)),
    ("ocean_Iceland_Norway", "Iceland-Norway", None),
    ("ocean_Indonesian_Throughflow", "Indonesian Throughflow", (-15, -13)),
    ("ocean_Mozambique_Channel", "Mozambique Channel", (-25.6, -7.8)),
    ("ocean_Pacific_undercurrent", "Pacific Equatorial Undercurrent", (24.5, 28.3)),
    ("ocean_Taiwan_Luzon", "Taiwan-Luzon Strait", (-3.0, -1.8)),
    ("ocean_Windward_Passage", "Windward Passage", (-15, 5)),
]


class Passage:
    """Class to hold passage metadata and associate a plotting function"""

    def __init__(
        self,
        label,
        pathpp,
        tscomponent,
        passage_label="",
        obsrange=None,
        varlist=["umo", "vmo"],
    ):

        # mutliple pp components may be passed if there are separate
        # u and v components for a transport
        tscomponent = (
            [tscomponent] if not isinstance(tscomponent, list) else tscomponent
        )
        tscomponent = [f"{pathpp}/{x}" for x in tscomponent]
        tscomponent = [x for x in tscomponent if os.path.exists(x)]
        pathpp = [discover_ts_dir(x) for x in tscomponent]

        # resolve paths to the files to use for plotting
        files = [glob.glob(f"{directory}/*.nc") for directory in pathpp]
        files = [filename for sublist in files for filename in sublist]
        files = [
            filename
            for filename in files
            if any(variable in filename for variable in varlist)
        ]

        self.files = files
        self.passage_label = passage_label
        self.label = label
        self.obsrange = obsrange

    def calculate(self):
        if len(self.files) == 0:
            # use print instead of exception to print message to Dora
            print(f"No files found to calculate {self.passage_label}")
            self.transport = None

        else:
            # invoke generic section transport diagnostic
            dset_transport = xr.open_mfdataset(self.files, use_cftime=True)
            self.transport = generic_section_transport.calculate(dset_transport)

        return self

    def plot(self):
        if self.transport is not None:
            fig = generic_section_transport.plot(
                self.transport,
                label=self.label,
                passage_label=self.passage_label,
                obsrange=self.obsrange,
            )
            return fig


def parse(cliargs=None, template=False):
    """
    Function to capture the user-specified command line options
    """
    description = """ """

    parser = default_diag_parser(description=description, template=template)

    if template is True:
        return parser.parse_args(None).__dict__
    else:
        return parser.parse_args(cliargs)


def run(dictArgs):
    """Function to call read, calc, and plot in sequence"""

    # set visual backend
    if dictArgs["interactive"] is False:
        plt.switch_backend("Agg")
    else:
        plt.switch_backend("TkAgg")

    # --- the main show ---

    assert len(dictArgs["infile"]) == 1, "Only one path may be provided to this routine"
    infile = dictArgs["infile"][0]

    # read in the data
    passages = [Passage(dictArgs["label"], infile, *x) for x in defined_passages]

    # calculate the transports for each of the passages
    passages = [x.calculate() for x in passages]

    # loop over passages and call their plot method
    figs = [passage.plot() for passage in passages if passage.transport is not None]

    # get a list of output filenames
    filenames = [
        passage.passage_label for passage in passages if passage.transport is not None
    ]

    # ---------------------

    filenames = [x.replace(" ", "_") for x in filenames]
    filenames = [f"{dictArgs['outdir']}/{x}" for x in filenames]
    imgbufs = image_handler(figs, dictArgs, filename=filenames)

    return imgbufs


def parse_and_run(cliargs=None):
    args = parse(cliargs)
    args = args.__dict__
    imgbuf = run(args)
    return imgbuf


if __name__ == "__main__":
    parse_and_run()
