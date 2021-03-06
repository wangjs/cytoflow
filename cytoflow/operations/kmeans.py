#!/usr/bin/env python3.4
# coding: latin-1

# (c) Massachusetts Institute of Technology 2015-2016
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

'''
Created on Dec 16, 2015

@author: brian
'''

from warnings import warn
from itertools import product

import matplotlib.pyplot as plt

from traits.api import (HasStrictTraits, Str, CStr, Dict, Any, Instance, Bool, 
                        Constant, List, provides, Property, Enum)

import numpy as np
import sklearn.cluster
import scipy.stats

import pandas as pd
import seaborn as sns

from cytoflow.views import IView, HistogramView, ScatterplotView
import cytoflow.utility as util

from .i_operation import IOperation
from .base_op_views import By1DView, By2DView, AnnotatingView

@provides(IOperation)
class KMeansOp(HasStrictTraits):
    """
    This module uses a K-means clustering algorithm to cluster events.  
    
    Call `estimate()` to compute the cluster centroids.
      
    Calling `apply()` creates a new categorical metadata variable 
    named `name`, with possible values `{name}_1` .... `name_n` where `n` is 
    the number of clusters, specified with `n_clusters`.
    
    The same model may not be appropriate for different subsets of the data set.
    If this is the case, you can use the `by` attribute to specify metadata by 
    which to aggregate the data before estimating (and applying) a model.  The 
    number of clusters is the same across each subset, though.

    Attributes
    ----------
    name : Str
        The operation name; determines the name of the new metadata column
        
    channels : List(Str)
        The channels to apply the clustering algorithm to.

    scale : Dict(Str : Enum("linear", "logicle", "log"))
        Re-scale the data in the specified channels before fitting.  If a 
        channel is in `channels` but not in `scale`, the current package-wide
        default (set with `set_default_scale`) is used.

    num_clusters : Int (default = 2)
        How many components to fit to the data?  Must be a positive integer.
    
    by : List(Str)
        A list of metadata attributes to aggregate the data before estimating
        the model.  For example, if the experiment has two pieces of metadata,
        `Time` and `Dox`, setting `by = ["Time", "Dox"]` will fit the model 
        separately to each subset of the data with a unique combination of
        `Time` and `Dox`.
        
    Statistics
    ----------       
    centers : Float
        the location of each cluster's centroid in each channel
  
    Examples
    --------
    
    >>> clust_op = KMeansOp(name = "Clust",
    ...                         channels = ["V2-A", "Y2-A"],
    ...                         scale = {"V2-A" : "log"},
    ...                         num_clusters = 2)
    >>> clust_op.estimate(ex2)
    >>> clust_op.default_view(channels = ["V2-A"], ["Y2-A"]).plot(ex2)
    >>> ex3 = clust_op.apply(ex2)
    """
    
    id = Constant('edu.mit.synbio.cytoflow.operations.kmeans')
    friendly_id = Constant("KMeans Clustering")
    
    name = CStr()
    channels = List(Str)
    scale = Dict(Str, util.ScaleEnum)
    num_clusters = util.PositiveInt(allow_zero = False)
    by = List(Str)
    
    _kmeans = Dict(Any, Instance(sklearn.cluster.MiniBatchKMeans), transient = True)
    _scale = Dict(Str, Instance(util.IScale), transient = True)
    
    def estimate(self, experiment, subset = None):
        """
        Estimate the Gaussian mixture model parameters
        """

        if experiment is None:
            raise util.CytoflowOpError("No experiment specified")
        
        if self.num_clusters < 2:
            raise util.CytoflowOpError("num_clusters must be >= 2")
        
        if len(self.channels) == 0:
            raise util.CytoflowOpError("Must set at least one channel")

        for c in self.channels:
            if c not in experiment.data:
                raise util.CytoflowOpError("Channel {0} not found in the experiment"
                                      .format(c))
                
        for c in self.scale:
            if c not in self.channels:
                raise util.CytoflowOpError("Scale set for channel {0}, but it isn't "
                                           "in the experiment"
                                           .format(c))
       
        for b in self.by:
            if b not in experiment.data:
                raise util.CytoflowOpError("Aggregation metadata {0} not found"
                                      " in the experiment"
                                      .format(b))
            if len(experiment.data[b].unique()) > 100: #WARNING - magic number
                raise util.CytoflowOpError("More than 100 unique values found for"
                                      " aggregation metadata {0}.  Did you"
                                      " accidentally specify a data channel?"
                                      .format(b))

                
        if subset:
            try:
                experiment = experiment.query(subset)
            except:
                raise util.CytoflowViewError("Subset string '{0}' isn't valid"
                                        .format(subset))
                
            if len(experiment) == 0:
                raise util.CytoflowViewError("Subset string '{0}' returned no events"
                                        .format(subset))
                
        if self.by:
            groupby = experiment.data.groupby(self.by)
        else:
            # use a lambda expression to return a group that contains
            # all the events
            groupby = experiment.data.groupby(lambda _: True)
            
        # get the scale. estimate the scale params for the ENTIRE data set,
        # not subsets we get from groupby().  And we need to save it so that
        # the data is transformed the same way when we apply()
        for c in self.channels:
            if c in self.scale:
                self._scale[c] = util.scale_factory(self.scale[c], experiment, channel = c)
            else:
                self._scale[c] = util.scale_factory(util.get_default_scale(), experiment, channel = c)
                    
        for group, data_subset in groupby:
            if len(data_subset) == 0:
                raise util.CytoflowOpError("Group {} had no data"
                                           .format(group))
            x = data_subset.loc[:, self.channels[:]]
            for c in self.channels:
                x[c] = self._scale[c](x[c])
            
            # drop data that isn't in the scale range
            for c in self.channels:
                x = x[~(np.isnan(x[c]))]
            x = x.values
            
            self._kmeans[group] = kmeans = \
                sklearn.cluster.MiniBatchKMeans(n_clusters = self.num_clusters)
            
            kmeans.fit(x)
                                                 
         
    def apply(self, experiment):
        """
        Apply the KMeans clustering to the data
        """
 
        if experiment is None:
            raise util.CytoflowOpError("No experiment specified")
         
        # make sure name got set!
        if not self.name:
            raise util.CytoflowOpError("You have to set the gate's name "
                                  "before applying it!")
         
        if self.name in experiment.data.columns:
            raise util.CytoflowOpError("Experiment already has a column named {0}"
                                  .format(self.name))
         
        if len(self.channels) == 0:
            raise util.CytoflowOpError("Must set at least one channel")
 
        for c in self.channels:
            if c not in experiment.data:
                raise util.CytoflowOpError("Channel {0} not found in the experiment"
                                      .format(c))
                 
        for c in self.scale:
            if c not in self.channels:
                raise util.CytoflowOpError("Scale set for channel {0}, but it isn't "
                                           "in the experiment"
                                           .format(c))
        
        for b in self.by:
            if b not in experiment.data:
                raise util.CytoflowOpError("Aggregation metadata {0} not found"
                                      " in the experiment"
                                      .format(b))
            if len(experiment.data[b].unique()) > 100: #WARNING - magic number
                raise util.CytoflowOpError("More than 100 unique values found for"
                                      " aggregation metadata {0}.  Did you"
                                      " accidentally specify a data channel?"
                                      .format(b))
                 
        if self.by:
            groupby = experiment.data.groupby(self.by)
        else:
            # use a lambda expression to return a group that contains
            # all the events
            groupby = experiment.data.groupby(lambda _: True)
                 
        event_assignments = pd.Series(["{}_None".format(self.name)] * len(experiment), dtype = "object")
         
        # make the statistics       
        clusters = [x + 1 for x in range(self.num_clusters)]
          
        idx = pd.MultiIndex.from_product([experiment[x].unique() for x in self.by] + [clusters] + [self.channels], 
                                         names = list(self.by) + ["Cluster"] + ["Channel"])
        centers_stat = pd.Series(index = idx, dtype = np.dtype(object)).sort_index()
                     
        for group, data_subset in groupby:
            if len(data_subset) == 0:
                raise util.CytoflowOpError("Group {} had no data"
                                           .format(group))
            x = data_subset.loc[:, self.channels[:]]
            for c in self.channels:
                x[c] = self._scale[c](x[c])
                 
            # which values are missing?
 
            x_na = pd.Series([False] * len(x))
            for c in self.channels:
                x_na[np.isnan(x[c]).values] = True
                         
            x = x.values
            x_na = x_na.values
            group_idx = groupby.groups[group]
            
            kmeans = self._kmeans[group]
  
            predicted = np.full(len(x), -1, "int")
            predicted[~x_na] = kmeans.predict(x[~x_na])
                 
            predicted_str = pd.Series(["(none)"] * len(predicted))
            for c in range(0, self.num_clusters):
                predicted_str[predicted == c] = "{0}_{1}".format(self.name, c + 1)
            predicted_str[predicted == -1] = "{0}_None".format(self.name)
            predicted_str.index = group_idx
      
            event_assignments.iloc[group_idx] = predicted_str
            
            for c in range(self.num_clusters):
                if len(self.by) == 0:
                    g = [c + 1]
                elif hasattr(group, '__iter__'):
                    g = tuple(list(group) + [c + 1])
                else:
                    g = tuple([group] + [c + 1])
                
                for cidx1, channel1 in enumerate(self.channels):
                    g2 = tuple(list(g) + [channel1])
                    centers_stat.loc[g2] = self._scale[channel1].inverse(kmeans.cluster_centers_[c, cidx1])
         
        new_experiment = experiment.clone()          
        new_experiment.add_condition(self.name, "category", event_assignments)
        
        new_experiment.statistics[(self.name, "centers")] = pd.to_numeric(centers_stat)
 
        new_experiment.history.append(self.clone_traits(transient = lambda _: True))
        return new_experiment
    
    def default_view(self, **kwargs):
        """
        Returns a diagnostic plot of the Gaussian mixture model.
         
        Returns
        -------
            IView : an IView, call plot() to see the diagnostic plot.
        """
        channels = kwargs.pop('channels', self.channels)
        scale = kwargs.pop('scale', self.scale)
        
        for c in channels:
            if c not in self.channels:
                raise util.CytoflowViewError("Channel {} isn't in the operation's channels"
                                             .format(c))
                
        for s in scale:
            if s not in self.channels:
                raise util.CytoflowViewError("Channel {} isn't in the operation's channels"
                                             .format(s))

        for c in channels:
            if c not in scale:
                scale[c] = util.get_default_scale()
            
        if len(channels) == 0:
            raise util.CytoflowViewError("Must specify at least one channel for a default view")
        elif len(channels) == 1:
            return KMeans1DView(op = self, 
                                channel = channels[0], 
                                scale = scale[channels[0]], 
                                **kwargs)
        elif len(channels) == 2:
            return KMeans2DView(op = self, 
                                xchannel = channels[0], 
                                ychannel = channels[1],
                                xscale = scale[channels[0]],
                                yscale = scale[channels[1]], 
                                **kwargs)
        else:
            raise util.CytoflowViewError("Can't specify more than two channels for a default view")
    
@provides(IView)
class KMeans1DView(By1DView, AnnotatingView, HistogramView):
    """
    Attributes
    ----------    
    op : Instance(GaussianMixture1DOp)
        The op whose parameters we're viewing.
    """
    
    id = Constant('edu.mit.synbio.cytoflow.view.gaussianmixture1dview')
    friendly_id = Constant("1D Gaussian Mixture Diagnostic Plot")
    
    channel = Str
    scale = util.ScaleEnum
    
    def plot(self, experiment, **kwargs):
        """
        Plot the plots.
        """
                
        view, trait_name = self._strip_trait(self.op.name)
    
        super(KMeans1DView, view).plot(experiment,
                                       annotation_facet = self.op.name,
                                       annotation_trait = trait_name,
                                       annotations = self.op._kmeans,
                                       scale = self.op._scale[self.channel],
                                       **kwargs)
 
    def _annotation_plot(self, axes, xlim, ylim, xscale, yscale, annotation, annotation_facet, annotation_value, annotation_color):
                                                        
        # plot the cluster centers
            
        km = annotation
        
        cidx = self.op.channels.index(self.channel)
        for k in range(0, self.op.num_clusters):
            c = xscale.inverse(km.cluster_centers_[k][cidx])
            axes.axvline(c, linewidth=3, color='blue')                      

     
@provides(IView)
class KMeans2DView(By2DView, AnnotatingView, ScatterplotView):
    """
    Attributes
    ----------
    op : Instance(GaussianMixture2DOp)
        The op whose parameters we're viewing.        
    """
     
    id = Constant('edu.mit.synbio.cytoflow.view.gaussianmixture2dview')
    friendly_id = Constant("Gaussian Mixture Diagnostic Plot")
    
    xchannel = Str
    ychannel = Str
    
    xscale = util.ScaleEnum
    yscale = util.ScaleEnum
    
    def plot(self, experiment, **kwargs):
        """
        Plot the plots.
        """
                
        view, trait_name = self._strip_trait(self.op.name)
    
        super(KMeans2DView, view).plot(experiment,
                                       annotation_facet = self.op.name,
                                       annotation_trait = trait_name,
                                       annotations = self.op._kmeans,
                                       xscale = self.op._scale[self.xchannel],
                                       yscale = self.op._scale[self.ychannel],
                                       **kwargs)
 
    def _annotation_plot(self, axes, xlim, ylim, xscale, yscale, annotation, annotation_facet, annotation_value, annotation_color):
                                                        
        # plot the cluster centers
            
        km = annotation
        
        ix = self.op.channels.index(self.xchannel)
        iy = self.op.channels.index(self.ychannel)
        
        for k in range(self.op.num_clusters):
            x = xscale.inverse(km.cluster_centers_[k][ix])
            y = yscale.inverse(km.cluster_centers_[k][iy])
            
            axes.plot(x, y, '*', color = 'blue')
