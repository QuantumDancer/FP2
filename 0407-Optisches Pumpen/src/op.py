import os
# ========================================================================
from data import DataErrors
# make sure to add ../../lib to your project path or copy files from there
# ========================================================================
from numpy import sqrt

class OPData(DataErrors):

    CH1 = 1;
    CH2 = 2;

    def __init__(self):
        super().__init__()
        self.channel = OPData.CH1;

    @classmethod
    def fromPath(cls, path, channel):
        data = cls()
        data.path = path
        data.channel = channel
        if path:
            data.loadData()
        return data

    def loadData(self):
        d = os.getcwd()
        p = os.path.abspath(os.path.join(d, self.path))
        with open(p, 'r') as f:
            i = 0
            for row in f:
                if i > 0:
                    datapoint = list(map(float, row.strip().split('\t')))
                    x = datapoint[0]
                    y = datapoint[self.channel]
                    self.addPoint(x, y, 0, 0)
                i += 1
                
def prepareGraph(g):
    g.SetMarkerStyle(8)
    g.SetMarkerSize(0.2)
    g.SetLineColor(15)
    g.SetLineWidth(0)
    
inductorIToBVals = {1:(7.99e-4, 0.01e-4), 2:(8.14e-4, 0.01e-4), 4:(4.76e-4, 0.01e-4)}
def inductorIToB(number, current, error):
    IToB, sIToB = inductorIToBVals[number]
    B = IToB * current
    sB = B * sqrt((sIToB/IToB)**2 + (error/current)**2)
    return B, sB