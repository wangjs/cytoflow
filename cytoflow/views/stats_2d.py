#!/usr/bin/env python3.4
# coding: latin-1

# (c) Massachusetts Institute of Technology 2015-2017
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from traits.api import provides
import matplotlib.pyplot as plt

import numpy as np

import cytoflow.utility as util

from .i_view import IView
from .base_views import Base2DStatisticsView

@provides(IView)
class Stats2DView(Base2DStatisticsView):
    """
    Plot two statistics on a scatter plot.  A point (X,Y) is drawn for every
    pair of elements with the same value of `variable`; the X value is from 
    `xstatistic` and the Y value is from `ystatistic`.
    
    Attributes
    ----------
    name : Str
        The plot's name 
    
    variable : Str
        the name of the conditioning variable
        
    xstatistic : Tuple(Str, Str)
        The statistic to plot on the X axis.  Must have the same indices
        as `ystatistic`.
        
    xscale : Enum("linear", "log", "logicle") (default = "linear")
        What scale to use on the X axis
    
    ystatistic : Tuple(Str, Str)
       The statistic to plot on the Y axis.  Must have the same indices
       as `xstatistic`.
        
    yscale : Enum("linear", "log", "logicle") (default = "linear")
        What scale to use on the Y axis
        
    xfacet : Str
        the conditioning variable for horizontal subplots
        
    yfacet : Str
        the conditioning variable for vertical subplots
        
    huefacet : 
        the conditioning variable for color.
        
    huescale : Enum("linear", "log", "logicle") (default = "linear")
        scale for the hue facet, if there are a lot of hue values.
        
    x_error_statistic, y_error_statistic : Tuple(Str, Str)
        if specified, draw error bars.  must be the name of a statistic,
        with the same indices as `xstatistic` and `ystatistic`.
    
    subset : Str
        What subset of the data to plot?
        
    Examples
    --------
    
    Assume we want an input-output curve for a repressor that's under the
    control of a Dox-inducible promoter.  We have an "input" channel
    `(Dox --> eYFP, FITC-A channel)` and an output channel 
    `(Dox --> repressor --| eBFP, Pacific Blue channel)` as well as a 
    constitutive expression channel (mKate, PE-Tx-Red-YG-A channel). 
    We have induced several wells with different amounts of Dox.  We want 
    to plot the relationship between the input and output channels (binned by 
    input channel intensity) as we vary Dox, faceted by constitutive channel 
    bin.
    
    >>> cfp_bin_op = flow.BinningOp(name = "CFP_Bin",
    ...                             channel = "PE-Tx-Red-YG-A",
    ...                             scale = "log",
    ...                             bin_width = 0.1)
    >>> ifp_bin_op = flow.BinningOp(name = "IFP_Bin",
    ...                             channel = "Pacific Blue-A",
    ...                             scale = "log",
    ...                             bin_width = 0.1).apply(ex_cfp_binned)
    >>> ifp_mean = flow.ChannelStatisticOp(name = "IFP",
    ...                                    channel = "FITC-A",
    ...                                    by = ["IFP_Bin", "CFP_Bin"],
    ...                                    function = flow.geom_mean)
    >>> ofp_mean = flow.ChannelStatisticOp(name = "OFP",
    ...                                    channel = "Pacific_Blue-A",
    ...                                    by = ["IFP_Bin", "CFP_Bin"],
    ...                                    function = flow.geom_mean)
    >>> ex = cfp_bin_op.apply(ex)
    >>> ex = ifp_bin_op.apply(ex)
    >>> ex = ifp_mean.apply(ex)
    >>> ex = ofp_mean.apply(ex)
    >>> view = flow.Stats2DView(name = "IFP vs OFP",
    ...                         variable = "IFP_Bin",
    ...                         xstatistic = ("IFP", "geom_mean"),
    ...                         ystatistic = ("OFP", "geom_mean"),
    ...                         huefacet = "CFP_Bin").plot(ex_ifp_binned)
    >>> view.plot(ex_binned)
    """
    
    # traits   
    id = "edu.mit.synbio.cytoflow.view.stats2d"
    friendly_id = "2D Statistics View" 
   
    def enum_plots(self, experiment):
        """
        Returns an iterator over the possible plots that this View can
        produce.  The values returned can be passed to "plot".
        """
                
        return super().enum_plots(experiment)
            
    def plot(self, experiment, plot_name = None, **kwargs):
        """
        Plot a chart of two statistics' values as a common variable changes.
        
        Parameters
        ----------
        
        color : a matplotlib color
            The color to plot with.  Overridden if `huefacet` is not `None`
            
        linestyle : ['solid' | 'dashed', 'dashdot', 'dotted' | (offset, on-off-dash-seq) | '-' | '--' | '-.' | ':' | 'None' | ' ' | '']
            
        marker : a matplotlib marker style
            See http://matplotlib.org/api/markers_api.html#module-matplotlib.markers
            
        markersize : int
            The marker size in points
            
        markerfacecolor : a matplotlib color
            The color to make the markers.  Overridden (?) if `huefacet` is not `None`
            
        alpha : the alpha blending value, from 0.0 (transparent) to 1.0 (opaque)
        
        Other Parameters
        ----------------
        
        Other `kwargs` are passed to matplotlib.pyplot.plot_.
    
        .. _matplotlib.pyplot.hist: https://matplotlib.org/devdocs/api/_as_gen/matplotlib.pyplot.plot.html
        
        See Also
        --------
        BaseView.plot : common parameters for data views
        
        """

        super().plot(experiment, plot_name, **kwargs)


    def _grid_plot(self, experiment, grid, xlim, ylim, xscale, yscale, **kwargs):

        data = grid.data
        xstat = experiment.statistics[self.xstatistic]
        xname = xstat.name
        ystat = experiment.statistics[self.ystatistic]
        yname = ystat.name
        
        if self.x_error_statistic[0]:
            x_error_stat = experiment.statistics[self.x_error_statistic]
            x_error_name = x_error_stat.name
        else:
            x_error_stat = None

        if self.y_error_statistic[0]:
            y_error_stat = experiment.statistics[self.y_error_statistic]
            y_error_name = y_error_stat.name
        else:
            y_error_stat = None
        
        xlim = kwargs.pop("xlim", None)
        if xlim is None:
            xlim = (xscale.clip(data[xname].min() * 0.9),
                    xscale.clip(data[xname].max() * 1.1))
            
            if x_error_stat:
                try: 
                    xlim = (xscale.clip(min([x[0] for x in data[x_error_name]]) * 0.9),
                            xscale.clip(max([x[1] for x in data[x_error_name]]) * 1.1))
                except IndexError:
                    xlim = (xscale.clip((data[xname].min() - data[x_error_name].min()) * 0.9), 
                            xscale.clip((data[xname].max() + data[x_error_name].max()) * 1.1))
                      
        ylim = kwargs.pop("ylim", None)
        if ylim is None:
            ylim = (yscale.clip(data[yname].min() * 0.9),
                    yscale.clip(data[yname].max() * 1.1))
            
            if y_error_stat:
                try: 
                    ylim = (yscale.clip(min([x[0] for x in data[y_error_name]]) * 0.9),
                            yscale.clip(max([x[1] for x in data[y_error_name]]) * 1.1))
                except IndexError:
                    ylim = (yscale.clip((data[yname].min() - data[y_error_name].min()) * 0.9), 
                            yscale.clip((data[yname].max() + data[y_error_name].max()) * 1.1))
        
        # plot the error bars first so the axis labels don't get overwritten
        if x_error_stat:
            grid.map(_x_error_bars, xname, yname, x_error_name)
            
        if y_error_stat:
            grid.map(_y_error_bars, xname, yname, y_error_name)

        grid.map(plt.plot, xname, yname, **kwargs)


def _x_error_bars(x, y, xerr, ax = None, color = None, **kwargs):
    
    if isinstance(xerr.iloc[0], tuple):
        x_lo = [xe[0] for xe in xerr]
        x_hi = [xe[1] for xe in xerr]
    else:
        x_lo = [x.iloc[i] - xe for i, xe in xerr.reset_index(drop = True).items()]
        x_hi = [x.iloc[i] + xe for i, xe in xerr.reset_index(drop = True).items()]
        
    plt.hlines(y, x_lo, x_hi, color = color, **kwargs)
    
    
def _y_error_bars(x, y, yerr, ax = None, color = None, **kwargs):
    
    if isinstance(yerr.iloc[0], tuple):
        y_lo = [ye[0] for ye in yerr]
        y_hi = [ye[1] for ye in yerr]
    else:
        y_lo = [y.iloc[i] - ye for i, ye in yerr.reset_index(drop = True).items()]
        y_hi = [y.iloc[i] + ye for i, ye in yerr.reset_index(drop = True).items()]
        
    plt.vlines(x, y_lo, y_hi, color = color, **kwargs)
    
    
if __name__ == '__main__':
    import cytoflow as flow
    tube1 = flow.Tube(file = '../../cytoflow/tests/data/Plate01/RFP_Well_A3.fcs',
                      conditions = {"Dox" : 10.0})
    
    tube2 = flow.Tube(file = '../../cytoflow/tests/data/Plate01/CFP_Well_A4.fcs',
                      conditions = {"Dox" : 1.0})                      

    ex = flow.ImportOp(conditions = {"Dox" : "float"}, tubes = [tube1, tube2])
    
    thresh = flow.ThresholdOp()
    thresh.name = "Y2-A+"
    thresh.channel = 'Y2-A'
    thresh.threshold = 2005.0

    ex2 = thresh.apply(ex)
    
    s = flow.Stats2DView()
    s.variable = "Dox"
    s.xchannel = "V2-A"
    s.xfunction = np.mean
    s.ychannel = "Y2-A"
    s.yfunction = np.mean
    s.huefacet = "Y2-A+"

    
    plt.ioff()
    s.plot(ex2)
    plt.show()