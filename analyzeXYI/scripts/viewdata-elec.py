# -*- coding: utf-8 -*-
"""
Created on Sat Jul 16 17:07:23 2022

@author: darro
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from mpl_toolkits.axes_grid1 import make_axes_locatable
from sklearn.cluster import KMeans
import init

# The default data class
# Contains data from the XY stage and the electrometer
class load_data:
    def __init__(self, loc, fname):
        self.XY = np.genfromtxt(os.path.join(loc,fname + 'XY.csv'), delimiter = ',', comments='#', names = True, skip_header=1)
        self.IV = np.genfromtxt(os.path.join(loc,fname + 'IV.csv'), delimiter = ',', comments='#', names = True, skip_header=0)

# Main loop for aligning and analysing the data
# Do all of the analysis tasks necessary for finding the sensor
def main():
    timecorr()
    parsescan()
    rastersnake()
    cluster()   
        
# Correct for the offset between electrometer time and unix time  
# The parameter dt can be used as a fitting paramter
# The correct value of dt will 'focus' the plots from lightmap and histplot
def timecorr():
    t0 = 1659771983.4903615 
    if t0 == 0:
        t0 = data.XY['time'][0]
        dt = -13
    else:
        dt = -4
    t = t0 + dt
    data.IV['CH1_Time'] = data.IV['CH1_Time']+t
  
# Reorganize data into ordered structures
# This function makes assumptions about the structure of the input data
def parsescan():
    settle = 0 # number of indices to trim while electrometer is settling
    data.coordinates = []
    for i in range(int(len(data.XY)/2)):
        data.coordinates.append([data.XY['xpos'][2*i],data.XY['ypos'][2*i],data.XY['time'][2*i],data.XY['time'][2*i+1]])
    #data.coordinates.append([data.XY['xpos'][-1],data.XY['ypos'][-1],data.XY['time'][-1],data.XY['time'][-1]+param[6]])
    #print(data.coordinates)
    data.XYIr = []
    data.XYI = []
    data.X, data.Y, data.I = [],[],[]
    f, g = open(os.path.join(PROC,bname+'XYI_rich.csv'),'w+'), open(os.path.join(PROC,bname+'XYI.csv'),'w+')
    f.write('X,Y,I');g.write('X,Y,I,Ierr')
    data.index = []
    for row in data.coordinates:
        l = np.where(data.IV['CH1_Time'] >= row[2])[0][0]+settle
        m = np.where(data.IV['CH1_Time'] <= row[3])[0][-1]-settle
        data.index.append([l,m])
        for i in range(l,m):
            I = data.IV['CH1_Current'][i]
            data.XYIr.append([row[0],row[1],I])
            f.write('\n%s,%s,%s'%(row[0],row[1],I))
        Iavg = np.average(data.IV['CH1_Current'][l:m])
        Ierr = np.std(data.IV['CH1_Current'][l:m])/np.sqrt(len(data.IV['CH1_Current'][l:m]))
        #if Iavg != Iavg: # Check for missing data
        #    print(data.IV['CH1_Current'][l:m])
        #    print(l,m)
        #    print(row[2],row[3])
        data.XYI.append([row[0],row[1],Iavg,Ierr])
        data.X.append(row[0])
        data.Y.append(row[1])
        data.I.append(Iavg)
        g.write('\n%s,%s,%s,%s'%(row[0],row[1],Iavg,Ierr))
    data.X = np.asarray(data.X)
    data.Y = np.asarray(data.Y)
    data.I = np.asarray(data.I)
    f.close();g.close()
    data.Xr, data.Yr, data.Ir = [],[],[]
    for row in data.XYIr:
        data.Xr.append(row[0])
        data.Yr.append(row[1])
        data.Ir.append(row[2])

# Convert the shape of the data from bidirectional to unidirectional        
def rastersnake():
    X = np.unique(data.X)
    Y = np.unique(data.Y)
    data.Xproc, data.Yproc, data.Iproc, data.Ieproc = [],[],[],[]
    for x in X:
        for y in Y:
            for i in range(len(data.XYI)):
                if x == data.XYI[i][0]:
                    if y == data.XYI[i][1]:
                        data.Xproc.append(data.XYI[i][0])
                        data.Yproc.append(data.XYI[i][1])
                        data.Iproc.append(data.XYI[i][2])
                        data.Ieproc.append(data.XYI[i][3])
    data.Xproc = np.asarray(data.Xproc)
    data.Yproc = np.asarray(data.Yproc)
    data.Iproc = np.asarray(data.Iproc)
    data.Ieproc = np.asarray(data.Iproc)
    data.Iproc = np.nan_to_num(data.Iproc,nan=0) # Replace missing data with 0

# Clump the data and set thresholds
def cluster():           
    # Determine which K-Means cluster each point belongs to
    cluster_id = KMeans(10).fit_predict(data.Iproc.reshape(-1, 1))
    # Determine densities by cluster assignment and plot
    figure, axis = plt.subplots(dpi=200)
    bins = np.linspace(data.Iproc.min(), data.Iproc.max(), 40)
    data.Kmean, data.Kstd = [],[]
    axis.set_xlabel('Current [A]')
    axis.set_ylabel('Counts')
    # Average the clusters
    for ii in np.unique(cluster_id):
        subset = data.Iproc[cluster_id==ii]
        axis.hist(subset, bins=bins, alpha=0.5, label=f"Cluster {ii}")
        data.Kmean.append(np.mean(subset))
        data.Kstd.append(np.std(subset))
    # Find thresholds relative to the clusters
    data.Imax = data.Kmean[np.where(data.Kmean == max(data.Kmean))[0][0]]
    data.Imin = data.Kmean[np.where(data.Kmean == min(data.Kmean))[0][0]]
    data.Ihalf = (data.Imax - data.Imin)/2+data.Imin
    data.Ie2 = (data.Imax - data.Imin)/np.exp(2)+data.Imin
    #data.Imaxx = np.max(data.Iproc)
    data.Icluster = [data.Imin,data.Ihalf,data.Ie2]
    # Plot the thresholds
    for th in data.Icluster:
        axis.axvline(th)
    axis.legend()
    
# Find the centroid of the X and Y data above some photosensor current threshold
def findsensor(thresh):
    data.Xtemp, data.Ytemp, data.Itemp = [],[],[]
    for i in range(len(data.Iproc)):
        if data.Iproc[i] >= thresh:
            data.Xtemp.append(data.Xproc[i])
            data.Ytemp.append(data.Yproc[i])
            data.Itemp.append(data.Iproc[i]) 
    data.Isum = np.sum(data.Itemp)
    data.Xmean = np.dot(data.Xtemp,data.Itemp)/data.Isum
    data.Ymean = np.dot(data.Ytemp,data.Itemp)/data.Isum
    return data.Xmean, data.Ymean

# Plots go here
# Plot 2D histograms of position and signal    
def histplot():
    figure, axis = plt.subplots(2,1,dpi=200,figsize=(12,12))  
    axis[0].hist2d(data.Xr,np.abs(data.Ir),bins=len(np.unique(data.Xr)),norm=LogNorm()) 
    axis[1].hist2d(data.Yr,np.abs(data.Ir),bins=len(np.unique(data.Yr)),norm=LogNorm()) 
    for th in data.Icluster:
        for i in range(len(findsensor(th))):
            axis[i].axvline(findsensor(th)[i])
            axis[i].axhline(th)
    for ax in axis:
        ax.set_ylabel('PD Current\n'+r'I = 10$^y$ [A]')
    axis[0].set_xlabel('X position [mm]')
    axis[1].set_xlabel('Y position [mm]')
    #figure.savefig(os.path.join(PLOTS,'%s_histplot.svg'))
    plt.show()

# Plot a 2D reconstruction of the sensor lightmap
def lightmap():
    x=np.unique(data.Xproc)
    y=np.unique(data.Yproc)
    X,Y = np.meshgrid(y,x)
    I=data.Iproc.reshape(len(x),len(y))
    figure, axis = plt.subplots(1,1,dpi=200,figsize=(5.2,4))
    im = axis.pcolormesh(Y,X,I) 
    axis.set_xlabel('X position [mm]')
    axis.set_ylabel('Y position [mm]')
    divider = make_axes_locatable(axis)
    cax = divider.append_axes('right', size='5%', pad=0.1)
    figure.colorbar(im,cax=cax,orientation='vertical',label='Current [A]')
    axis.axis('square')
    for th in data.Icluster[1:]:
        print(th)
        print(findsensor(th)[0],findsensor(th)[1])
        axis.scatter(findsensor(th)[0],findsensor(th)[1])
        axis.contour(Y,X,I,[th],colors='k')
    #figure.savefig(os.path.join(PLOTS,'%s_lightmap.svg'))
    plt.show()
        
# Plot the position and signal data as a function of time    
def plot():
    figure, axis = plt.subplots(3,1,dpi=200,figsize=(12,12))
    axis[0].plot(data.IV['CH1_Time'],data.IV['CH1_Current']*1E12)
    axis[1].plot(data.XY['time'],data.XY['xpos'])
    axis[2].plot(data.XY['time'],data.XY['ypos'])
    axis[0].set_yscale('log')
    for ax in axis:
        ax.set_xlim(data.IV['CH1_Time'][0],data.IV['CH1_Time'][-1])
    axis[0].set_ylabel('PD Current [pA]')
    axis[1].set_ylabel('X-position [mm]')
    axis[2].set_ylabel('Y-position [mm]')
    axis[2].set_xlabel('Time [s]')
    #figure.savefig(os.path.join(PLOTS,'%s_XYI.svg')) 
    plt.show()

# Debugging plots go here
# Plot the position and signal data, highlight the averaged data
def stepplot():
    figure, axis = plt.subplots(1,1,dpi=200,figsize=(12,12))
    axis.plot(data.IV['CH1_Time'],data.IV['CH1_Current']*1E12)
    #axis[1].plot(data.XY['time'],data.XY['xpos'])
    #axis[2].plot(data.XY['time'],data.XY['ypos'])
    #axis[0].set_yscale('log')

    for index in data.index:
        axis.axvspan(data.IV['CH1_Time'][index[0]],data.IV['CH1_Time'][index[1]],color='g',alpha=0.2)
        #axis.axvspan(index[2],index[3],color='g',alpha=0.2)
        #axis[1].axvspan(index[2],index[3],color='g',alpha=0.2)
        #axis[2].axvspan(index[2],index[3],color='g',alpha=0.2)

    limit = [3000,5500,0,-1]
    axis.set_xlim(data.IV['CH1_Time'][limit[0]],data.IV['CH1_Time'][limit[1]])
    axis.axvspan(data.IV['CH1_Time'][limit[0]],data.IV['CH1_Time'][limit[1]],alpha=0.2)
    axis.set_ylabel('PD Current [pA]')
    #axis[1].set_ylabel('X-position [mm]')
    #axis[2].set_ylabel('Y-position [mm]')
    axis.set_xlabel('Time [s]')
    figure.savefig(os.path.join(PLOTS,'%s_stepplot.svg'))
    plt.show()

# Plot the time each measurement is made, useful for finding range issues with instrument
def checkgap(tvals):
    figure, axis = plt.subplots(1,1,dpi=200)
    for tval in tvals:
        data.plot(tval,data.IV['CH1_Time'][tval],'ro')
    data.set_xlabel('Measurement')
    data.set_ylabel('Time [s]')    
    
def plots():
    plot()
    #stepplot()
    histplot()
    lightmap()

    
if __name__ == "__main__":
    SCRIPTS,HOME,DATA,ARCHIVE,TEMP,DEV,PROC,PLOTS,REPORTS = init.envr() # Setup the local environment
    bname = os.listdir(DEV)[0][:-6] # Find the basename for the data files
    data = load_data(DEV,bname) # Create the data class
    main() # Align the data and do analysis
    plots() # What plots to draw



