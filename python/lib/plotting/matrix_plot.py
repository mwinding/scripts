
# Create a plot that is a table, a matrix, with each cell of the table colored
# and optionally containing a numeric value.
# Also show the heatmap legend on the side.
# 
# Albert Cardona 20180604, adapting code from:
# https://stackoverflow.com/questions/25071968/heatmap-with-text-in-each-cell-with-matplotlibs-pyplot
#
# Tested with: python 3.6


import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.patches import Circle
import math
from itertools import repeat
from matplotlib.colors import LinearSegmentedColormap


def show_values(pc, fmt="%.2f", hideZeros=True, **kw):
    """
      Show the numeric values of each matrix cell inside the cell.
      'pc': the value returned from ax.pcolor(...), a PolyCollection.
      'fmt': the format of the number, defaults to float with 2 decimal points. Can also be a function that returns a string.
      Additional keyword arguments are passed verbatim to the ax.text function.
    """
    if isinstance(fmt, str):
        fmt_ = fmt
        fmt = lambda x: fmt_ % x

    pc.update_scalarmappable()
    ax = pc.axes # .get_axes() is deprecated
    for p, color, value in zip(pc.get_paths(), pc.get_facecolors(), pc.get_array()):
        x, y = p.vertices[:-2, :].mean(0)
        if np.all(color[:3] > 0.5): # TODO what is this for?
            color = (0.0, 0.0, 0.0)
        else:
            color = (1.0, 1.0, 1.0)
        if hideZeros and value <= 0:
            continue
        ax.text(x, y, fmt(value), ha="center", va="center", color=color, **kw)


def show_circles(pc, radiusFn, cmap, hideZeros=True, colored=False):
    """
      Show a circle with a radius proprotional to the value at each cell.
      'pc': the value returned from ax.pcolor(...), a PolyCollection.
      'radiusFn': a function that maps a numeric value to a radius.
    """
    pc.update_scalarmappable() # TODO what is this?
    ax = pc.axes # .get_axes() is deprecated
    for p, color, value in zip(pc.get_paths(), pc.get_facecolors(), pc.get_array()):
        x, y = p.vertices[:-2, :].mean(0)
        """ # TODO What is this for?
        if np.all(color[:3] > 0.5):
            color = (0.0, 0.0, 0.0)
        else:
            color = (1.0, 1.0, 1.0)
        """
        if hideZeros and value <= 0:
            continue
        # Color could also be cmap=cmap(value) instead of black color=(0.0, 0.0, 0.0) or max like now cmap(1.0)
        color = cmap(value) if colored else (0.0, 0.0, 0.0) # black
        ax.add_patch(Circle((x, y), radiusFn(value), color=color, fill=True))


def cm2inch(*tup):
    """
        Specify figure size in centimer in matplotlib
    """
    inch = 2.54
    if type(tup[0]) == tuple:
        return tuple(i/inch for i in tup[0])
    else:
        return (i/inch for i in tup)


def matrix_plot(
        matrix,
        title,
        xlabel, ylabel,
        xticklabels, yticklabels,
        x_axis_at_top=False,
        cmap='RdBu',
        with_values=False,
        with_circles=False,
        radius_scaling=1.0,
        fmt='%.2f',
        hideZeros=True,
        value_range=(0.0, 1.0),
        cm_dimensions=(40, 20),
        shrink=0.2, # the color bar height relative to the plot
        showColorbar=True,
        fontsize=8,
        fontsizeTickLabels=8,
        show=False):
    """
     'matrix': numpy 2d-shaped array with the values to plot.
               If it is a list of lists, it will be internally copied as a numpy array.
     'title': string, optional (can be None)
     'xlabel': string, optional (can be None), the text label of the X axis.
     'ylabel': string, optional (can be None), the text label of the Y axis.
     'xticklabels: a sequence of numeric or string values to use for the X axis.
     'yticklabels': a sequence of numeric or string values to use for the Y axis.
     'x_axis_at_top': boolean, whether to place the X axis at the top rather than at the bottom.
     'cmap': string, the color gradient to use, default is red-to-blue 'RdBu'.
        See the color map reference: https://matplotlib.org/examples/color/colormaps_reference.html
     'with_values': boolean, whether to show the numeric values inside each cell or not.
     'with_circles': boolean, whether to color the cells of the matrix, or to show instead a colored circle within each cell.
     'radius_scaling': scalar, when using with_circles, the circle radius is multiplied by this scaling factor.
     'fmt': default to '%.2f', showing two decimals in floating point for every value to be shown.
     'hideZeros': boolean, whether to avoid showing text in cells where the value is zero.
     'value_range': default to a tuple (0.0, 1.0) defining the min and max values to use for the color bar. 
     'cm_dimensions': default to a tuple of (40, 20) cm.
     'shrink': defaults to 0.2 (one fifth), proportion of the color bar relative to the height of the graph.
     'fontsize': defaults to 8, for the font of the numeric values inside the matrix.
     'show': whether to show the plot prior to returning (blocks execution).
    """
    # Plot it out
    fig, ax = plt.subplots()

    # Ensure names are visible on the Y, X axis
    plt.subplots_adjust(left=0.2, top=0.8)

    cmapCells = cmap
    if with_circles:
        cmapCells = colormapConstantWhite()

    if type(matrix) == list:
        matrix = np.array(matrix)

    c = ax.pcolor(matrix, edgecolors='k', linestyle='dashed', linewidths=0.2, cmap=cmapCells, vmin=value_range[0], vmax=value_range[1])

    # put the major ticks at the middle of each cell
    ax.set_yticks(np.arange(matrix.shape[0]) + 0.5, minor=False)
    ax.set_xticks(np.arange(matrix.shape[1]) + 0.5, minor=False)

    if x_axis_at_top:
        ax.xaxis.tick_top()
    # Could use also:
    # ax.tick_params(labelbottom='off',labeltop='on')

    ax.set_xticklabels(xticklabels, minor=False, rotation='vertical', verticalalignment='bottom', fontsize=fontsizeTickLabels)
    ax.set_yticklabels(yticklabels, minor=False, fontsize=fontsizeTickLabels)

    # set title and x/y labels
    if title:
        if x_axis_at_top:
            plt.title(title, y=1.2)
        else:
            plt.title(title)
            # Note: could also use plt.text(...) for absolute positioning


    if xlabel: plt.xlabel(xlabel)
    if ylabel: plt.ylabel(ylabel)      

    # Remove last blank column
    # TODO why?
    plt.xlim( (0, matrix.shape[1]) )

    # Turn off all the ticks
    ax = plt.gca()    
    for t in ax.xaxis.get_major_ticks():
        t.tick1On = False
        t.tick2On = False
    for t in ax.yaxis.get_major_ticks():
        t.tick1On = False
        t.tick2On = False

    # Invert Y axis
    ax.invert_yaxis()

    # Add color bar
    if showColorbar:
        #plt.colorbar(c, shrink=shrink)
        # Manually, because plt.colorbar doesn't accept a cmap argument
        # which is needed when using with_circles
        cax, _ = matplotlib.colorbar.make_axes(ax, shrink=shrink, fontsize=fontsize)
        cbar = matplotlib.colorbar.ColorbarBase(cax, cmap=cmap)

    # Add circles
    if with_circles:
        # Make the area of the circle proportional to the value. """
        # Circle area = 2 * PI * pow(radius, 2)
        # radius = sqrt(area / (2 * PI))
        radiusFn = lambda value: radius_scaling * math.sqrt(value / (2 * math.pi))
        show_circles(c, radiusFn, cmap, colored=showColorbar, hideZeros=hideZeros)

    # Add text in each cell
    if with_values: show_values(c, fmt=fmt, hideZeros=hideZeros, fontsize=fontsize)

    # resize 
    fig = plt.gcf()
    fig.set_size_inches(cm2inch(cm_dimensions))

    # Ensure fonts will be exported as text rather than as paths:
    matplotlib.rcParams['svg.fonttype'] = 'none'

    # NOPE: places colorbar over the plot
    #plt.tight_layout()

    if show:
        plt.show()

    return fig, ax, c


def colormapWhiteToGreenToDarkGreen():
    """
    From 0 to 0.5 white to pure green,
    From 0.5 to 1.0 pure green to dark green.
    """
    half1 = list((r/255.0, g/255.0, b/255.0) for r, g, b in zip(range(255, -1, -2), repeat(255, 128), range(255, -1, -2)))
    half2 = list((r/255.0, g/255.0, b/255.0) for r, g, b in zip(repeat(0, 128), range(255, 128, -1), repeat(0, 128)))
    mixed_greens = LinearSegmentedColormap.from_list(
            'whiteToGreenToDarkGreen',
            half1 + half2)
    return mixed_greens


def colormapConstantWhite():
    """ Always white, no matter what value. """
    return LinearSegmentedColormap.from_list("ConstantWhite", list(repeat((1.0, 1.0, 1.0), 256)))


def test():
    x_axis_size = 19
    y_axis_size = 10
    title = "ROC's AUC"
    xlabel = "Timeshift"
    ylabel = "Scales"
    data = np.random.rand(y_axis_size,x_axis_size)
    xticklabels = range(1, x_axis_size+1) # could be text
    yticklabels = range(1, y_axis_size+1) # could be text   
    matrix_plot(data, title, xlabel, ylabel, xticklabels, yticklabels, x_axis_at_top=True, with_values=False)
    #plt.savefig('image_output.png', dpi=300, format='png', bbox_inches='tight') # use format='svg' or 'pdf' for vectorial pictures
    plt.show()

